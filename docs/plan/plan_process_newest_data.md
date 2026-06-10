# Plan: Incremental Batch Reading + Error Recovery

## Context

Pipeline hiện tại đọc lại toàn bộ dữ liệu bronze mỗi lần chạy (full overwrite). Khi không có data mới, Silver và Gold vẫn chạy lại tốn tài nguyên. Không có cơ chế phục hồi khi job lỗi giữa chừng. Mục tiêu: thêm time-based partitioning ở Bronze, checkpoint ở Silver/Gold, và DLQ ở connector.

---

## Approach

### Bronze — đổi partitioner sang time-based
S3 Sink hiện dùng `DefaultPartitioner` → `partition=0/`. Đổi sang `TimeBasedPartitioner` + `RecordField(__ts_ms)` để bronze ghi vào `year=YYYY/month=MM/day=dd/`. Silver sẽ dùng prefix này để filter chỉ đọc ngày mới.

### Silver — incremental read + checkpoint
- **Fact tables** (`orders`, `order_items`, `order_payments`, `order_reviews`): đọc chỉ date partitions mới (từ `last_checkpoint + 1` đến `today`)
- **Dimension tables** (`customers`, `products`, `sellers`, `geolocation`, `category_translation`): vẫn đọc toàn bộ (cần broadcast join đúng đắn)
- Ghi silver với `mode("overwrite").partitionBy("purchase_date")` + `partitionOverwriteMode=dynamic` → idempotent khi re-run
- Checkpoint ghi SAU KHI write thành công → fail = không tiến checkpoint → next run tự cover lại

### Gold — dynamic partition overwrite + checkpoint
- Vẫn đọc ALL silver (RFM/rankings cần global data)
- Đổi MinIO write sang `partitionOverwriteMode=dynamic` (không thay đổi logic aggregation)
- MongoDB `bulk_upsert` đã idempotent, không đổi
- Checkpoint tương tự Silver

### Error handling
- **Connector → Bronze**: thêm DLQ topic `dlq.bronze.sink` vào SINK_CONFIG
- **Spark jobs**: checkpoint chỉ ghi khi thành công → tự động re-cover khi retry
- **Airflow `wait_bronze`**: nâng cấp check từ "có bất kỳ object nào" → "có partition hôm nay không"

---

## Files

### Tạo mới
**`spark-batch/checkpoint.py`** — utility dùng boto3 (có sẵn trên Airflow worker do client-mode):
- `_get_s3_client()` — boto3 client dùng `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY` env vars
- `read_checkpoint(bucket, key) -> date | None` — đọc `{"last_processed_date": "YYYY-MM-DD"}`, trả `None` nếu chưa có
- `write_checkpoint(bucket, key, d: date)` — ghi JSON, raise nếu lỗi (để Airflow mark fail)

### Chỉnh sửa

#### `spark-batch/transform_bronze_to_silver.py`
1. **Imports**: thêm `from checkpoint import read_checkpoint, write_checkpoint`, `from datetime import date, timedelta`
2. **SparkSession**: thêm `.config("spark.sql.sources.partitionOverwriteMode", "dynamic")`
3. **Constants**: thêm `SILVER_CHECKPOINT_BUCKET = "silver-zone"`, `SILVER_CHECKPOINT_KEY = "_checkpoints/silver.json"`
4. **Hàm mới `get_date_range()`**: đọc checkpoint → trả `(start_date, end_date)`. First-run: `start_date = date(2016,1,1)` để cover toàn bộ data cũ
5. **Hàm mới `list_bronze_date_partitions(table, start, end)`**: dùng boto3 `list_objects_v2` với delimiter `/`, parse `year=/month=/day=` prefixes trong khoảng `[start, end]`. **Backward-compat**: nếu không tìm được date partition nào (data legacy `partition=0`), include path `partition=0/` để first-run vẫn đọc được data cũ
6. **Hàm mới `read_bronze_incremental(table, start, end)`**: gọi `list_bronze_date_partitions`, trả `None` nếu không có path mới
7. **`process_unified_silver()`**:
   - Gọi `get_date_range()` đầu hàm; nếu `start > end` → log + return (skip)
   - Fact tables dùng `read_bronze_incremental()`, dimension tables vẫn dùng `read_bronze()` (recursiveFileLookup full)
   - Thêm column: `silver = silver.withColumn("purchase_date", F.to_date("purchase_ts"))`
   - Write: `silver.write.mode("overwrite").partitionBy("purchase_date").parquet(SILVER_OUT)`
   - Sau write: `write_checkpoint(SILVER_CHECKPOINT_BUCKET, SILVER_CHECKPOINT_KEY, end_date)`
   - Bọc toàn bộ trong `try/except` re-raise để Airflow nhận exit code lỗi

