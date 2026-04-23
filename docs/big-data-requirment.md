# BÁO CÁO PHÂN TÍCH YÊU CẦU VÀ TRIỂN KHAI DỰ ÁN BIG DATA

## PHẦN 0: YÊU CẦU CỦA GIẢNG VIÊN

### I. Mục tiêu và yêu cầu chung

Bài tập lớn yêu cầu sinh viên xây dựng một hệ thống xử lý dữ liệu lớn hoàn chỉnh, vận dụng kiến thức đã học để giải quyết bài toán thực tế. Sinh viên phải triển khai một trong hai mô hình kiến trúc: **Kiến trúc Lambda** hoặc **Kiến trúc Kappa**, tập trung xây dựng pipeline dữ liệu end-to-end (thu thập → xử lý → lưu trữ → trực quan hóa).

### II. Yêu cầu kỹ thuật

| Thành phần | Công nghệ |
|-----------|-----------|
| Xử lý dữ liệu | Apache Spark (PySpark hoặc Scala) |
| Lưu trữ phân tán | HDFS hoặc tương đương |
| Hàng đợi tin nhắn | Apache Kafka, RabbitMQ, v.v. |
| Cơ sở dữ liệu | NoSQL |
| Triển khai | Kubernetes hoặc Cloud (không khuyến khích chỉ dùng Docker) |

### III. Yêu cầu xử lý dữ liệu với Spark

Sinh viên cần thể hiện kỹ năng Spark mức trung cấp qua các phép biến đổi và hành động đa dạng. Nếu dùng framework tương đương thay Spark, cần giải thích kiến trúc và so sánh ưu/nhược điểm với Spark. nam depzai
#### 1. Tổng hợp phức tạp
- Hàm cửa sổ và hàm tổng hợp nâng cao
- Thao tác pivot và unpivot
- Hàm tổng hợp tùy biến

#### 2. Biến đổi nâng cao
- Nhiều giai đoạn biến đổi
- Chuỗi thao tác phức tạp
- UDF tùy biến cho logic nghiệp vụ

#### 3. Thao tác Join
- Broadcast join (tập dữ liệu không cân bằng)
- Sort-merge join (dữ liệu quy mô lớn)
- Tối ưu nhiều join

#### 4. Tối ưu hiệu năng
- Partition pruning và bucketing
- Chiến lược cache và persistence
- Tối ưu truy vấn và kế hoạch thực thi

#### 5. Xử lý luồng (Streaming)
- Structured Streaming, các chế độ output
- Watermarking và xử lý dữ liệu đến trễ
- Quản lý state; đảm bảo exactly-once

#### 6. Phân tích nâng cao
- Học máy (Spark MLlib)
- Đồ thị (GraphFrames)
- Thống kê, chuỗi thời gian

### IV. Các nhóm bài học cần có

Dự án phải thể hiện kiến thức và kỹ năng trong các lĩnh vực sau:

#### 1. Thu thập dữ liệu
- Nhiều nguồn đa dạng (OLTP database, files, streaming sources)
- Đảm bảo chất lượng dữ liệu (validation, cleansing)
- Xử lý dữ liệu đến trễ (late arrival data)
- Xử lý trùng lặp và phiên bản dữ liệu

#### 2. Xử lý dữ liệu với Spark
- Tối ưu Spark jobs (execution plan, shuffle optimization)
- Quản lý bộ nhớ hiệu quả (memory tuning, spill handling)
- Chiến lược phân vùng dữ liệu (partitioning strategies)
- Tối ưu theo chi phí (resource allocation, cost-effective processing)

#### 3. Xử lý luồng (Streaming)
- Đảm bảo exactly-once semantics
- Window operations (tumbling, sliding, session windows)
- State management (stateful processing)
- Fault tolerance và recovery mechanisms

#### 4. Lưu trữ dữ liệu
- Định dạng lưu trữ tối ưu (Parquet, ORC, Avro)
- Chiến lược phân vùng (partitioning by date, category)
- Nén dữ liệu (compression codecs)
- Quản lý dữ liệu nóng/lạnh (hot/cold data tiers)

