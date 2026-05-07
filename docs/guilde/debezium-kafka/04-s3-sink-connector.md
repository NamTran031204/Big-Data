# 04 — Cấu hình S3 Sink Connector (Kafka → MinIO/Bronze)

## 1. S3 Sink Connector là gì?

S3 Sink Connector là một **plugin Kafka Connect** đọc messages từ Kafka topics và tự động ghi xuống S3-compatible storage (MinIO) dưới dạng file Parquet.

```
Kafka Topic: olist.public.orders
       ↓ S3 Sink Connector đọc
       ↓ Batch 100 records hoặc hết 60 giây
       ↓ Chuyển đổi JSON → Parquet
       ↓ Ghi xuống MinIO
MinIO: s3a://bigdata/bronze/olist.public.orders/year=2018/month=11/...parquet
```

**Không cần viết code.** Chỉ cần cấu hình JSON.

## 2. Cài đặt S3 Sink Plugin vào Kafka Connect

Image `debezium/connect:2.4` chỉ có Debezium plugins, chưa có S3 Sink. Cần build custom image:

### 2.1. Dockerfile cho Kafka Connect

Tạo file `docker/kafka-connect/Dockerfile`:

```dockerfile
FROM quay.io/debezium/connect:2.4

# Cài Confluent S3 Sink Connector
ENV CONNECT_PLUGIN_PATH=/kafka/connect

# Tải S3 Sink Connector từ Confluent Hub
RUN mkdir -p /kafka/connect/confluent-s3-sink && \
    cd /kafka/connect/confluent-s3-sink && \
    curl -sL "https://d2p6pa21dvn84.cloudfront.net/api/plugins/confluentinc/kafka-connect-s3/versions/10.5.13/confluentinc-kafka-connect-s3-10.5.13.zip" -o s3-sink.zip && \
    unzip s3-sink.zip && \
    rm s3-sink.zip && \
    mv confluentinc-kafka-connect-s3-10.5.13/lib/* . && \
    rm -rf confluentinc-kafka-connect-s3-10.5.13
```

### 2.2. Cập nhật docker-compose.yml

```yaml
  debezium-connect:
    build:
      context: ./docker/kafka-connect
      dockerfile: Dockerfile
    container_name: debezium-connect
    depends_on:
      - kafka
      - postgres
      - minio
    ports:
      - "8083:8083"
    environment:
      BOOTSTRAP_SERVERS: kafka:29092
      GROUP_ID: "1"
      CONFIG_STORAGE_TOPIC: my_connect_configs
      OFFSET_STORAGE_TOPIC: my_connect_offsets
      STATUS_STORAGE_TOPIC: my_connect_statuses
      CONFIG_STORAGE_REPLICATION_FACTOR: 1
      OFFSET_STORAGE_REPLICATION_FACTOR: 1
      STATUS_STORAGE_REPLICATION_FACTOR: 1
      CONNECT_PLUGIN_PATH: /kafka/connect
    networks:
      - kafka-network
      - minio-network
```

> **Quan trọng:** Kafka Connect phải nằm trong cả 2 network: `kafka-network` (để kết nối Kafka) và `minio-network` (để ghi MinIO).

## 3. Cấu hình S3 Sink Connector

### 3.1. File cấu hình JSON

Tạo file `connectors/s3-sink-bronze.json`:

```json
{
  "name": "olist-s3-sink-bronze",
  "config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "tasks.max": "3",

    "topics": "olist.public.orders,olist.public.order_items,olist.public.order_payments,olist.public.order_reviews,olist.public.customers,olist.public.products,olist.public.sellers,olist.public.geolocation,olist.public.product_category_name_translation",

    "s3.bucket.name": "bigdata",
    "s3.region": "us-east-1",
    "store.url": "http://minio:9000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",

    "topics.dir": "bronze",

    "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
    "parquet.codec": "snappy",

    "flush.size": "500",
    "rotate.interval.ms": "60000",
    "rotate.schedule.interval.ms": "120000",

    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "partition.duration.ms": "86400000",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd",
    "locale": "en-US",
    "timezone": "Asia/Ho_Chi_Minh",
    "timestamp.extractor": "Record",

    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "key.converter.schemas.enable": false,
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": false,

    "schema.compatibility": "NONE",
    "behavior.on.null.values": "ignore",

    "aws.access.key.id": "${MINIO_ACCESS_KEY}",
    "aws.secret.access.key": "${MINIO_SECRET_KEY}"
  }
}
```

