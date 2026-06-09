from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql import DataFrame
import psycopg2


spark = (
    SparkSession.builder
    .appName("UserBehaviorStreaming")
    .config(
        "spark.sql.session.timeZone",
        "Asia/Ho_Chi_Minh"
    )
    .config(
        "spark.driver.extraJavaOptions",
        "-Duser.timezone=Asia/Ho_Chi_Minh"
    )
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"
    )
    .config(
        "spark.jars",
        r"C:\spark\jars\postgresql-42.7.7.jar"
    )
    .getOrCreate()
)

# spark.conf.set(
#     "spark.sql.session.timeZone",
#     "Asia/Ho_Chi_Minh"
# )

# print(
#     spark.sparkContext._jvm.java.util.TimeZone.getDefault().getID()
# )
#
# print(
#     spark.conf.get(
#         "spark.sql.session.timeZone"
#     )
# )

# =====================
# Kafka Source
# =====================

df = (
    spark.readStream
    .format("kafka")
    .option(
        "kafka.bootstrap.servers",
        "localhost:9092"
    )
    .option(
        "subscribe",
        "user_behavior_events"
    )
    .load()
)

# =====================
# Schema
# =====================

schema = StructType([
    StructField("eventId", StringType()),
    StructField("userId", StringType()),
    StructField("productId", StringType()),
    StructField("category", StringType()),
    StructField("behavior", StringType()),
    StructField("score", IntegerType()),
    StructField("timestamp", StringType())
])

# =====================
# Parse JSON
# =====================

json_df = (
    df.selectExpr(
        "CAST(value AS STRING)"
    )
)

parsed_df = (
    json_df.select(
        from_json(
            col("value"),
            schema
        ).alias("data")
    )
    .select("data.*")
)

# =====================
# Preference
# =====================

event_df = parsed_df.withColumn(
    "event_time",
    to_timestamp("timestamp")
)

preference_df = (
    event_df
    .groupBy(
        window(
            col("event_time"),
            "30 seconds"
        ),
        col("userId"),
        col("category")
    )
    .agg(
        sum("score")
        .alias("total_score")
    )
)

# =====================
# Write PostgreSQL
# =====================

def write_to_postgres(batch_df: DataFrame, batch_id: int):

    result_df = (
        batch_df
        .select(
            col("userId").alias("user_id"),
            col("category"),
            col("total_score").cast("double").alias("score"),
            col("window.end").alias("updated_at")
        )
        .groupBy(
            "user_id",
            "category"
        )
        .agg(
            sum("score").alias("score"),
            max("updated_at").alias("updated_at")
        )
    )

    temp_table = "user_preference_staging"

    # overwrite staging mỗi batch
    result_df.write \
        .format("jdbc") \
        .option(
            "url",
            "jdbc:postgresql://localhost:5432/postgres"
        ) \
        .option(
            "driver",
            "org.postgresql.Driver"
        ) \
        .option(
            "dbtable",
            temp_table
        ) \
        .option(
            "user",
            "postgres"
        ) \
        .option(
            "password",
            "postgres"
        ) \
        .mode("overwrite") \
        .save()

    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="postgres",
        user="postgres",
        password="postgres"
    )

    cur = conn.cursor()

    # ==========================
    # UPDATE USER PREFERENCE
    # ==========================

    cur.execute("""
        INSERT INTO user_preference
        (
            user_id,
            category,
            score,
            updated_at
        )
        SELECT
            user_id,
            category,
            score,
            updated_at
        FROM user_preference_staging
        ON CONFLICT (user_id, category)
        DO UPDATE SET
            score =
                user_preference.score +
                EXCLUDED.score,
            updated_at =
                EXCLUDED.updated_at;
    """)

    # ==========================
    # DELETE OLD RECOMMENDATION
    # CHỈ CHO USER THAY ĐỔI
    # ==========================

    cur.execute("""
        DELETE FROM user_recommendation
        WHERE user_id IN (
            SELECT DISTINCT user_id
            FROM user_preference_staging
        );
    """)

    # ==========================
    # RECOMPUTE RECOMMENDATION
    # CHỈ CHO USER THAY ĐỔI
    # ==========================

    cur.execute("""
        INSERT INTO user_recommendation
        (
            user_id,
            product_id,
            sequence_no,
            recommendation_score,
            updated_at
        )
        WITH changed_users AS (
            SELECT DISTINCT user_id
            FROM user_preference_staging
        ),
        ranked AS (
            SELECT
                up.user_id,
                p.product_id,

                ROW_NUMBER() OVER (
                    PARTITION BY up.user_id
                    ORDER BY
                        up.score DESC,
                        p.product_id
                ) AS sequence_no,

                up.score AS recommendation_score,

                NOW() AS updated_at

            FROM user_preference up

            JOIN changed_users cu
                ON up.user_id = cu.user_id

            JOIN product p
                ON p.product_category_name = up.category
        )
        SELECT
            user_id,
            product_id,
            sequence_no,
            recommendation_score,
            updated_at
        FROM ranked
        WHERE sequence_no <= 10;
    """)

    # ==========================
    # CLEAN STAGING
    # ==========================

    cur.execute("""
        TRUNCATE TABLE user_preference_staging;
    """)

    conn.commit()

    cur.close()
    conn.close()

    print(
        f"Batch {batch_id} processed successfully"
    )

preference_df.printSchema()

query = (
    preference_df.writeStream
    .foreachBatch(
        write_to_postgres
    )
    .outputMode("update")
    .start()
)

query.awaitTermination()