#### 5. Tích hợp hệ thống
- Service discovery mechanisms
- Xử lý lỗi và retry logic
- Circuit breaker pattern
- Load balancing strategies

#### 6. Tối ưu hiệu năng
- Caching strategies (memory, disk)
- Query optimization techniques
- Resource allocation và tuning
- Phát hiện và giải quyết bottlenecks

#### 7. Giám sát & gỡ lỗi
- Metrics collection và monitoring
- Alerting và notification
- Centralized logging
- Root cause analysis

#### 8. Mở rộng (Scaling)
- Horizontal scaling (scale out)
- Vertical scaling (scale up)
- Auto-scaling policies
- Resource planning và cost management

#### 9. Chất lượng dữ liệu & kiểm thử
- Data quality checks và validation
- Unit testing
- Integration testing
- Performance testing

#### 10. Bảo mật & quản trị
- Access control và authentication
- Data encryption (at rest, in transit)
- Audit logging
- Compliance requirements

#### 11. Chịu lỗi (Fault Tolerance)
- Failure recovery mechanisms
- Data replication strategies
- Backup và restore procedures
- Disaster recovery planning

---

## PHẦN 1: ĐÁNH GIÁ KẾ HOẠCH KIẾN TRÚC HIỆN TẠI

### 1.1. Tổng quan kế hoạch trong README.md

Kế hoạch hiện tại trong README.md đã đề xuất một kiến trúc Lambda Architecture với các thành phần chính:

**Kiến trúc đề xuất:**
- ✅ Lambda Architecture (phù hợp với yêu cầu)
- ✅ Data Lakehouse (Bronze → Silver → Gold layers)
- ✅ Streaming + Batch processing
- ✅ PostgreSQL → Debezium CDC → Kafka → Spark
- ✅ MinIO (HDFS equivalent)
- ✅ MongoDB Atlas (NoSQL)
- ✅ Kubernetes (Minikube)
- ✅ Grafana (Visualization)

**Công nghệ được đề cập:**
- ✅ Apache Kafka (Confluent Cloud)
- ✅ Apache Spark (PySpark + Java/Spring Boot)
- ✅ MongoDB Atlas
- ✅ MinIO (S3-compatible)
- ✅ Debezium CDC
- ✅ Kubernetes (Minikube)
- ✅ Airflow (orchestration)
- ✅ Grafana
- ✅ dbt (data transformation)

### 1.2. Đánh giá kế hoạch theo yêu cầu giảng viên

#### ✅ **Điểm mạnh của kế hoạch:**

| Yêu cầu | Đánh giá | Chi tiết |
|---------|----------|----------|
| **Kiến trúc** | ✅ Tốt | Lambda Architecture được thiết kế rõ ràng với Batch + Speed layers |
| **Lưu trữ phân tán** | ✅ Tốt | MinIO làm HDFS equivalent, phân layer Bronze/Silver/Gold |
| **Message Queue** | ✅ Tốt | Kafka (Confluent Cloud) với CDC pattern |
| **NoSQL Database** | ✅ Tốt | MongoDB Atlas |
| **Kubernetes** | ✅ Tốt | Minikube với Debezium pod |
| **Định dạng dữ liệu** | ✅ Tốt | Parquet format (columnar, compressed) |
| **Orchestration** | ✅ Tốt | Airflow DAGs |

#### ⚠️ **Các điểm cần bổ sung/làm rõ:**

**1. Yêu cầu Spark Processing (Quan trọng nhất):**
- ⚠️ **Thiếu chi tiết**: README chỉ liệt kê "window_aggregates.py" và "broadcast_joins.py" nhưng chưa nói rõ:
    - Pivot/Unpivot operations
    - Custom UDFs cho business logic
    - Bucketing strategies
    - Cache/Persistence optimization
    - Execution plan analysis
- ⚠️ **Thiếu ML & Graph**: Chưa đề cập MLlib, GraphFrames, Time Series
- ✅ **Đã có**: Windowing, Watermarking, Broadcast Join

