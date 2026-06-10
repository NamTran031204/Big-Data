"""
Silver -> Gold: tính các metric theo docs/data-view/gold-data-requirment.md
(phần SQL / Window / Pivot / UDF; cột ML & GraphFrames để phase sau = null).

Ghi Gold ra 3 NƠI:
  1. MinIO  : s3a://gold-zone/<collection>/   (parquet)
  2. Mongo local : container bigdata-mongodb   (MONGO_LOCAL_URI)
  3. Mongo Atlas : nếu có env MONGO_ATLAS_URI  (rỗng -> bỏ qua)

Cấu hình lấy từ biến môi trường (truyền qua SparkSubmitOperator hoặc shell),
không hardcode secret trong code.
"""

import os
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

from services.mongodb_connect.mongo_connector import MongoConnector

# ==========================================================
# Cấu hình
# ==========================================================
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123456")

MONGO_DB = os.environ.get("MONGO_DB", "olist_gold")
MONGO_LOCAL_URI = os.environ.get(
    "MONGO_LOCAL_URI", "mongodb://admin:admin123456@bigdata-mongodb:27017/?authSource=admin"
)
MONGO_ATLAS_URI = os.environ.get("MONGO_ATLAS_URI", "").strip()

SILVER_IN = "s3a://silver-zone/olist_unified_silver/"
GOLD_BASE = "s3a://gold-zone"

