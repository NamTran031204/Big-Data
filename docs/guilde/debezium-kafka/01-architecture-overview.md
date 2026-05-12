# 01 — Tổng quan Kiến trúc: Debezium → Kafka Connect → MinIO

## 1. Sơ đồ tổng thể

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL (OLTP)                                │
│  9 bảng: orders, order_items, order_payments, order_reviews,           │
│          customers, products, sellers, geolocation,                    │
│          product_category_name_translation                             │
│                                                                        │
│  WAL (Write-Ahead Log) ← ghi lại mọi INSERT/UPDATE/DELETE             │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │  Debezium đọc WAL (không query table)
                   ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                     Kafka Connect Cluster                               │
│                                                                        │
│  ┌────────────────────────┐     ┌─────────────────────────────┐        │
│  │  SOURCE CONNECTOR       │     │  SINK CONNECTOR              │        │
│  │  (Debezium PostgreSQL)  │     │  (S3/MinIO Sink)             │        │
│  │                         │     │                              │        │
│  │  WAL → Kafka Topics     │     │  Kafka Topics → MinIO/Bronze │        │
│  └────────────┬────────────┘     └──────────────┬──────────────┘        │
│               │                                  │                      │
└───────────────┼──────────────────────────────────┼──────────────────────┘
                ↓                                  ↑
┌──────────────────────────────────────────────────────────────────────────┐
│                        Apache Kafka Broker                              │
│                                                                        │
│  Topics:                                                               │
│    olist.public.orders                    (99K+ records)               │
│    olist.public.order_items               (112K+ records)              │
│    olist.public.order_payments            (103K+ records)              │
│    olist.public.order_reviews             (99K+ records)               │
│    olist.public.customers                 (99K+ records)               │
│    olist.public.products                  (32K+ records)               │
│    olist.public.sellers                   (3K+ records)                │
│    olist.public.geolocation               (1M+ records)               │
│    olist.public.product_category_name_translation  (71 records)        │
│                                                                        │
│  Internal Topics (Kafka Connect):                                      │
│    my_connect_configs                                                  │
│    my_connect_offsets                                                  │
│    my_connect_statuses                                                 │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ↓ S3 Sink Connector đọc từ topics
┌──────────────────────────────────────────────────────────────────────────┐
│                        MinIO (S3-compatible)                            │
│                                                                        │
│  Bucket: bigdata                                                       │
│    └── bronze/                                                         │
│        ├── orders/              year=2018/month=11/part-0001.parquet   │
│        ├── order_items/         year=2018/month=11/part-0001.parquet   │
│        ├── order_payments/      ...                                    │
│        ├── order_reviews/       ...                                    │
│        ├── customers/           ...                                    │
│        ├── products/            ...                                    │
│        ├── sellers/             ...                                    │
│        ├── geolocation/         ...                                    │
│        └── category_translation/...                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

## 2. Thành phần và vai trò

| Thành phần | Vai trò | Cần viết code? |
|---|---|---|
| **PostgreSQL** | Database nguồn, chứa 9 bảng Olist | Không (đã có entity từ Spring Boot) |
| **Debezium Source Connector** | Đọc WAL log, tự động publish CDC events lên Kafka | Không — cấu hình JSON |
| **Kafka Broker** | Trung gian lưu trữ và truyền tải events | Không — đã có trong docker-compose |
| **Kafka Connect** | Framework chạy Source + Sink connectors | Không — dùng Docker image `debezium/connect` |
| **S3 Sink Connector** | Đọc từ Kafka topics, ghi Parquet files xuống MinIO | Không — cấu hình JSON |
| **MinIO** | Object storage S3-compatible, lưu Bronze data | Không — đã có trong docker-compose |

> **Không cần viết một dòng Java Producer/Consumer nào.** Toàn bộ pipeline hoạt động qua cấu hình connector.

## 3. Luồng dữ liệu chi tiết theo thời gian

```
T=0s   Ứng dụng Spring Boot INSERT đơn hàng mới vào PostgreSQL
T=0s   PostgreSQL ghi vào WAL: "INSERT orders: {order_id='abc123', ...}"
T=~1s  Debezium đọc WAL, tạo CDC event, publish lên topic olist.public.orders
T=~1s  Kafka nhận message, lưu vào partition, replicate
T=~5s  S3 Sink Connector batch đủ records (hoặc hết flush interval)
T=~5s  S3 Sink Connector ghi file Parquet xuống MinIO: bronze/orders/...
```

## 4. Tại sao dùng Kafka Connect thay vì tự viết code?

| Tự viết Java Consumer | Kafka Connect |
|---|---|
| Phải tự manage offset | Tự động manage offset |
| Phải tự handle partition rebalance | Tự động handle |
| Phải tự chuyển đổi JSON → Parquet | Có sẵn Parquet converter |
| Phải tự retry khi MinIO down | Có sẵn retry + dead letter queue |
| Phải tự scale khi throughput tăng | Tự scale theo tasks config |
| ~500 dòng Java code | ~50 dòng JSON config |
