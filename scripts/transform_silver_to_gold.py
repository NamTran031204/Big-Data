from pyspark.sql import SparkSession
import pyspark.sql.functions as F

spark = SparkSession.builder \
    .appName("Olist_Silver_To_Gold") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

def create_gold_metrics():
    print("--- Creating Business Metrics (Gold Layer) ---")
    
    # Đọc dữ liệu sạch từ Silver (định dạng Parquet)
    orders = spark.read.parquet("s3a://silver-zone/orders/")
    
    # Ví dụ: Thống kê số lượng đơn hàng theo trạng thái
    order_status_stats = orders.groupBy("order_status") \
        .agg(F.count("order_id").alias("total_count"))

    # Ghi vào Gold Layer
    order_status_stats.write.mode("overwrite").parquet("s3a://gold-zone/order_status_report/")
    
    # Nếu muốn ghi vào MongoDB để làm Dashboard (như lỗi log trước đó gợi ý)
    # Bạn cần thêm mongo-spark-connector vào config
    print("✅ Gold Layer metrics generated!")

if __name__ == "__main__":
    create_gold_metrics()