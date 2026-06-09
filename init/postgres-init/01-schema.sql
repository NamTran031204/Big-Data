-- =====================================================================
-- Olist OLTP schema (PostgreSQL)
-- Tạo 9 bảng nguồn. Debezium yêu cầu mỗi bảng có PRIMARY KEY.
-- Các bảng có khả năng trùng key tự nhiên (geolocation theo zip,
-- order_reviews theo review_id) dùng surrogate key BIGSERIAL.
-- Tên bảng khớp với spark-batch/schemas.py và topic Debezium
-- olist_cdc.public.<table>.
-- =====================================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id              VARCHAR(64) PRIMARY KEY,
    customer_unique_id       VARCHAR(64),
    customer_zip_code_prefix INTEGER,
    customer_city            VARCHAR(128),
    customer_state           VARCHAR(8)
);

-- geolocation: nhiều dòng trên cùng 1 zip -> surrogate PK
CREATE TABLE IF NOT EXISTS geolocation (
    id                          BIGSERIAL PRIMARY KEY,
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat             DOUBLE PRECISION,
    geolocation_lng             DOUBLE PRECISION,
    geolocation_city            VARCHAR(128),
    geolocation_state           VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id              VARCHAR(64) PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city            VARCHAR(128),
    seller_state           VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS products (
    product_id                 VARCHAR(64) PRIMARY KEY,
    product_category_name      VARCHAR(128),
    product_name_lenght        INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty         INTEGER,
    product_weight_g           INTEGER,
    product_length_cm          INTEGER,
    product_height_cm          INTEGER,
    product_width_cm           INTEGER
);

CREATE TABLE IF NOT EXISTS category_translation (
    product_category_name         VARCHAR(128) PRIMARY KEY,
    product_category_name_english VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id                      VARCHAR(64) PRIMARY KEY,
    customer_id                   VARCHAR(64),
    order_status                  VARCHAR(32),
    order_purchase_timestamp      TIMESTAMP,
    order_approved_at             TIMESTAMP,
    order_delivered_carrier_date  TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id            VARCHAR(64),
    order_item_id       INTEGER,
    product_id          VARCHAR(64),
    seller_id           VARCHAR(64),
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(12,2),
    freight_value       NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS order_payments (
    order_id             VARCHAR(64),
    payment_sequential   INTEGER,
    payment_type         VARCHAR(32),
    payment_installments INTEGER,
    payment_value        NUMERIC(12,2),
    PRIMARY KEY (order_id, payment_sequential)
);

-- order_reviews: review_id KHÔNG duy nhất trong dataset -> surrogate PK
CREATE TABLE IF NOT EXISTS order_reviews (
    id                      BIGSERIAL PRIMARY KEY,
    review_id               VARCHAR(64),
    order_id                VARCHAR(64),
    review_score            INTEGER,
    review_comment_title    VARCHAR(256),
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);
