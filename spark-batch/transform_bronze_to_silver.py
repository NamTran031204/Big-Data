"""
Bronze -> Silver: đọc dữ liệu CDC (đã unwrap) từ MinIO bronze-zone, làm sạch,
khử trùng theo CDC (lấy bản ghi mới nhất, bỏ bản đã xoá), join thành 1 bảng
hợp nhất grain = order_item, ghi xuống silver-zone.

Nguồn bronze do Confluent S3 Sink ghi (xem init/register-s3-sink.sh):
    s3a://bronze-zone/cdc/olist_cdc.public.<table>/partition=0/*.parquet
Các cột đã phẳng (ExtractNewRecordState). Cột phụ Debezium: __op, __ts_ms,
__deleted. Số thực (price/payment_value/freight) là DOUBLE (decimal.handling=double).
Cột thời gian là epoch microseconds (io.debezium.time.MicroTimestamp) -> đổi sang
timestamp bằng timestamp_micros().

Lưu ý grain & tránh nhân dòng:
- order_items là 1:N theo order -> chọn làm grain chính.
- order_payments là 1:M theo order -> GỘP về 1 dòng/đơn (tổng tiền + loại thanh
  toán chủ đạo) TRƯỚC khi join để không nhân dòng item.
- reviews gộp về 1 review mới nhất/đơn.
=> doanh thu chính xác dùng (price + freight_value) ở grain item.
"""

import os
import sys

# PYTHONPATH=/opt/project KHÔNG chứa thư mục spark-batch -> thêm dir của script này
# vào sys.path để import được module checkpoint cạnh bên.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

from checkpoint import read_watermark, write_watermark

# ==========================================================
# Spark session + cấu hình MinIO (endpoint nội bộ container)
# ==========================================================
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123456")

