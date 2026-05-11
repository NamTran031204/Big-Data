# 03 — Cấu hình Debezium Source Connector

## 1. Debezium là gì trong Kafka Connect?

Debezium **không phải** một service độc lập. Nó là một **plugin** chạy bên trong **Kafka Connect**.

```
Kafka Connect (container debezium/connect:2.4)
    ├── Debezium PostgreSQL Connector (plugin, đã cài sẵn trong image)
    └── REST API (:8083) ← dùng để đăng ký connector qua HTTP
```

**Quy trình:**
1. Kafka Connect khởi động → load plugins
2. Bạn gửi HTTP POST request tới `:8083` với cấu hình connector
3. Kafka Connect tạo connector instance, bắt đầu đọc WAL PostgreSQL
4. CDC events tự động publish lên Kafka topics

## 2. Docker Compose cho Kafka Connect + Debezium

Cập nhật service trong `docker-compose.yml`:

```yaml
  debezium-connect:
    image: quay.io/debezium/connect:2.4
    container_name: debezium-connect
    depends_on:
      - kafka
      - postgres
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
      # Plugin path cho S3 Sink Connector (cài thêm sau)
      CONNECT_PLUGIN_PATH: /kafka/connect
    networks:
      - kafka-network
```

> **Lưu ý:** `BOOTSTRAP_SERVERS` dùng `kafka:29092` (internal listener) chứ không phải `localhost:9092`.

## 3. Cấu hình Debezium PostgreSQL Source Connector

### 3.1. File cấu hình JSON

Tạo file `connectors/debezium-postgres-source.json`:

```json
{
  "name": "olist-postgres-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",

    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres_user",
    "database.password": "postgres_password",
    "database.dbname": "olist",
    "database.server.name": "olist",

    "topic.prefix": "olist",
    "schema.include.list": "public",

    "table.include.list": "public.orders,public.order_items,public.order_payments,public.order_reviews,public.customers,public.products,public.sellers,public.geolocation,public.product_category_name_translation",

    "plugin.name": "pgoutput",

    "slot.name": "debezium_olist",
    "publication.name": "dbz_publication",

    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "key.converter.schemas.enable": false,
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": false,

    "snapshot.mode": "initial",

    "heartbeat.interval.ms": "10000",
    "tombstones.on.delete": false,

    "transforms": "route",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "olist\\.public\\.(.*)",
    "transforms.route.replacement": "olist.public.$1"
  }
}
```

### 3.2. Giải thích từng tham số quan trọng

| Tham số | Giá trị | Ý nghĩa |
|---|---|---|
| `connector.class` | `...PostgresConnector` | Loại connector: đọc từ PostgreSQL |
| `topic.prefix` | `olist` | Prefix cho Kafka topics: `olist.public.orders`, `olist.public.customers`,... |
| `schema.include.list` | `public` | Chỉ theo dõi schema `public` |
| `table.include.list` | 9 bảng | Liệt kê cụ thể 9 bảng cần theo dõi |
| `plugin.name` | `pgoutput` | Plugin decode WAL (PostgreSQL 10+ dùng `pgoutput`) |
| `slot.name` | `debezium_olist` | Tên replication slot trong PostgreSQL |
| `snapshot.mode` | `initial` | Lần đầu: snapshot toàn bộ dữ liệu → sau đó chuyển sang streaming |
| `key.converter` | JsonConverter | Format key: JSON (đơn giản, dễ debug) |
| `value.converter` | JsonConverter | Format value: JSON |

### 3.3. Snapshot Mode giải thích

`snapshot.mode: initial` nghĩa là:

```
Lần đầu Debezium khởi chạy:
  1. Lock bảng (briefly)
  2. SELECT * FROM orders → publish tất cả records hiện có lên Kafka
  3. SELECT * FROM customers → publish tất cả records lên Kafka
  4. ... (lặp cho 9 bảng)
  5. Release lock
  6. Bắt đầu streaming từ WAL (CDC mode)

Các lần sau (restart):
  - Không snapshot lại
  - Tiếp tục đọc WAL từ vị trí lưu trong offset
```

## 4. Đăng ký Connector qua REST API

### 4.1. Đăng ký Debezium Source Connector