**2. Streaming Requirements:**
- ✅ **Đã có**: Windowing, Watermarking được đề cập
- ⚠️ **Thiếu**: Exactly-once semantics, Stateful processing (mapGroupsWithState), Checkpoint recovery

**3. Thu thập dữ liệu:**
- ✅ **Đã có**: PostgreSQL → Debezium CDC (nguồn OLTP)
- ⚠️ **Thiếu**:
    - Nhiều nguồn đa dạng (chỉ có 1 nguồn Postgres)
    - Data quality validation framework
    - Duplicate detection mechanism
    - Late arrival data handling strategy

**4. Tối ưu hiệu năng:**
- ⚠️ **Thiếu hoàn toàn**:
    - Memory tuning strategies
    - Cost optimization
    - Bottleneck identification
    - Resource allocation planning

**5. Giám sát & Debug:**
- ✅ **Đã có**: Grafana monitoring
- ⚠️ **Thiếu**:
    - Metrics collection (Prometheus)
    - Alerting rules
    - Centralized logging (ELK stack)
    - Root cause analysis tools

**6. Scaling:**
- ⚠️ **Thiếu hoàn toàn**:
    - Horizontal/vertical scaling strategies
    - Auto-scaling policies
    - Resource planning

**7. Testing:**
- ❌ **Không đề cập**: Unit testing, Integration testing, Performance testing

**8. Security:**
- ❌ **Không đề cập**: Authentication, Authorization, Encryption, Audit logs

**9. Fault Tolerance:**
- ⚠️ **Thiếu**: Backup strategies, Disaster recovery, Replication policies

**10. Tích hợp hệ thống:**
- ⚠️ **Thiếu**: Circuit breaker, Retry logic, Service discovery

### 1.3. Đánh giá chi tiết theo từng component

#### 1.3.1. Data Ingestion Layer
**Kế hoạch hiện tại:** PostgreSQL → Debezium → Kafka → Spark
- ✅ CDC pattern tốt
- ⚠️ Thiếu: Data quality checks, Schema validation, Duplicate handling
- ⚠️ Thiếu: Multiple data sources (hiện chỉ có Postgres)

#### 1.3.2. Storage Layer
**Kế hoạch hiện tại:** MinIO với Bronze/Silver/Gold
- ✅ Lakehouse architecture tốt
- ✅ Parquet format phù hợp
- ⚠️ Thiếu: Compression strategy, Partitioning details, Hot/cold data tiers

#### 1.3.3. Processing Layer
**Kế hoạch hiện tại:** PySpark + Java/Spring Boot
- ✅ Kết hợp PySpark và Java tốt
- ⚠️ Thiếu: Cụ thể về các Spark operations nâng cao
- ⚠️ Thiếu: MLlib, GraphFrames implementations
- ⚠️ Thiếu: Performance optimization details

#### 1.3.4. Serving Layer
**Kế hoạch hiện tại:** MongoDB + Grafana + dbt
- ✅ MongoDB phù hợp cho NoSQL
- ✅ Grafana cho visualization
- ⚠️ dbt: Cần làm rõ vai trò (dbt thường dùng cho SQL warehouse, không phổ biến cho MongoDB)

#### 1.3.5. Deployment Layer
**Kế hoạch hiện tại:** Kubernetes (Minikube)
- ✅ K8s phù hợp yêu cầu
- ⚠️ Thiếu: K8s YAML files structure
- ⚠️ Thiếu: Resource limits, Auto-scaling configs

### 1.4. Kết luận đánh giá kế hoạch

**Tổng thể: Kế hoạch nền tảng TỐT (70%) nhưng thiếu chi tiết triển khai (30%)**

**✅ Điểm mạnh:**
1. Kiến trúc Lambda rõ ràng, phù hợp yêu cầu
2. Tech stack hợp lý: Kafka, Spark, MongoDB, K8s
3. Data Lakehouse với Bronze/Silver/Gold layers
4. CDC pattern với Debezium

