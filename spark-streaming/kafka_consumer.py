import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, timestamp_seconds
from pyspark.sql.types import StructType, StringType, IntegerType, DoubleType

os.environ["HADOOP_HOME"] = "C:\\hadoop"
os.environ["PATH"] += os.pathsep + "C:\\hadoop\\bin"
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

# Thêm JAR: Kafka, Hadoop-AWS (MinIO), và PostgreSQL
spark = SparkSession.builder \
    .appName("KafkaConsumer_FullPipeline") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.7.2") \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .getOrCreate()

# Cấu hình S3A cho MinIO
hadoop_conf = spark._jsc.hadoopConfiguration()
hadoop_conf.set("fs.s3a.endpoint", "http://localhost:9000")
hadoop_conf.set("fs.s3a.access.key", "minioadmin")
hadoop_conf.set("fs.s3a.secret.key", "minioadmin123")
hadoop_conf.set("fs.s3a.path.style.access", "true")
hadoop_conf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
hadoop_conf.set("fs.s3a.connection.ssl.enabled", "false")

spark.sparkContext.setLogLevel("WARN")

schema = StructType() \
    .add("order_id", StringType()) \
    .add("user_id", IntegerType()) \
    .add("amount", DoubleType()) \
    .add("timestamp", DoubleType())

# Hàm ghi dữ liệu vào Postgres (Sẽ kích hoạt khi có cấu hình chính thức từ nhóm)
def write_to_postgres(batch_df, batch_id):
    # batch_df.write \
    #     .format("jdbc") \
    #     .option("url", "jdbc:postgresql://localhost:5432/bigdata_db") \
    #     .option("dbtable", "revenue_summary") \
    #     .option("user", "myuser") \
    #     .option("password", "mypassword") \
    #     .option("driver", "org.postgresql.Driver") \
    #     .mode("append") \
    #     .save()
    pass

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "orders_topic") \
    .option("startingOffsets", "earliest") \
    .load()

parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", timestamp_seconds(col("timestamp")))

revenue_by_window = parsed_df \
    .groupBy(window(col("event_time"), "10 seconds")) \
    .sum("amount") \
    .withColumnRenamed("sum(amount)", "total_revenue")

# Tạm thời xuất Console và lưu Checkpoint lên MinIO
query = revenue_by_window.writeStream \
    .outputMode("complete") \
    .foreachBatch(write_to_postgres) \
    .format("console") \
    .option("truncate", "false") \
    .option("checkpointLocation", "s3a://checkpoint/spark_job_v2") \
    .start()

query.awaitTermination()