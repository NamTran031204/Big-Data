# BÁO CÁO BÀI TẬP LỚN
## Môn học: IT4931 — Lưu trữ và Xử lý Dữ liệu Lớn
## Đề tài: Hệ thống Xử lý Dữ liệu Lớn cho Nền tảng Thương mại Điện tử (Olist Dataset) theo Kiến trúc Lambda

---

# I. ĐỊNH NGHĨA BÀI TOÁN

## 1.1. Bài toán lựa chọn

### Bối cảnh thực tế

Thương mại điện tử là một trong những lĩnh vực sản sinh dữ liệu với tốc độ và khối lượng lớn nhất hiện nay. Mỗi giây, hàng nghìn đơn hàng được đặt, hàng chục nghìn sự kiện người dùng được ghi lại — từ lượt xem sản phẩm, thao tác thêm vào giỏ hàng, cho đến hoàn tất thanh toán và đánh giá sau mua. Các hệ thống OLTP truyền thống (quan hệ, transaction-based) không được thiết kế để xử lý phân tích trên quy mô này trong thời gian thực.

Nhóm lựa chọn bài toán: **Xây dựng hệ thống phân tích dữ liệu thương mại điện tử**, sử dụng bộ dữ liệu thực tế từ sàn Olist — một sàn thương mại điện tử lớn của Brazil, với dữ liệu đã được công bố công khai trên Kaggle.

### Mô tả bài toán

Từ hệ thống vận hành OLTP (PostgreSQL), nhóm xây dựng một pipeline xử lý dữ liệu lớn, mục tiêu là biến dữ liệu từ data thô thành **Thông tin**. Các thành phần của luồng dữ liệu gồm:

- **Thu thập dữ liệu liên tục** từ PostgreSQL thông qua cơ chế Change Data Capture (CDC) — bắt mọi thay đổi INSERT/UPDATE/DELETE tại nguồn mà không ảnh hưởng đến hệ thống giao dịch.
- **Phân tầng dữ liệu** theo mô hình Medallion: Bronze (dữ liệu thô CDC) → Silver (dữ liệu đã làm sạch, hợp nhất) → Gold (dữ liệu đã tổng hợp, sẵn sàng phân tích).
- **Tổng hợp các nhóm chỉ số kinh doanh** cốt lõi: doanh thu, hành vi khách hàng (RFM), hiệu suất sản phẩm, mạng lưới nhà bán hàng.
- **Lưu trữ kết quả Gold** vào ba đích đến: MinIO (data lake dạng Parquet), MongoDB cục bộ, và MongoDB Atlas (cloud).
- **Điều phối toàn bộ pipeline** qua Apache Airflow và triển khai trên Kubernetes.

### Dataset sử dụng

Bộ dữ liệu **Brazilian E-Commerce Public Dataset by Olist** gồm 9 bảng quan hệ:

| Bảng | Mô tả | Số dòng gốc |
|------|-------|-------------|
| orders | Đơn hàng chính | ~100.000 |
| order\_items | Chi tiết sản phẩm trong đơn | ~112.000 |
| order\_payments | Thông tin thanh toán | ~103.000 |
| order\_reviews | Đánh giá của khách hàng | ~99.000 |
| customers | Thông tin khách hàng | ~100.000 |
| products | Danh mục sản phẩm | ~33.000 |
| sellers | Thông tin nhà bán | ~3.000 |
| geolocation | Bản đồ mã zip | ~1.000.000 |
| category\_translation | Tên danh mục (anh/bồ) | 71 |

---

## 1.2. Phân tích mức độ phù hợp với dữ liệu lớn

### Tại sao bài toán này cần kiến trúc Big Data?

**Về khối lượng dữ liệu (Volume):**
- Dataset Olist là dữ liệu tĩnh lịch sử với hơn 300MB dung lượng gốc, nhưng trong thực tế triển khai, dữ liệu được bổ sung liên tục qua cơ chế CDC. Mỗi thay đổi trong PostgreSQL tạo ra một sự kiện Kafka, và theo thời gian Bronze zone tích lũy hàng triệu bản ghi CDC.
- Bảng geolocation có ~1 triệu dòng — không thể broadcast trực tiếp mà cần chiến lược join tối ưu.
- Gold layer ghi song song vào 3 đích đến, với 14+ collection khác nhau, đòi hỏi xử lý phân tán.

**Về tốc độ dữ liệu (Velocity):**
- Debezium CDC bắt các thay đổi tại PostgreSQL và đưa vào Kafka trong vòng dưới 1 giây.
- S3 Sink Connector flush dữ liệu vào MinIO theo batch (flush.size=1000 records hoặc mỗi 60 giây).
- Airflow kích hoạt Spark job theo lịch hàng ngày để đảm bảo Gold layer luôn cập nhật.

**Về sự đa dạng (Variety):**
- Dữ liệu đến từ nhiều nguồn: CSV (seed ban đầu), CDC events (Debezium), Parquet files (MinIO), NoSQL documents (MongoDB).
- Mỗi tầng có schema khác nhau: Bronze lưu trường CDC metadata (`__op`, `__ts_ms`, `__deleted`), Silver là bảng phẳng hợp nhất, Gold là các collection tổng hợp theo use case.

**Về độ phức tạp xử lý:**
- Cần khử trùng lặp CDC (nhiều sự kiện trên cùng một bản ghi), chuyển đổi timestamp ở định dạng microseconds của Debezium, gộp thanh toán về grain đơn hàng, và join 9 bảng theo chuỗi.
- Gold layer yêu cầu các phép tính cửa sổ (Window functions), pivot, UDF, NTILE, LAG/LEAD — không thể thực hiện bằng SQL thông thường trên OLTP.

### Giới hạn khi dùng công cụ truyền thống

Nếu chỉ dùng PostgreSQL hoặc một ứng dụng Python đơn lẻ:
- Query phân tích nặng (GROUP BY, JOIN nhiều bảng, aggregation theo thời gian) sẽ block các transaction OLTP.
- Không có cơ chế replication tự động từ OLTP sang analytical store.
- Không thể scale out khi dữ liệu tăng trưởng vượt 1 node.

---

## 1.3. Phạm vi và giới hạn dự án

### Phạm vi đã triển khai

- Toàn bộ Batch Layer: CDC → Bronze → Silver → Gold (3 sinks).
- Speed Layer (Real-time Streaming): Phát triển thành công luồng xử lý dữ liệu thời gian thực sử dụng Spark Structured Streaming tích hợp Apache Kafka. Hệ thống thực hiện đón bắt dòng sự kiện hành vi người dùng (`user_behavior_events`) liên tục theo mô hình bảng không giới hạn (*Unbounded Table*), tính toán cộng dồn điểm ưa thích theo phễu chuyển đổi (VIEW, CLICK, ADD_TO_CART, PURCHASE).
- Cơ chế Persistence kết nối PostgreSQL (foreachBatch): Xây dựng thành công kiến trúc lưu trữ đa nguồn. Kết quả tính toán từ luồng Stream được đồng bộ trực tiếp vào cơ sở dữ liệu PostgreSQL (`olist`) qua phương thức xử lý vi chuỗi `foreachBatch`, thực hiện ghi đè qua bảng staging và thực thi trigger cập nhật tự động cho hai bảng `user_preference` và `user_recommendation` (Top 10 sản phẩm gợi ý).
- Quản lý trạng thái và chịu lỗi (MinIO Checkpointing): Đảm bảo cơ chế chịu lỗi phân tán cho luồng streaming bằng cách đồng bộ hóa toàn bộ vết xử lý (`Checkpointing`) lên **MinIO Object Storage** qua giao thức S3A (`s3a://checkpoint/...`), giải quyết triệt để bài toán xung đột tệp tin tạm trên môi trường Windows.
- Orchestration: Airflow DAG `batch_pipeline` với 4 bước.
- Triển khai Docker Compose (môi trường phát triển) và Kubernetes/Minikube (môi trường sản xuất giả lập).
- 5 nhóm chỉ số Gold với tổng cộng 14 collection.

### Phạm vi chưa triển khai (Phase 2 — tương lai)

- **ML/MLlib columns:** Các chỉ số học máy trong Gold (churn\_probability, clv\_predicted, review\_sentiment, fraud\_risk\_score, predicted\_delivery\_days) hiện được để `null`.
- **GraphFrames:** PageRank cho mạng lưới nhà bán hàng (seller\_network\_centrality, seller\_cluster).
- **CI/CD và Secret Management** (Vault/k8s Secrets).

---

# II. KIẾN TRÚC VÀ THIẾT KẾ

## 2.1. Kiến trúc tổng thể — Lambda Architecture

Nhóm chọn **Kiến trúc Lambda** vì bài toán yêu cầu đồng thời: (1) xử lý toàn bộ dữ liệu lịch sử chính xác (Batch Layer) và (2) phản hồi gần real-time với sự kiện mới (Speed Layer). Lambda Architecture tách biệt hai luồng này, cho phép độc lập scale và fault-tolerant.

### Ba tầng của Lambda Architecture trong dự án

**Batch Layer (đã triển khai đầy đủ):**
- Xử lý toàn bộ dữ liệu lịch sử từ Bronze zone.
- Kết quả chính xác, có thể recompute từ đầu.
- Công nghệ: Apache Spark (PySpark), MinIO, Apache Airflow.

**Speed Layer (đã triển khai đầy đủ):**
- Xử lý dòng sự kiện biến động liên tục về hành vi tương tác của khách hàng (User-behavior events) theo thời gian thực để đưa ra phản hồi gợi ý sản phẩm ngay lập tức với độ trễ thấp (micro-batch xử lý theo cửa sổ 30 giây).
- Công nghệ: Spark Structured Streaming, Apache Kafka.

**Serving Layer:**
- Tổng hợp kết quả từ Batch và Speed Layer.
- Công nghệ: MongoDB (local + Atlas), MinIO (Parquet).

---

## 2.2. Các thành phần hệ thống và vai trò

### Nhóm Nguồn dữ liệu

**PostgreSQL 16 (OLTP)**
- Vai trò: Hệ thống giao dịch gốc, lưu trữ 9 bảng nghiệp vụ Olist.
- Cấu hình đặc biệt: `wal_level=logical` — bật Write-Ahead Log ở mức logical replication; `REPLICA IDENTITY FULL` trên tất cả bảng — đảm bảo Debezium nhận đủ giá trị trước và sau mỗi thay đổi.
- Dữ liệu khởi tạo: 9 file CSV được nạp tự động khi container khởi động lần đầu qua `init/postgres-init/*.sql`.

### Nhóm Thu thập và Truyền dữ liệu

**Debezium Connect 2.4**
- Vai trò: CDC connector, đọc WAL log của PostgreSQL và phát sự kiện thay đổi dưới dạng message Kafka.
- Plugin sử dụng: `pgoutput` (native PostgreSQL logical replication protocol).
- Cấu hình quan trọng: `decimal.handling.mode=double` — chuyển các cột NUMERIC (price, payment\_value) thành số thực thay vì chuỗi base64 encoded, tránh lỗi parsing ở Spark.
- Tích hợp: chạy trên cùng Kafka Connect cluster với S3 Sink Connector.

