# Những hạng mục CHƯA implement ở phase này

> Phase hiện tại tập trung **luồng Batch chạy đúng end-to-end** (Postgres → CDC → Bronze →
> Silver → Gold ở 3 nơi), **Airflow điều phối**, và **deploy K8s (minikube)**.
> Tài liệu này liệt kê những phần **cố ý hoãn** lại, kèm lý do và gợi ý hướng làm phase sau.

---

## 1. Luồng Streaming (Speed Layer) — ✅ ĐÃ LÀM

| Hạng mục | Hiện trạng | Ghi chú |
|---|---|---|
| `spark-streaming/kafka_consumer.py` | ✅ Hoàn thiện: đọc `user_behavior_events`, cộng dồn điểm theo (user, category), foreachBatch → Postgres | Broker đọc từ ENV `KAFKA_BOOTSTRAP` (mặc định `kafka:9094`) |
| Sink streaming → PostgreSQL | ✅ `write_to_postgres()`: upsert `user_preference` + tính lại `user_recommendation` | DDL: `init/postgres-init/04-streaming-tables.sql` |
| Xử lý hành vi người dùng → gợi ý sản phẩm | ✅ eventType→điểm (VIEW/CLICK/ADD_TO_CART/PURCHASE), top-10 sản phẩm theo category ưa thích | Chiến lược category-preference |
| Host/port Kafka trong streaming | ✅ ENV-driven; `make run-streaming` truyền `kafka:9094` | Host: `KAFKA_BOOTSTRAP=localhost:9092 PG_HOST=localhost` |
| Stack Python cũ (`services/user_behavior/*`, `spark-streaming/producer.py`) | ❌ ĐÃ XOÁ | Sai schema (`behavior`/`score`) + sai DB (`postgres`, bảng `customer`/`product`). Luồng chuẩn: SpringBoot → `kafka_consumer.py` |

**Cách chạy:** `make run-streaming` (cần `make seed-streaming-tables` nếu volume Postgres đã tồn tại
từ trước; cần rebuild image spark để có `psycopg2-binary`).

---

## 2. SpringBoot — fake-insert dữ liệu vào Postgres — ✅ ĐÃ LÀM

| Hạng mục | Hiện trạng |
|---|---|
| Sinh dữ liệu giả "liên tục" insert vào Postgres (dựa trên product/seller thật) để CDC bắt được | ✅ `FakeOltpInsertScheduler` — mỗi `fakeoltp.interval-ms` (mặc định 8s) ghi 1 order graph: `customers` → `orders` → `order_items` (1–3 dòng) → `order_payments` qua `JdbcTemplate`, `@Transactional` |
| Bật/tắt | `fakeoltp.enabled` (mặc định true) trong `application.yaml` / `application-k8s-deploy.yaml` |

**Lưu ý:** `FakeUserBehaviorScheduler` (sinh sự kiện Kafka cho streaming) và `FakeOltpInsertScheduler`
(insert OLTP cho batch/CDC) chạy song song — bổ trợ nhau. Order giả có prefix `sim_o_` / customer `sim_c_`
để dễ truy vết.

**Cơ chế nạp dữ liệu nền:** vẫn import 1 lần từ CSV → Postgres bằng `init/postgres-init/*.sql`
(initdb) hoặc `make seed-postgres`; fake-insert chạy thêm phía trên để demo CDC realtime.

---

## 3. Các cột Gold dùng ML / GraphFrames / NLP — HOÃN (đang để `null`)

Đã làm đầy đủ phần **SQL / Window / Pivot / UDF**. Các cột sau hiện ghi `null` + TODO:

| Bảng Gold | Cột chưa làm | Công nghệ cần |
|---|---|---|
| `gold_customer_rfm` | `churn_probability`, `clv_predicted` | MLlib (Logistic Regression, Regression) |
| `gold_product_metrics` | `recommended_products`, `review_sentiment` | MLlib ALS (collaborative filtering), NLP/Sentiment |
| `gold_seller_metrics` | `seller_network_centrality`, `seller_cluster`, `fraud_risk_score` | GraphFrames (PageRank, Connected Components), MLlib Anomaly Detection |
| `gold_delivery_metrics` | `predicted_delivery_days`, `delivery_hotspot` | MLlib Random Forest, Geo heatmap |
| `gold_revenue_metrics` | `revenue_5min`, `revenue_hourly` | Thuộc **Streaming** (tumbling/sliding window) |