spark = (
    SparkSession.builder.appName("Olist_Silver_To_Gold")
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

# ==========================================================
# Kết nối các Mongo sink khả dụng
# ==========================================================
SINKS = []
for _label, _uri in [("local", MONGO_LOCAL_URI), ("atlas", MONGO_ATLAS_URI)]:
    if not _uri:
        print(f"⏭️  Bỏ qua Mongo[{_label}] (chưa cấu hình URI)")
        continue
    try:
        _conn = MongoConnector(uri=_uri, db_name=MONGO_DB)
        _conn.connect()
        SINKS.append((_label, _conn))
        print(f"🔌 Đã kết nối Mongo[{_label}]")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  Không kết nối được Mongo[{_label}]: {e}")


def write_to_gold(df, table_name, key_fields):
    """Ghi 1 gold collection ra cả 3 nơi (MinIO parquet + các Mongo sink)."""
    n = df.count()
    print(f"\n   >>> Ghi: {table_name} ({n:,} dòng)")

    # 1) MinIO parquet
    df.write.mode("overwrite").parquet(f"{GOLD_BASE}/{table_name}/")
    print(f"   ✅ MinIO parquet: {table_name}")

    if not SINKS:
        return

    # 2+3) Mongo (gom về driver vì gold đã là aggregate nhỏ)
    rows = [r.asDict(recursive=True) for r in df.toLocalIterator()]
    for label, conn in SINKS:
        try:
            for i in range(0, len(rows), 1000):
                conn.bulk_upsert(table_name, rows[i : i + 1000], key_fields)
            print(f"   ✅ mongo[{label}] {table_name}: {len(rows):,} docs")
        except Exception as e:  # noqa: BLE001
            print(f"   !! mongo[{label}] {table_name} lỗi: {e}")


# ==========================================================
# Gold metrics
# ==========================================================
def create_gold_metrics():
    print("\n" + "=" * 50)
    print("🏆 [GOLD] Silver -> Gold bắt đầu")
    print("=" * 50)

    print("\nĐọc silver-zone...")
    silver = spark.read.parquet(SILVER_IN)
    print(f"   -> {silver.count():,} dòng silver (grain = order_item)")

    # ingest_date dạng chuỗi (an toàn cho Mongo: không dùng datetime.date) -> dùng làm KEY upsert
    silver = silver.withColumn("ingest_date", F.date_format(F.col("purchase_ts"), "yyyy-MM-dd"))
    # date dạng ISODate (datetime.datetime, BSON serialize được) -> trục thời gian cho Atlas Charts
    silver = silver.withColumn("date", F.date_trunc("day", F.col("purchase_ts")))

    # ---- DF theo grain đơn hàng (khử trùng item) cho metric mức đơn ----
    print("\nChuẩn bị orders grain (dropDuplicates order_id)...")
    orders_g = silver.dropDuplicates(["order_id"]).select(
        "order_id", "customer_unique_id", "c_state", "order_status", "purchase_ts",
        "ingest_date", "date", "order_payment_value", "payment_type", "review_score",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    )
    print(f"   -> {orders_g.count():,} đơn hàng (order grain)")

    # =====================================================
    # UC1 — REVENUE
    # =====================================================
    print("\n" + "-" * 40)
    print("[UC1] REVENUE: doanh thu theo ngày / danh mục / bang / payment")
    print("-" * 40)

    # Doanh thu theo ngày (mức đơn) + tăng trưởng (LAG) + spike flag
    print("   Tính gold_revenue_metrics (daily, LAG, spike flag)...")
    daily = orders_g.groupBy("ingest_date", "date").agg(
        F.sum("order_payment_value").alias("revenue_daily"),
        F.countDistinct("order_id").alias("order_count"),
        F.avg("order_payment_value").alias("avg_order_value"),
    )
    w_day = Window.orderBy("ingest_date")
    daily = daily.withColumn("prev_rev", F.lag("revenue_daily").over(w_day))
    daily = daily.withColumn(
        "revenue_growth_rate",
        F.when(
            (F.col("prev_rev").isNotNull()) & (F.col("prev_rev") != 0),
            F.round((F.col("revenue_daily") - F.col("prev_rev")) / F.col("prev_rev") * 100, 2),
        ).otherwise(None),
    )
    stats = daily.select(
        F.avg("revenue_daily").alias("m"), F.stddev("revenue_daily").alias("s")
    ).collect()[0]
    thr = (stats["m"] or 0) + 2 * (stats["s"] or 0)
    daily = daily.withColumn(
        "revenue_spike_flag", (F.col("revenue_daily") > F.lit(thr)).cast("int")
    ).drop("prev_rev")
    # cột ML/streaming chưa làm
    daily = daily.withColumn("revenue_5min", F.lit(None).cast("double")) \
                 .withColumn("revenue_hourly", F.lit(None).cast("double"))
    write_to_gold(daily, "gold_revenue_metrics", ["ingest_date"])

    # Breakdown: theo danh mục (grain item: item_revenue), theo bang, theo payment_type
    # Đều thêm ingest_date + date -> lọc được theo date range trên Atlas Charts.
    print("   Tính breakdown: by_category / by_state / by_payment_type...")
    by_cat = silver.groupBy("ingest_date", "date", "product_category_name_english").agg(
        F.sum("item_revenue").alias("revenue"),
        F.countDistinct("order_id").alias("order_count"),
    )
    write_to_gold(by_cat, "gold_revenue_by_category", ["ingest_date", "product_category_name_english"])

    by_state = orders_g.groupBy("ingest_date", "date", "c_state").agg(
        F.sum("order_payment_value").alias("revenue"),
        F.countDistinct("order_id").alias("order_count"),
    )
    write_to_gold(by_state, "gold_revenue_by_state", ["ingest_date", "c_state"])

    by_pay = orders_g.groupBy("ingest_date", "date", "payment_type").agg(
        F.sum("order_payment_value").alias("revenue"),
        F.countDistinct("order_id").alias("order_count"),
    )
    write_to_gold(by_pay, "gold_revenue_by_payment_type", ["ingest_date", "payment_type"])

    # =====================================================
    # UC2 — CUSTOMER RFM
    # =====================================================
    print("\n" + "-" * 40)
    print("[UC2] CUSTOMER RFM: phân khúc khách hàng + acquisition")
    print("-" * 40)

    print("   Tính RFM (recency / frequency / monetary + NTILE scoring)...")
    cust = orders_g.filter(F.col("customer_unique_id").isNotNull())
    snapshot = cust.agg(F.max("purchase_ts").alias("snap")).collect()[0]["snap"]
    rfm = cust.groupBy("customer_unique_id").agg(
        F.datediff(F.lit(snapshot), F.max("purchase_ts")).alias("recency_days"),
        F.countDistinct("order_id").alias("frequency"),
        F.sum("order_payment_value").alias("monetary"),
    )
    # điểm RFM 1..5 bằng NTILE (recency: gần hơn -> điểm cao hơn)
    rfm = rfm.withColumn("r_score", 6 - F.ntile(5).over(Window.orderBy(F.col("recency_days").asc())))
    rfm = rfm.withColumn("f_score", F.ntile(5).over(Window.orderBy(F.col("frequency").asc())))
    rfm = rfm.withColumn("m_score", F.ntile(5).over(Window.orderBy(F.col("monetary").asc())))
    rfm = rfm.withColumn("rfm_score", F.col("r_score") + F.col("f_score") + F.col("m_score"))
    rfm = rfm.withColumn(
        "customer_segment",
        F.when((F.col("r_score") >= 4) & (F.col("f_score") >= 4), "Champion")
         .when((F.col("f_score") >= 4), "Loyal")
         .when((F.col("r_score") <= 2) & (F.col("f_score") <= 2), "Lost")
         .when((F.col("r_score") <= 2), "At Risk")
         .otherwise("Standard"),
    )
    # cột ML chưa làm
    rfm = rfm.withColumn("churn_probability", F.lit(None).cast("double")) \
             .withColumn("clv_predicted", F.lit(None).cast("double"))
    write_to_gold(rfm, "gold_customer_rfm", ["customer_unique_id"])

    # Khách mới / quay lại theo ngày (first-purchase detection)
    print("   Tính gold_customer_acquisition (new vs returning per day)...")
    w_cust = Window.partitionBy("customer_unique_id").orderBy("purchase_ts")
    acq = cust.withColumn("__order_seq", F.row_number().over(w_cust))
    acq = acq.withColumn("is_new", (F.col("__order_seq") == 1).cast("int"))
    acq_daily = acq.groupBy("ingest_date", "date").agg(
        F.sum("is_new").alias("new_customer_count"),
        F.sum((F.col("is_new") == 0).cast("int")).alias("returning_customer_count"),
    )
    write_to_gold(acq_daily, "gold_customer_acquisition", ["ingest_date"])

    # =====================================================
    # UC3 — PRODUCT
    # =====================================================
    print("\n" + "-" * 40)
    print("[UC3] PRODUCT: metrics sản phẩm / top products / category rank")
    print("-" * 40)

    print("   Tính gold_product_metrics (sales, review, return rate, category rank)...")
    # Thêm ingest_date + date -> lọc theo date range. Lưu kèm thành phần cộng được
    # (review_score_sum/review_count cho avg, canceled_orders/order_count cho return rate).
    prod = silver.groupBy("ingest_date", "date", "product_id", "product_category_name_english").agg(
        F.sum("item_revenue").alias("total_sales"),
        F.avg("review_score").alias("avg_review_score"),
        F.sum("review_score").alias("review_score_sum"),
        F.count("review_score").alias("review_count"),
        F.countDistinct("order_id").alias("order_count"),
        F.countDistinct(
            F.when(F.col("order_status") == "canceled", F.col("order_id"))
        ).alias("canceled_orders"),
    )
    prod = prod.withColumn(
        "product_return_rate",
        F.round(F.col("canceled_orders") / F.col("order_count"), 4),
    )
    prod = prod.withColumn(
        "category_rank",
        F.rank().over(
            Window.partitionBy("ingest_date", "product_category_name_english")
            .orderBy(F.col("total_sales").desc())
        ),
    )
    # cột ML/NLP chưa làm
    prod = prod.withColumn("review_sentiment", F.lit(None).cast("double")) \
               .withColumn("recommended_products", F.lit(None).cast("string"))
    write_to_gold(prod, "gold_product_metrics", ["ingest_date", "product_id"])

    # Top 10 sản phẩm theo ngày (Window RANK)
    print("   Tính gold_top_products_daily (RANK <= 10 per day)...")
    daily_prod = silver.groupBy("ingest_date", "date", "product_id").agg(
        F.sum("item_revenue").alias("daily_sales")
    )
    daily_prod = daily_prod.withColumn(
        "rank",
        F.rank().over(Window.partitionBy("ingest_date").orderBy(F.col("daily_sales").desc())),
    ).filter(F.col("rank") <= 10)
    write_to_gold(daily_prod, "gold_top_products_daily", ["ingest_date", "product_id"])

    # Sales by category matrix (pivot category x state), thêm ingest_date + date
    print("   Tính gold_sales_by_category (pivot category x state)...")
    sales_matrix = (
        silver.groupBy("ingest_date", "date", "product_category_name_english")
        .pivot("c_state")
        .agg(F.sum("item_revenue"))
        .na.fill(0.0)
    )
    write_to_gold(sales_matrix, "gold_sales_by_category", ["ingest_date", "product_category_name_english"])

    # Xếp hạng tăng trưởng category theo từng ngày (DENSE_RANK theo doanh thu trong ngày)
    print("   Tính gold_category_rank (DENSE_RANK revenue per day)...")
    cat_rank = by_cat.withColumn(
        "category_growth_rank",
        F.dense_rank().over(Window.partitionBy("ingest_date").orderBy(F.col("revenue").desc())),
    )
    write_to_gold(cat_rank, "gold_category_rank", ["ingest_date", "product_category_name_english"])

    # =====================================================
    # UC4 — SELLER
    # =====================================================
    print("\n" + "-" * 40)
    print("[UC4] SELLER: metrics seller / delivery / daily breakdown")
    print("-" * 40)

    print("   Tính gold_seller_metrics (revenue, rank, delivery, fulfillment rate)...")
    seller = silver.groupBy("seller_id", "s_state", "s_city").agg(
        F.sum("item_revenue").alias("seller_revenue"),
        F.countDistinct("order_id").alias("seller_order_count"),
        F.avg("review_score").alias("seller_review_avg"),
        F.countDistinct("c_state").alias("geographic_coverage"),
    )
    seller = seller.withColumn(
        "seller_revenue_rank", F.rank().over(Window.orderBy(F.col("seller_revenue").desc()))
    )
    # thời gian giao trung bình + tỷ lệ giao đúng hạn (mức đơn, khử trùng)
    seller_orders = silver.select(
        "seller_id", "order_id", "purchase_ts",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ).dropDuplicates(["seller_id", "order_id"])
    seller_orders = seller_orders.withColumn(
        "delivery_days", F.datediff("order_delivered_customer_date", "purchase_ts")
    ).withColumn(
        "on_time",
        (F.col("order_delivered_customer_date") <= F.col("order_estimated_delivery_date")).cast("int"),
    )
    seller_deliv = seller_orders.groupBy("seller_id").agg(
        F.round(F.avg("delivery_days"), 2).alias("seller_avg_delivery_days"),
        F.round(F.avg("on_time"), 4).alias("seller_fulfillment_rate"),
    )
    seller = seller.join(seller_deliv, "seller_id", "left")
    # cột Graph/ML chưa làm
    seller = seller.withColumn("seller_network_centrality", F.lit(None).cast("double")) \
                   .withColumn("seller_cluster", F.lit(None).cast("int")) \
                   .withColumn("fraud_risk_score", F.lit(None).cast("double"))
    write_to_gold(seller, "gold_seller_metrics", ["seller_id"])

    # ----- Seller theo NGÀY (nguồn cho dashboard seller theo date range) -----
    print("   Tính gold_seller_daily (revenue / delivery per seller per day)...")
    seller_daily_rev = silver.groupBy("seller_id", "ingest_date", "date").agg(
        F.sum("item_revenue").alias("revenue"),
        F.countDistinct("order_id").alias("order_count"),
        F.count(F.lit(1)).alias("items_sold"),
        F.sum("review_score").alias("review_score_sum"),
        F.count("review_score").alias("review_count"),
        F.round(F.avg("review_score"), 2).alias("avg_review"),
    )
    # Giao hàng mức đơn (khử trùng [seller_id, order_id]) -> thành phần cộng được theo ngày.
    seller_orders_daily = silver.select(
        "seller_id", "order_id", "ingest_date", "date", "purchase_ts",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ).dropDuplicates(["seller_id", "order_id"])
    seller_orders_daily = seller_orders_daily.filter(
        F.col("order_delivered_customer_date").isNotNull()
    ).withColumn(
        "delivery_days", F.datediff("order_delivered_customer_date", "purchase_ts")
    ).withColumn(
        "on_time",
        (F.col("order_delivered_customer_date") <= F.col("order_estimated_delivery_date")).cast("int"),
    )
    seller_daily_deliv = seller_orders_daily.groupBy("seller_id", "ingest_date", "date").agg(
        F.sum("on_time").alias("on_time_count"),
        F.count("order_id").alias("delivered_count"),
        F.sum("delivery_days").alias("sum_delivery_days"),
        F.round(F.avg("on_time"), 4).alias("on_time_rate"),
        F.round(F.avg("delivery_days"), 2).alias("avg_delivery_days"),
    )
    seller_daily = seller_daily_rev.join(
        seller_daily_deliv, ["seller_id", "ingest_date", "date"], "left"
    )
    write_to_gold(seller_daily, "gold_seller_daily", ["seller_id", "ingest_date"])

    # ----- Top sản phẩm của seller theo NGÀY -----
    print("   Tính gold_seller_product_daily (top products per seller per day)...")
    seller_prod_daily = silver.groupBy(
        "seller_id", "product_id", "product_category_name_english", "ingest_date", "date"
    ).agg(
        F.sum("item_revenue").alias("revenue"),
        F.count(F.lit(1)).alias("qty"),
        F.countDistinct("order_id").alias("order_count"),
        F.sum("review_score").alias("review_score_sum"),
        F.count("review_score").alias("review_count"),
        F.round(F.avg("review_score"), 2).alias("avg_review"),
        F.countDistinct(
            F.when(F.col("order_status") == "canceled", F.col("order_id"))
        ).alias("canceled_count"),
    )
    write_to_gold(seller_prod_daily, "gold_seller_product_daily",
                  ["seller_id", "product_id", "ingest_date"])

    # =====================================================
    # UC5 — DELIVERY
    # =====================================================
    print("\n" + "-" * 40)
    print("[UC5] DELIVERY: tỷ lệ giao đúng hạn / thời gian giao theo bang")
    print("-" * 40)

    print("   Tính gold_delivery_metrics (on_time_rate, avg_delivery_days per state per day)...")
    deliv = orders_g.filter(F.col("order_delivered_customer_date").isNotNull())
    deliv = deliv.withColumn(
        "delivery_days", F.datediff("order_delivered_customer_date", "purchase_ts")
    ).withColumn(
        "on_time",
        (F.col("order_delivered_customer_date") <= F.col("order_estimated_delivery_date")).cast("int"),
    )
    # Thêm ingest_date + date. Lưu thành phần cộng được (on_time_count, delivered_count,
    # sum_delivery_days) để Charts tính lại tỷ lệ đúng cho cả range = SUM(tử)/SUM(mẫu);
    # giữ on_time_delivery_rate / avg_delivery_time_days (giá trị ngày) cho biểu đồ trend.
    deliv_state = deliv.groupBy("ingest_date", "date", "c_state").agg(
        F.round(F.avg("on_time"), 4).alias("on_time_delivery_rate"),
        F.round(F.avg("delivery_days"), 2).alias("avg_delivery_time_days"),
        F.sum("on_time").alias("on_time_count"),
        F.sum("delivery_days").alias("sum_delivery_days"),
        F.sum((F.col("on_time") == 0).cast("int")).alias("late_delivery_count"),
        F.count("order_id").alias("delivered_count"),
    )
    # cột ML chưa làm
    deliv_state = deliv_state.withColumn("predicted_delivery_days", F.lit(None).cast("double")) \
                             .withColumn("delivery_hotspot", F.lit(None).cast("string"))
    write_to_gold(deliv_state, "gold_delivery_metrics", ["ingest_date", "c_state"])

    print("\nTạo MongoDB indexes...")
    create_gold_indexes()
    print("\n" + "=" * 50)
    print("🎉 [GOLD] Hoàn tất Gold Layer")
    print("=" * 50)


# ASCENDING = 1 trong pymongo; dùng số trực tiếp để khỏi import thêm.
_ASC = 1


def create_gold_indexes():
    """Tạo index cho các collection daily/seller để Atlas Charts filter nhanh
    theo seller_id + ingest_date (idempotent, bỏ qua nếu lỗi)."""
    compound = {
        "gold_seller_daily": [("seller_id", _ASC), ("ingest_date", _ASC)],
        "gold_seller_product_daily": [("seller_id", _ASC), ("product_id", _ASC), ("ingest_date", _ASC)],
    }
    single = [
        "gold_revenue_metrics", "gold_revenue_by_category", "gold_revenue_by_state",
        "gold_revenue_by_payment_type", "gold_customer_acquisition", "gold_product_metrics",
        "gold_top_products_daily", "gold_sales_by_category", "gold_category_rank",
        "gold_delivery_metrics",
    ]
    for label, conn in SINKS:
        try:
            for coll, fields in compound.items():
                conn.create_compound_index(coll, fields)
            for coll in single:
                conn.create_index(coll, "ingest_date")
            print(f"   -> mongo[{label}] đã tạo index")
        except Exception as e:  # noqa: BLE001
            print(f"   !! mongo[{label}] tạo index lỗi: {e}")


if __name__ == "__main__":
    try:
        create_gold_metrics()
    finally:
        for _label, _conn in SINKS:
            _conn.close()
        spark.stop()