**Apache Kafka 7.5 (Confluent)**
- Vai trò: Message broker trung gian, đệm dữ liệu CDC trước khi ghi vào Bronze zone.
- Topics được tạo tự động: `olist_cdc.public.<tên_bảng>` (9 topics tương ứng 9 bảng).
- Phân vùng: 1 partition/topic (hiện tại nhóm mới cấu hình đủ demo, production cần nhiều hơn để đáp ứng được hệ thống thực tế).

**Confluent S3 Sink Connector**
- Vai trò: Đọc Kafka topics và ghi Parquet snappy vào MinIO Bronze zone.
- Định dạng đầu ra: Parquet với Snappy compression — tối ưu cho Spark đọc theo cột.
- Transform áp dụng: `ExtractNewRecordState` — tách lấy phần `after` của sự kiện CDC (giá trị mới), loại bỏ cấu trúc envelope Debezium, thêm metadata `__op`, `__ts_ms`.
- Cấu hình quan trọng: `value.converter.schemas.enable=true` — bắt buộc để Parquet Formatter có thể suy diễn schema cột.

### Nhóm Lưu trữ Phân tán

**MinIO**
- Vai trò: Object storage tương thích S3 API, đóng vai trò Data Lake.
- Cấu trúc bucket:
  - `bronze-zone/cdc/olist_cdc.public.<table>/`: Parquet thô từ CDC, chứa metadata Debezium.
  - `silver-zone/olist_unified_silver/`: Parquet đã làm sạch, hợp nhất 9 bảng về grain order\_item.
  - `gold-zone/<collection>/`: Parquet tổng hợp cho từng use case analytics.
- Truy cập: thông qua S3A connector của Hadoop (`s3a://`).

**Apache Spark 3.5.1**
- Vai trò: Engine xử lý phân tán cho cả Batch Layer.
- Triển khai: 1 Master + 1 Worker (có thể mở rộng).
- Điểm mount code: `/opt/project` — code Spark được mount vào container, không cần build lại image khi sửa code.
- Giao tiếp MinIO: hadoop-aws 3.3.4 + aws-java-sdk-bundle 1.12.262.

### Nhóm Serving Layer

**MongoDB**
- Vai trò: Serving layer cho Gold data, lưu trữ các collection tổng hợp dưới dạng document.
- Database: `olist_gold`.
- Ghi bằng bulk\_upsert — cập nhật nếu tồn tại theo key fields, insert nếu chưa có.
- Index: compound index trên (dimension\_id, ingest\_date) cho các collection có chiều cao cardinality.

### Nhóm Điều phối

**Apache Airflow 2.11**
- Vai trò: Điều phối toàn bộ batch pipeline theo lịch hàng ngày.
- DAG `batch_pipeline` có 4 bước tuần tự: đảm bảo connector → kiểm tra Bronze → Silver job → Gold job.
- Operator: `SparkSubmitOperator` với `deploy_mode=client` (submit từ Airflow container đến Spark Master).

### Nhóm Triển khai

**Docker Compose** — môi trường phát triển: 13 services trên 4 Docker network.

**Kubernetes (Minikube)** — môi trường có namespace `bigdata` với đầy đủ Deployment, Service, PersistentVolumeClaim, ConfigMap, Secret.

---

## 2.3. Sơ đồ luồng dữ liệu

### Luồng Batch Layer (end-to-end)

```
[CSV files]
    │
    │ docker entrypoint (init/postgres-init/*.sql)
    ▼
[PostgreSQL OLTP] ─── WAL (wal_level=logical) ───►
    │                                              │
    │                                    [Debezium CDC Source]
    │                                              │
    │                                    [Apache Kafka Topics]
    │                                    olist_cdc.public.*
    │                                              │
    │                               [S3 Sink + ExtractNewRecordState]
    │                                              │
    ▼                                              ▼
[PostgreSQL]                        [MinIO: bronze-zone/cdc/]
                                    Parquet, snappy, schema embedded
                                              │
                                    [Spark: transform_bronze_to_silver.py]
                                    - dedup CDC (Window __ts_ms)
                                    - timestamp_micros() conversion
                                    - payment aggregation (order grain)
                                    - 9-way join → order_item grain
                                    - Data Quality filter
                                              │
                                    [MinIO: silver-zone/olist_unified_silver/]
                                    Unified Parquet, grain = order_item
                                              │
                                    [Spark: transform_silver_to_gold.py]
                                    - 5 UC aggregations
                                    - Window, Pivot, UDF, NTILE
                                    - 14 collections
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                    [MinIO: gold-zone/]  [MongoDB local]  [MongoDB Atlas]
                    Parquet per coll.   olist_gold DB    (nếu URI có)
```

### Luồng Orchestration (Airflow DAG)

```
ensure_connectors (PUT /connectors)
        │
        ▼
wait_bronze (kiểm tra MinIO bronze-zone có objects?)
        │ (short-circuit nếu chưa có)
        ▼
silver (SparkSubmitOperator → Spark Master)
        │
        ▼
gold (SparkSubmitOperator → Spark Master)
```

### Chiến lược Join trong Silver Layer

Nhóm áp dụng **Broadcast Join** cho các bảng chiều (dimension) nhỏ và **Sort-Merge Join** (mặc định của Spark) cho bảng lớn:

- `broadcast(customers)` — ~100.000 dòng
- `broadcast(products)` — ~33.000 dòng
- `broadcast(category_translation)` — 71 dòng
- `broadcast(sellers)` — ~3.000 dòng
- `broadcast(geolocation)` — group by zip code trước khi broadcast
- `orders`, `order_items` — join inner bình thường (không broadcast, bảng lớn tương đương)

---

# III. CHI TIẾT TRIỂN KHAI

## 3.1. Mã nguồn và tổ chức code

### Cấu trúc thư mục chính

```
Big-Data/
├── init/                          # Infrastructure
│   ├── docker-compose.yml         # 13 services, 4 networks
│   ├── .env                       # Credentials và endpoints
│   ├── Dockerfile                 # Debezium + S3 Sink image
│   ├── airflow.Dockerfile         # Airflow + JDK17 + Spark
│   ├── spark.Dockerfile           # Spark + PyMongo
│   ├── postgres-init/             # SQL scripts khởi tạo DB
│   │   ├── 01-schema.sql          # DDL 9 bảng + replica identity
│   │   ├── 02-copy.sql            # COPY CSV → bảng
│   │   ├── 03-streaming-tables.sql  # user_preference, user_recommendation
│   ├── register-connector.sh      # Debezium source connector
│   └── register-s3-sink.sh        # Confluent S3 sink connector
├── spark-batch/
│   ├── transform_bronze_to_silver.py  # Bronze → Silver
│   └── transform_silver_to_gold.py    # Silver → Gold (3 sinks)
├── spark-streaming/
│   └── kafka_consumer.py          # Speed layer (phase sau)
├── services/
│   └── mongodb_connect/
│       └── mongo_connector.py     # MongoConnector class
├── airflow/
│   └── dags/
│       └── batch_pipeline_dag.py  # Airflow DAG
├── k8s/                           # Kubernetes manifests
│   ├── 00-namespace.yaml
│   ├── 10-zookeeper.yaml
│   ├── 20-kafka.yaml
│   ├── 30-postgres.yaml
│   ├── 40-debezium.yaml
│   ├── 50-minio.yaml
│   ├── 60-spark.yaml
│   ├── 70-airflow.yaml
│   └── 80-mongodb.yaml
└── docs/                          # Tài liệu kỹ thuật
```

---

## 3.2. Khởi tạo hạ tầng

### Custom Docker Images

Nhóm phải build 3 custom image vì các image gốc thiếu dependency cần thiết:

**Image 1 — bigdata-debezium:** Dựa trên `debezium/connect:2.4`, bổ sung Confluent S3 Sink Plugin. Không có image nào đóng gói sẵn cả Debezium source và Confluent S3 sink trên cùng một container.

**Image 2 — bigdata-airflow:** Dựa trên `apache/airflow:2.11.2-python3.11`, bổ sung OpenJDK 17, Spark 3.5.1 binary, thư viện `apache-airflow-providers-apache-spark` và `boto3`. Airflow cần JDK để submit Spark job.

**Image 3 — bigdata-spark:** Dựa trên `apache/spark:3.5.1-python3`, bổ sung `pymongo` để Spark job có thể ghi trực tiếp vào MongoDB.

### Khởi động theo đúng thứ tự

Các service có dependency chain nghiêm ngặt:

- ZooKeeper phải up trước Kafka
- Kafka phải up trước Debezium (Kafka Connect cần Kafka broker)
- PostgreSQL phải up trước Debezium (CDC source)
- MinIO phải up trước khi đăng ký S3 Sink Connector
- Tất cả phải up trước khi trigger Airflow DAG

Docker Compose `depends_on` + `healthcheck` xử lý phần này tự động.

---

## 3.3. Cấu hình CDC (Debezium + Kafka)

### Debezium Source Connector

Connector được đăng ký qua REST API (`init/register-connector.sh`):

**Các tham số quan trọng và lý do:**

- `plugin.name: pgoutput` — sử dụng native PostgreSQL logical replication, không cần cài thêm plugin vào Postgres.
- `decimal.handling.mode: double` — chuyển NUMERIC sang DOUBLE PRECISION. Nếu để mặc định `precise`, Debezium encode thành Avro binary, Spark sẽ nhận chuỗi base64 thay vì số.
- `snapshot.mode: initial` — chụp toàn bộ dữ liệu hiện có khi connector khởi động lần đầu, sau đó chuyển sang streaming mode.
- `tombstones.on.delete: false` — không phát tombstone message (null value) khi DELETE, tránh lỗi S3 Sink Connector không xử lý được null payload.
- `heartbeat.interval.ms: 10000` — gửi heartbeat 10 giây/lần để giữ replication slot không bị timed out khi không có thay đổi.
- `topic.prefix: olist_cdc` — tiền tố cho tên topic Kafka,
  tạo ra các topic dạng `olist_cdc.public.<tên_bảng>`.
- `slot.name: debezium_slot` — tên replication slot trong
  PostgreSQL. Cần nhớ tên này khi cần drop slot thủ công
  lúc đổi config connector.
- `publication.autocreate.mode: filtered` kết hợp với
  `table.include.list` — chỉ theo dõi đúng 9 bảng Olist,
  không bắt thay đổi từ các bảng hệ thống hoặc bảng
  streaming (user_preference, user_recommendation).
- `schema.include.list: public` — giới hạn phạm vi CDC
  trong schema public của PostgreSQL.

### S3 Sink Connector

**Các tham số quan trọng:**

