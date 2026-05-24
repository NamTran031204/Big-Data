from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_timestamp, broadcast
from schemas import TABLE_SCHEMAS

# 1. Khởi tạo Spark
spark = SparkSession.builder \
    .appName("Olist_Bronze_To_Silver_Final") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123456") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

def read_bronze_parquet(table_name, schema, keep_ingest_date=False):
    """
    keep_ingest_date: Nếu là False, sẽ xóa cột này để tránh lỗi trùng tên khi join
    """
    path = f"s3a://bronze-zone/{table_name}/"
    print(f"--- 📖 Đang đọc bảng: {table_name} ---")
    df = spark.read.schema(schema).parquet(path)
    
    if not keep_ingest_date:
        return df.drop("ingest_date")
    return df
    """Đọc dữ liệu Parquet từ Bronze (Tự động nhận diện phân vùng ingest_date)"""
    path = f"s3a://bronze-zone/{table_name}/"
    print(f"--- 📖 Đang đọc bảng: {table_name} ---")
    # Sử dụng .parquet() vì thực tế file trong MinIO là parquet
    return spark.read.schema(schema).parquet(path)

def process_unified_silver():
    # Chỉ giữ ingest_date ở bảng orders
    orders = read_bronze_parquet("orders", TABLE_SCHEMAS["orders"], keep_ingest_date=True).dropDuplicates(["order_id"])
    
    # Các bảng còn lại đều bỏ ingest_date đi
    items = read_bronze_parquet("order_items", TABLE_SCHEMAS["order_items"]).dropDuplicates(["order_id", "order_item_id"])
    payments = read_bronze_parquet("order_payments", TABLE_SCHEMAS["order_payments"])
    
    customers = read_bronze_parquet("customers", TABLE_SCHEMAS["customers"]) \
        .withColumnRenamed("customer_zip_code_prefix", "c_zip") \
        .withColumnRenamed("customer_city", "c_city") \
        .withColumnRenamed("customer_state", "c_state") \
        .dropDuplicates(["customer_id"])

    products = read_bronze_parquet("products", TABLE_SCHEMAS["products"]).dropDuplicates(["product_id"])
    category = read_bronze_parquet("category_translation", TABLE_SCHEMAS["category_translation"])
    reviews = read_bronze_parquet("order_reviews", TABLE_SCHEMAS["order_reviews"]).dropDuplicates(["review_id"])
    
    sellers = read_bronze_parquet("sellers", TABLE_SCHEMAS["sellers"]) \
        .withColumnRenamed("seller_zip_code_prefix", "s_zip") \
        .withColumnRenamed("seller_city", "s_city") \
        .withColumnRenamed("seller_state", "s_state") \
        .dropDuplicates(["seller_id"])

    geo = read_bronze_parquet("geolocation", TABLE_SCHEMAS["geolocation"]) \
        .dropDuplicates(["geolocation_zip_code_prefix"])

    # ... (Các bước join giữ nguyên như cũ) ...
    # 2. Đọc dữ liệu và xử lý trùng lặp (Dedup)
    orders = read_bronze_parquet("orders", TABLE_SCHEMAS["orders"]).dropDuplicates(["order_id"])
    items = read_bronze_parquet("order_items", TABLE_SCHEMAS["order_items"]).dropDuplicates(["order_id", "order_item_id"])
    payments = read_bronze_parquet("order_payments", TABLE_SCHEMAS["order_payments"])
    
    # Renamed để tránh xung đột cột địa lý
    customers = read_bronze_parquet("customers", TABLE_SCHEMAS["customers"]) \
        .withColumnRenamed("customer_zip_code_prefix", "c_zip") \
        .withColumnRenamed("customer_city", "c_city") \
        .withColumnRenamed("customer_state", "c_state") \
        .dropDuplicates(["customer_id"])

    products = read_bronze_parquet("products", TABLE_SCHEMAS["products"]).dropDuplicates(["product_id"])
    category = read_bronze_parquet("category_translation", TABLE_SCHEMAS["category_translation"])
    reviews = read_bronze_parquet("order_reviews", TABLE_SCHEMAS["order_reviews"]).dropDuplicates(["review_id"])
    
    sellers = read_bronze_parquet("sellers", TABLE_SCHEMAS["sellers"]) \
        .withColumnRenamed("seller_zip_code_prefix", "s_zip") \
        .withColumnRenamed("seller_city", "s_city") \
        .withColumnRenamed("seller_state", "s_state") \
        .dropDuplicates(["seller_id"])

    geo = read_bronze_parquet("geolocation", TABLE_SCHEMAS["geolocation"]) \
        .dropDuplicates(["geolocation_zip_code_prefix"])

    # 3. Ép kiểu dữ liệu (Clean)
    orders = orders.withColumn("purchase_ts", to_timestamp("order_purchase_timestamp"))

    # 4. Thực hiện Join (Tiêu chí: orders + items + payments + customers...)
    print("--- 🔗 Đang thực hiện Join đại hợp nhất ---")
    
    # Join Core
    silver_df = orders.join(items, "order_id", "left") \
                      .join(payments, "order_id", "left") \
                      .join(customers, "customer_id", "left")
    
    # Join Products & Category
    silver_df = silver_df.join(products, "product_id", "left") \
                         .join(category, "product_category_name", "left")
    
    # Join Reviews
    silver_df = silver_df.join(reviews, "order_id", "left")
    
    # Join Sellers & Geolocation (Join theo Zip của Seller)
    silver_df = silver_df.join(sellers, "seller_id", "left") \
                         .join(geo, col("s_zip") == col("geolocation_zip_code_prefix"), "left")

    # 5. Lưu xuống Silver Layer
    output_path = "s3a://silver-zone/olist_unified_silver/"
    silver_df.write.mode("overwrite").parquet(output_path)
    
    print(f"✅ Thành công! Dữ liệu Silver đã được lưu tại: {output_path}")
    silver_df.select("order_id", "purchase_ts", "product_category_name_english", "payment_value").show(5)

if __name__ == "__main__":
    process_unified_silver()