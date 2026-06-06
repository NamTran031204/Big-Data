from pyspark.sql import SparkSession
import pyspark.sql.functions as F

# ==========================================
# 1. CẤU HÌNH SPARK & KẾT NỐI MINIO
# ==========================================
spark = SparkSession.builder \
    .appName("Olist_Kafka_To_Bronze") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
            "org.apache.hadoop:hadoop-aws:3.3.4,"
            "org.postgresql:postgresql:42.7.3") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123456") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

# Giảm bớt log rác của Spark trên terminal
spark.sparkContext.setLogLevel("WARN")

# ==========================================
# 2. THÔNG SỐ HỆ THỐNG
# ==========================================
KAFKA_BOOTSTRAP = "kafka:9094" 
DEBEZIUM_PREFIX = "olist_cdc.public"
MINIO_BUCKET = "bronze-zone"

# Danh sách 9 bảng của bộ Olist
TABLES = [
    "customers", "geolocation", "sellers", "products",
    "category_translation", "orders", "order_items",
    "order_payments", "order_reviews"
]

def ingest_all_topics():
    print(f"🚀 Bắt đầu hút dữ liệu từ Kafka đưa lên MinIO (Bucket: {MINIO_BUCKET})...")
    
    for table in TABLES:
        topic_name = f"{DEBEZIUM_PREFIX}.{table}"
        output_path = f"s3a://{MINIO_BUCKET}/{table}/"
        checkpoint_path = f"s3a://{MINIO_BUCKET}/_checkpoints/{table}"
        
        print(f"\n--- ⏳ Đang xử lý Topic: {topic_name} ---")
        
        try:
            # 1. Đọc dữ liệu từ Kafka
            df_kafka = spark.read.format("kafka") \
                .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
                .option("subscribe", topic_name) \
                .option("startingOffsets", "earliest") \
                .load()

            # 2. Extract dữ liệu thô (Giữ nguyên cấu trúc JSON của Debezium cho lớp Bronze)
            df_bronze = df_kafka.selectExpr(
                "CAST(key AS STRING) as kafka_key",
                "CAST(value AS STRING) as json_data", 
                "topic",
                "partition",
                "offset",
                "timestamp as kafka_timestamp"
            )
            
            # 3. Ghi vào MinIO định dạng Parquet (Sử dụng Checkpoint để không bị đọc trùng lặp)
            df_bronze.write.mode("append") \
                .option("checkpointLocation", checkpoint_path) \
                .parquet(output_path)
                
            print(f"✅ Đã ghi dữ liệu thành công vào: {output_path}")
            
        except Exception as e:
            print(f"⚠️ Bỏ qua {topic_name} (Có thể do topic trống). Chi tiết lỗi: {e}")

if __name__ == "__main__":
    ingest_all_topics()
    print("\n🎉 HOÀN TẤT QUÁ TRÌNH INGEST BRONZE LAYER!")
    spark.stop()