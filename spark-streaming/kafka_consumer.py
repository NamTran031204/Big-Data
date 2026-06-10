"""
Speed layer — User-behavior streaming consumer.
"""
import os
import sys

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    from_json, col, window, to_timestamp, count,
    when, lit, sum as _sum, max as _max, expr,
)
from pyspark.sql.types import StructType, StringType, LongType

import psycopg2

# ── Cấu hình từ ENV ────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka:9094")
PG_HOST         = os.environ.get("PG_HOST", "postgres")
PG_PORT         = int(os.environ.get("PG_PORT", "5432"))
PG_URL          = os.environ.get("PG_URL", "jdbc:postgresql://postgres:5432/olist")
PG_USER         = os.environ.get("PG_USER", "postgres")
PG_PASSWORD     = os.environ.get("PG_PASSWORD", "postgres")
CHECKPOINT      = os.environ.get("CHECKPOINT", "/tmp/ckpt_user_behavior")
DEBUG_CONSOLE   = os.environ.get("DEBUG_CONSOLE", "0") == "1"

# Chạy trên host Windows cần PYSPARK python + driver host loopback.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

_builder = (
    SparkSession.builder
    .appName("UserBehavior_Consumer")
    .config("spark.sql.session.timeZone", "Asia/Ho_Chi_Minh")
)

# Khi chạy local (host)
if os.environ.get("LOCAL_RUN", "0") == "1":
    _builder = (
        _builder
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
                "org.postgresql:postgresql:42.7.3")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
    )

spark = _builder.getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# ── Schema khớp với UserBehaviorEvent ──
user_behavior_schema = StructType() \
    .add("eventId",     StringType()) \
    .add("eventType",   StringType()) \
    .add("eventTime",   StringType()) \
    .add("userId",      StringType()) \
    .add("sessionId",   StringType()) \
    .add("productId",   StringType()) \
    .add("sellerId",    StringType()) \
    .add("category",    StringType()) \
    .add("dwellTimeMs", LongType())   \
    .add("searchTerm",  StringType())

# ── Đọc raw từ Kafka ─────────────────────────────────────────────────────────────
raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
    .option("subscribe", "user_behavior_events") \
    .option("startingOffsets", "latest") \
    .load()

print(f"Du lieu kafka {raw_df}", flush=True)

# ── Parse JSON ───────────────────────────────────────────────────────────────────
parsed_df = raw_df \
    .selectExpr("CAST(value AS STRING) AS raw_json", "timestamp AS kafka_ts") \
    .select(
        from_json(col("raw_json"), user_behavior_schema).alias("e"),
        col("kafka_ts"),
    ) \
    .select(
        col("e.eventId"),
        col("e.eventType"),
        col("e.eventTime"),
        col("e.userId"),
        col("e.sessionId"),
        col("e.productId"),
        col("e.sellerId"),
        col("e.category"),
        col("e.dwellTimeMs"),
        col("kafka_ts"),
    ) \
    .filter(col("userId").isNotNull() & col("category").isNotNull())

# ── eventType -> điểm ưa thích ──
score_expr = (
    when(col("eventType") == "VIEW", lit(1))
    .when(col("eventType") == "CLICK", lit(2))
    .when(col("eventType") == "ADD_TO_CART", lit(3))
    .when(col("eventType") == "PURCHASE", lit(5))
    .otherwise(lit(0))
)

# Xử lý eventTime: ISO string hoặc JSON array [y,M,d,H,m,s,ns]
ts_expr = (
    when(col("eventTime").startswith("["), 
        expr("""
            make_timestamp(
                cast(split(trim('[]' from eventTime), ',')[0] as int),
                cast(split(trim('[]' from eventTime), ',')[1] as int),
                cast(split(trim('[]' from eventTime), ',')[2] as int),
                cast(split(trim('[]' from eventTime), ',')[3] as int),
                cast(split(trim('[]' from eventTime), ',')[4] as int),
                cast(split(trim('[]' from eventTime), ',')[5] as double)
            )
        """)
    ).otherwise(to_timestamp(col("eventTime")))
)