**Vì sao hoãn:** user chốt scope phase này = "đầy đủ SQL/Window/Pivot, BỎ ML & GraphFrames".
ML/Graph cần thêm dependency (`graphframes`, mô hình huấn luyện) và khối lượng lớn.

---

## 4. Airflow DAG — phần nâng cao chưa làm

| Hạng mục | Hiện trạng |
|---|---|
| DAG `batch_pipeline` (ensure_connectors → wait_bronze → silver → gold) | ✅ Đã làm (TaskFlow) |
| Sensor chờ Bronze | Best-effort (dùng boto3 nếu có, không thì bỏ qua) — **chưa phải sensor chặt** |
| Retry/alerting/SLA, email notification | Chưa cấu hình |
| DAG cho streaming / ML | Chưa có |
| Incremental theo CDC | ✅ Đã làm — watermark `max(__ts_ms)` lưu ở `s3a://checkpoint/`; Silver chỉ rebuild các `order_id` thay đổi rồi merge, Gold chỉ chạy khi Silver tiến watermark (xem `spark-batch/checkpoint.py`). Còn lại: backfill/partition theo ngày, Airflow retry/alert/SLA. |

---

## 5. Chất lượng dữ liệu & mô hình dữ liệu — giới hạn hiện tại

- **Silver grain = order_item.** Payment được **gộp về mức đơn** (tổng tiền + loại thanh toán
  chủ đạo) để tránh nhân dòng → `revenue_by_payment_type` dùng *loại thanh toán chủ đạo/đơn*
  (xấp xỉ, không tách trường hợp 1 đơn nhiều loại thanh toán).
- **Doanh thu** dùng song song 2 thước đo: `item_revenue = price+freight` (mức item, cho
  by_category) và `order_payment_value` (mức đơn, cho daily/by_state/AOV) → tổng có thể lệch nhẹ.
- **DQ kiểm tra cơ bản** (loại dòng thiếu `order_id`/`purchase_ts`), chưa có:
  - Great Expectations / kiểm thử ràng buộc tự động
  - Quản lý schema drift, quarantine bản lỗi
  - Kiểm thử đơn vị cho từng transform

---

## 6. Hạ tầng / vận hành chưa hoàn thiện

| Hạng mục | Ghi chú |
|---|---|
| **MongoDB Atlas** | Chưa có URI thật (`MONGO_ATLAS_URI` để trống → tự skip). Điền sau là chạy được. |
| Spark **deploy-mode cluster + `--packages`** | Cần internet trên `spark-worker` lần đầu (Ivy resolve `hadoop-aws`). Chưa pre-bake jar vào image. |
| Bảo mật | Secret/credential để plaintext trong `.env`, `register-*.sh`, k8s Secret stringData (dev). Production cần vault/sealed-secrets. |
| K8s | Airflow dùng **LocalExecutor** (rút gọn, không Celery/Redis như Docker). Chưa Ingress/HPA/NetworkPolicy. Chưa kiểm thử thực tế trên minikube (mới validate YAML). |
| Monitoring | Grafana/Prometheus dashboards (nhắc trong kiến trúc) **chưa dựng**. |
| CI/CD | Chưa có. |
| CLAUDE.md | Còn ghi path Spark cũ (`/opt/spark-apps`); thực tế đã đổi `/opt/project`. |

---

## 7. Thứ tự ưu tiên gợi ý cho phase sau

1. ~~**SpringBoot fake-insert → Postgres** để demo CDC realtime~~ ✅ ĐÃ LÀM (xem mục 2).
2. ~~**Streaming**: hoàn thiện `kafka_consumer.py` (đổi `kafka:9094`), xử lý hành vi user, sink → Postgres, gợi ý sản phẩm~~ ✅ ĐÃ LÀM (xem mục 1).
3. **ML/GraphFrames Gold**: churn, CLV, ALS recommend, sentiment, PageRank, fraud, delivery prediction.
4. ~~**Incremental** Silver/Gold (thay vì overwrite)~~ ✅ ĐÃ LÀM (watermark CDC `__ts_ms`). Còn lại: backfill/partition theo ngày + Airflow retry/alert.
5. **Monitoring** (Grafana) + bảo mật secret + kiểm thử K8s thực tế trên minikube.
