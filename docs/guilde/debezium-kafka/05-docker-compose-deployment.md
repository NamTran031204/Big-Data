# 05 — Docker Compose Tổng hợp & Triển khai

## 1. Docker Compose hoàn chỉnh

Dưới đây là cấu hình Docker Compose đầy đủ tích hợp tất cả services cần thiết cho pipeline Debezium → Kafka → MinIO:

```yaml
version: '3.8'

services:
  # ============================================================
  # 1. PostgreSQL (Source Database)
  # ============================================================
  postgres:
    image: postgres:16
    container_name: bigdata-postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: olist
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./spark-batch/init-postgres.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    command:
      - "postgres"
      - "-c" 
      - "wal_level=logical"
      - "-c"
      - "max_replication_slots=4"
      - "-c"
      - "max_wal_senders=4"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - kafka-network
      - minio-network

  # ============================================================
  # 2. Zookeeper (Kafka dependency)
  # ============================================================
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: kafka-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    networks:
      - kafka-network

  # ============================================================
  # 3. Kafka Broker
  # ============================================================
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: kafka-broker
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "9094:9094"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092,PLAINTEXT_DOCKER://kafka:9094
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT,PLAINTEXT_DOCKER:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_LOG_RETENTION_HOURS: 168
    healthcheck:
      test: ["CMD-SHELL", "kafka-topics --bootstrap-server localhost:9092 --list"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - kafka-network

  # ============================================================
  # 4. Kafka UI
  # ============================================================
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: kafka-ui
    depends_on:
      - kafka
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9094
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
      KAFKA_CLUSTERS_0_KAFKACONNECT_0_NAME: debezium
      KAFKA_CLUSTERS_0_KAFKACONNECT_0_ADDRESS: http://debezium-connect:8083
    networks:
      - kafka-network

  # ============================================================
  # 5. Kafka Connect + Debezium + S3 Sink
  # ============================================================
  debezium-connect:
    build:
      context: ./docker/kafka-connect
      dockerfile: Dockerfile
    container_name: debezium-connect
    depends_on:
      kafka:
        condition: service_healthy
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
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
      AWS_ACCESS_KEY_ID: ${MINIO_ACCESS_KEY}
      AWS_SECRET_ACCESS_KEY: ${MINIO_SECRET_KEY}
    networks:
      - kafka-network
      - minio-network

  # ============================================================
  # 6. MinIO (Object Storage - Bronze Layer)
  # ============================================================
  minio:
    image: minio/minio:RELEASE.2025-06-13T11-33-47Z
    container_name: minio-server
    hostname: minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      MINIO_PROMETHEUS_AUTH_TYPE: "public"
    volumes:
      - minio-data:/data
      - ./config:/root/.minio
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    networks:
      - minio-network

  # ============================================================
  # 7. MinIO Client (Tạo bucket + access key)
  # ============================================================
  mc:
    image: minio/mc:latest
    container_name: minio-mc
    depends_on:
      minio:
        condition: service_healthy
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - ./spark-batch/init-bucket.sh:/spark-batch/init-bucket.sh:ro
      - ./config:/config
    entrypoint: /bin/sh
    command: ["/spark-batch/init-bucket.sh"]
    networks:
      - minio-network

  # ============================================================
  # 8. MongoDB (Serving Layer - Gold Data)
  # ============================================================
  mongodb:
    image: mongo:7.0
    container_name: bigdata-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: metadata
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db

volumes:
  postgres_data:
  minio-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./data/minio
  mongodb_data:

networks:
  minio-network:
    driver: bridge
  kafka-network:
    driver: bridge
```

## 2. File .env

Tạo file `.env` trong cùng thư mục:

```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# MinIO
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=admin123456
MINIO_ACCESS_KEY=<lấy từ init-bucket.sh output>
MINIO_SECRET_KEY=<lấy từ init-bucket.sh output>

# MongoDB
MONGO_USER=admin
MONGO_PASSWORD=mongo123456
```

## 3. Thứ tự triển khai từng bước

### Bước 1: Khởi động infrastructure

```bash
# Tạo thư mục data
mkdir -p data/minio

# Khởi động tất cả services
docker compose up -d

# Kiểm tra tất cả services đã healthy
docker compose ps
```

### Bước 2: Kiểm tra PostgreSQL

```bash
# Kết nối PostgreSQL
docker exec -it bigdata-postgres psql -U postgres -d olist

# Kiểm tra WAL level
SHOW wal_level;
-- Phải là: logical

# Kiểm tra 9 bảng
\dt
```

