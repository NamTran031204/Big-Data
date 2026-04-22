import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, timestamp_seconds
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType

# 1. Set environment variables for Hadoop and PySpark
os.environ["HADOOP_HOME"] = "C:\\hadoop" 
os.environ["PATH"] += os.pathsep + "C:\\hadoop\\bin"
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# 2. Khởi tạo SparkSession
spark = SparkSession.builder \
    .appName("KafkaConsumer_Week2") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8") \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# 3. Định nghĩa cấu trúc dữ liệu (Schema)
schema = StructType() \
    .add("order_id", StringType()) \
    .add("user_id", IntegerType()) \
    .add("amount", DoubleType()) \
    .add("timestamp", DoubleType())

print("Đang kết nối Spark với Kafka ...")

# 4. Đọc luồng dữ liệu từ Kafka với quản lý Offset
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

# 6. Window Operations (10 seconds)
revenue_by_window = parsed_df \
    .groupBy(window(col("event_time"), "10 seconds")) \
    .sum("amount") \
    .withColumnRenamed("sum(amount)", "total_revenue")

# 7. Ghi kết quả và CẤU HÌNH CHECKPOINT (Task 3 tuần 2)
query = revenue_by_window.writeStream \
    .outputMode("complete") \
    .format("console") \
    .option("truncate", "false") \
    .option("checkpointLocation", "C:/temp/checkpoint_week2") \
    .start()

print("✅ Hệ thống đang chạy. Đang đợi dữ liệu từ Producer...")
query.awaitTermination()