- `format.class: io.confluent.connect.s3.format.parquet.ParquetFormat` — ghi Parquet thay vì JSON, tối ưu cho Spark.
- `parquet.codec: snappy` — nén Snappy: nhanh decompress, phù hợp cho Spark scan theo cột.
- `value.converter.schemas.enable: true` — **bắt buộc** khi dùng ParquetFormat. Connector cần schema để ánh xạ field → column Parquet. Nếu `false`, ghi sẽ thất bại.
- `transforms.unwrap.type: io.debezium.transforms.ExtractNewRecordState` — lấy phần `payload.after` (bản ghi mới sau thay đổi), loại bỏ envelope Debezium phức tạp.
- `transforms.unwrap.add.fields: op,ts_ms` — giữ lại `__op` (loại thao tác: c/u/d/r) và `__ts_ms` (timestamp microseconds) làm metadata cho bước khử trùng CDC ở Silver.
- `flush.size: 1000` và `rotate.schedule.interval.ms: 60000` — flush sau 1000 records hoặc sau 60 giây, tùy điều kiện nào đến trước.

---

## 3.4. Spark Batch: Bronze → Silver

### Mục tiêu

Chuyển đổi dữ liệu CDC thô từ 9 bảng riêng lẻ thành một bảng thống nhất sạch, có grain **order\_item** (mỗi dòng là một sản phẩm trong một đơn hàng).

### Các bước xử lý chi tiết

**Bước 1 — Đọc Bronze từ MinIO**

Spark đọc Parquet từ đường dẫn `s3a://bronze-zone/cdc/olist_cdc.public.<table>/`. Do S3 Sink Connector tổ chức theo `partition=0/`, Spark tự động tìm đệ quy.

**Bước 2 — Khử trùng CDC (dedup\_cdc)**

Mỗi bản ghi có thể xuất hiện nhiều lần trong Kafka nếu bị update nhiều lần. Quy tắc khử trùng:
- Lọc bỏ các dòng có `__deleted = 'true'` (sự kiện DELETE).
- Dùng Window Function: `ROW_NUMBER() OVER (PARTITION BY <primary_key> ORDER BY __ts_ms DESC)`, chỉ giữ dòng có row\_number = 1 (bản ghi mới nhất).
- Sau khi dedup, xóa cột metadata `__op`, `__ts_ms`, `__deleted`.

**Bước 3 — Chuyển đổi timestamp Debezium**

Debezium lưu timestamp dưới dạng **epoch microseconds** (số nguyên), không phải milliseconds thông thường. Spark không tự nhận ra định dạng này. Nhóm dùng hàm `timestamp_micros()` của Spark SQL để chuyển đổi đúng.

**Bước 4 — Gộp thanh toán về grain đơn hàng**

Bảng `order_payments` có nhiều dòng trên cùng `order_id` (1 đơn có thể thanh toán nhiều lần, chia nhỏ installments). Nếu join trực tiếp, mỗi dòng order\_item sẽ bị nhân lên bằng số lần thanh toán.

Giải pháp: `GROUP BY order_id`, tính `SUM(payment_value)` làm `order_payment_value`, lấy loại thanh toán chiếm giá trị lớn nhất làm `payment_type` chủ đạo.

**Bước 5 — Lấy review mới nhất/đơn hàng**

`order_reviews` có thể có nhiều review trên cùng `order_id` (khách review nhiều lần). Dùng Window: `ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_creation_date DESC)`, chỉ giữ review mới nhất.

**Bước 6 — Join hợp nhất (9-way join)**

Thứ tự join được thiết kế để bảng lớn nằm bên trái (driver), bảng nhỏ được broadcast:

- `order_items` INNER JOIN `orders` (on order\_id) — 2 bảng lớn, sort-merge
- LEFT JOIN `payments` đã gộp (on order\_id)
- LEFT JOIN `broadcast(customers)` (on customer\_id) — ~100K rows
- LEFT JOIN `broadcast(products)` (on product\_id) — ~33K rows
- LEFT JOIN `broadcast(category_translation)` (on product\_category\_name) — 71 rows
- LEFT JOIN `reviews` mới nhất (on order\_id)
- LEFT JOIN `broadcast(sellers)` (on seller\_id) — ~3K rows
- LEFT JOIN `broadcast(geolocation)` (on zip\_code) — geo được group-by trước khi broadcast

**Bước 7 — Kiểm tra chất lượng dữ liệu (DQ)**

Lọc bỏ dòng thiếu các trường khóa: `order_id IS NOT NULL` và `purchase_ts IS NOT NULL`. Các dòng này là CDC noise (sự kiện không hoàn chỉnh) và không có giá trị phân tích.

**Bước 8 — Ghi Silver**

Ghi Parquet sang `s3a://silver-zone/olist_unified_silver/` với mode `overwrite` (toàn bộ recompute mỗi lần chạy — đảm bảo correctness, đánh đổi tốc độ).

---

## 3.5. Spark Batch: Silver → Gold

### Mục tiêu

Từ bảng Silver thống nhất, tạo ra 14 Gold collection phục vụ 5 nhóm use case phân tích.

### UC1 — Revenue Metrics

**Collection chính `gold_revenue_metrics`:** Tổng hợp doanh thu theo ngày.
- Tính `SUM(order_payment_value)` theo ngày → `revenue_daily`.
- LAG Window: so sánh với ngày trước → `revenue_growth_rate` (%).
- Spike detection: doanh thu > mean + 2 × stddev → `revenue_spike_flag = 1`.
- Cột `revenue_5min`, `revenue_hourly` để `null` (speed layer sẽ điền vào ở phase sau).

**Breakdowns:**
- `gold_revenue_by_category` — doanh thu theo danh mục sản phẩm × ngày
- `gold_revenue_by_state` — doanh thu theo bang (customer\_state) × ngày
- `gold_revenue_by_payment_type` — doanh thu theo phương thức thanh toán × ngày

### UC2 — Customer Analytics (RFM)

**Collection `gold_customer_rfm`:**
- Snapshot thời điểm = `MAX(purchase_ts)` toàn dataset.
- **Recency:** số ngày kể từ lần mua cuối đến snapshot.
- **Frequency:** số đơn hàng phân biệt.
- **Monetary:** tổng giá trị thanh toán.
- **Điểm NTILE 1–5:** chia mỗi chiều thành 5 phân vị. Recency nghịch đảo (gần nhất = 5 điểm).
- **Phân khúc khách hàng:** Champion (R≥4, F≥4), Loyal (F≥4), Lost (R≤2, F≤2), At Risk (R≤2), Standard.
- Cột `churn_probability`, `clv_predicted` để `null` (MLlib phase sau).

**Breakdowns:**
- `gold_customer_acquisition` — phân biệt khách mới (first purchase) vs. khách quay lại theo ngày.

### UC3 — Product Analytics

**Collection `gold_product_metrics`:**
- Doanh thu, số đơn, điểm review trung bình, tỷ lệ hủy (`product_return_rate`) theo sản phẩm × ngày.
- `category_rank`: RANK() trong cùng danh mục × ngày theo doanh thu.
- Cột `review_sentiment`, `recommended_products` để `null` (NLP/ALS phase sau).

**Breakdowns:**
- `gold_top_products_daily` — TOP 10 sản phẩm theo ngày (Window RANK).
- `gold_sales_by_category` — Pivot matrix (category × state) doanh số.
- `gold_category_rank` — DENSE\_RANK danh mục theo tổng doanh thu.

### UC4 — Seller Network Analysis

**Collection `gold_seller_metrics`:**
- Doanh thu, số đơn, điểm review trung bình, số bang phủ sóng (`geographic_coverage`) theo seller.
- `seller_revenue_rank`: RANK() tất cả seller theo doanh thu.
- Thời gian giao hàng trung bình, `seller_fulfillment_rate` (tỷ lệ đúng hạn).
- Cột `seller_network_centrality`, `seller_cluster`, `fraud_risk_score` để `null` (GraphFrames/ML phase sau).

**Breakdowns:**
- `gold_seller_daily` — doanh số, giao hàng theo seller × ngày.
- `gold_seller_product_daily` — sản phẩm bán được của từng seller × ngày.

### UC5 — Delivery Performance

**Collection `gold_delivery_metrics`:**
- Tính `delivery_days = DATEDIFF(delivered_date, purchase_date)`.
- `on_time = (delivered ≤ estimated)` — boolean cast thành integer.
- Tổng hợp theo bang × ngày: `on_time_delivery_rate`, `avg_delivery_time_days`, `late_delivery_count`.
- Cột `predicted_delivery_days`, `delivery_hotspot` để `null` (Random Forest phase sau).

### Ghi Gold vào 3 sinks

Hàm `write_to_gold()` tái sử dụng `MongoConnector.bulk_upsert()` cho cả MongoDB local và Atlas:

- **MinIO**: `spark_df.write.mode("overwrite").parquet(f"s3a://gold-zone/{collection}/")`.
- **MongoDB local**: convert DataFrame sang list dict → `bulk_upsert(collection, records, key_fields)`.
- **MongoDB Atlas**: tương tự, bỏ qua nếu `MONGO_ATLAS_URI` rỗng.

---

## 3.6. Airflow DAG và Orchestration

### DAG `batch_pipeline`

**Task 1 — ensure\_connectors:**
- Gọi REST API của Debezium Connect (`PUT /connectors/{name}/config`).
- Tạo mới connector nếu chưa tồn tại, hoặc cập nhật config nếu đã có.
- Đảm bảo idempotency: chạy lại DAG không tạo connector duplicate.

**Task 2 — wait\_bronze (short\_circuit):**
- Kiểm tra MinIO bucket `bronze-zone/` có objects chưa qua `boto3.list_objects_v2`.
- Nếu chưa có dữ liệu Bronze (Debezium chưa kịp flush), short\_circuit dừng pipeline.
- Nếu không kết nối được MinIO (môi trường thiếu boto3), mặc định `return True` để pipeline tiếp tục.

**Task 3 — silver (SparkSubmitOperator):**
- Submit job `transform_bronze_to_silver.py` đến Spark Master.
- `deploy_mode=client` — Spark Driver chạy trong Airflow container, không cần Driver node riêng.
- Truyền `--packages` để Ivy download hadoop-aws khi cần.

**Task 4 — gold (SparkSubmitOperator):**
- Submit job `transform_silver_to_gold.py`.
- Truyền thêm biến môi trường MongoDB URI.

---

## 3.7. Triển khai Kubernetes

### Cấu trúc namespace `bigdata`

Mỗi service được triển khai trong một Deployment riêng với Service tương ứng. Các điểm đáng chú ý:

**PostgreSQL (30-postgres.yaml):**
- ConfigMap `pg-initdb` chứa toàn bộ SQL khởi tạo (schema + replica identity), mount vào `/docker-entrypoint-initdb.d/`.
- PersistentVolumeClaim 3Gi đảm bảo dữ liệu không mất khi pod restart.