**⚠️ Điểm cần cải thiện:**
1. **Spark Processing (QUAN TRỌNG NHẤT)**: Cần bổ sung chi tiết 6 yêu cầu Spark
2. **Testing & Quality**: Thiếu hoàn toàn strategy
3. **Monitoring & Observability**: Cần bổ sung metrics, logging, alerting
4. **Performance Optimization**: Cần chiến lược cụ thể
5. **Security & Governance**: Cần bổ sung
6. **Multiple Data Sources**: Hiện chỉ có 1 nguồn

**🎯 Khuyến nghị:**
1. **Ưu tiên cao**: Làm đầy đủ 6 yêu cầu Spark Processing (60% điểm)
2. **Ưu tiên trung bình**: Bổ sung Testing, Monitoring, Performance tuning
3. **Ưu tiên thấp**: Security, Governance (nếu có thời gian)

**📊 Scoring:**
- Kiến trúc & Infrastructure: 8/10
- Spark Processing (chi tiết): 4/10 ⚠️
- Advanced Analytics (ML/Graph): 2/10 ⚠️
- Streaming Processing: 6/10
- Monitoring & Testing: 3/10 ⚠️
- **Tổng điểm ước tính**: 23/50 (46%) - CẦN CẢI THIỆN

---

## PHẦN 2: XÁC ĐỊNH MỤC TIÊU DỰ ÁN

### 2.1. Bối cảnh nghiệp vụ: HỆ THỐNG PHÂN TÍCH BÁN HÀNG E-COMMERCE THỜI GIAN THỰC

#### 2.1.1. Tại sao cần Big Data cho dữ liệu bán hàng?

**Trong thực tế:**

1. **Khối lượng (Volume):**
    - Sàn thương mại điện tử như Shopee, Lazada xử lý hàng triệu đơn hàng/ngày
    - Mỗi đơn hàng có nhiều sản phẩm, nhiều events (view, click, add to cart, checkout)
    - Dataset Olist có 100K đơn hàng - nhưng trong production có thể là 100M đơn hàng/năm

2. **Tốc độ (Velocity):**
    - Đơn hàng được tạo liên tục 24/7
    - Cần phân tích real-time để:
        - Phát hiện gian lận ngay lập tức
        - Đưa ra khuyến nghị sản phẩm trong vài milliseconds
        - Theo dõi inventory để tránh hết hàng
        - Phát hiện anomaly trong revenue

3. **Đa dạng (Variety):**
    - Dữ liệu structured: Orders, Products, Customers
    - Dữ liệu semi-structured: Reviews (text), Logs (JSON)
    - Dữ liệu streaming: Click events, Payment events
    - Dữ liệu geolocation

4. **Phân tích phức tạp:**
    - Customer Lifetime Value (CLV) prediction
    - Product recommendation (collaborative filtering)
    - Churn prediction
    - Fraud detection
    - Demand forecasting
    - Market basket analysis

#### 2.1.2. Các Use Cases cụ thể cho dự án

**UC1: Real-time Revenue Dashboard**
- Tính revenue theo cửa sổ thời gian (mỗi 5 phút, 1 giờ, 1 ngày)
- Phát hiện spike/drop bất thường
- Breakdown theo category, seller, region

**UC2: Customer Behavior Analysis**
- RFM Analysis (Recency, Frequency, Monetary)
- Customer segmentation
- Churn prediction

**UC3: Product Performance Analytics**
- Top selling products theo time window
- Review sentiment analysis
- Product recommendation engine (MLlib)

**UC4: Seller Network Analysis**
- Phân tích mạng lưới sellers (GraphFrames)
- Identify top sellers, fraudulent sellers
- Geographic distribution

**UC5: Delivery Performance Monitoring**
- Tracking delivery time
- Late delivery prediction
- Logistics optimization

### 2.2. Dataset Requirements

#### 2.2.1. Dataset Olist - Full Package

Dataset Olist Brazilian E-commerce có **9 tables** với tổng **~300MB**:

