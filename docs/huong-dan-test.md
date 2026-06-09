# Hướng dẫn Test luồng Batch (Olist - Lambda Architecture)

> Tài liệu này hướng dẫn kiểm thử **toàn bộ luồng batch** từ Postgres → CDC → Bronze
> → Silver → Gold (MinIO + Mongo local + Atlas), trên **Docker Compose** và **Kubernetes (minikube)**.
>
> Tất cả lệnh chạy ở thư mục gốc dự án (`Big-Data/`).

---

## 0. Sơ đồ luồng cần kiểm chứng

```
data/external/*.csv ─(seed)─► Postgres(olist)
   └► Debezium source ─► Kafka olist_cdc.public.* ─► Debezium S3 Sink ─► MinIO bronze-zone/cdc/
                                                                            │
                            Spark Silver ◄──────────────────────────────────┘
                                  └► MinIO silver-zone/olist_unified_silver/
                                        └► Spark Gold ─► MinIO gold-zone/ + Mongo local + Atlas
                            Điều phối: Airflow DAG `batch_pipeline`
```

| Service | Cổng | UI |
|---|---|---|
| Kafka UI | 8080 | http://localhost:8080 |
| Airflow | 8081 | http://localhost:8081 (airflow/airflow) |
| Spark Master UI | 8082 | http://localhost:8082 |
| MinIO Console | 9001 | http://localhost:9001 (minioadmin/minioadmin123456) |
| Debezium Connect | 8083 | http://localhost:8083/connectors |
| pgAdmin | 5050 | http://localhost:5050 |

---

## PHẦN A — TEST TRÊN DOCKER COMPOSE

### A1. Khởi động hạ tầng

```bash
make docker-up
```

> Lần đầu sẽ **build 3 image custom** (debezium + s3-sink, airflow + spark, spark + pymongo)
> và tải Spark/JDK → có thể mất 5–15 phút. Cần mạng internet.

**Kiểm tra tất cả container Up & healthy:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```
Mong đợi: `bigdata-postgres`, `kafka-broker`, `debezium-connect`, `minio-server`,
`bigdata-mongodb`, `spark-master`, `spark-worker`, `airflow-webserver`, `airflow-scheduler`,
`airflow-worker` … đều `Up` (một số kèm `(healthy)`).

> Nếu container `restarting`: `docker logs <tên> --tail 50` để xem lỗi.

---

### A2. Kiểm tra dữ liệu đã nạp vào Postgres

initdb tự chạy `01-schema → 02-load → 03-replica-identity` **khi volume rỗng**.

```bash
docker exec -it bigdata-postgres psql -U postgres -d olist -c "\dt"
docker exec -it bigdata-postgres psql -U postgres -d olist -c "
  SELECT 'orders' t, count(*) FROM orders
  UNION ALL SELECT 'order_items', count(*) FROM order_items
  UNION ALL SELECT 'customers', count(*) FROM customers
  UNION ALL SELECT 'products', count(*) FROM products;"
```
**Kết quả đúng (xấp xỉ):** orders ≈ 99441, order_items ≈ 112650, customers ≈ 99441, products ≈ 32951.

> Nếu bảng rỗng (volume đã tồn tại từ trước): `make seed-postgres`.

**Kiểm tra REPLICA IDENTITY = FULL:**
```bash
docker exec -it bigdata-postgres psql -U postgres -d olist -c "
  SELECT relname, relreplident FROM pg_class
  WHERE relname IN ('orders','order_items') ;"
```
`relreplident` = `f` (full) là đúng.

---

### A3. Đăng ký Debezium connectors (source + S3 sink)

```bash
make register-connectors
```
**Kiểm tra trạng thái RUNNING:**
```bash
curl -s http://localhost:8083/connectors
curl -s http://localhost:8083/connectors/olist-connector/status
curl -s http://localhost:8083/connectors/s3-sink-bronze/status
```
Mong đợi: cả `connector` và các `tasks` đều `"state":"RUNNING"`.

> **Lỗi thường gặp:**
> - `connector class not found` → image debezium chưa build từ `init/Dockerfile` (chạy `make docker-build`).
> - sink `FAILED` với lỗi schema/Parquet → kiểm tra `value.converter.schemas.enable=true`.
> - sink `FAILED` 403 → sai key MinIO trong config sink.

**Kiểm tra topic có message (Kafka UI :8080):** thấy `olist_cdc.public.orders`, `...customers`, …
với số message > 0. Hoặc:
```bash
docker exec -it kafka-broker kafka-topics --bootstrap-server localhost:9092 --list | grep olist_cdc
```

#### Lệnh tuần tự sau `make register-connectors` đến `make run-silver`

Sau khi register, chạy lần lượt các bước sau:

**Bước 1 — Đợi connector khởi động rồi kiểm tra trạng thái (PowerShell):**
```powershell
Start-Sleep -Seconds 5
Invoke-RestMethod -Uri "http://localhost:8083/connectors/olist-connector/status" | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "http://localhost:8083/connectors/s3-sink-bronze/status" | ConvertTo-Json -Depth 5
```
Mong đợi: cả `connector.state` và `tasks[0].state` đều `"RUNNING"`.

> **Nếu `s3-sink-bronze` FAILED với lỗi `timezone configuration must be set`:**
> Thêm `"timezone": "UTC"` vào config trong `init/register-s3-sink.sh`, xóa connector cũ rồi register lại:
> ```powershell
> Invoke-RestMethod -Method DELETE -Uri "http://localhost:8083/connectors/s3-sink-bronze"
> ```
> ```bash
> bash init/register-s3-sink.sh
> ```

**Bước 2 — Chờ tất cả bảng xuất hiện trong MinIO bronze-zone (Bash, tối đa ~2 phút):**
```bash
until docker exec bigdata-minio-server ls /data/bronze-zone/cdc/ 2>&1 | grep -q "olist_cdc.public.orders"; do
  sleep 5
  echo "waiting for orders..."