**Spark (60-spark.yaml):**
- Code Spark batch được đóng gói vào ConfigMap `spark-batch-code`, mount vào `/opt/project/spark-batch/`.
- Code services (MongoConnector) mount vào `/opt/project/services/`.
- `PYTHONPATH=/opt/project` — cho phép `import services.mongodb_connect` từ bất kỳ đâu.

**Airflow (70-airflow.yaml):**
- DAG files mount qua ConfigMap `airflow-dags`.
- Connection `spark_default` cấu hình trỏ đến Spark Master service (`spark://spark-master:7077`).

### Quy trình deploy

```
make k8s-build-images      # Đẩy 3 custom image vào Minikube Docker daemon
make k8s-code-configmaps   # Tạo ConfigMap từ code files
make k8s-up                # kubectl apply -f k8s/
make seed-postgres-k8s     # Copy CSV vào Postgres pod + chạy COPY
make k8s-test-all          # Chạy test suite cho tất cả services
```

---

## 3.8. Cấu hình môi trường

### File `init/.env`

Tất cả credentials và endpoints được tập trung vào file `.env`, tránh hardcode trong code:

- **MinIO:** endpoint, access key, secret key.
- **MongoDB:** URI local (`mongodb://admin:admin123456@bigdata-mongodb:27017/?authSource=admin`), URI Atlas (để trống mặc định).
- **Kafka:** bootstrap servers nội bộ (`kafka:9094`) và bên ngoài (`localhost:9092`).
- **Postgres:** host, port, user, password, database name.
- **Airflow:** fernet key, secret key.

### Biến môi trường runtime trong Spark

Spark jobs đọc cấu hình từ biến môi trường thay vì hardcode, được truyền qua `SparkSubmitOperator.env_vars` trong Airflow hoặc trực tiếp trong Makefile.

---

# IV. BÀI HỌC KINH NGHIỆM (LESSONS LEARNED)

---

## Bài học 1: Thu thập dữ liệu — Cấu hình Debezium CDC cho PostgreSQL

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Nhóm cần thiết lập Debezium để bắt mọi thay đổi từ PostgreSQL và đẩy vào Kafka. Đây là lần đầu nhóm làm việc với CDC và logical replication của PostgreSQL.

#### Thách thức gặp phải
- Connector đăng ký thành công nhưng không có message nào xuất hiện trên Kafka topics.
- Khi có message, phần dữ liệu số (price, payment\_value) bị nhận dạng là chuỗi base64 thay vì số thực.
- Sau khi xóa connector và đăng ký lại, gặp lỗi replication slot đã tồn tại.

#### Tác động đến hệ thống
- S3 Sink Connector ghi ra file Parquet với cột price là kiểu `bytes` thay vì `double`, khiến Spark đọc Bronze bị lỗi schema.
- Replication slot bị giữ tốn tài nguyên PostgreSQL, WAL log tích lũy không được giải phóng.

### Cách tiếp cận đã thử

**Cách 1:** Giữ `decimal.handling.mode` mặc định (`precise`), cố gắng parse base64 trong Spark bằng UDF. Không khả thi vì cần viết thêm Avro decoder, phức tạp không cần thiết.

**Cách 2:** Thay `decimal.handling.mode: double` trong connector config, xóa connector cũ và đăng ký lại. Gặp lỗi: replication slot tên `debezium_slot` đã tồn tại trong PostgreSQL.

**Cách 3:** Đăng nhập PostgreSQL, drop slot thủ công bằng `SELECT pg_drop_replication_slot('debezium_slot')`, sau đó đăng ký lại connector.

### Giải pháp cuối cùng

- Chuẩn hóa connector config với `decimal.handling.mode: double` từ đầu, không thay đổi sau khi đã có dữ liệu.
- Thêm `tombstones.on.delete: false` để tránh null-payload message làm S3 Sink bị lỗi.
- Thêm `heartbeat.interval.ms: 10000` để giữ replication slot active khi không có thay đổi.
- Script `register-connector.sh` dùng `PUT /connectors/{name}/config` thay vì `POST`, tự động update nếu đã tồn tại, idempotent hoàn toàn.
- **Kết quả:** Sau khi áp dụng, 9 Kafka topics có message đầy đủ, price và payment\_value là số thực DOUBLE trong Parquet.

### Điểm rút ra

- PostgreSQL `wal_level=logical` và `REPLICA IDENTITY FULL` là điều kiện tiên quyết, thiếu một trong hai Debezium không hoạt động đúng.
- `decimal.handling.mode=double` cần được quyết định trước khi có dữ liệu — thay đổi sau sẽ gây schema incompatibility trên Kafka topic.
- Dùng HTTP `PUT` thay vì `POST` cho API đăng ký connector — đây là best practice để script trở nên idempotent.
- Nên kiểm tra Debezium logs (`docker logs debezium`) ngay sau đăng ký connector để phát hiện lỗi sớm.

---

## Bài học 2: Xử lý dữ liệu với Spark — Khử trùng lặp CDC và chiến lược Join

### 2.1. Phân tầng Medallion và Khử trùng lặp CDC

#### Mô tả vấn đề

##### Bối cảnh và nền tảng
Khi Debezium CDC bắt thay đổi, mỗi UPDATE trên một bản ghi tạo ra nhiều Kafka message. Sau khi S3 Sink flush vào Bronze, cùng một `order_id` có thể xuất hiện 3–5 lần với `__ts_ms` khác nhau. Đồng thời, bảng `order_payments` có nhiều dòng per order (một đơn thanh toán nhiều lần), và nếu join trực tiếp sẽ làm nhân bội dữ liệu.

##### Thách thức gặp phải
- Silver DataFrame có số dòng gấp 4–6 lần Bronze do chưa dedup CDC.
- Join `order_items` (112K) với `order_payments` chưa gộp (~103K, nhiều dòng/order) cho ra kết quả ~400K dòng — sai grain.
- Khi thêm geolocation (~1M dòng), Spark báo lỗi OOM (Out of Memory) khi broadcast.

##### Tác động đến hệ thống
- Gold layer tính `SUM(revenue)` bị phóng đại nhiều lần do data multiplication.
- Spark Worker bị kill do OOM, job thất bại.

#### Cách tiếp cận đã thử

**Cách 1:** Dùng `DISTINCT` sau join để khử trùng. Không đúng vì `DISTINCT` không giải quyết được vấn đề CDC dedup theo key — bản ghi cũ và mới khác nhau ở một vài cột giá trị, không phải duplicate hoàn toàn.

**Cách 2:** Broadcast geolocation trực tiếp (~1M dòng). Gây OOM trên Worker 2GB.

**Cách 3:** GROUP BY `geolocation_zip_code_prefix`, lấy lat/lng trung bình trước khi broadcast. Kết quả: ~65K distinct zip codes — đủ nhỏ để broadcast.

#### Giải pháp cuối cùng

- **CDC dedup:** `ROW_NUMBER() OVER (PARTITION BY primary_key ORDER BY __ts_ms DESC) = 1` — luôn giữ bản ghi mới nhất, xử lý đúng cả UPDATE và DELETE (dòng `__deleted=true` bị lọc trước).
- **Payment aggregation:** `GROUP BY order_id` trước khi join, tính `SUM(payment_value)`, lấy `payment_type` chiếm giá trị lớn nhất. Đảm bảo grain order\_item sau join = grain order\_item trước join.
- **Geolocation:** Pre-aggregate về distinct zip codes, sau đó broadcast.
- **Thứ tự join:** Bảng lớn (fact) bên trái, bảng nhỏ (dimension) bên phải với `broadcast()` hint.
- **Kết quả:** Silver output đúng 112K dòng (= số order\_items), không có data multiplication, job hoàn thành trong 3–5 phút.

#### Điểm rút ra

- CDC dedup phải dùng Window function theo key + timestamp, không phải `DISTINCT`.
- Luôn kiểm tra row count sau mỗi join để phát hiện sớm data multiplication.
- Bảng có nhiều-dòng-per-key phải được gộp về grain phù hợp trước khi tham gia join chain.
- Chiến lược broadcast: chỉ broadcast bảng dưới ~100MB. Với bảng lớn, pre-aggregate trước rồi broadcast kết quả đã gộp.

### 2.2. Khai phá luồng dữ liệu hành vi với Spark Structured Streaming

#### Mô tả vấn đề

##### Bối cảnh và nền tảng
Để hiện thực hóa thành phần tầng tốc độ (Speed Layer) trong kiến trúc Lambda của dự án, nhóm triển khai kịch bản đón nhận và phân tích dòng sự kiện tương tác trực tuyến của khách hàng (user_behavior_events) được đẩy về liên tục từ hệ thống giả lập. Tiến trình này đòi hỏi phải vận hành công cụ Spark Structured Streaming để tính toán chỉ số ngay khi dữ liệu vừa phát sinh.

##### Thách thức gặp phải
- Dữ liệu hành vi người dùng đổ về dưới dạng chuỗi JSON thô vô định hình thông qua Kafka Broker.
- Việc phân tách chuỗi dữ liệu động trực tiếp trong quá trình stream tiêu tốn lượng lớn chu kỳ phân phối của hệ thống và dễ gây hiện tượng thắt nút cổ chai (processing lag) tại Driver khi mật độ tin nhắn tăng cao đột biến.

##### Tác động đến hệ thống
- Hệ thống tiêu tốn rất nhiều tài nguyên CPU tại Driver để thực hiện suy diễn schema tự động cho từng gói tin.
- Dẫn đến hiện tượng thắt nút cổ chai, làm gia tăng đáng kể độ trễ xử lý (processing lag) của luồng qua các cửa sổ thời gian và có nguy cơ làm tràn bộ đệm hệ thống khi mật độ tin nhắn tăng cao đột biến.

#### Cách tiếp cận đã thử
- **Cách 1:** Sử dụng hàm suy diễn tự động kiểu dữ liệu (inferSchema) hoặc các hàm parse động của Spark để xử lý chuỗi JSON từ Kafka đổ về nhằm tiết kiệm thời gian code cấu hình.
- **Cách 2:** Định nghĩa Schema tĩnh nghiêm ngặt bằng gói StructType ngay từ khâu khởi tạo kết nối luồng.

#### Giải pháp triển khai
- **Ánh xạ Schema tĩnh:** Khởi tạo định dạng cấu trúc bằng StructType bao gồm các trường thông tin tường minh (eventId, eventType, eventTime, userId, category, dwellTimeMs). Cách tiếp cận này giúp Spark bỏ qua bước suy diễn schema tự động, gia tốc tốc độ ánh xạ gói tin JSON từ dạng chuỗi thô sang bảng cấu trúc (Structured DataFrame).
- **Tính toán Feature Engineering:** Sử dụng cấu trúc điều kiện when().otherwise() gán trọng số trực tiếp cho từng loại tương tác tương ứng với mức độ quan tâm của khách hàng đối với danh mục sản phẩm (VIEW = 1, CLICK = 2, ADD_TO_CART = 3, PURCHASE = 5).
- **Kết quả:** Tiến trình bóc tách chuỗi JSON của hệ thống đạt tốc độ tối đa, giải phóng hoàn toàn áp lực xử lý cho Spark Driver. Các vi chuỗi (micro-batch) vận hành ổn định với độ trễ tối thiểu, đảm bảo dữ liệu hành vi được chuyển đổi sang dạng bảng cấu trúc sạch chỉ trong vòng dưới 1 giây sau khi thu nhận từ Kafka.
#### Điểm rút ra
- Đối với các kịch bản phân tích Real-time Streaming, việc định nghĩa schema tĩnh là quy định bắt buộc nhằm tối ưu hóa bộ nhớ và giữ độ trễ của các vi chuỗi (micro-batch) ở mức thấp nhất trên môi trường production.