1. **olist_orders_dataset.csv** (99,441 rows) ✅ Đã có
2. **olist_order_items_dataset.csv** (~112K rows) ❌ Cần tải
3. **olist_order_payments_dataset.csv** (~103K rows) ❌ Cần tải
4. **olist_order_reviews_dataset.csv** (~99K rows) ❌ Cần tải
5. **olist_customers_dataset.csv** (~99K rows) ❌ Cần tải
6. **olist_products_dataset.csv** (~32K rows) ❌ Cần tải
7. **olist_sellers_dataset.csv** (~3K rows) ❌ Cần tải
8. **olist_geolocation_dataset.csv** (~1M rows) ❌ Cần tải
9. **product_category_name_translation.csv** (71 rows) ❌ Cần tải

**Link download:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

#### 2.2.2. Quy mô dữ liệu cho bài tập lớn

**Mức tối thiểu (đạt yêu cầu):**
- Dataset gốc: 300MB (9 tables)
- Sau khi duplicate/simulate thêm: **2-3 GB**
- Số records: ~5-10 triệu dòng
- Thời gian: Mô phỏng data từ 2016-2018 (3 năm)

**Cách tạo data mô phỏng lớn hơn:**
```python
# Duplicate data với random variations
for i in range(10):  # Tạo 10x data
    df_duplicated = df.withColumn("order_id", 
        concat(col("order_id"), lit(f"_dup{i}")))
    df_duplicated = df_duplicated.withColumn("order_purchase_timestamp",
        date_add(col("order_purchase_timestamp"), randint(0, 365)))
```

**Lý do cần 2-3GB:**
- Thể hiện khả năng xử lý phân tán (partitioning)
- Chứng minh hiệu quả của broadcast join vs sort-merge join
- Watermarking có ý nghĩa khi data volume lớn
- MLlib training cần dataset đủ lớn để có model tốt

### 2.3. Kiến trúc hệ thống

**Chọn: Lambda Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│  PostgreSQL (OLTP) → Debezium CDC → Kafka Topics                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     SPEED LAYER (Real-time)                      │
│  Spark Structured Streaming → Real-time aggregations            │
│  (Watermarking, Window Functions, Stateful Processing)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     BATCH LAYER (Historical)                     │
│  Spark Batch Processing → Complex transformations               │
│  (Broadcast Joins, MLlib, GraphFrames, Advanced Analytics)      │
└─────────────────────────────────────────────────────────────────┐
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SERVING LAYER (Query)                         │
│  MongoDB (NoSQL) → Pre-computed views                           │
│  Grafana → Real-time Dashboards                                 │
└─────────────────────────────────────────────────────────────────┘

Storage: MinIO (S3-compatible) - Bronze/Silver/Gold layers
Orchestration: Apache Airflow
Deployment: Kubernetes (Minikube)
```

---

## PHẦN 3: KẾ HOẠCH TRIỂN KHAI & PHÂN CÔNG CÔNG VIỆC

### 3.1. Timeline tổng thể (10 tuần - 2.5 tháng)

| Giai đoạn | Tuần | Mục tiêu | Deliverables |
|-----------|------|----------|--------------|
| **Foundation** | 1 | Setup môi trường & Planning | Infra ready, Dataset ready, Task breakdown |
| **Infrastructure & Data** | 2 | Infra services + Data ingestion | Kafka, MongoDB, MinIO ready, Data loaded |
| **Batch Processing Core** | 3 | Joins, Aggregations, UDFs | Bronze → Silver → Gold pipeline |
| **Batch Optimization** | 4 | Window functions, Pivot, Optimization | Optimized batch processing |
| **Streaming Foundation** | 5 | Kafka integration, Basic streaming | Kafka → Spark Streaming working |
| **Streaming Advanced** | 6 | Window, Watermark, Stateful | Advanced streaming features |
| **Java Integration** | 7 | Java Kafka consumer, MongoDB writer | Java services operational |
| **Analytics** | 8 | MLlib, GraphFrames, Time Series | ML models + Graph analysis |
| **Integration & Testing** | 9 | End-to-end testing, Monitoring | Full pipeline + Grafana |
| **Finalization** | 10 | Documentation, Presentation | Report + Slides + Demo |
