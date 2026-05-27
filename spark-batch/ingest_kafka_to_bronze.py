from pyspark.sql import SparkSession
import pyspark.sql.functions as F

spark = SparkSession.builder \
    .appName("Olist_Kafka_To_Bronze") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
            "org.apache.hadoop:hadoop-aws:3.3.6,"
            "org.postgresql:postgresql:42.7.3") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123456") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

def ingest_kafka():
    print("--- Reading from Kafka Topic: orders_topic ---")
    
    # Đọc dữ liệu từ Kafka (Batch mode)
    df_kafka = spark.read.format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "orders_topic") \
        .option("startingOffsets", "earliest") \
        .load()

    # Chuyển đổi Value từ Binary sang String và thêm timestamp
    df_bronze = df_kafka.selectExpr("CAST(value AS STRING) as json_data", "timestamp as kafka_timestamp")
    
    # Ghi vào Bronze Layer
    # Dùng checkpoint để Spark nhớ vị trí đã đọc
    df_bronze.write.mode("append") \
        .option("checkpointLocation", "s3a://olist-bronze/_checkpoints/kafka_orders") \
        .parquet("s3a://olist-bronze/kafka_orders/")
    
    print(" Ingested Kafka data to Bronze!")

if __name__ == "__main__":
    ingest_kafka()