---

## Bài học 3: Xử lý luồng — Cấu hình S3 Sink Connector để đảm bảo flush đúng

### 3.1. Xử lý cấu hình S3 Sink Connector để đảm bảo flush đúng

#### Mô tả vấn đề

##### Bối cảnh và nền tảng
S3 Sink Connector phụ trách việc flush dữ liệu từ Kafka vào MinIO. Nhóm nhận thấy sau khi Debezium đã ghi message vào Kafka, MinIO vẫn chưa có file Parquet. Airflow DAG chạy `wait_bronze` và ngay lập tức short-circuit do không tìm thấy object.

##### Thách thức gặp phải
- Connector ở trạng thái RUNNING nhưng dữ liệu không xuất hiện trong MinIO.
- Khi dữ liệu có, format bị sai: nhận lỗi `ParquetWriteException: missing schema`.
- Airflow `wait_bronze` thỉnh thoảng short-circuit ngay cả khi đã có dữ liệu do race condition giữa Debezium flush và kiểm tra.

##### Tác động đến hệ thống
- Pipeline bị blocked ở `wait_bronze`, không tiến đến Silver được.
- Dữ liệu mắc kẹt trong Kafka, tăng lag consumer group.

#### Cách tiếp cận đã thử

**Cách 1:** Giảm `flush.size=10` để flush sớm hơn. Tạo quá nhiều small Parquet files, không tốt cho Spark (small file problem).

**Cách 2:** Bật `value.converter.schemas.enable=false`. Gây lỗi: `ParquetFormat requires schema`.

**Cách 3:** Giữ `value.converter.schemas.enable=true`, thêm `rotate.schedule.interval.ms=60000` để đảm bảo flush theo thời gian dù chưa đủ batch size.

#### Giải pháp cuối cùng

- `flush.size=1000` + `rotate.schedule.interval.ms=60000` — cân bằng giữa file size và độ trễ flush.
- `value.converter.schemas.enable=true` — bắt buộc khi dùng ParquetFormat.
- `value.converter=org.apache.kafka.connect.json.JsonConverter` — converter này bảo toàn schema trong JSON envelope, cần thiết cho ParquetFormat đọc schema.
- Airflow `wait_bronze`: thêm fallback `return True` khi không kết nối được MinIO, tránh pipeline bị block bởi network issue không liên quan.
- **Kết quả:** File Parquet xuất hiện trong MinIO trong vòng tối đa 60 giây sau khi có message Kafka; Parquet schema đúng với kiểu dữ liệu.

#### Điểm rút ra

- ParquetFormat của Confluent S3 Sink PHẢI có schema trong Kafka message — `schemas.enable=true` là bắt buộc, không phải tùy chọn.
- `flush.size` và `rotate.schedule.interval.ms` là hai cơ chế flush độc lập — nên cấu hình cả hai để đảm bảo flush đúng hạn kể cả khi traffic thấp.
- Small file problem trong data lake là thực sự — file quá nhỏ làm Spark mất nhiều overhead mở file hơn xử lý data. Flush 1000 records/file là điểm cân bằng hợp lý cho dataset này.

### 3.2. Quản lý Cửa sổ thời gian, Watermarking và Chịu lỗi qua MinIO Checkpoint

#### Mô tả vấn đề

##### Bối cảnh và nền tảng
Luồng dữ liệu hành vi người dùng là dòng dịch chuyển liên tục không có điểm dừng (Unbounded Table). Để đưa ra các chỉ số phân tích có giá trị nghiệp vụ, Spark Consumer cần phải phân đoạn dòng dữ liệu này thành các khối thời gian ngắn và đảm bảo tính bền vững của các mốc chỉ mục đọc (offsets) để hệ thống có khả năng tự phục hồi (Fault Tolerance) khi xảy ra sự cố.

##### Thách thức gặp phải
- Dữ liệu hành vi truyền về từ môi trường mạng vật lý thường xuyên bị trễ, mất đồng bộ hoặc đảo lộn thứ tự thời gian (out-of-order data).
- Khi cấu hình đường dẫn lưu nhật ký checkpoint cục bộ trên môi trường vật lý Windows (/tmp/...), tiến trình Spark liên tục gặp xung đột do cơ chế khóa tệp tin (file-locking) đặc thù của hệ điều hành với cấu trúc I/O của Hadoop Core.

##### Tác động đến hệ thống
- Nếu không kiểm soát dữ liệu trễ, các phép toán tổng hợp cửa sổ thời gian sẽ bị sai lệch nghiêm trọng, đồng thời tài nguyên RAM của hệ thống sẽ bị cạn kiệt do phải lưu giữ trạng thái của các cửa sổ vô hạn.
- Xung đột tệp trên Windows khiến tiến trình Spark Streaming bị sập hoàn toàn (crash) chỉ sau 1-2 chu kỳ xử lý. Hệ thống mất hoàn toàn mốc offset đọc của Kafka Consumer Group khi khởi động lại, gây rủi ro mất mát dữ liệu hành vi của người dùng.

#### Cách tiếp cận đã thử
- **Cách 1:** Cố gắng cấp quyền ghi tối đa (chmod 777 hoặc phân quyền Administrator) cho các thư mục lưu tạm trên ổ đĩa vật lý cục bộ của máy trạm Windows (C:/tmp/...). Phương án này thất bại vì cơ chế khóa tệp tin (file-locking) của Windows xung đột tận gốc với cách thiết kế I/O của Hadoop Core chạy ngầm dưới Spark.
- **Cách 2:** Vô hiệu hóa hoàn toàn thuộc tính lưu vết trạng thái (checkpointLocation). Cách này khiến Spark báo lỗi ngay từ bước biên dịch vì checkpoint là tham số bắt buộc để vận hành luồng stream trạng thái (Stateful Streaming).
- **Cách 3:** Định tuyến toàn bộ vết nhật ký xử lý lên hệ thống Cloud Object Storage tập trung (MinIO) thông qua driver kết nối của giao thức S3A.

#### Giải pháp cuối cùng
- **Xử lý trễ bằng Watermarking:** Áp dụng hàm to_timestamp chuẩn hóa mốc thời gian sự kiện (eventTime), tích hợp thuộc tính .withWatermark("event_ts", "2 minutes") kết hợp cửa sổ chuyển động .groupBy(window(col("event_ts"), "30 seconds")). Cấu hình này cho phép Spark kiên nhẫn chờ các gói tin đến muộn tối đa 2 phút và tự động giải phóng các vùng bộ nhớ đệm của các cửa sổ cũ vượt ngưỡng để bảo vệ RAM.
- **Định tuyến Checkpoint lên Data Lake (MinIO) qua S3A:** Khai báo gói kết nối hệ thống org.apache.hadoop:hadoop-aws:3.3.4 để kích hoạt giao thức S3A. Toàn bộ tham số cấu hình hệ thống được gán trực tiếp vào hadoopConfiguration để kết nối thẳng đến dịch vụ minio:9000 dựa trên biến môi trường từ tệp .env. Đường dẫn checkpointLocation được định tuyến cố định lên Cloud Object Storage nội bộ qua đường dẫn mã hóa s3a://checkpoint/spark_streaming_user_behavior.
- **Kết quả đạt được:** Triệt tiêu hoàn toàn lỗi ghi tệp tạm trên Windows. Khi tiến trình streaming xảy ra sự cố restart, Spark tự động quét ngược lịch sử index trên MinIO để tiếp tục tiêu thụ dòng dữ liệu một cách tuần tự tại vị trí ngắt kết nối gần nhất, bảo toàn ngữ nghĩa xử lý chính xác duy nhất (Exactly-Once Semantics).

#### Điểm rút ra
- Cơ chế Watermark là điều kiện bắt buộc để quản lý vòng đời trạng thái bộ nhớ đệm (Stateful Stream Processing) trong xử lý dữ liệu thời gian thực.
- Tuyệt đối không sử dụng thư mục tạm của hệ điều hành máy trạm cục bộ để lưu vết Checkpoint. Sử dụng Object Storage thông qua giao thức S3A là giải pháp tối ưu nhất để loại bỏ xung đột môi trường và đạt chuẩn chịu lỗi Production.

---

## Bài học 4: Gold Layer — Tổng hợp dữ liệu nghiệp vụ và đồng bộ đa hệ thống lưu trữ

### Mô tả vấn đề

#### Bối cảnh và nền tảng

Sau khi dữ liệu được xử lý ở Silver Layer, dữ liệu đã được làm sạch CDC, loại bỏ các bản ghi cũ và chuẩn hóa về đúng grain.

Tuy nhiên dữ liệu Silver vẫn đang ở mức chi tiết (transaction-level), phù hợp cho việc lưu trữ và phân tích sâu nhưng chưa tối ưu để phục vụ trực tiếp cho ứng dụng hoặc dashboard.

Ví dụ:

Silver Layer có grain:

```
1 dòng = 1 order_item
```

Trong khi các hệ thống phía sau cần những dữ liệu tổng hợp như:

- Doanh thu theo thời gian.
- Hiệu suất bán hàng của seller.
- Phân tích hành vi khách hàng RFM.
- Các chỉ số phục vụ API và dashboard.

Vì vậy cần xây dựng Gold Layer để tổng hợp dữ liệu Silver thành các bảng dữ liệu phục vụ nghiệp vụ.

Ngoài ra Gold Layer cần phục vụ đồng thời nhiều hệ thống:

- MinIO: lưu trữ dữ liệu dạng Parquet lâu dài.
- MongoDB Local: phục vụ truy vấn ứng dụng.
- MongoDB Atlas: phục vụ phân tích và dashboard.

---

### Thách thức gặp phải

- Nếu sử dụng trực tiếp Silver Layer cho frontend hoặc API, mỗi lần truy vấn phải thực hiện lại các phép tính tổng hợp như:

```python
groupBy()
agg()
sum()
count()
```

dẫn đến thời gian phản hồi tăng khi dữ liệu lớn.

- Nếu Spark ghi trực tiếp dữ liệu từ nhiều partition vào MongoDB, mỗi executor có thể tạo một kết nối riêng:

```
Executor 1
Executor 2
Executor 3
...
```

