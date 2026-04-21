from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, timestamp_seconds
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType

# 1. Khởi tạo SparkSession với cấu hình để kết nối Kafka
spark = SparkSession.builder \
    .appName("BTL_SparkStreaming") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8") \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .getOrCreate()

# Giảm bớt log cảnh báo
spark.sparkContext.setLogLevel("WARN")

# 2. Định nghĩa cấu trúc dữ liệu
schema = StructType() \
    .add("order_id", StringType()) \
    .add("user_id", IntegerType()) \
    .add("amount", DoubleType()) \
    .add("timestamp", DoubleType())

print("⏳ Đang kết nối Spark với Kafka...")

# 3. Đọc luồng dữ liệu từ Kafka 
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "orders_topic") \
    .load()

# 4. Xử lý dữ liệu (Chuyển Byte thành JSON -> Trích xuất cột -> Đổi thời gian)
parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", timestamp_seconds(col("timestamp")))

# 5. WINDOW OPERATIONS 
# Gom các đơn hàng vào các khung thời gian (window) mỗi 10 giây để tính TỔNG DOANH THU
revenue_by_window = parsed_df \
    .groupBy(window(col("event_time"), "10 seconds")) \
    .sum("amount") \
    .withColumnRenamed("sum(amount)", "total_revenue")

# 6. In kết quả ra màn hình
query = revenue_by_window.writeStream \
    .outputMode("complete") \
    .format("console") \
    .option("truncate", "false") \
    .start()

query.awaitTermination()