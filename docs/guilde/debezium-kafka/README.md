# Hướng dẫn triển khai: Debezium → Kafka Connect → MinIO

## Tổng quan Pipeline

```
PostgreSQL (9 bảng Olist)
    ↓ WAL Log (không query database)
Debezium Source Connector (plugin Kafka Connect)
    ↓ CDC events tự động publish
Kafka Broker (9 topics)
    ↓ Consumer tự động
S3 Sink Connector (plugin Kafka Connect)
    ↓ JSON → Parquet, partitioned by date
MinIO Bronze Layer (s3a://bigdata/bronze/)
```

**Không cần viết Java Producer/Consumer.** Toàn bộ pipeline chạy bằng cấu hình JSON.

---

## Tài liệu hướng dẫn

| # | File | Nội dung |
|---|---|---|
| 01 | [Architecture Overview](01-architecture-overview.md) | Sơ đồ kiến trúc, vai trò từng thành phần, luồng dữ liệu |
| 02 | [PostgreSQL Setup](02-postgresql-setup.md) | Bật WAL logical, schema 9 bảng (từ JPA entity), kiểm tra readiness |
| 03 | [Debezium Source Connector](03-debezium-source-connector.md) | Cấu hình connector JSON, REST API, CDC event format, snapshot mode |
| 04 | [S3 Sink Connector](04-s3-sink-connector.md) | Cài plugin, cấu hình Parquet output, partitioning, tuning |
| 05 | [Docker Compose & Deployment](05-docker-compose-deployment.md) | Docker Compose tổng hợp, .env, triển khai từng bước, scripts |
| 06 | [Advanced & Troubleshooting](06-advanced-and-troubleshooting.md) | SMT transform, Schema Registry, monitoring, xử lý lỗi |

---

## Quick Start

```bash
# 1. Tạo thư mục
mkdir -p data/minio docker/kafka-connect connectors

# 2. Khởi động services
docker compose up -d

# 3. Đợi tất cả healthy (~60 giây)
docker compose ps

# 4. Đăng ký connectors
./scripts/register-connectors.sh

# 5. Kiểm tra data trong MinIO
docker exec minio-mc mc ls myminio/bigdata/bronze/ --recursive
```

---

## Mapping với các bảng trong dự án

| PostgreSQL Table | Kafka Topic | MinIO Bronze Path |
|---|---|---|
| `orders` | `olist.public.orders` | `bronze/olist.public.orders/year=.../` |
| `order_items` | `olist.public.order_items` | `bronze/olist.public.order_items/year=.../` |
| `order_payments` | `olist.public.order_payments` | `bronze/olist.public.order_payments/year=.../` |
| `order_reviews` | `olist.public.order_reviews` | `bronze/olist.public.order_reviews/year=.../` |
| `customers` | `olist.public.customers` | `bronze/olist.public.customers/year=.../` |
| `products` | `olist.public.products` | `bronze/olist.public.products/year=.../` |
| `sellers` | `olist.public.sellers` | `bronze/olist.public.sellers/year=.../` |
| `geolocation` | `olist.public.geolocation` | `bronze/olist.public.geolocation/year=.../` |
| `product_category_name_translation` | `olist.public.product_category_name_translation` | `bronze/olist.public.product_category_name_translation/year=.../` |