gây nhiều connection đồng thời và làm giảm hiệu năng database.

- Khi pipeline chạy lại, nếu sử dụng cách ghi thông thường:

```python
insert()
```

có thể tạo ra duplicate document trong MongoDB.

- Các truy vấn trên MongoDB nếu không có index sẽ phải scan toàn bộ collection.

---

### Cách tiếp cận đã thử

**Cách 1:** Cho ứng dụng đọc trực tiếp dữ liệu Silver.

Không tối ưu vì Silver chứa dữ liệu chi tiết.

Ví dụ để tính doanh thu:

```python
silver.groupBy("order_date") \
      .agg(sum("price"))
```

phải thực hiện lại mỗi lần truy vấn.

Khi dữ liệu tăng, thời gian xử lý cũng tăng theo.

---

**Cách 2:** Spark ghi trực tiếp từng record sang MongoDB.

Mỗi Spark partition tự ghi dữ liệu:

```
Spark Worker
      |
      |
      v
MongoDB
```

Điều này gây:

- Nhiều kết nối đồng thời.
- Tăng tải MongoDB.
- Pipeline khó kiểm soát.

---

**Cách 3:** Sử dụng insert thông thường khi ghi Gold.

Nếu pipeline chạy lại:

```python
insert_one()
insert_one()
insert_one()
```

sẽ tạo nhiều document trùng nhau.

---

### Giải pháp cuối cùng

#### 1. Xây dựng Gold Dataset bằng Aggregation

Dữ liệu Silver được tổng hợp thành các bảng nghiệp vụ phù hợp với mục đích sử dụng.

---

### Revenue Metric

Grain:

```
1 dòng = 1 khoảng thời gian
```

Từ Silver thực hiện:

```python
groupBy("order_date")
```

Sau đó tính:

```python
sum(price)
count(order_id)
```

Kết quả tạo bảng doanh thu phục vụ dashboard.

---

### Seller Performance

Grain:

```
1 dòng = 1 seller
```

Tổng hợp các chỉ số:

- Tổng doanh thu.
- Số lượng đơn hàng.
- Hiệu suất giao hàng.

Dữ liệu sau khi tổng hợp nhỏ hơn nhiều so với Silver.

---

### Customer RFM

Grain:

```
1 dòng = 1 customer
```

Tính ba nhóm chỉ số:

**Recency**

Khoảng thời gian từ lần mua gần nhất.

**Frequency**

Số lượng đơn hàng của khách.

**Monetary**

Tổng giá trị khách hàng đã chi tiêu.

---

### 2. Multi-Sink Pattern

Sau khi tạo Gold DataFrame, dữ liệu được ghi ra nhiều hệ thống.

---

### Lưu Gold trên MinIO

Dữ liệu được lưu dưới dạng Parquet:

```python
gold.write \
.mode("append") \
.parquet(output_path)
```

Mục đích:

- Lưu trữ dữ liệu lâu dài.
- Có thể đọc lại bằng Spark.
- Phục vụ các truy vấn phân tích lớn.

---

### Đồng bộ sang MongoDB

Do dữ liệu Gold đã được tổng hợp nhỏ hơn Silver, có thể đưa sang MongoDB để phục vụ ứng dụng.

Thay vì để từng Spark partition ghi trực tiếp, sử dụng:

```python
toLocalIterator()
```

để lấy dữ liệu tuần tự về driver.

Flow:

```
Gold DataFrame

      |

toLocalIterator()

      |

bulk_upsert()

      |

MongoDB
```

Cách này giúp:

- Kiểm soát lượng dữ liệu ghi.
- Giảm số lượng connection.
- Tránh gây quá tải database.

---

### 3. Bulk Upsert đảm bảo Idempotent

Pipeline có thể chạy lại nhiều lần.

Nếu chỉ dùng insert:

```
Run 1:
document A

Run 2:
document A
```

sẽ tạo duplicate.

Giải pháp sử dụng:

```python
UpdateOne(
    filter,
    update,
    upsert=True
)
```

Nếu document đã tồn tại:

```
UPDATE
```

Nếu chưa tồn tại:

```
INSERT
```

Ví dụ:

Revenue:

```
ingest_date
```

RFM:

```
customer_unique_id
```

Seller:

```
seller_id
```

được dùng làm key xác định bản ghi.

---

### 4. Tối ưu MongoDB bằng Index

Sau khi load Gold data, pipeline tự động tạo index.

Ví dụ:

```python
create_gold_indexes()
```

Index:

```python
[
    ("seller_id", 1),
    ("ingest_date", 1)
]
```

Giúp MongoDB tìm kiếm theo dimension nhanh hơn.

Nếu không có index:

```
COLLSCAN
```

MongoDB phải đọc toàn bộ collection.

Có index:

```
INDEX SCAN
```

chỉ đọc phần dữ liệu cần thiết.

---

### Kết quả

- Silver Layer được chuyển thành các bảng dữ liệu nghiệp vụ.
- Gold Layer có kích thước nhỏ hơn, phù hợp cho truy vấn.
- Spark không phải tính toán lại KPI mỗi lần ứng dụng truy cập.
- MongoDB giảm tải nhờ bulk upsert.
- Pipeline chạy lại không tạo duplicate.
- FE/FastAPI có thể truy vấn dữ liệu nhanh hơn.
- Dữ liệu được phục vụ đồng thời cho Data Lake và hệ thống ứng dụng.

---

### Điểm rút ra

- Silver Layer tập trung vào làm sạch và chuẩn hóa dữ liệu, Gold Layer tập trung vào nghiệp vụ.
- Mỗi bảng Gold cần xác định grain rõ ràng trước khi tổng hợp.
- Nên thực hiện aggregation trong Spark trước khi đưa dữ liệu sang database.
- Khi Spark ghi sang hệ thống ngoài cần kiểm soát số lượng connection.
- Bulk Upsert phù hợp hơn insert từng document trong Data Pipeline.
- Index MongoDB nên được tạo ngay trong pipeline để đảm bảo hiệu năng truy vấn.
- Một Data Pipeline hoàn chỉnh không chỉ biến đổi dữ liệu mà còn phải tối ưu cách dữ liệu được lưu trữ và phục vụ cho hệ thống phía sau.

---

## Bài học 5: Tích hợp hệ thống — Quản lý multi-network Docker và dependency giữa services

### 5.1. Quản lý đa mạng lưới cô lập bằng Multi-network Docker Compose

#### Mô tả vấn đề

##### Bối cảnh và nền tảng
Hệ thống gồm 13 Docker services cần giao tiếp theo nhiều chiều: Debezium cần đọc PostgreSQL (kafka-network) VÀ ghi MinIO (minio-network), Spark cần đọc MinIO (minio-network) VÀ ghi MongoDB (spark-network).

##### Thách thức gặp phải
- Debezium S3 Sink không thể kết nối MinIO do không cùng Docker network.
- Spark job kết nối được MinIO nhưng không kết nối được MongoDB (khác network).
- Airflow submit Spark job thất bại do không resolve được hostname `spark-master`.

##### Tác động đến hệ thống
- S3 Sink Connector báo `Connection refused` đến MinIO endpoint.
- Spark Gold job hoàn thành Silver nhưng bỏ qua MongoDB sink hoàn toàn.

#### Cách tiếp cận đã thử

**Cách 1:** Đặt tất cả services vào một Docker network duy nhất. Vấn đề bảo mật — mọi service đều nhìn thấy nhau.

**Cách 2:** Dùng multi-network Docker Compose — mỗi service join đúng các networks cần thiết. Cần thiết kế cẩn thận.

#### Giải pháp cuối cùng

Thiết kế 4 Docker networks với nguyên tắc **minimum necessary access**:

- `kafka-network`: postgres + zookeeper + kafka + debezium
- `minio-network`: debezium + minio + spark-master + spark-worker + airflow
- `spark-network`: spark-master + spark-worker + mongodb + airflow
- `airflow-network`: airflow-webserver + airflow-scheduler + mongodb (cho MongoHook tương lai)

Services cần giao tiếp nhiều chiều (debezium, spark, airflow) được join vào nhiều networks tương ứng.

- **Kết quả:** Tất cả kết nối giải quyết đúng theo hostname Docker DNS. Spark job ghi đồng thời MinIO và MongoDB thành công.

#### Điểm rút ra

- Multi-network Docker Compose là best practice cho hệ thống phức tạp — tránh flat network cho phép mọi service nói chuyện với mọi service.
- Service ở điểm giao (như Debezium — vừa là Kafka consumer, vừa là MinIO producer) cần join nhiều network.
- Dùng Docker DNS hostname (tên service trong compose) thay vì IP address — IP thay đổi khi container restart, hostname thì không.
- Kiểm tra network bằng `docker network inspect <network>` để xác nhận đúng services trong network trước khi debug connectivity issue.

### 5.2 Kiến trúc Đồng bộ Đa nguồn Staging & Transaction qua foreachBatch

#### Mô tả vấn đề

##### Bối cảnh và nền tảng
Kết quả tính toán tổng hợp điểm ưa thích từ luồng sinh sự kiện của Speed Layer cần phải được đồng bộ hóa ngay lập tức vào cơ sở dữ liệu quan hệ PostgreSQL (olist). Mục tiêu là cập nhật liên tục hai bảng nghiệp vụ: user_preference (bảng lưu lũy kế điểm theo danh mục) và user_recommendation (bảng lưu Top 10 sản phẩm gợi ý cá nhân hóa) nhằm phục vụ trực tiếp cho Product-API hiển thị lên giao diện.

##### Thách thức gặp phải
- Phương thức tích hợp JDBC mặc định của luồng xử lý Spark (.writeStream) cấu trúc dạng streaming chỉ hỗ trợ ghi thô ở các chế độ cơ bản (Append/Overwrite) trên một bảng đơn mục tiêu.
- Spark JDBC hoàn toàn không hỗ trợ thực thi chuỗi câu lệnh kiểm soát giao dịch nâng cao có tính nguyên tố cao (Atomic Transactions) như xử lý xung đột khóa chính (ON CONFLICT DO UPDATE), xóa dữ liệu cũ và gộp liên đới sang bảng thứ hai.

##### Tác động đến hệ thống
- Hệ thống dễ sinh lỗi ghi trùng lặp dữ liệu (duplicate) nếu tiến trình chạy lại.
- Việc cố gắng thực thi nhiều câu lệnh truy vấn riêng lẻ từ Spark sang hệ quản trị cơ sở dữ liệu quan hệ (RDBMS) không qua cơ chế quản lý transaction sẽ gây xung đột tài nguyên, tăng hàng đợi kết nối và làm nghẽn mạch toàn bộ hệ thống cơ sở dữ liệu cốt lõi của nhóm.