```bash
# Đợi Kafka Connect sẵn sàng
curl -s http://localhost:8083/ | jq .

# Đăng ký connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/debezium-postgres-source.json
```

### 4.2. Kiểm tra trạng thái

```bash
# Danh sách connectors
curl -s http://localhost:8083/connectors | jq .

# Trạng thái connector cụ thể
curl -s http://localhost:8083/connectors/olist-postgres-source/status | jq .

# Kết quả mong đợi:
# {
#   "name": "olist-postgres-source",
#   "connector": { "state": "RUNNING" },
#   "tasks": [{ "id": 0, "state": "RUNNING" }]
# }
```

### 4.3. Xóa / cập nhật connector

```bash
# Xóa connector
curl -X DELETE http://localhost:8083/connectors/olist-postgres-source

# Cập nhật cấu hình
curl -X PUT http://localhost:8083/connectors/olist-postgres-source/config \
  -H "Content-Type: application/json" \
  -d @connectors/debezium-postgres-source-v2.json
```

## 5. Kafka Topics được tạo tự động

Sau khi connector chạy, Debezium tự tạo các topic:

```
olist.public.orders                              ← CDC events bảng orders
olist.public.order_items                         ← CDC events bảng order_items
olist.public.order_payments                      ← CDC events bảng order_payments
olist.public.order_reviews                       ← CDC events bảng order_reviews
olist.public.customers                           ← CDC events bảng customers
olist.public.products                            ← CDC events bảng products
olist.public.sellers                             ← CDC events bảng sellers
olist.public.geolocation                         ← CDC events bảng geolocation
olist.public.product_category_name_translation   ← CDC events bảng category
```

Kiểm tra trên Kafka UI (`http://localhost:8080`) hoặc:

```bash
# List topics
docker exec kafka-broker kafka-topics --list --bootstrap-server localhost:9092

# Xem messages trong topic orders (10 messages đầu)
docker exec kafka-broker kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic olist.public.orders \
  --from-beginning \
  --max-messages 10
```

## 6. Format CDC Event từ Debezium

Mỗi message trên Kafka topic có dạng:

### 6.1. INSERT event (op = "c")

```json
{
  "before": null,
  "after": {
    "order_id": "e481f51cbdc54678b7cc49136f2d6af7",
    "customer_id": "9ef432eb6251297304e76186b10a928d",
    "order_status": "delivered",
    "order_purchase_timestamp": 1533686400000000,
    "order_approved_at": 1533772800000000,
    "order_delivered_carrier_date": 1534032000000000,
    "order_delivered_customer_date": 1534204800000000,
    "order_estimated_delivery_date": 1535328000000000
  },
  "source": {
    "version": "2.4.0.Final",
    "connector": "postgresql",
    "name": "olist",
    "ts_ms": 1699000000000,
    "db": "olist",
    "schema": "public",
    "table": "orders"
  },
  "op": "c",
  "ts_ms": 1699000001000
}
```

### 6.2. UPDATE event (op = "u")

```json
{
  "before": {
    "order_id": "e481f51cbdc54678b7cc49136f2d6af7",
    "order_status": "shipped"
  },
  "after": {
    "order_id": "e481f51cbdc54678b7cc49136f2d6af7",
    "order_status": "delivered",
    "order_delivered_customer_date": 1534204800000000
  },
  "op": "u"
}
```

### 6.3. DELETE event (op = "d")

```json
{
  "before": {
    "order_id": "e481f51cbdc54678b7cc49136f2d6af7"
  },
  "after": null,
  "op": "d"
}
```

> **Lưu ý:** Timestamps trong Debezium CDC được trả về dạng **microseconds since epoch**, không phải ISO string. S3 Sink Connector hoặc Spark cần convert khi đọc.

## 7. Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|---|---|---|
| `FAILED: io.debezium.DebeziumException` | PostgreSQL chưa bật `wal_level=logical` | Kiểm tra `SHOW wal_level;` |
| `Replication slot already exists` | Connector cũ chưa dọn slot | `SELECT pg_drop_replication_slot('debezium_olist');` |
| `Connection refused` | Sai hostname hoặc khác network | Đảm bảo postgres cùng `kafka-network` |
| `Permission denied for replication` | User không có quyền replication | `ALTER ROLE postgres_user REPLICATION;` |