### Bước 3: Kiểm tra Kafka

```bash
# Kiểm tra Kafka hoạt động
docker exec kafka-broker kafka-topics --list --bootstrap-server localhost:9092

# Mở Kafka UI
# Truy cập http://localhost:8080
```

### Bước 4: Kiểm tra MinIO

```bash
# Kiểm tra MinIO
docker exec minio-mc mc ls myminio/

# Kiểm tra bucket bigdata
docker exec minio-mc mc ls myminio/bigdata/

# Mở MinIO Console
# Truy cập http://localhost:9001
```

### Bước 5: Kiểm tra Kafka Connect

```bash
# Đợi Kafka Connect sẵn sàng (có thể mất 30-60 giây)
curl -s http://localhost:8083/ | jq .

# Kiểm tra plugins đã cài
curl -s http://localhost:8083/connector-plugins | jq '.[].class'
# Phải thấy:
# "io.debezium.connector.postgresql.PostgresConnector"
# "io.confluent.connect.s3.S3SinkConnector"
```

### Bước 6: Đăng ký Debezium Source Connector

```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/debezium-postgres-source.json

# Kiểm tra trạng thái
curl -s http://localhost:8083/connectors/olist-postgres-source/status | jq .
```

### Bước 7: Đăng ký S3 Sink Connector

```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-bronze.json

# Kiểm tra trạng thái
curl -s http://localhost:8083/connectors/olist-s3-sink-bronze/status | jq .
```

### Bước 8: Xác minh end-to-end

```bash
# Kiểm tra Kafka topics (9 topics mới từ Debezium)
docker exec kafka-broker kafka-topics --list --bootstrap-server localhost:9092

# Kiểm tra data đã vào MinIO
docker exec minio-mc mc ls myminio/bigdata/bronze/ --recursive | head -20

# Kiểm tra số lượng files
docker exec minio-mc mc ls myminio/bigdata/bronze/ --recursive | wc -l
```

## 4. Script đăng ký tất cả connectors

Tạo file `scripts/register-connectors.sh`:

```bash
#!/bin/bash
set -e

CONNECT_URL="http://localhost:8083"

echo "Đang đợi Kafka Connect sẵn sàng..."
while ! curl -s ${CONNECT_URL}/ > /dev/null 2>&1; do
    echo "  Đang chờ..."
    sleep 5
done
echo "✓ Kafka Connect sẵn sàng!"

echo ""
echo "Đăng ký Debezium PostgreSQL Source Connector..."
curl -X POST ${CONNECT_URL}/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/debezium-postgres-source.json
echo ""
echo "✓ Debezium Source Connector đã đăng ký!"

echo ""
echo "Đợi 10 giây để Debezium snapshot dữ liệu..."
sleep 10

echo ""
echo "Đăng ký S3 Sink Connector (Kafka → MinIO/Bronze)..."
curl -X POST ${CONNECT_URL}/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/s3-sink-bronze.json
echo ""
echo "✓ S3 Sink Connector đã đăng ký!"

echo ""
echo "Kiểm tra trạng thái connectors..."
echo "  Source: $(curl -s ${CONNECT_URL}/connectors/olist-postgres-source/status | jq -r '.connector.state')"
echo "  Sink:   $(curl -s ${CONNECT_URL}/connectors/olist-s3-sink-bronze/status | jq -r '.connector.state')"

echo ""
echo "============================================"
echo "  ✓ Pipeline Debezium → Kafka → MinIO hoàn tất!"
echo "============================================"
```

## 5. Kiểm tra trạng thái toàn bộ pipeline

```bash
# Script kiểm tra nhanh
echo "=== PostgreSQL ==="
docker exec bigdata-postgres pg_isready && echo "✓ OK" || echo "✗ FAIL"

echo "=== Kafka ==="
docker exec kafka-broker kafka-topics --list --bootstrap-server localhost:9092 | wc -l

echo "=== Kafka Connect ==="
curl -s http://localhost:8083/connectors | jq .

echo "=== Source Connector ==="
curl -s http://localhost:8083/connectors/olist-postgres-source/status | jq '.connector.state'

echo "=== Sink Connector ==="
curl -s http://localhost:8083/connectors/olist-s3-sink-bronze/status | jq '.connector.state'

echo "=== MinIO Bronze ==="
docker exec minio-mc mc du myminio/bigdata/bronze/
```