preference_df = (
    parsed_df
    .withColumn("event_ts", ts_expr)
    .withColumn("score", score_expr)
    .withWatermark("event_ts", "2 minutes")
    .groupBy(
        window(col("event_ts"), "30 seconds"),
        col("userId"),
        col("category"),
    )
    .agg(_sum("score").alias("total_score"))
)

def write_to_postgres(batch_df: DataFrame, batch_id: int):
    print(f"\n>>> start write_to_postgres batch {batch_id}", flush=True)
    
    # Gom về (user_id, category)
    result_df = (
        batch_df
        .select(
            col("userId").alias("user_id"),
            col("category"),
            col("total_score").cast("double").alias("score"),
            col("window.end").alias("updated_at"),
        )
        .groupBy("user_id", "category")
        .agg(_sum("score").alias("score"), _max("updated_at").alias("updated_at"))
    )
    
    # Kiểm tra rỗng bằng count() thay vì rdd.isEmpty()
    if batch_df.limit(1).count() == 0:
        print(f"Batch {batch_id} is empty, skipping.", flush=True)
        return

    print(f"Batch {batch_id}: writing {result_df.count()} rows to staging...", flush=True)
    result_df.write \
        .format("jdbc") \
        .option("url", PG_URL) \
        .option("driver", "org.postgresql.Driver") \
        .option("dbtable", "user_preference_staging") \
        .option("user", PG_USER) \
        .option("password", PG_PASSWORD) \
        .mode("overwrite") \
        .save()

    print(f"Batch {batch_id}: connecting to Postgres for upsert...", flush=True)
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname="olist",
        user=PG_USER, password=PG_PASSWORD,
    )
    try:
        cur = conn.cursor()

        # 2) Cộng dồn điểm vào user_preference.
        cur.execute("""
            INSERT INTO user_preference (user_id, category, score, updated_at)
            SELECT user_id, category, score, updated_at
            FROM user_preference_staging
            ON CONFLICT (user_id, category)
            DO UPDATE SET
                score      = user_preference.score + EXCLUDED.score,
                updated_at = EXCLUDED.updated_at;
        """)

        # 3) Xoá recommendation cũ của các user vừa thay đổi.
        cur.execute("""
            DELETE FROM user_recommendation
            WHERE user_id IN (SELECT DISTINCT user_id FROM user_preference_staging);
        """)

        # 4) Tính lại top-10 sản phẩm theo category ưa thích cho user vừa đổi.
        cur.execute("""
            INSERT INTO user_recommendation
                (user_id, product_id, sequence_no, recommendation_score, updated_at)
            WITH changed_users AS (
                SELECT DISTINCT user_id FROM user_preference_staging
            ),
            ranked AS (
                SELECT
                    up.user_id,
                    p.product_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY up.user_id
                        ORDER BY up.score DESC, p.product_id
                    ) AS sequence_no,
                    up.score AS recommendation_score,
                    NOW()    AS updated_at
                FROM user_preference up
                JOIN changed_users cu ON up.user_id = cu.user_id
                JOIN products p ON p.product_category_name = up.category
            )
            SELECT user_id, product_id, sequence_no, recommendation_score, updated_at
            FROM ranked
            WHERE sequence_no <= 10;
        """)

        # 5) Dọn staging.
        cur.execute("TRUNCATE TABLE user_preference_staging;")

        conn.commit()
        cur.close()
        print(f"[user_behavior] batch {batch_id} completed.", flush=True)
    finally:
        conn.close()


# ── Query chính: foreachBatch -> Postgres ──────────────────────────────────────────
query = (
    preference_df.writeStream
    .foreachBatch(write_to_postgres)
    .outputMode("update")
    .option("checkpointLocation", CHECKPOINT)
    .start()
)

if DEBUG_CONSOLE:
    parsed_df \
        .withColumn("event_ts", ts_expr) \
        .groupBy(window(col("event_ts"), "30 seconds"), col("eventType")) \
        .agg(count("*").alias("cnt")) \
        .writeStream \
        .queryName("debug_count_by_type") \
        .outputMode("complete") \
        .format("console") \
        .option("numRows", 20) \
        .option("truncate", False) \
        .trigger(processingTime="30 seconds") \
        .start()

spark.streams.awaitAnyTermination()
