from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from services.mongodb_connect.mongo_connector import MongoConnector

# ==============================
# Spark Session
# ==============================
spark = SparkSession.builder \
    .appName("Olist_Silver_To_Gold_Final") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123456") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

# ==============================
# MongoDB Atlas
# ==============================
MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"

mongo = MongoConnector(
    uri=MONGO_URI,
    db_name="olist_gold"
)

mongo.connect()


# ==============================
# Write Gold Function
# ==============================
def write_to_gold(df, table_name, key_fields):

    # =========================
    # Write parquet
    # =========================
    df.write.mode("overwrite").parquet(
        f"s3a://gold-zone/{table_name}/"
    )

    print(f"✅ Written parquet: {table_name}")

    # =========================
    # Batch write Mongo
    # =========================
    batch_size = 1000

    batch = []

    for row in df.toLocalIterator():

        record = row.asDict(recursive=True)

        batch.append(record)

        if len(batch) >= batch_size:

            mongo.bulk_upsert(
                collection_name=table_name,
                data_list=batch,
                key_fields=key_fields
            )

            print(f"Inserted {len(batch)} docs")

            batch = []

    # insert remaining
    if batch:

        mongo.bulk_upsert(
            collection_name=table_name,
            data_list=batch,
            key_fields=key_fields
        )

        print(f"Inserted remaining {len(batch)} docs")


# ==============================
# Create Gold Metrics
# ==============================
def create_gold_metrics():

    print("🏆 Creating Gold Layer")

    silver_df = spark.read.parquet(
        "s3a://silver-zone/olist_unified_silver/"
    )

    silver_df = silver_df.withColumn(
        "ingest_date",
        F.date_format(
            F.col("purchase_ts"),
            "yyyy-MM-dd"
        )
    )

    # silver_df.printSchema()

    # =====================================
    # UC1 - Revenue Metrics
    # =====================================
    revenue_metrics = silver_df.groupBy(
        "ingest_date",
        "s_state",
        "product_category_name_english"
    ).agg(
        F.sum("payment_value").alias("daily_revenue"),
        F.countDistinct("order_id").alias("order_count"),
        F.avg("payment_value").alias("avg_order_value")
    )

    write_to_gold(
        revenue_metrics,
        "gold_revenue_metrics",
        [
            "ingest_date",
            "s_state",
            "product_category_name_english"
        ]
    )

    # =====================================
    # UC2 - Customer RFM
    # =====================================
    customer_rfm = silver_df.groupBy(
        "customer_unique_id"
    ).agg(
        F.datediff(
            F.current_date(),
            F.max("purchase_ts")
        ).alias("recency_days"),

        F.countDistinct("order_id").alias("frequency"),

        F.sum("payment_value").alias("monetary")
    )

    customer_rfm = customer_rfm.withColumn(
        "customer_segment",
        F.when(F.col("monetary") > 500, "VIP")
         .when(F.col("frequency") > 3, "Loyal")
         .otherwise("Standard")
    )

    write_to_gold(
        customer_rfm,
        "gold_customer_rfm",
        ["customer_unique_id"]
    )

    # =====================================
    # UC3 - Product Metrics
    # =====================================
    product_metrics = silver_df.groupBy(
        "product_id",
        "product_category_name_english"
    ).agg(
        F.sum("payment_value").alias("total_sales"),
        F.avg("review_score").alias("avg_review_score")
    )

    window_spec = Window.partitionBy(
        "product_category_name_english"
    ).orderBy(
        F.col("total_sales").desc()
    )

    product_metrics = product_metrics.withColumn(
        "category_rank",
        F.rank().over(window_spec)
    )

    write_to_gold(
        product_metrics,
        "gold_product_metrics",
        ["product_id"]
    )

    # =====================================
    # UC4 - Seller Metrics
    # =====================================
    seller_metrics = silver_df.groupBy(
        "seller_id",
        "s_city"
    ).agg(
        F.sum("payment_value").alias("seller_revenue"),
        F.count("order_id").alias("seller_order_count")
    )

    write_to_gold(
        seller_metrics,
        "gold_seller_metrics",
        ["seller_id"]
    )


# ==============================
# Main
# ==============================
if __name__ == "__main__":

    create_gold_metrics()

    mongo.close()

    spark.stop()