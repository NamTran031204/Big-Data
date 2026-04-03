# Big-Data

# Cấu trúc dự án
sales-bigdata-pipeline/
├── docker/                         # Hạ tầng (Infrastructure-as-Code)
│   ├── docker-compose.yml          # File điều khiển toàn bộ dịch vụ
│   ├── postgres/                   # Cấu hình cho DB Source & Warehouse
│   │   └── init-source.sql         # Script tạo table cho Olist ban đầu
│   ├── kafka/                      # Cấu hình Kafka & Debezium
│   │   └── connectors/             # File JSON cấu hình Debezium CDC
│   └── airflow/                    # Dockerfile tùy chỉnh cho Airflow
│
├── data/                           # Lưu trữ cục bộ (Local Storage)
│   ├── external/                   # Chứa CSV tải từ Kaggle (Olist)
│   └── minio/                      # Thư mục vật lý ánh xạ vào MinIO (Data Lake)
│       ├── raw/                    # Dữ liệu Parquet thô từ Kafka
│       └── gold/                   # Dữ liệu sạch sau khi Spark xử lý
│
├── services/                       # Mã nguồn các dịch vụ xử lý
│   ├── ingestion-java/             # Spring Boot: Kafka -> MinIO (Parquet)
│   │   ├── src/main/java/...       # Logic chuyển đổi JSON sang Parquet
│   │   └── pom.xml                 # Dependency: spring-kafka, hadoop-common, parquet
│   ├── spark-jobs/                 # PySpark: Xử lý dữ liệu lớn
│   │   ├── transform_sales.py      # Làm sạch và tính toán KPIs
│   │   └── data_validation.py      # Kiểm tra chất lượng (Great Expectations)
│   └── warehouse-dbt/              # DBT: Biến đổi dữ liệu trong Postgres
│       ├── models/                 # SQL models cho doanh thu, sản phẩm
│       └── dbt_project.yml
│
├── orchestration/                  # Điều phối (Orchestration)
│   └── dags/                       # Các luồng tự động hóa của Airflow
│       └── main_pipeline_dag.py    # Điều khiển: Spark -> DBT -> Dashboard
│
├── monitoring/                     # Giám sát (Monitoring)
│   └── grafana/                    # Dashboard JSON & Data Sources
│
├── scripts/                        # Các script tiện ích
│   ├── setup_connectors.sh         # Script kích hoạt Debezium qua API
│   └── load_csv_to_source.py       # Script nạp Olist CSV vào Postgres ban đầu
├── Makefile                        # Phím tắt điều khiển dự án (make up, make down)
└── README.md                       # Tài liệu hướng dẫn chi tiết

# Luồng dữ liệu (Data Pipeline)

Giai đoạn 1: Thu thập (Ingestion)
PostgreSQL (Source): Nơi lưu trữ dữ liệu bán hàng ban đầu (giả lập database của app bán hàng).

Debezium: Công cụ theo dõi thay đổi (CDC) - nếu có đơn hàng mới vào Postgres, thông báo ngay cho Kafka.

Apache Kafka: Hệ thống hàng đợi tin nhắn, trung chuyển dữ liệu theo thời gian thực.

Giai đoạn 2: Lưu trữ thô (Data Lake)
MinIO: Kho lưu trữ tệp tin (tương đương Amazon S3), dùng để lưu trữ dữ liệu thô dưới dạng file để không làm nặng database.

Parquet: Định dạng file nén chuyên dụng cho Big Data, giúp đọc/ghi dữ liệu nhanh hơn nhiều so với CSV truyền thống.

Giai đoạn 3: Xử lý dữ liệu (Processing)
PySpark: Dùng để tính toán doanh thu, lọc dữ liệu rác và gộp các bảng dữ liệu lại với nhau.

Java / Spring Boot: Dùng để viết các dịch vụ nhỏ (Microservices) đọc dữ liệu từ Kafka và ghi vào Data Lake .

Giai đoạn 4: Kho dữ liệu & Biến đổi (Warehouse & Transform)
PostgreSQL (Warehouse): Một database riêng biệt chỉ chứa dữ liệu đã được làm sạch và tính toán xong, sẵn sàng để vẽ biểu đồ.

DBT (Data Build Tool): Sử dụng SQL để tạo ra các bảng báo cáo cuối cùng (ví dụ: bảng tổng doanh thu theo tháng) từ dữ liệu thô trong kho.

Giai đoạn 5: Quản lý & Hiển thị
Apache Airflow: Giúp lập lịch tự động: 8h sáng chạy Spark, 9h sáng cập nhật báo cáo, nếu lỗi thì gửi thông báo.

Grafana: Giao diện Dashboard để vẽ biểu đồ đường, cột, bản đồ nhiệt thể hiện tình hình kinh doanh.