# 02 — Cấu hình PostgreSQL cho Debezium CDC

## 1. Yêu cầu bắt buộc: Bật logical replication

Debezium đọc WAL log, nhưng PostgreSQL mặc định KHÔNG bật logical decoding. Phải cấu hình trước.

### 1.1. Thêm cấu hình vào `postgresql.conf`

```properties
# Bật logical replication (bắt buộc cho Debezium)
wal_level = logical

# Số lượng replication slots tối đa (Debezium cần 1 slot)
max_replication_slots = 4

# Số sender processes cho WAL streaming
max_wal_senders = 4

# Giữ WAL segments cho replication (tránh bị xóa trước khi Debezium đọc)
wal_keep_size = 512MB
```

### 1.2. Cấu hình trong Docker Compose

Thêm PostgreSQL service vào `docker-compose.yml`:

```yaml
  postgres:
    image: postgres:16
    container_name: bigdata-postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: olist
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-postgres.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    command:
      - "postgres"
      - "-c"
      - "wal_level=logical"
      - "-c"
      - "max_replication_slots=4"
      - "-c"
      - "max_wal_senders=4"
    networks:
      - kafka-network
      - minio-network
```

> **Lưu ý:** PostgreSQL phải nằm cùng network với Kafka (`kafka-network`) để Debezium kết nối được.

### 1.3. Cấu hình `pg_hba.conf` (cho phép replication connections)

```
# Cho phép replication từ Debezium
host    replication     all     0.0.0.0/0       md5
host    all             all     0.0.0.0/0       md5
```

Trong Docker, thêm vào command:
```yaml
    command:
      - "postgres"
      - "-c"
      - "wal_level=logical"
      - "-c"
      - "max_replication_slots=4"
      - "-c"
      - "max_wal_senders=4"
      - "-c"
      - "hba_file=/var/lib/postgresql/data/pg_hba.conf"
```

## 2. Schema PostgreSQL (từ entity của dự án)

Dựa trên 9 entity Java hiện tại, schema PostgreSQL cần tạo:

### 2.1. Bảng `customers`

```sql
CREATE TABLE customers (
    customer_id              VARCHAR(50) PRIMARY KEY,
    customer_unique_id       VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(5),
    customer_city            VARCHAR(100),
    customer_state           VARCHAR(2)
);
```

**Debezium topic:** `olist.public.customers`
**Primary key cho CDC:** `customer_id`

### 2.2. Bảng `orders`

```sql
CREATE TABLE orders (
    order_id                       VARCHAR(50) PRIMARY KEY,
    customer_id                    VARCHAR(50) NOT NULL REFERENCES customers(customer_id),
    order_status                   VARCHAR(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);

CREATE INDEX idx_order_status ON orders(order_status);
CREATE INDEX idx_order_purchase_timestamp ON orders(order_purchase_timestamp);
```

**Debezium topic:** `olist.public.orders`
**Primary key cho CDC:** `order_id`

### 2.3. Bảng `products`

```sql
CREATE TABLE products (
    product_id                 VARCHAR(50) PRIMARY KEY,
    product_category_name      VARCHAR(100),
    product_name_lenght        INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty         INTEGER,
    product_weight_g           INTEGER,
    product_length_cm          INTEGER,
    product_height_cm          INTEGER,
    product_width_cm           INTEGER
);
```

**Debezium topic:** `olist.public.products`
**Primary key cho CDC:** `product_id`

### 2.4. Bảng `sellers`

```sql
CREATE TABLE sellers (
    seller_id              VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(5),
    seller_city            VARCHAR(100),
    seller_state           VARCHAR(2)
);
```

**Debezium topic:** `olist.public.sellers`
**Primary key cho CDC:** `seller_id`

### 2.5. Bảng `order_items`

```sql
CREATE TABLE order_items (
    order_id            VARCHAR(50) REFERENCES orders(order_id),
    order_item_id       INTEGER,
    product_id          VARCHAR(50) REFERENCES products(product_id),
    seller_id           VARCHAR(50) REFERENCES sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price               DECIMAL(10,2),
    freight_value       DECIMAL(10,2),
    PRIMARY KEY (order_id, order_item_id)
);
```

**Debezium topic:** `olist.public.order_items`
**Composite key cho CDC:** `(order_id, order_item_id)`

### 2.6. Bảng `order_payments`

```sql
CREATE TABLE order_payments (
    order_id             VARCHAR(50) REFERENCES orders(order_id),
    payment_sequential   INTEGER,
    payment_type         VARCHAR(20),
    payment_installments INTEGER,
    payment_value        DECIMAL(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);
```

**Debezium topic:** `olist.public.order_payments`
**Composite key cho CDC:** `(order_id, payment_sequential)`

### 2.7. Bảng `order_reviews`

```sql
CREATE TABLE order_reviews (
    review_id                VARCHAR(50) PRIMARY KEY,
    order_id                 VARCHAR(50) REFERENCES orders(order_id),
    review_score             INTEGER CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title     VARCHAR(255),
    review_comment_message   TEXT,
    review_creation_date     TIMESTAMP,
    review_answer_timestamp  TIMESTAMP
);
```

**Debezium topic:** `olist.public.order_reviews`
**Primary key cho CDC:** `review_id`

### 2.8. Bảng `geolocation`

```sql
CREATE TABLE geolocation (
    id                          BIGSERIAL PRIMARY KEY,
    geolocation_zip_code_prefix VARCHAR(5),
    geolocation_lat             DOUBLE PRECISION,
    geolocation_lng             DOUBLE PRECISION,
    geolocation_city            VARCHAR(100),
    geolocation_state           VARCHAR(2)
);
```

**Debezium topic:** `olist.public.geolocation`
**Primary key cho CDC:** `id`

### 2.9. Bảng `product_category_name_translation`

```sql
CREATE TABLE product_category_name_translation (
    product_category_name         VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);
```

**Debezium topic:** `olist.public.product_category_name_translation`
**Primary key cho CDC:** `product_category_name`

## 3. Kiểm tra PostgreSQL đã sẵn sàng cho Debezium

Sau khi khởi tạo, chạy các lệnh kiểm tra:

```sql
-- Kiểm tra wal_level
SHOW wal_level;
-- Kết quả phải là: logical

-- Kiểm tra max_replication_slots
SHOW max_replication_slots;
-- Kết quả phải >= 4

-- Kiểm tra max_wal_senders
SHOW max_wal_senders;
-- Kết quả phải >= 4

-- Kiểm tra tất cả bảng đã tạo
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' ORDER BY table_name;
-- Phải có 9 bảng
```

## 4. Lưu ý quan trọng

> [!WARNING]
> **Bảng PHẢI có PRIMARY KEY.** Debezium cần PK để xác định record nào bị thay đổi. Bảng không có PK sẽ KHÔNG hoạt động với CDC.

Tất cả 9 bảng trong dự án đều có PK (đã kiểm tra từ entity) — đáp ứng yêu cầu.

> [!NOTE]
> **REPLICA IDENTITY.** Mặc định PostgreSQL chỉ gửi giá trị cũ của PK columns khi UPDATE/DELETE. Nếu muốn Debezium gửi đầy đủ cả giá trị cũ (before) và mới (after) của tất cả columns, chạy:
> ```sql
> ALTER TABLE orders REPLICA IDENTITY FULL;
> ALTER TABLE order_items REPLICA IDENTITY FULL;
> -- ... tương tự cho các bảng khác
> ```