spark = (
    SparkSession.builder.appName("Olist_Bronze_To_Silver")
    .config(
        "spark.jars.packages",
        "org.apache.hadoop:hadoop-aws:3.3.4,"
        "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    )
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

BRONZE_BASE = "s3a://bronze-zone/cdc/olist_cdc.public"
SILVER_OUT = "s3a://silver-zone/olist_unified_silver/"
# Ghi tạm khi merge incremental (tránh đọc-ghi cùng SILVER_OUT trong 1 lệnh)
SILVER_TMP = "s3a://silver-zone/_olist_unified_silver_tmp/"
# Watermark incremental: max(__ts_ms) đã xử lý thành công
SILVER_CKPT = "s3a://checkpoint/silver_watermark"


# ==========================================================
# Helpers
# ==========================================================
def read_bronze(table):
    """Đọc toàn bộ parquet (mọi partition) của 1 bảng CDC."""
    path = f"{BRONZE_BASE}.{table}/"
    print(f"--- 📖 Đọc bronze: {table}")
    return (
        spark.read.option("recursiveFileLookup", "true").parquet(path)
    )


def dedup_cdc(df, keys):
    """Lấy bản ghi MỚI NHẤT theo khoá (CDC) và loại bản đã xoá."""
    cols = df.columns
    if "__deleted" in cols:
        df = df.filter((F.col("__deleted").isNull()) | (F.col("__deleted") != "true"))
    if "__ts_ms" in cols:
        w = Window.partitionBy(*keys).orderBy(F.col("__ts_ms").desc_nulls_last())
        df = df.withColumn("__rn", F.row_number().over(w)).filter(F.col("__rn") == 1).drop("__rn")
    else:
        df = df.dropDuplicates(keys)
    # bỏ cột phụ Debezium
    return df.drop("__op", "__ts_ms", "__deleted")


def micros_to_ts(df, name):
    """Đổi cột epoch-microseconds (bigint) sang timestamp; nếu đã là chuỗi thì to_timestamp."""
    if name not in df.columns:
        return df
    dtype = dict(df.dtypes).get(name)
    if dtype in ("bigint", "long", "int"):
        return df.withColumn(name, F.expr(f"timestamp_micros({name})"))
    return df.withColumn(name, F.to_timestamp(F.col(name)))


# ==========================================================
# Incremental helpers (CDC watermark theo __ts_ms)
# ==========================================================
def _max_ts_ms(df):
    """max(__ts_ms) của 1 bronze df (None nếu không có cột hoặc không có dòng)."""
    if "__ts_ms" not in df.columns:
        return None
    r = df.agg(F.max("__ts_ms").alias("m")).first()
    return r["m"] if r is not None else None


def _changed_order_ids(df, wm):
    """distinct order_id có __ts_ms > wm; nếu wm None (first run) -> tất cả order_id."""
    if wm is not None and "__ts_ms" in df.columns:
        df = df.filter(F.col("__ts_ms") > F.lit(wm))
    return df.select("order_id").distinct()


# ==========================================================
# Build silver
# ==========================================================
def process_unified_silver():
    print("\n" + "=" * 50)
    print("[SILVER] Bronze -> Silver bắt đầu")
    print("=" * 50)

    # ---- Watermark + phát hiện đơn thay đổi (incremental theo CDC __ts_ms) ----
    wm = read_watermark(spark, SILVER_CKPT)
    incremental = wm is not None
    print(f"\nWatermark trước đó (__ts_ms): {wm}  |  incremental={incremental}")

    # đọc bronze 4 bảng fact 1 lần, cache để tái dùng (detect + build)
    orders_b = read_bronze("orders").cache()
    items_b = read_bronze("order_items").cache()
    pay_b = read_bronze("order_payments").cache()
    rev_b = read_bronze("order_reviews").cache()

    # watermark mới = max(__ts_ms) trên toàn bộ rows fact (trước khi drop cột phụ)
    ts_candidates = [
        t for t in (_max_ts_ms(orders_b), _max_ts_ms(items_b), _max_ts_ms(pay_b), _max_ts_ms(rev_b))
        if t is not None
    ]
    new_wm = max(ts_candidates) if ts_candidates else None

    # tập order_id thay đổi (ở BẤT KỲ bảng fact nào) kể từ watermark trước
    affected = (
        _changed_order_ids(orders_b, wm)
        .unionByName(_changed_order_ids(items_b, wm))
        .unionByName(_changed_order_ids(pay_b, wm))
        .unionByName(_changed_order_ids(rev_b, wm))
        .distinct()
    ).cache()

    if incremental:
        n_aff = affected.count()
        if n_aff == 0:
            print("⏭️  Không có dữ liệu mới (CDC) kể từ watermark trước -> bỏ qua Silver")
            return
        print(f"   -> {n_aff:,} order_id thay đổi -> chỉ rebuild các đơn này")
    else:
        print("   -> First run (chưa có watermark) -> xử lý toàn bộ")

    def _fact(df_b, keys):
        """Lọc theo affected (nếu incremental) TRƯỚC rồi dedup CDC -> dedup chỉ chạy
        trên các đơn thay đổi. dedup_cdc đọc full bronze của bảng nên vẫn ra
        current-state đúng cho đơn đó, dù chỉ một bảng khác của đơn bị đổi."""
        if incremental:
            df_b = df_b.join(F.broadcast(affected), "order_id", "inner")
        return dedup_cdc(df_b, keys)

    # ---- orders (grain gốc theo đơn) ----
    print("\n[1/8] orders: dedup CDC...")
    orders = _fact(orders_b, ["order_id"])
    for c in [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        orders = micros_to_ts(orders, c)
    orders = orders.withColumnRenamed("order_purchase_timestamp", "purchase_ts")

    # ---- order_items (grain chính order_item) ----
    print("[2/8] order_items: dedup CDC...")
    items = _fact(items_b, ["order_id", "order_item_id"])
    items = micros_to_ts(items, "shipping_limit_date")
    items = items.withColumn(
        "item_revenue", F.col("price") + F.coalesce(F.col("freight_value"), F.lit(0.0))
    )

    # ---- order_payments: GỘP về 1 dòng/đơn (tránh nhân dòng) ----
    print("[3/8] order_payments: dedup + gộp 1 dòng/đơn...")
    pay = _fact(pay_b, ["order_id", "payment_sequential"])
    pay_total = pay.groupBy("order_id").agg(
        F.sum("payment_value").alias("order_payment_value"),
        F.max("payment_installments").alias("payment_installments"),
    )
    # loại thanh toán chủ đạo = loại có payment_value lớn nhất trong đơn
    w_pay = Window.partitionBy("order_id").orderBy(F.col("payment_value").desc_nulls_last())
    pay_dom = (
        pay.withColumn("__r", F.row_number().over(w_pay))
        .filter(F.col("__r") == 1)
        .select("order_id", F.col("payment_type").alias("payment_type"))
    )
    payments = pay_total.join(pay_dom, "order_id", "left")

    # ---- reviews: 1 review mới nhất/đơn ----
    print("[4/8] order_reviews: review mới nhất/đơn...")
    reviews_raw = rev_b
    if incremental:
        reviews_raw = reviews_raw.join(F.broadcast(affected), "order_id", "inner")
    reviews_raw = micros_to_ts(reviews_raw, "review_creation_date")
    if "__deleted" in reviews_raw.columns:
        reviews_raw = reviews_raw.filter(
            (F.col("__deleted").isNull()) | (F.col("__deleted") != "true")
        )
    w_rev = Window.partitionBy("order_id").orderBy(F.col("review_creation_date").desc_nulls_last())
    reviews = (
        reviews_raw.withColumn("__r", F.row_number().over(w_rev))
        .filter(F.col("__r") == 1)
        .select("order_id", "review_id", "review_score")
    )

    # ---- Dimensions: LUÔN đọc full + broadcast (cần cho join đúng) ----
    print("[5/8] customers...")
    customers = (
        dedup_cdc(read_bronze("customers"), ["customer_id"])
        .withColumnRenamed("customer_zip_code_prefix", "c_zip")
        .withColumnRenamed("customer_city", "c_city")
        .withColumnRenamed("customer_state", "c_state")
    )
    print("[6/8] products + category_translation...")
    products = dedup_cdc(read_bronze("products"), ["product_id"])
    category = dedup_cdc(read_bronze("category_translation"), ["product_category_name"])
    print("[7/8] sellers + geolocation...")
    sellers = (
        dedup_cdc(read_bronze("sellers"), ["seller_id"])
        .withColumnRenamed("seller_zip_code_prefix", "s_zip")
        .withColumnRenamed("seller_city", "s_city")
        .withColumnRenamed("seller_state", "s_state")
    )
    geo = (
        read_bronze("geolocation")
        .groupBy("geolocation_zip_code_prefix")
        .agg(
            F.avg("geolocation_lat").alias("geolocation_lat"),
            F.avg("geolocation_lng").alias("geolocation_lng"),
        )
    )

    # ---- JOIN (broadcast các chiều nhỏ) ----
    print("[8/8] JOIN hợp nhất (grain = order_item)...")
    slice_df = (
        items.join(orders, "order_id", "inner")
        .join(payments, "order_id", "left")
        .join(F.broadcast(customers), "customer_id", "left")
        .join(F.broadcast(products), "product_id", "left")
        .join(F.broadcast(category), "product_category_name", "left")
        .join(reviews, "order_id", "left")
        .join(F.broadcast(sellers), "seller_id", "left")
        .join(F.broadcast(geo), F.col("s_zip") == F.col("geolocation_zip_code_prefix"), "left")
    )

    # ---- Data quality: bỏ dòng thiếu khoá cốt lõi ----
    slice_df = slice_df.filter(
        F.col("order_id").isNotNull() & F.col("purchase_ts").isNotNull()
    )

    # ---- Merge vào silver (thay thế đúng các đơn thay đổi) ----
    print(f"\nGhi silver-zone: {SILVER_OUT}")
    if incremental:
        try:
            existing = spark.read.parquet(SILVER_OUT)
            has_existing = True
        except Exception:
            has_existing = False  # silver chưa từng được tạo

        if has_existing:
            # bỏ bản cũ của các đơn thay đổi + thêm bản mới rebuild
            merged = existing.join(
                F.broadcast(affected), "order_id", "left_anti"
            ).unionByName(slice_df, allowMissingColumns=True)
            # Ghi qua TMP rồi mới overwrite SILVER_OUT (tránh đọc & ghi cùng 1 path)
            merged.write.mode("overwrite").parquet(SILVER_TMP)
            spark.read.parquet(SILVER_TMP).write.mode("overwrite").parquet(SILVER_OUT)
        else:
            slice_df.write.mode("overwrite").parquet(SILVER_OUT)
    else:
        # first run: ghi toàn bộ
        slice_df.write.mode("overwrite").parquet(SILVER_OUT)

    total = spark.read.parquet(SILVER_OUT).count()
    print(f"✅ Silver đã ghi: {SILVER_OUT} (tổng {total:,} dòng)")

    # ---- Ghi watermark SAU KHI ghi silver thành công (fail -> không tiến) ----
    if new_wm is not None:
        write_watermark(spark, SILVER_CKPT, new_wm)
        print(f"✅ Watermark Silver tiến tới __ts_ms = {new_wm}")

    spark.read.parquet(SILVER_OUT).select(
        "order_id", "purchase_ts", "product_category_name_english",
        "item_revenue", "order_payment_value", "payment_type", "review_score",
    ).show(5, truncate=False)


if __name__ == "__main__":
    process_unified_silver()
    spark.stop()
