"""
Speed layer — User-behavior streaming consumer.

Đọc topic `user_behavior_events` (do SpringBoot FakeUserBehaviorScheduler sinh ra),
cộng dồn điểm ưa thích theo (userId, category) trên cửa sổ 30s, rồi qua foreachBatch:
  1) upsert vào user_preference  (cộng dồn điểm),
  2) tính lại user_recommendation (top-10 sản phẩm trong các category ưa thích) cho user vừa đổi.

Cấu hình qua ENV (mặc định = chạy TRONG container spark, broker INTERNAL kafka:9094):
  KAFKA_BOOTSTRAP   mặc định "kafka:9094"     (chạy trên host Windows: "localhost:9092")
  PG_HOST           mặc định "postgres"       (chạy trên host: "localhost")  -> dùng cho psycopg2
  PG_PORT           mặc định "5432"           (chạy trên host: "5433" — host map 5433->container 5432)
  PG_URL            mặc định "jdbc:postgresql://postgres:5432/olist"          -> dùng cho JDBC staging
  PG_USER/PG_PASSWORD  mặc định postgres/postgres
  CHECKPOINT        mặc định "/tmp/ckpt_user_behavior"
  DEBUG_CONSOLE     "1" để bật thêm các query in console (mặc định tắt)

Submit trong container (xem `make run-streaming`):
  spark-submit --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.postgresql:postgresql:42.7.3 \
    /opt/project/spark-streaming/kafka_consumer.py
"""
import os
import sys

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    from_json, col, window, to_timestamp, count,
    when, lit, sum as _sum, max as _max,
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
# Trong container thì các biến này thừa nhưng vô hại.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

_builder = (
    SparkSession.builder
    .appName("UserBehavior_Consumer")
    .config("spark.sql.session.timeZone", "Asia/Ho_Chi_Minh")
)
# Khi chạy local (host), packages chưa được truyền qua spark-submit -> set ở đây.
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

# ── Schema khớp với UserBehaviorEvent (Jackson camelCase, eventTime là ISO string) ──
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

# ── eventType -> điểm ưa thích (funnel: VIEW < CLICK < ADD_TO_CART < PURCHASE) ──────
score_expr = (
    when(col("eventType") == "VIEW", lit(1))
    .when(col("eventType") == "CLICK", lit(2))
    .when(col("eventType") == "ADD_TO_CART", lit(3))
    .when(col("eventType") == "PURCHASE", lit(5))
    .otherwise(lit(0))
)

preference_df = (
    parsed_df
    .withColumn("event_ts", to_timestamp(col("eventTime")))
    .withColumn("score", score_expr)
    .withWatermark("event_ts", "2 minutes")
    .groupBy(
        window(col("event_ts"), "30 seconds"),
        col("userId"),
        col("category"),
    )
    .agg(_sum("score").alias("total_score"))
)


# ════════════════════════════════════════════════════════════════════════════════
# Sink Postgres: upsert user_preference + tính lại user_recommendation (top-10).
# Logic port từ services/user_behavior/kafka_to_console.py, sửa cho schema thật
# (DB olist, bảng products / product_category_name).
# ════════════════════════════════════════════════════════════════════════════════
def write_to_postgres(batch_df: DataFrame, batch_id: int):
    # Gom về (user_id, category) trong batch, lấy mốc thời gian cuối cửa sổ.
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

    if result_df.rdd.isEmpty():
        return

    # 1) Ghi đè staging mỗi batch qua JDBC.
    result_df.write \
        .format("jdbc") \
        .option("url", PG_URL) \
        .option("driver", "org.postgresql.Driver") \
        .option("dbtable", "user_preference_staging") \
        .option("user", PG_USER) \
        .option("password", PG_PASSWORD) \
        .mode("overwrite") \
        .save()

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
        print(f"[user_behavior] batch {batch_id} đã ghi Postgres xong.")
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

# ── Query debug (tùy chọn, bật bằng DEBUG_CONSOLE=1) ────────────────────────────────
if DEBUG_CONSOLE:
    parsed_df \
        .withColumn("event_ts", to_timestamp(col("eventTime"))) \
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
