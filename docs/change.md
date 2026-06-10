# Nhật ký thay đổi — so với commit `8f1b52d`

## Tổng quan

Lần chỉnh sửa này tập trung vào ba việc chính: **(1)** hoàn thiện toàn bộ luồng Docker/K8s cho pipeline batch thực tế (đúng path S3 Sink, đúng cấu hình Spark cluster), **(2)** fix các lỗi cấu hình quan trọng khiến pipeline chưa chạy được (ParquetFormat schema, credentials MinIO, decimal type), và **(3)** dọn dẹp tài liệu cũ lỗi thời.

---

## 1. Makefile — Viết lại hoàn toàn

Makefile cũ chỉ có 4 target đơn giản. Phiên bản mới chia thành hai nhóm rõ ràng:

- **Docker targets**: `docker-build`, `docker-up`, `docker-down`, `seed-postgres`, `register-connectors`, `run-silver`, `run-gold`, `airflow-trigger`, `pipeline-docker`
- **Kubernetes targets**: `k8s-build-images`, `k8s-code-configmaps`, `k8s-up`, `k8s-down`, `seed-postgres-k8s`, `k8s-status`, `k8s-test-*` (cho từng pod), `k8s-test-all`

**Các biến cấu hình cố định ở đầu file:**
```makefile
NS              := bigdata
SPARK_PACKAGES  := org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.7.3
SILVER_APP      := /opt/project/spark-batch/transform_bronze_to_silver.py
GOLD_APP        := /opt/project/spark-batch/transform_silver_to_gold.py
```

`run-silver` và `run-gold` chạy `spark-submit` **trong container spark-master** (client mode), trỏ đúng đường dẫn `/opt/project/` mà volume đã mount.

---

## 2. SpringBoot — Thay đổi cấu hình kết nối

### `application.yaml` — đổi nhiều endpoint và credential

```yaml
# TRƯỚC (sai: trỏ vào DB airflow, port 5433)
spring.datasource.url: jdbc:postgresql://localhost:5433/airflow
spring.datasource.username: airflow
spring.datasource.password: airflow

# SAU (đúng: trỏ vào DB olist)
spring.datasource.url: jdbc:postgresql://localhost:5432/postgres
spring.datasource.username: postgres
spring.datasource.password: postgres
```

```yaml
# MongoDB — thêm xác thực
# TRƯỚC
spring.mongodb.uri: mongodb://127.0.0.1:27017/olist_db
# SAU
spring.mongodb.uri: mongodb://admin:admin123456@127.0.0.1:27017/olist_db?authSource=admin
```

```yaml
# MinIO — đồng bộ với docker-compose
# TRƯỚC
minio.access-key: admin
minio.secret-key: password123
# SAU
minio.access-key: minioadmin
minio.secret-key: minioadmin123456
```

```yaml
# Server port — tránh xung đột với Airflow (8081)
# TRƯỚC
server.port: 8081
# SAU
server.port: 8085
```

### `KafkaProducerConfig.java` — cải thiện producer

- Thêm bean tạo topic `user_behavior_events` (3 partition, 1 replica).
- `userBehaviorKafkaTemplate` đổi kiểu từ `KafkaTemplate<String, UserBehaviorEvent>` sang `KafkaTemplate<String, String>` và dùng `StringSerializer` thay vì `JsonSerializer` — serialize thủ công bên ngoài để kiểm soát dễ hơn.

### `ReferenceDataService.java` — đổi tên topic và cách serialize

- Inject thêm `ObjectMapper`.
- Đổi topic đích từ `"user-behavior-topic"` sang `"user_behavior_events"` (khớp tên topic vừa tạo ở trên).
- Serialize `UserBehaviorEvent` thành JSON string thủ công thay vì để Kafka tự serialize.

### `OrderItemJpaRepository.java` — thêm projection query

Thêm interface `OrderItemSummary` và query JPQL trả về bộ `(orderId, productId, sellerId)` với phân trang — dùng cho luồng tạo sự kiện hành vi người dùng.

---

## 3. Dọn dẹp tài liệu cũ

- **Xóa** `docs/big-data.md` (~2.964 dòng): file kế hoạch triển khai 10 tuần đã lỗi thời, không còn phản ánh kiến trúc thực.
- **Xóa** `docs/spark-container-design.md` (~522 dòng): báo cáo thiết kế Docker cũ, đã được thay thế bởi các Dockerfile thực tế trong `init/`.
- **Xóa** các file `.pyc` trong `dags/__pycache__/` và `scripts/__pycache__/` (không nên commit binary cache).

