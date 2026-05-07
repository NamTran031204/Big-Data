# 06 — Xử lý nâng cao & Troubleshooting

## 1. Single Message Transform (SMT) — Trích xuất dữ liệu từ CDC envelope

### 1.1. Vấn đề: Debezium Envelope quá phức tạp cho Bronze

Debezium CDC event có dạng envelope:

```json
{
  "before": null,
  "after": { "order_id": "abc123", "order_status": "delivered", ... },
  "source": { "table": "orders", "ts_ms": 1699000000000, ... },
  "op": "c",
  "ts_ms": 1699000001000
}
```

Nếu ghi thẳng vào MinIO, file Parquet sẽ chứa cả envelope (`before`, `after`, `source`, `op`) → Spark đọc phải navigate nested struct rất phiền.

### 1.2. Giải pháp: Dùng SMT `ExtractNewRecordState`

Thêm vào cấu hình Debezium Source Connector:

```json
{
  "config": {
    "...": "...",

    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": true,
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "transforms.unwrap.add.fields": "op,table,source.ts_ms"
  }
}
```

**Kết quả:** Message trên Kafka sẽ là flat JSON:

```json
{
  "order_id": "abc123",
  "customer_id": "cust456",
  "order_status": "delivered",
  "order_purchase_timestamp": 1533686400000000,
  "__op": "c",
  "__table": "orders",
  "__source_ts_ms": 1699000000000
}
```

→ S3 Sink ghi Parquet → Spark đọc trực tiếp mà không cần parse envelope.

### 1.3. Xử lý DELETE events

Khi `delete.handling.mode: rewrite`:
- Record bị DELETE sẽ được ghi với field `__deleted = true`
- Spark có thể filter: `df.filter(col("__deleted") != True)`

## 2. Schema Registry (Tùy chọn nâng cao)

### 2.1. Khi nào cần Schema Registry?

| Không cần | Cần |
|---|---|
| Dữ liệu ít thay đổi schema | Schema thay đổi liên tục |
| Team nhỏ | Nhiều consumer cần biết schema |
| Dùng JSON converter | Dùng Avro converter (nhỏ hơn ~40%) |

### 2.2. Cấu hình nếu muốn dùng

Thêm service vào docker-compose:

```yaml
  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    container_name: schema-registry
    depends_on:
      - kafka
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:29092
    networks:
      - kafka-network
```

Cập nhật converter trong connector config:

```json
{
  "key.converter": "io.confluent.connect.avro.AvroConverter",
  "key.converter.schema.registry.url": "http://schema-registry:8081",
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "http://schema-registry:8081"
}
```

## 3. Monitoring Pipeline

### 3.1. JMX Metrics từ Kafka Connect

Kafka Connect expose JMX metrics:

```
# Source connector metrics
debezium.postgres:type=connector-metrics,server=olist,task=0
  → MilliSecondsBehindSource    (Debezium lag)
  → NumberOfEventsFiltered
  → TotalNumberOfEventsSeen

# Sink connector metrics  
kafka.connect:type=sink-task-metrics,connector=olist-s3-sink-bronze,task=0
  → sink-record-send-rate       (records/sec ghi vào MinIO)
  → sink-record-lag-max         (lag tối đa)
  → put-batch-avg-time-ms       (thời gian ghi trung bình)
```

### 3.2. Tích hợp Prometheus

Thêm JMX Exporter vào Kafka Connect:

```yaml
  debezium-connect:
    environment:
      EXTRA_ARGS: "-javaagent:/kafka/connect/jmx-exporter/jmx_prometheus_javaagent.jar=9404:/kafka/connect/jmx-exporter/config.yml"
    ports:
      - "9404:9404"  # Prometheus scrape endpoint
```

### 3.3. Các metric cần giám sát

| Metric | Ý nghĩa | Ngưỡng cảnh báo |
|---|---|---|
| `MilliSecondsBehindSource` | Debezium đang chậm bao lâu so với DB | > 60000ms |
| `sink-record-lag-max` | S3 Sink chậm bao nhiêu records | > 10000 |
| `kafka_consumer_group_lag` | Kafka consumer lag | > 5000 |
| `sink-record-send-rate` | Throughput ghi MinIO | < 10 records/sec |

## 4. Troubleshooting Guide

### 4.1. Debezium không kết nối được PostgreSQL

```bash
# Kiểm tra log
docker logs debezium-connect 2>&1 | grep -i "error\|exception"

# Kiểm tra PostgreSQL network
docker exec debezium-connect ping postgres

# Kiểm tra credentials
docker exec bigdata-postgres psql -U postgres -d olist -c "SELECT 1;"
```

### 4.2. S3 Sink không ghi được vào MinIO

```bash
# Kiểm tra MinIO từ Kafka Connect container
docker exec debezium-connect curl -s http://minio:9000/minio/health/live

# Kiểm tra access key
docker exec debezium-connect env | grep AWS

# Reset connector
curl -X POST http://localhost:8083/connectors/olist-s3-sink-bronze/restart
```

### 4.3. Kafka topics có data nhưng MinIO trống

Nguyên nhân phổ biến: **flush.size chưa đạt và rotate.interval.ms chưa hết.**

```bash
# Kiểm tra offset đang đọc
curl -s http://localhost:8083/connectors/olist-s3-sink-bronze/status | jq '.tasks'

# Giảm flush.size để test
curl -X PUT http://localhost:8083/connectors/olist-s3-sink-bronze/config \
  -H "Content-Type: application/json" \
  -d '{ ... "flush.size": "10" ... }'
```

### 4.4. Replication slot bị chiếm

```sql
-- Xem tất cả replication slots
SELECT slot_name, active FROM pg_replication_slots;

-- Xóa slot cũ
SELECT pg_drop_replication_slot('debezium_olist');
```

### 4.5. Reset toàn bộ pipeline

```bash
# Xóa tất cả connectors
curl -X DELETE http://localhost:8083/connectors/olist-postgres-source
curl -X DELETE http://localhost:8083/connectors/olist-s3-sink-bronze

# Xóa replication slot trong PostgreSQL
docker exec bigdata-postgres psql -U postgres -d olist \
  -c "SELECT pg_drop_replication_slot('debezium_olist');"

# Xóa data trong MinIO
docker exec minio-mc mc rm --recursive --force myminio/bigdata/bronze/

# Đăng ký lại connectors
./scripts/register-connectors.sh
```

## 5. Tóm tắt toàn bộ cấu hình files cần tạo

```
project/
├── docker-compose.yml          ← Tất cả services
├── .env                        ← Credentials
├── docker/
│   └── kafka-connect/
│       └── Dockerfile          ← Custom image: Debezium + S3 Sink plugin
├── connectors/
│   ├── debezium-postgres-source.json   ← Cấu hình Source connector
│   └── s3-sink-bronze.json             ← Cấu hình Sink connector
└── scripts/
    ├── init-postgres.sql       ← Tạo 9 bảng PostgreSQL
    ├── init-bucket.sh          ← Tạo bucket MinIO (đã có)
    └── register-connectors.sh  ← Đăng ký connectors
```