#### Cách tiếp cận đã thử
- **Cách 1:** Sử dụng các lệnh ghi SQL hoặc cấu hình JDBC mặc định của Spark để ghi trực tiếp kết quả luồng sang các bảng Postgres. Phương án này không khả thi vì JDBC mặc định của luồng streaming chỉ hỗ trợ Append/Overwrite đơn thuần, hoàn toàn bất lực trước các logic transaction phức tạp liên đới nhiều bảng.
- **Cách 2:** Ghi dữ liệu luồng ra Console Sink hoặc tệp tin Parquet tạm, sau đó dùng một công cụ/script Python độc lập bên ngoài để đọc và nạp vào Postgres. Cách này làm tăng độ trễ hệ thống, vi phạm nguyên lý thời gian thực của Speed Layer và làm phình to kiến trúc hạ tầng một cách không cần thiết.
- **Cách 3:** Sử dụng phương thức xử lý vi chuỗi nâng cao .foreachBatch() để bóc tách luồng thành các batch nhỏ, kết hợp ghi đè bảng tạm Staging bằng Spark JDBC và thực thi chuỗi transaction bằng Driver gốc psycopg2.

#### Giải pháp cuối cùng
- **Ghi đệm Staging:** Trong mỗi chu kỳ micro-batch, Spark thực hiện gom nhóm dữ liệu về grain (user_id, category), lấy mốc thời gian cuối cửa sổ và sử dụng Spark JDBC ghi đè siêu tốc (mode("overwrite")) toàn bộ cục dữ liệu tạm thời đó vào một bảng trung gian trong Postgres mang tên user_preference_staging.
- **Kích hoạt Transaction Nguyên tố (Atomic):** Ngay sau khi bảng staging được nạp đầy, tiến trình mở một kết nối Driver gốc duy nhất bằng thư viện psycopg2 sang Postgres và thực thi chuỗi lệnh quản trị transaction khép kín:
  - **Bước 1 (Upsert điểm):** Chạy câu lệnh INSERT INTO user_preference ... SELECT ... FROM user_preference_staging ON CONFLICT (user_id, category) DO UPDATE SET score = user_preference.score + EXCLUDED.score nhằm cập nhật tổng điểm tương tác.
  - **Bước 2 (Xóa vết cũ):** Thực hiện DELETE FROM user_recommendation để xóa sạch các đề xuất sản phẩm cũ của những người dùng vừa có biến động hành vi trong batch hiện tại.
  - **Bước 3 (Truy vấn thuật toán sinh đề xuất mới):** Thực hiện câu lệnh nạp dữ liệu phức tạp (INSERT INTO user_recommendation), sử dụng hàm cửa sổ ROW_NUMBER() OVER (PARTITION BY up.user_id ORDER BY up.score DESC, p.product_id) thực hiện JOIN trực tiếp bảng điểm ưa thích với danh mục sản phẩm của hệ thống, xếp hạng mức độ ưu tiên từ cao xuống thấp và chỉ lọc lấy đúng Top 10 sản phẩm hàng đầu (WHERE sequence_no <= 10).
  - **Bước 4 (Dọn dẹp hạ tầng):** Chạy lệnh TRUNCATE TABLE user_preference_staging để dọn sạch bảng tạm, sau đó gọi lệnh conn.commit() để chốt hạ phiên làm việc an toàn.

#### Điểm rút ra
Phương thức foreachBatch phối hợp với chiến thuật bảng đệm Staging là mô hình kiến trúc tối ưu nhất để giải quyết bài toán đồng bộ hóa dữ liệu từ công cụ xử lý luồng (Streaming Engines) sang các hệ cơ sở dữ liệu quan hệ truyền thống (RDBMS), bảo toàn vẹn toàn tính toàn vẹn của dữ liệu nghiệp vụ và giải phóng áp lực tính toán cho Spark Driver.

---

## Bài học 6: Tối ưu hiệu năng — Cấu hình Spark cho môi trường resource-constrained

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Môi trường phát triển là máy cá nhân (8GB RAM, 4 core). Spark Master + Worker + Airflow + Kafka + MinIO chạy đồng thời tiêu thụ phần lớn tài nguyên. Spark job thường xuyên bị slow hoặc OOM.

#### Thách thức gặp phải
- Spark Silver job mất 20–30 phút trên dataset ~100K rows — bất thường.
- Spark Gold job bị OOM khi collect RFM statistics (mean, stddev) về Driver.
- Nhiều Spark stages có skew partition — một task chạy 90% thời gian, các task còn lại idle.

#### Tác động đến hệ thống
- Airflow DAG timeout sau 1 giờ, đánh dấu job failed.
- Driver OOM crash khiến toàn bộ application failed, không có partial result.

### Cách tiếp cận đã thử

**Cách 1:** Tăng `spark.executor.memory=4g`. Conflict với Kafka và Airflow cùng chạy, toàn bộ hệ thống chậm hơn.

**Cách 2:** Dùng `spark.sql.shuffle.partitions=10` thay vì mặc định 200 — phù hợp với dataset nhỏ.

**Cách 3:** Cache Silver DataFrame (`silver.cache()`) trước khi dùng cho nhiều UC tables. Tránh đọc lại từ MinIO 5 lần.

### Giải pháp cuối cùng

- `spark.sql.shuffle.partitions=10` — giảm từ 200 xuống 10 phù hợp với dataset ~100K rows. Quá nhiều partition tạo overhead scheduling.
- `silver.cache()` + `silver.count()` (trigger cache materialization) trước vòng lặp Gold UC. Silver được đọc từ MinIO 1 lần, dùng 5 lần từ memory.
- `broadcast()` hint chủ động cho các bảng dimension nhỏ — Spark optimizer đôi khi không tự nhận diện broadcast threshold.
- Thống kê Driver (mean, stddev) dùng `df.agg(...).collect()` một lần, lưu vào Python biến cục bộ, tránh nhiều collect calls.
- **Kết quả:** Silver job: 20–30 phút → 3–5 phút. Gold job: không còn OOM. Toàn bộ DAG hoàn thành trong ~12 phút.

### Điểm rút ra

- `spark.sql.shuffle.partitions=200` là mặc định cho cluster lớn — với dataset nhỏ cần giảm, hoặc dùng `spark.sql.adaptive.enabled=true` (AQE) để Spark tự điều chỉnh.
- Cache hữu ích khi cùng DataFrame được đọc nhiều lần trong một session. Tuy nhiên cache tốn memory — chỉ cache DataFrame đủ nhỏ.
- Hạn chế `collect()` về Driver: chỉ dùng khi cần một số lượng nhỏ giá trị tổng hợp. Driver memory là bottleneck khi collect tập lớn.
- Spark UI (port 4040 khi job đang chạy, 8082 sau khi xong) là công cụ thiết yếu để diagnose slow stages và skew partitions.

---

## Bài học 7: Giám sát và Gỡ lỗi — Theo dõi pipeline qua Airflow + Spark UI

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Khi pipeline có vấn đề, nhóm cần xác định nguyên nhân gốc rễ nhanh chóng. Ban đầu, nhóm chỉ nhìn vào log cuối của Airflow task — thường là thông báo lỗi chung chung không đủ thông tin.

#### Thách thức gặp phải
- Airflow báo task `gold` failed với `SparkException: Job aborted` — không rõ nguyên nhân.
- Spark UI hiển thị nhiều failed stages nhưng không rõ stage nào là nguyên nhân gốc.
- Debezium connector trạng thái `RUNNING` nhưng Kafka topics không có message mới.

#### Tác động đến hệ thống
- Mất 2–3 giờ debug mỗi khi có lỗi mới do thiếu observability.
- Khó phân biệt lỗi transient (network timeout) vs. lỗi persistent (schema mismatch).

### Cách tiếp cận đã thử

**Cách 1:** Đọc Airflow task log từ đầu đến cuối. Quá dài (>10.000 dòng), mất nhiều thời gian.

**Cách 2:** Tìm từ khóa `ERROR` hoặc `Exception` trong log. Bỏ sót warning quan trọng xuất hiện trước exception.

**Cách 3:** Thiết lập hierarchy debugging: Airflow → Spark UI → Executor logs → Application logs.

### Giải pháp cuối cùng

Nhóm xây dựng quy trình debug 4 bước:

1. **Airflow UI** (`localhost:8081`): Xem task log, tìm `Caused by:` — đây là root cause thực sự, không phải message đầu tiên.
2. **Spark Master UI** (`localhost:8082`): Xem Applications tab, click vào application failed, xem Jobs → Stages → Failed Tasks. Stage nào có nhiều Failed Tasks nhất là điểm khởi đầu.
3. **Executor stderr**: Trong Spark UI, click vào failed task, xem "Stderr" — chứa Java stack trace đầy đủ.
4. **Debezium REST API**: `GET /connectors/{name}/status` trả về `{connector: {state: "RUNNING"}, tasks: [{state: "FAILED", trace: "..."}]}` — connector ở trạng thái RUNNING nhưng task bên trong có thể FAILED.

Thêm `log.setLevel(logging.INFO)` vào Spark jobs để in row count sau mỗi bước transform — giúp nhanh chóng xác định bước nào tạo ra data bất thường.

- **Kết quả:** Thời gian debug trung bình giảm từ 2–3 giờ xuống 20–30 phút.

### Điểm rút ra

- `Caused by:` trong Java stack trace là root cause thực sự — không đọc từ đầu mà tìm `Caused by:` cuối cùng trong chain.
- Debezium connector status phân biệt trạng thái **connector** (worker process) và **task** (actual CDC thread) — connector RUNNING không có nghĩa task đang hoạt động.
- Spark UI là công cụ không thể thiếu — debug qua log thuần túy là không đủ với distributed computing.
- Row count logging ở mỗi bước transform là "poor man's data observability" — đơn giản nhưng cực kỳ hữu ích.

---

## Bài học 8: Mở rộng (Scaling) — Triển khai từ Docker Compose lên Kubernetes

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Sau khi pipeline hoạt động ổn định trên Docker Compose, nhóm cần port sang Kubernetes để đáp ứng yêu cầu bài tập. Kubernetes có model khác hoàn toàn: không có `depends_on`, không có shared volume tự động, networking dùng Service thay vì DNS compose.

#### Thách thức gặp phải
- PostgreSQL pod khởi động trước Debezium nhưng schema SQL chưa chạy xong, Debezium kết nối thất bại.
- Spark code không được mount vào pod vì Kubernetes không có Docker volume đơn giản.
- Spark Master RPC port (`7077`) không accessible từ Airflow pod do không có Service đúng.

#### Tác động đến hệ thống
- Debezium pod CrashLoopBackOff liên tục trong 5–10 phút sau khi deploy.
- Airflow SparkSubmit failed với `Connection refused to spark-master:7077`.

### Cách tiếp cận đã thử

**Cách 1:** Dùng `initContainers` để wait-for PostgreSQL ready trước khi Debezium start. Đúng hướng nhưng phức tạp khi viết health check.

**Cách 2:** Đóng gói code Spark vào Docker image. Cần build lại image mỗi khi sửa code — quá chậm cho development.