---

## 4. `init/docker-compose.yml` — Cấu hình lại nhiều service

### Airflow

```yaml
# TRƯỚC: dùng image gốc
image: apache/airflow:2.11.2

# SAU: build custom (JDK 17 + Spark 3.5.1 + spark provider)
build:
  context: .
  dockerfile: airflow.Dockerfile
image: bigdata-airflow:2.11.2
```

Thêm các biến môi trường:
```yaml
AIRFLOW__CORE__LOAD_EXAMPLES: 'false'      # tắt ví dụ mẫu
AIRFLOW_CONN_SPARK_DEFAULT: 'spark://spark-master:7077'  # kết nối SparkSubmitOperator
PYTHONPATH: '/opt/project'                 # import services.mongodb_connect trong driver
```

Thêm volume mount code và kết nối thêm 3 network (`kafka-network`, `minio-network`, `spark-network`) để Airflow worker có thể trigger spark-submit và giao tiếp với Kafka/MinIO.

### PostgreSQL

Thêm mount:
```yaml
- ./postgres-init:/docker-entrypoint-initdb.d:ro   # chạy SQL init lúc volume rỗng
- ../data/external:/csv:ro                          # CSV để COPY server-side
```

### MongoDB

Thêm kết nối `spark-network` và `airflow-network` (vì Spark driver gold và Airflow worker đều cần ghi vào Mongo local). Thêm healthcheck (`mongosh ping`).

### Container names — thêm prefix `bigdata-`

| Service | Tên cũ | Tên mới |
|---|---|---|
| Zookeeper | kafka-zookeeper | bigdata-kafka-zookeeper |
| Kafka broker | kafka-broker | bigdata-kafka-broker |
| Kafka UI | kafka-ui | bigdata-kafka-ui |
| MinIO | minio-server | bigdata-minio-server |
| MinIO mc | minio-mc | bigdata-minio-mc |

### Debezium

```yaml
# TRƯỚC: image gốc
image: quay.io/debezium/connect:2.4

# SAU: build custom (thêm plugin Confluent S3 Sink)
build:
  context: .
  dockerfile: Dockerfile
image: bigdata-debezium:2.4
```

Thêm `minio-network` để S3 Sink connector ghi được tới `minio:9000`.

### Spark Master & Worker

```yaml
# TRƯỚC: image gốc, mount vào /opt/spark/...
image: apache/spark:3.5.1
volumes:
  - ../spark-batch:/opt/spark/spark-batch

# SAU: build custom (thêm pymongo), mount vào /opt/project
image: bigdata-spark:3.5.1
volumes:
  - ../spark-batch:/opt/project/spark-batch
  - ../spark-streaming:/opt/project/spark-streaming
  - ../services:/opt/project/services
environment:
  - PYTHONPATH=/opt/project
```

Spark master thêm `airflow-network`; spark worker thêm `airflow-network`, bỏ `kafka-network` (batch không đọc Kafka trực tiếp).

---

## 5. `init/register-connector.sh` — Cải thiện đăng ký source connector

- Đổi wait từ `sleep 2` sang retry loop (thử mỗi 5s cho đến khi Debezium sẵn sàng).
- Sử dụng biến `CONNECT_URL` (mặc định `http://localhost:8083`) để dễ gọi từ trong cluster.

Thêm các config quan trọng:
```json
"decimal.handling.mode": "double"      // price/payment_value ra DOUBLE thay vì base64
"table.include.list": "public.customers,...",  // chỉ capture 9 bảng Olist
"publication.autocreate.mode": "filtered",
"snapshot.mode": "initial",
"tombstones.on.delete": "false",
"heartbeat.interval.ms": "10000"
```

---

## 6. `init/register-s3-sink.sh` — Fix nhiều lỗi cấu hình quan trọng

### Đổi tên connector và bucket đích

```bash
# TRƯỚC
"name": "s3-sink-connector"
"s3.bucket.name": "raw-data"

# SAU
"name": "s3-sink-bronze"
"s3.bucket.name": "bronze-zone"
"topics.dir": "cdc"      # output: bronze-zone/cdc/olist_cdc.public.<table>/...
```

