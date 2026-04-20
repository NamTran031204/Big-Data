# Big Data - Real-time Streaming Pipeline

## 🛠 Tech Stack
- **Language:** Python 3.12
- **Stream Processing:** PySpark 3.5.8 (Structured Streaming)
- **Message Broker:** Apache Kafka (Dockerized)
- **Data Generation:** Faker Library
- **Environment:** Docker, Java 17

## Tính năng đã hoàn thành (Tuần 1)
- [x] Thiết lập hạ tầng Kafka & Zookeeper bằng Docker Compose.
- [x] Phát triển script `producer.py` giả lập dữ liệu đơn hàng thời gian thực.
- [x] Phát triển script `spark_streaming.py` kết nối Kafka và xử lý Windowing.
- [x] Thực hiện gom nhóm dữ liệu theo **Tumbling Window 10 giây**.
- [x] Xử lý lỗi NativeIO và Hostname trên môi trường Windows.

## Kiến thức tìm hiểu
- Mô hình **Unbounded Table** trong Structured Streaming.
- Cơ chế **Event-time processing** và **Watermarking**.
- Quản lý trạng thái và tính chịu lỗi với **Checkpointing**.