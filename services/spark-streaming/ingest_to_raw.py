import os
import sys

os.environ['SPARK_HOME'] = r"C:\spark"
sys.path.append(r"C:\spark\python")
sys.path.append(r"C:\spark\python\lib\py4j-0.10.9.7-src.zip")

from pyspark.sql import SparkSession


# Khởi tạo Spark Session Native
spark = SparkSession.builder \
    .appName("Olist_Initial_Ingestion") \
    .config("spark.sql.parquet.compression.codec", "snappy") \
    .getOrCreate()

# Đường dẫn 
input_path = "data/external/olist_orders_dataset.csv"
output_path = "data/raw/orders_parquet"

def ingest_csv_to_parquet():
    if not os.path.exists(input_path):
        print(f" Không tìm thấy file CSV tại: {input_path}")
        return

    print("Reading CSV with Spark...")
    # Đọc CSV 
    df = spark.read.csv(input_path, header=True, inferSchema=True)

    print(f" Đang chuyển đổi {df.count()} dòng sang định dạng Parquet...")
    
    # Lưu vào lớp Raw (Bronze)
    df.write.mode("overwrite").parquet(output_path)
    
    print(f" Thành công! Dữ liệu thô đã nằm tại: {output_path}")

if __name__ == "__main__":
    ingest_csv_to_parquet()
    spark.stop()