### 3.2. Giải thích tham số quan trọng

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `s3.bucket.name` | `bigdata` | Bucket đã tạo trong init-bucket.sh |
| `store.url` | `http://minio:9000` | Endpoint MinIO (internal Docker) |
| `topics.dir` | `bronze` | Thư mục gốc trong bucket: `bigdata/bronze/` |
| `format.class` | `...ParquetFormat` | Ghi dạng Parquet (columnar, nén tốt) |
| `parquet.codec` | `snappy` | Nén Snappy (nhanh, hỗ trợ Spark tốt) |
| `flush.size` | `500` | Ghi file mới sau mỗi 500 records |
| `rotate.interval.ms` | `60000` | Hoặc ghi file mới sau 60 giây (tùy cái nào trước) |
| `partitioner.class` | `TimeBasedPartitioner` | Phân folder theo thời gian |
| `path.format` | `year=YYYY/month=MM/day=dd` | Cấu trúc thư mục: `year=2018/month=11/day=01` |

### 3.3. Cấu trúc file trong MinIO sau khi chạy

```
bigdata/
└── bronze/
    ├── olist.public.orders/
    │   ├── year=2017/month=10/day=02/
    │   │   └── olist.public.orders+0+0000000000.snappy.parquet
    │   ├── year=2018/month=01/day=15/
    │   │   └── olist.public.orders+0+0000000500.snappy.parquet
    │   └── year=2018/month=11/day=01/
    │       ├── olist.public.orders+0+0000001000.snappy.parquet
    │       └── olist.public.orders+0+0000001500.snappy.parquet
    │
    ├── olist.public.order_items/
    │   └── year=2018/month=11/day=01/
    │       └── ...parquet
    │
    ├── olist.public.order_payments/
    │   └── ...
    ├── olist.public.order_reviews/
    │   └── ...
    ├── olist.public.customers/
    │   └── ...
    ├── olist.public.products/
    │   └── ...
    ├── olist.public.sellers/
    │   └── ...
    ├── olist.public.geolocation/
    │   └── ...
    └── olist.public.product_category_name_translation/
        └── ...
```

## 4. Đăng ký S3 Sink Connector

```bash
# Kiểm tra Kafka Connect có plugin S3 Sink
curl -s http://localhost:8083/connector-plugins | jq '.[].class' | grep -i s3
# Phải thấy: "io.confluent.connect.s3.S3SinkConnector"

# Đăng ký connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-bronze.json

# Kiểm tra trạng thái
curl -s http://localhost:8083/connectors/olist-s3-sink-bronze/status | jq .
```

## 5. Xác minh dữ liệu Bronze trong MinIO

### 5.1. Qua MinIO Console

Truy cập `http://localhost:9001` → login → browse bucket `bigdata` → thấy folder `bronze/`.

### 5.2. Qua MinIO Client (mc)

```bash
# Kiểm tra files trong bronze
docker exec minio-mc mc ls myminio/bigdata/bronze/ --recursive

# Xem tổng dung lượng
docker exec minio-mc mc du myminio/bigdata/bronze/
```

### 5.3. Qua PySpark (kiểm tra đọc được Parquet)

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("verify-bronze") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "ACCESS_KEY") \
    .config("spark.hadoop.fs.s3a.secret.key", "SECRET_KEY") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .getOrCreate()

# Đọc Bronze orders
df = spark.read.parquet("s3a://bigdata/bronze/olist.public.orders/")
df.printSchema()
df.show(5)
df.count()
```

## 6. Tuning hiệu suất cho S3 Sink

| Tham số | Khuyến nghị cho dev | Production |
|---|---|---|
| `flush.size` | 500 | 5000-10000 |
| `rotate.interval.ms` | 60000 (1 phút) | 600000 (10 phút) |
| `tasks.max` | 3 | = số partitions Kafka |
| `parquet.codec` | snappy | snappy hoặc zstd |

- **`flush.size` nhỏ:** File nhỏ, nhiều files → Spark chậm khi đọc (quá nhiều small files)
- **`flush.size` lớn:** File lớn, ít files → Spark nhanh hơn nhưng dữ liệu tới MinIO chậm hơn

## 7. Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|---|---|---|
| `Unable to connect to S3` | MinIO hostname sai hoặc khác network | Đảm bảo cùng `minio-network` |
| `Access Denied` | Sai Access Key/Secret Key | Kiểm tra credentials từ `init-bucket.sh` |
| `Bucket does not exist` | Bucket `bigdata` chưa tạo | Chạy lại `init-bucket.sh` |
| `No suitable converter found` | Schema conflict | Thêm `"schema.compatibility": "NONE"` |
| `Parquet schema mismatch` | Schema thay đổi giữa các records | Cài đặt SMT để flatten Debezium envelope |