### Fix regex topics (thiếu `.*` cũ)

```bash
# TRƯỚC (sai — không match đúng)
"topics.regex": "olist_cdc\\.public\\.*"

# SAU (đúng)
"topics.regex": "olist_cdc\\.public\\..*"
```

### Fix schema enable (lỗi ParquetFormat)

```json
// TRƯỚC — schemas.enable=false -> ParquetFormat không có schema -> lỗi
"value.converter.schemas.enable": "false"

// SAU — bắt buộc true để ParquetFormat đọc được Connect schema
"value.converter.schemas.enable": "true"
```

### Đổi cách cấp credentials MinIO

```bash
# TRƯỚC: dùng EnvironmentVariableCredentialsProvider (cần env AWS_*)
"s3.credentials.provider.class": "com.amazonaws.auth.EnvironmentVariableCredentialsProvider"

# SAU: truyền thẳng key vào config connector
"aws.access.key.id": "${MINIO_KEY}"
"aws.secret.access.key": "${MINIO_SECRET}"
```

Tăng `flush.size` từ `100` lên `1000` để giảm số file parquet nhỏ.

---

## 7. `init/scripts/init-bucket.sh` — Đơn giản hóa

Xóa toàn bộ logic tạo service account (bước 3, 4 cũ — không cần thiết và gây lỗi). Giữ lại đúng 2 bước: kết nối MinIO (có retry) và tạo bucket.

Danh sách bucket thay đổi:
```bash
# TRƯỚC: bigdata + bronze-zone + silver-zone + gold-zone
# SAU: bronze-zone + silver-zone + gold-zone + checkpoint
```

Thêm bucket `checkpoint` cho Spark Streaming; bỏ bucket `bigdata` không dùng.

---

## 8. `spark-batch/transform_bronze_to_silver.py` — Viết lại hoàn toàn

**Đổi đường dẫn đọc** để khớp cấu trúc thực tế của S3 Sink output:
```
# TRƯỚC: s3a://bronze-zone/{table}/
# SAU:   s3a://bronze-zone/cdc/olist_cdc.public.{table}/
```

**Thêm xử lý CDC đúng cách:**
- Hàm `dedup_cdc()`: lọc bỏ bản ghi đã xóa (`__deleted`), giữ bản ghi mới nhất theo `__ts_ms`, xóa các cột phụ Debezium.
- Hàm `micros_to_ts()`: đổi timestamp epoch-microseconds (kiểu Debezium `MicroTimestamp`) sang Spark timestamp bằng `timestamp_micros()`.

**Fix grain payment** để tránh nhân dòng order_item khi join:
- Gộp `order_payments` về 1 dòng/đơn (tổng tiền, loại thanh toán chủ đạo) **trước** khi join với order_items.

**Lấy cấu hình MinIO từ biến môi trường** thay vì hardcode `localhost:9000`.

---

## 9. `spark-batch/transform_silver_to_gold.py` — Cải thiện cấu hình

- Lấy toàn bộ config (MinIO endpoint, MongoDB URIs) từ biến môi trường — không còn hardcode URI Atlas.
- Hỗ trợ 2 Mongo sink độc lập:
  - `MONGO_LOCAL_URI` — mặc định trỏ vào `bigdata-mongodb` (container local).
  - `MONGO_ATLAS_URI` — nếu rỗng thì tự động bỏ qua, pipeline vẫn chạy bình thường.
- Cập nhật packages Spark: `hadoop-aws:3.3.4` + `aws-java-sdk-bundle:1.12.262` (bỏ kafka và postgresql không cần cho gold).

---

## 10. `services/mongodb_connect/mongo_connector.py` — Fix tương thích Python

```python
# TRƯỚC (chỉ hoạt động trên Python 3.11+)
from datetime import datetime, UTC

# SAU (tương thích Python 3.10 trở xuống — phiên bản trong container)
from datetime import datetime, timezone
UTC = timezone.utc
```

---

## 11. `spark-streaming/kafka_consumer.py` — Fix MinIO secret key

```python
# TRƯỚC (sai credential, không kết nối được MinIO)
hadoop_conf.set("fs.s3a.secret.key", "minioadmin123")

# SAU (đồng bộ với docker-compose)
hadoop_conf.set("fs.s3a.secret.key", "minioadmin123456")
```
