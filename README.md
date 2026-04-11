# Big-Data

# Cấu trúc dự án
```
BIGDATA/
├── config/                     Lưu thông tin kết nối Cloud
│   ├── confluent_cloud.conf    # API Key, Secret của Kafka
│   ├── mongodb_atlas.env       # URI kết nối NoSQL
│   └── spark_config.py         # Cấu hình Spark Master & Driver
├── data/                       Mô phỏng HDFS/S3
│   ├── external/               # Chứa các file CSV Olist gốc
│   ├── raw/                    # Dữ liệu thô từ Kafka đổ về (Parquet)
│   ├── silver/                 # Dữ liệu đã sạch & Join (Delta/Parquet)
│   └── gold/                   # Dữ liệu Aggregated sẵn sàng cho NoSQL
├── deployment/             
│   ├── k8s/                    # File .yaml cho Minikube (Kubernetes)
│   │   ├── debezium-pod.yaml      # Triển khai CDC trên K8s
│   │   └── grafana-service.yaml   # Monitoring trên K8s
│   └── local_setup/            # Script cài đặt môi trường Native (Java, Spark)
├── orchestration/              Điều phối luồng
│   └── dags/                   # Các script Python cho Airflow (Native)
├── scripts/                    Các công cụ bổ trợ
│   ├── ingest_initial.py       # Script nạp dữ liệu ban đầu vào Postgres
│   └── verify_pipeline.py      # Kiểm tra kết nối end-to-end
├── services/                   Mã nguồn xử lý
│   ├── spark-streaming/        # Code PySpark xử lý luồng (Intermediate level)
│   │   ├── window_aggregates.py   # Xử lý Windowing & Watermarking
│   │   └── broadcast_joins.py     # Tối ưu hóa hiệu năng Spark
│   ├── warehouse-nosql/        # Code đẩy dữ liệu vào MongoDB
│   └── ingestion-native/       # Nếu có code Java/Python CDC riêng
├── README.md              
└── requirements.txt        # Các thư viện Python (PySpark, pymongo, confluent-kafka)           
```
            
# Luồng dữ liệu (Data Pipeline)

Giai đoạn 1: Thu thập & Luồng dữ liệu (Streaming Ingestion)
PostgreSQL (Native Source): Cơ sở dữ liệu nguồn cài trực tiếp trên Windows, lưu trữ giao dịch bán hàng Olist.

Debezium (Kubernetes - Minikube): Chạy dưới dạng một Pod trên Minikube (để đáp ứng yêu cầu K8s). Nó theo dõi thay đổi (CDC) từ Postgres và đẩy ngay lập tức lên Cloud.

Confluent Cloud (Apache Kafka): Hệ thống hàng đợi tin nhắn nằm hoàn toàn trên Cloud. Giúp giảm tải RAM cho máy.

Giai đoạn 2: Lưu trữ phân tán (Distributed Storage - Bronze Layer)
MinIO (Local/K8s): Đóng vai trò là hệ thống lưu trữ đối tượng (tương đương HDFS hoặc Amazon S3). Đây là nơi lưu trữ dữ liệu thô (Raw Data) để phục vụ việc tính toán lại khi cần.

Parquet Format: Dữ liệu từ Kafka được nạp vào MinIO dưới định dạng cột Parquet, giúp tối ưu hóa dung lượng lưu trữ và tốc độ đọc cho Spark.

Giai đoạn 3: Xử lý dữ liệu nâng cao (Processing - Silver & Gold Layer)
PySpark (Native): Cài đặt trực tiếp trên Windows (đã cấu hình Java 17). Tại đây thực hiện:

Windowing: Tính toán doanh thu theo cửa sổ thời gian (10 phút, 1 giờ).

Broadcast Join: Tối ưu hóa việc gộp bảng lớn (Orders) với bảng nhỏ (Categories).

Watermarking: Xử lý dữ liệu đến trễ từ luồng Kafka.

Java / Spring Boot: Viết Microservice đọc dữ liệu vàng từ Kafka để ghi vào kho NoSQL.

Giai đoạn 4: Kho dữ liệu NoSQL & Biến đổi (Serving Layer)
MongoDB Atlas (NoSQL Cloud): Dùng MongoDB trên mây để lưu trữ kết quả đã xử lý. 

dbt (Data Build Tool): Sử dụng để quản lý các câu lệnh biến đổi dữ liệu, đảm bảo dữ liệu trong MongoDB luôn ở trạng thái sẵn sàng nhất cho việc báo cáo.

Giai đoạn 5: Triển khai & Trực quan hóa (Deployment & Monitoring)
Minikube (Kubernetes): Toàn bộ các dịch vụ bổ trợ (Debezium, Monitoring) được triển khai trên cụm K8s nội bộ.

Grafana: Kết nối trực tiếp vào MongoDB Atlas hoặc Postgres để vẽ Dashboard thời gian thực, theo dõi các chỉ số kinh doanh và hiệu năng hệ thống.


# Ae cài python 3.12 và java 17 nhé (python 3.14 và java bản cao hơn có nhiều cái không tương thích với nhau)
# Ở đây tôi đang dùng dataset của olist. Link đây nhé : https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
# Ae cài spark bản 3.5.8 nhé( dùng cho ổn định)