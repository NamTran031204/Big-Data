from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# 1. Khởi tạo Spark với cấu hình S3 (MinIO) và MongoDB
# Lưu ý: Cần package mongo-spark-connector để ghi vào MongoDB
spark = SparkSession.builder \
    .appName("Olist_Silver_To_Gold_Final") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.mongodb.output.uri", "mongodb://127.0.0.1:27017/olist_gold") \
    .getOrCreate()

def write_to_gold(df, table_name):
    """Ghi dữ liệu song song vào cả Parquet (S3) và MongoDB"""
    # Ghi vào S3 (Data Lake)
    df.write.mode("overwrite").parquet(f"s3a://gold-zone/{table_name}/")
    # Ghi vào MongoDB (Serving Layer cho Dashboard)
    df.write.format("mongodb").mode("append").option("collection", table_name).save()
    print(f"✅ Đã cập nhật bảng Gold: {table_name}")

def create_gold_metrics():
    print("--- 🏆 Đang tính toán các chỉ số Business (Gold Layer) ---")
    
    # Đọc Wide Table từ Silver
    silver_df = spark.read.parquet("s3a://silver-zone/olist_unified_silver/")

    # --- UC1: Real-time Revenue Dashboard ---
    # Doanh thu theo ngày, bang và danh mục
    revenue_metrics = silver_df.groupBy("ingest_date", "s_state", "product_category_name_english") \
        .agg(
            F.sum("payment_value").alias("daily_revenue"),
            F.countDistinct("order_id").alias("order_count"),
            F.avg("payment_value").alias("avg_order_value")
        )
    write_to_gold(revenue_metrics, "gold_revenue_metrics")

    # --- UC2: Customer Behavior (RFM) ---
    # Tính Recency, Frequency, Monetary
    customer_rfm = silver_df.groupBy("customer_unique_id") \
        .agg(
            F.datediff(F.current_date(), F.max("purchase_ts")).alias("recency_days"),
            F.countDistinct("order_id").alias("frequency"),
            F.sum("payment_value").alias("monetary")
        )
    # Tạm thời gán segment đơn giản (UDF logic)
    customer_rfm = customer_rfm.withColumn("customer_segment", 
        F.when(F.col("monetary") > 500, "VIP")
         .when(F.col("frequency") > 3, "Loyal")
         .otherwise("Standard"))
    write_to_gold(customer_rfm, "gold_customer_rfm")

    # --- UC3: Product Performance ---
    # Top sản phẩm bán chạy và điểm đánh giá
    product_metrics = silver_df.groupBy("product_id", "product_category_name_english") \
        .agg(
            F.sum("payment_value").alias("total_sales"),
            F.avg("review_score").alias("avg_review_score")
        )
    # Xếp hạng sản phẩm trong từng Category (Window Function)
    window_spec = Window.partitionBy("product_category_name_english").orderBy(F.col("total_sales").desc())
    product_metrics = product_metrics.withColumn("category_rank", F.rank().over(window_spec))
    write_to_gold(product_metrics, "gold_product_metrics")

    # --- UC4: Seller Network Analysis ---
    seller_metrics = silver_df.groupBy("seller_id", "s_city") \
        .agg(
            F.sum("payment_value").alias("seller_revenue"),
            F.count("order_id").alias("seller_order_count")
        )
    write_to_gold(seller_metrics, "gold_seller_metrics")

    # --- UC5: Delivery Performance ---
    # Tỷ lệ giao hàng đúng hạn (Giả định có các cột thời gian)
    if "order_delivered_customer_date" in silver_df.columns:
        delivery_metrics = silver_df.withColumn("is_late", 
            F.when(col("order_delivered_customer_date") > col("order_estimated_delivery_date"), 1).otherwise(0)) \
            .groupBy("ingest_date", "s_state") \
            .agg(
                F.avg("is_late").alias("late_rate"),
                F.count("order_id").alias("total_delivery")
            )
        write_to_gold(delivery_metrics, "gold_delivery_metrics")

if __name__ == "__main__":
    create_gold_metrics()