**Cách 3:** Dùng ConfigMap để mount code Spark vào `/opt/project/`. Linh hoạt, không cần build image khi sửa code.

### Giải pháp cuối cùng

- **Init Containers:** Thêm `initContainers` vào Debezium Deployment chạy `curl --retry 10 http://postgres:5432` trước khi main container start. Đảm bảo PostgreSQL sẵn sàng trước Debezium.
- **ConfigMap cho code:** `kubectl create configmap spark-batch-code --from-file=spark-batch/`, mount vào `/opt/project/spark-batch/`. `make k8s-code-configmaps` tự động hóa bước này.
- **Service cho Spark Master:** Tạo Service `spark-master` với port `7077` (RPC) và `8082` (Web UI) — Kubernetes cần Service để expose pod port.
- **PYTHONPATH:** ConfigMap `spark-env` với `PYTHONPATH=/opt/project` — đảm bảo Spark job import được `services.mongodb_connect`.
- **Kết quả:** Kubernetes deploy ổn định, tất cả pod Running sau ~3 phút. `make k8s-test-all` pass.

### Điểm rút ra

- Kubernetes không có `depends_on` như Docker Compose — phải tự xử lý startup ordering bằng `initContainers` hoặc readiness probes.
- ConfigMap là cách mount code vào pod mà không rebuild image — lý tưởng cho development và demo.
- Mỗi pod port cần Service tương ứng để accessible trong cluster — đây là khác biệt cơ bản so với Docker Compose.
- `kubectl describe pod <pod>` và `kubectl logs <pod> --previous` là hai lệnh debug K8s phổ biến nhất.

---

## Bài học 9: Chất lượng dữ liệu và Kiểm thử — Kiểm tra tính nhất quán qua các tầng Medallion

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Với kiến trúc 3 tầng (Bronze → Silver → Gold), lỗi dữ liệu ở tầng dưới sẽ lan rộng lên tầng trên. Nhóm cần kiểm tra tính đúng đắn của dữ liệu sau mỗi bước transform, không chỉ kiểm tra job có thành công hay không.

#### Thách thức gặp phải
- Silver job thành công (exit 0) nhưng số dòng Silver chỉ bằng 60% Bronze — bị lọc sai.
- Gold `revenue_daily` trả về giá trị âm do dữ liệu test bị insert sai.
- Một số cột timestamp trong Silver là `null` do hàm `timestamp_micros()` nhận sai kiểu input.

#### Tác động đến hệ thống
- Gold metrics sai hoàn toàn, không phản ánh business logic đúng.
- Bug âm thầm không được phát hiện đến khi kiểm tra thủ công kết quả Gold.

### Cách tiếp cận đã thử

**Cách 1:** Tin tưởng vào exit code của Spark job. Không đủ — Spark có thể thành công với 0 dòng output.

**Cách 2:** Thêm assertion trong Spark code: `assert silver.count() > 0, "Silver is empty"`. Dừng job khi có vấn đề nhưng không rõ vấn đề ở đâu.

**Cách 3:** Log row count sau mỗi bước transform quan trọng. Cung cấp visibility tốt hơn.

### Giải pháp cuối cùng

Nhóm xây dựng **data quality checklist** chạy sau mỗi Spark job:

**Kiểm tra Bronze:**
- Count bản ghi mỗi bảng: `SELECT COUNT(*) FROM (READ bronze parquet)`.
- Không có cột bắt buộc nào là null (`order_id`, `__ts_ms`).

**Kiểm tra Silver:**
- `silver.count()` phải xấp xỉ `order_items.count()` (±5%).
- `silver.filter(col("price").isNull()).count() == 0`.
- Kiểm tra grain: `silver.groupBy("order_id", "order_item_id").count().filter("count > 1").count() == 0`.

**Kiểm tra Gold:**
- `gold_revenue_metrics.filter(col("revenue_daily") < 0).count() == 0`.
- Row count mỗi collection > 0.

Những check này được log ra trong Spark job — khi có số bất thường, nhóm biết ngay cần kiểm tra lại.

- **Kết quả:** Phát hiện 3 lỗi data quality trong quá trình phát triển mà không có check này sẽ bị bỏ qua.

### Điểm rút ra

- Exit code = 0 của Spark job chỉ nghĩa là "job không crash", không nghĩa là "dữ liệu đúng".
- Row count là metric đơn giản nhất nhưng bắt được nhiều lỗi nhất (empty DataFrame, data duplication, over-filtering).
- Kiểm tra grain (unique key constraint) là bước quan trọng sau join — đảm bảo không có data multiplication ẩn.
- Data quality check nên là một phần của pipeline, không phải là bước debug thủ công sau khi phát hiện vấn đề.

---

## Bài học 10: Bảo mật và Quản trị — Quản lý credentials trong môi trường multi-service

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Hệ thống có nhiều credentials: PostgreSQL password, MinIO access key/secret key, MongoDB URI có password, MongoDB Atlas connection string. Ban đầu nhóm hardcode trực tiếp vào code và Docker Compose file để nhanh chóng thử nghiệm.

#### Thách thức gặp phải
- Credentials xuất hiện trong `git log` sau khi commit code lên repository.
- Thay đổi password một service đòi hỏi sửa nhiều file khác nhau.
- Kubernetes Deployments có credentials dạng plaintext trong YAML manifest.

#### Tác động đến hệ thống
- Rủi ro bảo mật nếu repository public.
- Khó maintain khi credentials thay đổi.

### Cách tiếp cận đã thử

**Cách 1:** Dùng biến môi trường OS. Không portable, người khác clone repo cần cấu hình tay.

**Cách 2:** File `.env` với `docker-compose` interpolation. Tiện lợi cho Docker Compose, nhưng vẫn cần xử lý `.env` cho Kubernetes.

**Cách 3:** Kubernetes Secrets + Docker `.env` file, loại trừ `.env` khỏi git.

### Giải pháp cuối cùng

- **Docker Compose:** Tất cả credentials trong `init/.env`, Docker Compose đọc qua `${VAR_NAME}`. File `.env` không commit git (thêm vào `.gitignore`). Cung cấp file `.env.example` với placeholder values để người dùng mới biết cần điền gì.
- **Kubernetes:** Dùng `kubectl create secret generic postgres-secret --from-literal=...`, manifest YAML tham chiếu qua `secretKeyRef` thay vì hardcode value.
- **Spark code:** Đọc từ biến môi trường (`os.environ.get("MONGO_LOCAL_URI", "")`) thay vì hardcode. Nếu biến trống, bỏ qua sink tương ứng.
- **Kết quả:** Không có credentials trong git history. Dễ thay đổi một credentials mà không ảnh hưởng code.

### Điểm rút ra

- `.env.example` (commit vào git) + `.env` thực (không commit) là pattern chuẩn cho quản lý credentials local.
- Kubernetes Secrets không phải "thực sự bảo mật" (base64, không encrypt) nhưng tốt hơn plaintext trong YAML. Production cần HashiCorp Vault hoặc AWS Secrets Manager.
- Code phải fail gracefully khi thiếu credentials (không crash, chỉ skip), đặc biệt với optional services như MongoDB Atlas.
- Luôn scan git history trước khi public hóa repository (`git log -p | grep -i password`).

---

## Bài học 11: Chịu lỗi — Xử lý restart và recovery trong pipeline phân tán

### Mô tả vấn đề

#### Bối cảnh và nền tảng
Trong môi trường phát triển, service thường xuyên restart (OOM, Docker daemon restart, máy tắt đột ngột). Nhóm cần đảm bảo pipeline có thể phục hồi mà không mất dữ liệu hoặc tạo ra duplicate.

#### Thách thức gặp phải
- Kafka Consumer Group offset bị mất khi Debezium container restart, S3 Sink đọc lại từ đầu topic và ghi duplicate Parquet files vào Bronze.
- PostgreSQL WAL replication slot bị drop tự động do `max_slot_wal_keep_size` khi WAL log tích lũy quá lớn.
- Spark Silver/Gold job với mode `append` tạo duplicate khi chạy lại do không có dedup ở giai đoạn ghi.

#### Tác động đến hệ thống
- Bronze zone chứa duplicate Parquet, Silver dedup không đủ mạnh để lọc sạch.
- PostgreSQL slot bị drop → Debezium mất vị trí đọc WAL → cần re-snapshot toàn bộ.
- Gold collection có document duplicate, MongoDB `bulk_upsert` giải quyết một phần nhưng cần key đúng.

### Cách tiếp cận đã thử

**Cách 1:** Dùng Spark `overwrite` mode cho Silver/Gold. Đảm bảo idempotency — chạy lại bao nhiêu lần vẫn cho kết quả đúng, nhưng tốn thời gian recompute toàn bộ.

**Cách 2:** Kafka `enable.auto.commit=true` cho S3 Sink. Offset được commit sau khi flush thành công, restart không đọc lại từ đầu.

**Cách 3:** MongoDB `bulk_upsert` với key fields xác định — update nếu key tồn tại, insert nếu không. Idempotent cho Gold MongoDB.

### Giải pháp cuối cùng

- **Spark `overwrite` mode:** Tất cả Silver và Gold write đều dùng `overwrite`. Đây là quyết định có chủ ý: đánh đổi tốc độ lấy correctness và simplicity. Trong phase 1 batch, recompute toàn bộ mỗi ngày là chấp nhận được.
- **Kafka offset commit:** Cấu hình S3 Sink với `offset.flush.interval.ms=10000`, đảm bảo offset được commit thường xuyên.
- **MongoDB `bulk_upsert`:** Dùng `UpdateOne` với `upsert=True` và filter theo key fields. Chạy lại bao nhiêu lần vẫn không tạo duplicate.
- **Airflow `wait_bronze`:** Kiểm tra MinIO trước khi chạy Silver/Gold — nếu Bronze trống (có thể do Debezium chưa kịp flush sau restart), pipeline dừng sớm thay vì sinh ra Silver/Gold rỗng.
- **Kết quả:** Pipeline có thể restart từ bất kỳ bước nào mà không cần manual intervention. Airflow DAG re-trigger cho kết quả đúng.

### Điểm rút ra

- **Idempotency** là thuộc tính quan trọng nhất của pipeline phân tán — mỗi bước phải cho cùng kết quả dù chạy 1 hay N lần.
- `overwrite` mode là giải pháp đơn giản nhất để đảm bảo idempotency cho batch pipeline. Incremental/append cần cơ chế dedup phức tạp hơn.
- MongoDB `upsert` thay vì `insert` là default assumption cho serving layer — dữ liệu luôn được cập nhật, không bao giờ duplicate.
- Thiết kế recovery path trước khi cần, không phải sau khi sự cố xảy ra. Câu hỏi cần tự hỏi: "Nếu bước này fail, pipeline có thể tiếp tục từ đâu?"

---

*Báo cáo được thực hiện trong khuôn khổ môn học IT4931 — Lưu trữ và Xử lý Dữ liệu Lớn, Trường Đại học Bách khoa Hà Nội.*
