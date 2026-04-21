# Big Data - Real-time Streaming Pipeline

## Tech Stack
- **Language:** Python 3.12
- **Stream Processing:** PySpark 3.5.8 (Structured Streaming)
- **Message Broker:** Apache Kafka (Dockerized)
- **Data Generation:** Faker Library
- **Environment:** Docker, Java 17

##  Tiến độ
### Tuần 1: Streaming Study & Prep
- [x] Thiết lập hạ tầng Kafka & Zookeeper bằng Docker Compose.
- [x] Phát triển script \`producer.py\` giả lập dữ liệu đơn hàng thời gian thực.
- [x] Tìm hiểu mô hình **Unbounded Table** và **Windowing**.

### Tuần 2: Kafka Consumer Setup
- [x] Tạo script \`kafka_consumer.py\` thay thế bản test cũ, cấu hình Schema chuẩn.
- [x] Kiểm tra luồng dữ liệu (Pipeline basics): Producer -> Kafka -> Consumer.
- [ ] Cấu hình Checkpoint cục bộ để quản lý Offset (Đang chờ tích hợp MinIO).
- [ ] Hoàn thiện sơ đồ kiến trúc hệ thống (Streaming Architecture).

## Kiến thức tìm hiểu
- Mô hình **Unbounded Table** trong Structured Streaming.
- Cơ chế **Event-time processing** và **Watermarking**.
- Quản lý trạng thái và tính chịu lỗi với **Checkpointing**.
