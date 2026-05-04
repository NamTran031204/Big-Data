# Big Data - Real-time Streaming Pipeline

## Tech Stack
- **Language:** Python 3.12
- **Stream Processing:** PySpark 3.5.8 (Structured Streaming)
- **Message Broker:** Apache Kafka (Dockerized)
- **Storage & Fault Tolerance:** MinIO (S3 Compatible Storage)
- **Data Generation:** Faker Library
- **Environment:** Docker, Java 21, Hadoop Winutils (Windows Fix)

## Tiến độ
### Tuần 1: Streaming Study & Prep
- [x] Thiết lập hạ tầng Kafka & Zookeeper bằng Docker Compose.
- [x] Phát triển script \`producer.py\` giả lập dữ liệu đơn hàng thời gian thực.
- [x] Tìm hiểu mô hình **Unbounded Table** và **Windowing**.

### Tuần 2: Kafka Consumer Setup
- [x] **Create kafka_consumer.py:** Đọc dữ liệu từ Kafka topic \`orders_topic\`, parse JSON và định nghĩa Schema chuẩn. Viết kết quả ra Console để kiểm thử.
- [x] **Test streaming pipeline basics:** Sử dụng bộ sinh dữ liệu giả lập, xác nhận Spark đọc thành công từ Kafka và kiểm tra cơ chế quản lý offset.
- [x] **Create checkpoint directory:** Thiết lập vị trí lưu trữ checkpoint trên **MinIO** thông qua giao thức S3A. Đã kiểm tra khả năng phục hồi dữ liệu sau khi gặp sự cố.
- [x] **Document streaming architecture:** Hoàn thiện sơ đồ luồng dữ liệu (Data flow diagram) và ánh xạ các Kafka topics trong hệ thống.