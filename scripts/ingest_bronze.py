import os
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from schemas import TABLE_SCHEMAS 

spark = SparkSession.builder \
    .appName("Olist_Bronze_Ingestion") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "password123") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

def process_table(table_key, csv_name, partition_col=None):
    print(f"--- Processing: {table_key} ---")
    
    input_path = f"../data/external/{csv_name}"
    output_path = f"s3a://olist-bronze/{table_key}/"
    
    df = spark.read.csv(input_path, header=True, schema=TABLE_SCHEMAS.get(table_key))
    
    df = df.dropDuplicates()

    if partition_col:
        print(f"   -> Adding partition column based on: {partition_col}")
        df = df.withColumn("ingest_date", F.to_date(F.col(partition_col)))
    writer = df.write.mode("overwrite")
    
    if partition_col:
        writer = writer.partitionBy("ingest_date")
        
    writer.parquet(output_path)
    print(f" Finished: {table_key}\n")
    print(f"--- Processing: {table_key} ---")

    input_path = f"../data/external/{csv_name}"
    output_path = f"s3a://olist-bronze/{table_key}/"
    
    df = spark.read.csv(input_path, header=True, schema=TABLE_SCHEMAS.get(table_key))
    
    df = df.dropDuplicates()

    writer = df.write.mode("overwrite")
    
    if partition_col:

        df = df.withColumn("ingest_date", F.to_date(F.col(partition_col)))
        writer = writer.partitionBy("ingest_date")
        
    writer.parquet(output_path)
    print(f" Finished: {table_key}\n")

if __name__ == "__main__":
    jobs = [
        ("orders", "olist_orders_dataset.csv", "order_purchase_timestamp"),
        ("order_items", "olist_order_items_dataset.csv", "shipping_limit_date"),
        ("customers", "olist_customers_dataset.csv", None),
        ("products", "olist_products_dataset.csv", None),
        ("order_payments", "olist_order_payments_dataset.csv", None),
        ("order_reviews", "olist_order_reviews_dataset.csv", "review_creation_date"),
        ("sellers", "olist_sellers_dataset.csv", None),
        ("geolocation", "olist_geolocation_dataset.csv", None),
        ("category_translation", "product_category_name_translation.csv", None)
    ]
    
    for table_key, csv_name, p_col in jobs:
        try:
            process_table(table_key, csv_name, p_col)
        except Exception as e:
            print(f" Error at {table_key}: {e}")