import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, timestamp_seconds
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType

# 1. Fix lỗi Windows
os.environ["HADOOP_HOME"] = "C:\\hadoop" 
os.environ["PATH"] += os.pathsep + "C:\\hadoop\\bin"
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# 2. Khởi tạo SparkSession - THÊM THƯ VIỆN hadoop-aws
spark = SparkSession.builder \
    .appName("KafkaConsumer_Week2_MinIO") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8,org.apache.hadoop:hadoop-aws:3.3.4") \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .getOrCreate()

# --- CẤU HÌNH KẾT NỐI MINIO (S3A) ---
hadoop_conf = spark._jsc.hadoopConfiguration()
hadoop_conf.set("fs.s3a.endpoint", "http://localhost:9000")
hadoop_conf.set("fs.s3a.access.key", "minioadmin")
hadoop_conf.set("fs.s3a.secret.key", "minioadmin123")
hadoop_conf.set("fs.s3a.path.style.access", "true")
hadoop_conf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
hadoop_conf.set("fs.s3a.connection.ssl.enabled", "false") # MinIO chạy local không cần SSL

spark.sparkContext.setLogLevel("WARN")

# 3. Định nghĩa cấu trúc dữ liệu
schema = StructType() \
    .add("order_id", StringType()) \
    .add("user_id", IntegerType()) \
    .add("amount", DoubleType()) \
    .add("timestamp", DoubleType())

print("🚀 Đang kết nối Spark với Kafka và MinIO...")

# 4. Đọc luồng dữ liệu từ Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "orders_topic") \
    .option("startingOffsets", "earliest") \
    .load()

# 5. Xử lý dữ liệu
parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", timestamp_seconds(col("timestamp")))

# 6. Window Operations
revenue_by_window = parsed_df \
    .groupBy(window(col("event_time"), "10 seconds")) \
    .sum("amount") \
    .withColumnRenamed("sum(amount)", "total_revenue")

# 7. Ghi kết quả - ĐỔI ĐƯỜNG DẪN SANG S3A
query = revenue_by_window.writeStream \
    .outputMode("complete") \
    .format("console") \
    .option("truncate", "false") \
    .option("checkpointLocation", "s3a://checkpoint/spark_job") \
    .start()

print("✅ Hệ thống đang chạy. Kiểm tra Bucket 'checkpoint' trên MinIO để thấy dữ liệu!")
query.awaitTermination()