#### `spark-batch/transform_silver_to_gold.py`
1. **Imports**: thêm `from checkpoint import read_checkpoint, write_checkpoint`, `from datetime import date`
2. **SparkSession**: thêm `.config("spark.sql.sources.partitionOverwriteMode", "dynamic")`
3. **Constants**: thêm `GOLD_CHECKPOINT_BUCKET = "gold-zone"`, `GOLD_CHECKPOINT_KEY = "_checkpoints/gold.json"`
4. **`create_gold_metrics()`**: sau `write_to_gold` cuối cùng, thêm `write_checkpoint(...)`. Bọc trong `try/except` re-raise
5. **`write_to_gold()`**: không đổi logic — `mode("overwrite")` với dynamic mode đã set ở session level là đủ cho gold collections (không có `partitionBy` ở gold vì aggregation là global)

#### `airflow/dags/batch_pipeline_dag.py`
1. **`SINK_CONFIG`** — thay thế các key partitioner và thêm DLQ:
   ```python
   "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
   "partition.duration.ms": "86400000",
   "path.format": "'year'=YYYY/'month'=MM/'day'=dd",
   "timestamp.extractor": "RecordField",
   "timestamp.field": "__ts_ms",
   "locale": "en_US",
   "timezone": "UTC",
   # xoá "partitioner.class" cũ (DefaultPartitioner)
   "errors.tolerance": "all",
   "errors.deadletterqueue.topic.name": "dlq.bronze.sink",
   "errors.deadletterqueue.topic.replication.factor": "1",
   "errors.deadletterqueue.context.headers.enable": "true",
   "errors.log.enable": "true",
   "errors.log.include.messages": "true",
   ```
2. **`wait_bronze()`** — đổi logic check từ prefix `cdc/` bất kỳ sang prefix hôm nay cụ thể:
   ```python
   today = datetime.utcnow().date()
   day_prefix = f"year={today.year}/month={today.month:02d}/day={today.day:02d}/"
   # check ít nhất 1 trong 4 fact tables có partition hôm nay
   for table in ["orders", "order_items", "order_payments", "order_reviews"]:
       prefix = f"cdc/olist_cdc.public.{table}/{day_prefix}"
       resp = s3.list_objects_v2(Bucket="bronze-zone", Prefix=prefix, MaxKeys=1)
       if resp.get("KeyCount", 0) > 0:
           return True
   return False  # short-circuit → skip silver+gold
   ```
3. **`SparkSubmitOperator` silver và gold**: thêm `"spark.sql.sources.partitionOverwriteMode": "dynamic"` vào `conf={}`

#### `init/register-s3-sink.sh`
Cập nhật JSON body của lệnh `curl` để sync với `SINK_CONFIG` mới (cùng các key partitioner + DLQ). File này dùng khi bootstrap môi trường mới.

---

## Thứ tự deploy

1. Deploy `checkpoint.py` (không có side effect)
2. Deploy Silver + Gold jobs đã cập nhật (backward-compat: nếu connector chưa đổi, `list_bronze_date_partitions` sẽ fallback về `partition=0/`)
3. Deploy DAG + `register-s3-sink.sh` cùng nhau → `ensure_connectors` task sẽ PUT config mới lên connector ngay lần chạy tiếp theo

---

## Edge Cases

| Tình huống | Hành vi |
|---|---|
| First run (chưa có checkpoint) | `start_date = 2016-01-01`, fallback đọc `partition=0/` nếu chưa có date partitions |
| Không có data mới hôm nay | `wait_bronze` short-circuit → Silver/Gold skip, checkpoint không tiến |
| Silver OK, Gold fail | Silver checkpoint ghi, Gold checkpoint không ghi → next run Gold chạy lại từ đầu (idempotent) |
| Silver fail | Cả hai checkpoint không ghi → next run cover lại toàn bộ window bị miss |
| Partial Spark write (Silver) | Dynamic overwrite re-write đúng partitions bị fail → idempotent |
| CDC event đến trễ >1 ngày | Không được cover (known limitation) |

---

## Verification

1. **Connector**: `GET :8083/connectors/s3-sink-bronze/config` → confirm `partitioner.class=TimeBasedPartitioner`. Insert 1 row Postgres → sau 60s MinIO có `bronze-zone/cdc/.../year=.../month=.../day=.../`
2. **wait_bronze**: trigger DAG trước khi có bronze hôm nay → Silver/Gold status = "Skipped"
3. **Silver checkpoint**: sau DAG chạy xong, đọc `silver-zone/_checkpoints/silver.json` → có `last_processed_date`. Chạy lại DAG → Silver log "No new date range to process"
4. **Dynamic overwrite**: có 2 ngày dữ liệu → Silver write 2 partitions. Re-run chỉ cho ngày 1 → ngày 2 không thay đổi (file timestamp giữ nguyên)
5. **Gold idempotency**: chạy Gold 2 lần → MongoDB document count không thay đổi
6. **DLQ**: kiểm tra Kafka UI (port 8080) có topic `dlq.bronze.sink`
7. **Error recovery**: corrupt checkpoint JSON → Silver fail → restore checkpoint → next run xử lý đúng window