done
docker exec bigdata-minio-server ls /data/bronze-zone/cdc/
```
Mong đợi: thấy đủ các thư mục `olist_cdc.public.customers`, `olist_cdc.public.orders`, `olist_cdc.public.order_items`, v.v.

> Sink flush theo `flush.size=1000` message **hoặc** `rotate.schedule.interval.ms=60s` (whichever first).
> Bảng nhỏ (customers ≈ 99k) flush trước; bảng lớn có thể mất đến 60s.

**Bước 3 — Chạy Silver:**
```bash
make run-silver
```

---

### A4. Kiểm tra Bronze trên MinIO

Sau ~1–2 phút (sink flush theo `rotate.schedule.interval.ms=60s`):

- Mở MinIO Console http://localhost:9001 → bucket `bronze-zone` → thư mục
  `cdc/olist_cdc.public.<bảng>/partition=0/*.parquet`.

Hoặc CLI:
```bash
docker run --rm --network init_minio-network minio/mc sh -c "
  mc alias set m http://minio:9000 minioadmin minioadmin123456 &&
  mc ls -r m/bronze-zone/cdc/ | head"
```
> Tên network có thể là `init_minio-network` (compose tự thêm tiền tố thư mục).
> Kiểm tra: `docker network ls | grep minio`.

**Đúng khi:** có file `.parquet` trong từng `olist_cdc.public.<bảng>/`.

---

### A5. Chạy & kiểm tra Silver

```bash
make run-silver
```
Theo dõi log: kết thúc có dòng `✅ Silver đã ghi: s3a://silver-zone/...` và bảng mẫu 5 dòng.

**Kiểm tra trên MinIO:** bucket `silver-zone/olist_unified_silver/` có `_SUCCESS` + `*.parquet`.

**Kiểm chứng nội dung (đếm dòng / cột delivery):**
```bash
docker exec -it spark-master /opt/spark/bin/spark-submit \
  --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minioadmin \
  --conf spark.hadoop.fs.s3a.secret.key=minioadmin123456 \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  -c "import pyspark" 2>/dev/null || true
```
Hoặc đơn giản dùng PySpark shell / đọc lại trong job. **Đúng khi:** số dòng ~ bằng `order_items`
(grain = order_item), có cột `item_revenue`, `order_payment_value`, `payment_type`, `review_score`,
`order_delivered_customer_date`.

> **Lỗi thường gặp:**
> - `Path does not exist: s3a://bronze-zone/cdc/...` → Bronze chưa có data (xem A4).
> - `UnknownHost minio` → job chạy ngoài network; phải chạy **trong spark-master** (đã đúng với `make run-silver`).

---

### A6. Chạy & kiểm tra Gold (3 nơi)

```bash
make run-gold
```
Log mong đợi: với mỗi collection có `✅ parquet: gold_...` và `-> mongo[local] gold_...: N docs`
(Atlas hiện `⏭️ Bỏ qua Mongo[atlas]` vì chưa cấu hình URI).

**1) MinIO** `gold-zone/`: có các thư mục
`gold_revenue_metrics, gold_revenue_by_category, gold_revenue_by_state, gold_revenue_by_payment_type,
gold_customer_rfm, gold_customer_acquisition, gold_product_metrics, gold_top_products_daily,
gold_sales_by_category, gold_category_rank, gold_seller_metrics, gold_delivery_metrics`.

**2) Mongo local:**
```bash
docker exec -it bigdata-mongodb mongosh -u admin -p admin123456 --authenticationDatabase admin --quiet --eval '
  const db = db.getSiblingDB("olist_gold");
  db.getCollectionNames().forEach(c => print(c, db[c].countDocuments()));
  printjson(db.gold_customer_rfm.findOne());
'
```
**Đúng khi:** mỗi collection có document; `gold_customer_rfm` có `recency_days, frequency, monetary,
rfm_score, customer_segment` (và `churn_probability=null` — để phase sau).

**3) Atlas:** sau khi điền `MONGO_ATLAS_URI`, chạy lại `make run-gold` rồi kiểm tra trên Atlas UI.

---

### A7. Đối chiếu Gold với yêu cầu

Mở `docs/data-view/gold-data-requirment.md` và xác nhận từng metric SQL có mặt:

| Bảng | Cột phải có (phase này) |
|---|---|
| gold_revenue_metrics | revenue_daily, order_count, avg_order_value, revenue_growth_rate, revenue_spike_flag |
| gold_customer_rfm | recency_days, frequency, monetary, r/f/m_score, rfm_score, customer_segment |
| gold_product_metrics | total_sales, avg_review_score, product_return_rate, category_rank |
| gold_seller_metrics | seller_revenue, seller_order_count, seller_review_avg, seller_revenue_rank, seller_avg_delivery_days, seller_fulfillment_rate, geographic_coverage |
| gold_delivery_metrics | on_time_delivery_rate, avg_delivery_time_days, late_delivery_count |

> Các cột ML/GraphFrames (churn, clv, recommend, sentiment, centrality, fraud, predicted_delivery)
> hiện = `null` (xem `docs/chua-implement-phase-nay.md`).

---

### A8. Test bằng Airflow (thay cho chạy tay)

1. Mở http://localhost:8081 (airflow/airflow).
2. Bật & trigger DAG `batch_pipeline` (hoặc `make airflow-trigger`).
3. Quan sát 4 task: `ensure_connectors → wait_bronze → silver → gold` chuyển **xanh**.
4. Xem log task `gold` → có dòng ghi Mongo.

**Kiểm tra Spark nhận job:** Spark Master UI http://localhost:8082 thấy application chạy/đã xong.

> **Lỗi thường gặp:**
> - Task `silver/gold` lỗi `Initial job has not accepted any resources` → spark-worker chưa
>   đăng ký với master (kiểm tra :8082 phần Workers).
> - Lỗi tải `--packages` → spark-worker không có internet (deploy-mode cluster cần Ivy tải lần đầu).

---

## PHẦN B — TEST TRÊN KUBERNETES (minikube)

### B1. Deploy

```bash
make k8s-up            # start minikube + build image + tạo configmap code + apply manifests
make k8s-status        # chờ tất cả pod Running
kubectl -n bigdata get pods -w
```

### B2. Nạp dữ liệu Postgres trong cluster

```bash
make seed-postgres-k8s   # copy CSV vào pod postgres + chạy 02-load.sql
```

### B3. Test từng pod

```bash
make k8s-test-all        # chạy lần lượt tất cả test dưới đây
```
Hoặc từng phần:
```bash
make k8s-test-postgres   # pg_isready + đếm bảng orders
make k8s-test-minio      # pod ready + liệt kê /data
make k8s-test-kafka      # kafka-broker-api-versions + list topics
make k8s-test-debezium   # curl /connectors
make k8s-test-mongo      # mongosh ping
make k8s-test-spark      # spark-submit --version + code mounted
make k8s-test-airflow    # airflow dags list | grep batch_pipeline
```

### B4. Chạy pipeline trên k8s

```bash
# Đăng ký connector + trigger DAG (qua airflow trong cluster)
kubectl -n bigdata exec deploy/airflow-scheduler -- airflow dags trigger batch_pipeline

# Mở UI bằng port-forward
kubectl -n bigdata port-forward svc/airflow-webserver 8081:8080
kubectl -n bigdata port-forward svc/minio 9001:9001
```

### B5. Dọn dẹp
```bash
make k8s-down
```

---

## PHẦN C — CHECKLIST NHANH (Definition of Done)

- [ ] Tất cả container/pod Up/Running
- [ ] Postgres có dữ liệu 9 bảng (orders ≈ 99k)
- [ ] 2 connector RUNNING; topic `olist_cdc.public.*` có message
- [ ] MinIO `bronze-zone/cdc/*` có parquet
- [ ] MinIO `silver-zone/olist_unified_silver/` có parquet, grain = order_item
- [ ] MinIO `gold-zone/*` có đủ collection
- [ ] Mongo local `olist_gold.*` có document ở mọi collection
- [ ] Airflow DAG `batch_pipeline` chạy xanh hết 4 task
- [ ] (k8s) `make k8s-test-all` pass

---

## PHẦN D — TROUBLESHOOTING tổng hợp

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| Sink connector FAILED `class not found` | image debezium chưa build s3-sink | `make docker-build` rồi `docker compose up -d debezium` |
| Sink FAILED Parquet/schema | `schemas.enable` ở sink = false | đảm bảo `value.converter.schemas.enable=true` |
| Bronze parquet rỗng | chưa register / Postgres rỗng | A2, A3 |
| `price/payment_value` ra chuỗi base64 | thiếu `decimal.handling.mode=double` | đã set trong register-connector.sh |
| Silver toàn null timestamp | cột micros chưa convert | đã xử lý bằng `timestamp_micros()` |
| Gold `ModuleNotFoundError: services` | thiếu mount/PYTHONPATH | mount `../services` + `PYTHONPATH=/opt/project` (đã có) |
| Gold `ModuleNotFoundError: pymongo` | spark image gốc | dùng image `bigdata-spark:3.5.1` (đã build) |
| Gold không ghi được Mongo local | mongo không cùng network | mongo đã ở `spark-network`+`airflow-network` |
| Spark job treo "no resources" | worker chưa join master | kiểm tra Spark UI :8082 |
