from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from schemas import TABLE_SCHEMAS
from pyspark.sql.functions import col, to_timestamp
# Bổ sung cấu hình kết nối MinIO
spark = SparkSession.builder \
    .appName("Olist_Bronze_To_Silver") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

def process_to_silver():
    print("--- 📂 Processing Bronze to Silver Layer ---")
    order_schema = TABLE_SCHEMAS.get("orders")

    # Đọc dữ liệu JSONL từ Bronze
    # Spark sẽ tự động bỏ qua các dòng lỗi nếu bạn thêm mode='PERMISSIVE'
    df_raw = spark.read.schema(order_schema).json("s3a://bronze-zone/raw_data/*.jsonl")

    # Làm sạch và Ép kiểu
    df_silver = df_raw.select(
        col("order_id"),
        col("customer_id"),
        col("amount").cast("double"),
        col("order_status"),
        # Chuyển chuỗi ISO sang định dạng Timestamp chuẩn của Spark
        to_timestamp(col("order_purchase_timestamp")).alias("order_purchase_timestamp")
    ).filter(col("order_id").isNotNull()).dropDuplicates(["order_id"])

    # Lưu xuống Silver (Parquet)
    df_silver.write.mode("overwrite").parquet("s3a://silver-zone/orders_cleaned/")
    
    print(f"✅ Đã chuyển thành công {df_silver.count()} bản ghi sang Silver!")
    df_silver.show(5)

if __name__ == "__main__":
    process_to_silver()