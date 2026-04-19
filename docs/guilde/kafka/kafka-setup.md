# Kafka setup đề xuất cho dự án Big Data (mức lý thuyết)

## 1) Làm rõ yêu cầu dự án & tech stack từ `big-data.md`

### Mục tiêu hệ thống
- Xây dựng pipeline Big Data end-to-end theo **Lambda Architecture**.
- Luồng chính: **Data sources → Kafka → Spark (Streaming + Batch) → MongoDB/MinIO → Dashboard**.
- Use case trọng tâm: phân tích bán hàng e-commerce theo thời gian thực, dashboard revenue, cảnh báo bất thường, enrichment dữ liệu.

### Tech stack dự kiến
- **Message broker:** Apache Kafka (CDC + event streaming).
- **Streaming/Batch processing:** Apache Spark (Structured Streaming + batch jobs).
- **Ingestion CDC:** Debezium (PostgreSQL CDC) hoặc producer Java thay thế.
- **Storage:** MinIO (S3-compatible, Bronze/Silver/Gold) + MongoDB (serving layer).
- **Orchestration/Deploy/Obs:** Airflow, Kubernetes (Minikube), Grafana/Prometheus.
- **Java integration:** Java producer/consumer, enrichment service, offset/consumer group management, metrics.

---

## 2) Đọc cấu hình hiện tại trong `init/docker-compose.yml`

### Những gì bạn đang có
- 1 broker Kafka (`confluentinc/cp-kafka:7.5.0`) + Zookeeper.
- Nhiều listener:
  - `kafka:29092` (nội bộ),
  - `localhost:9092` (host),
  - `kafka:9094` (docker network cho Kafka UI).
- `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`.
- `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1`.
- Kafka UI kết nối `kafka:9094`.
- Có MongoDB và MinIO chạy song song, phù hợp mô hình pipeline.

### Nhận xét nhanh
- Cấu hình hiện tại **phù hợp học tập/dev local**.
- Chưa phù hợp production do:
  - single broker (không HA),
  - replication factor = 1,
  - PLAINTEXT (chưa có bảo mật),
  - auto-create topic có thể gây rủi ro vận hành.

---

## 3) Đề xuất cấu hình Kafka cho dự án (lý thuyết) + mục đích

## A. Kiến trúc cluster

### A1. Môi trường dev/học tập
- Có thể giữ **1 broker** để giảm tài nguyên.
- Giữ `replication.factor=1`, `min.insync.replicas=1`.
- Mục đích: đơn giản hoá setup, dễ debug, phù hợp máy cá nhân.

### A2. Môi trường staging/production
- Tối thiểu **3 brokers**.
- `replication.factor=3`, `min.insync.replicas=2`.
- `unclean.leader.election.enable=false`.
- Mục đích: chịu lỗi 1 broker, tránh mất dữ liệu khi failover.

> Khuyến nghị roadmap: có thể chuyển từ ZooKeeper sang **KRaft mode** khi ổn định để đơn giản hoá vận hành dài hạn.

---

## B. Topic design theo use case

### Topic đề xuất
- `orders_raw`: event CDC/order thô.
- `orders_enriched`: dữ liệu sau enrichment.
- `revenue_metrics`: kết quả aggregate gần real-time.
- `fraud_alerts`: cảnh báo ưu tiên cao.

### Partitioning strategy
- `orders_raw`: partition theo `order_id` hoặc `customer_id` (giữ thứ tự theo key).
- `orders_enriched`: cùng key như upstream để dễ correlate.
- `revenue_metrics`: partition theo `category` hoặc `region`.
- `fraud_alerts`: partition vừa phải, ưu tiên latency.

### Số partition (định hướng)
- Bắt đầu 6–12 partitions cho topic throughput cao (`orders_raw`), sau đó scale theo consumer lag.
- Mục đích: tăng song song xử lý cho Spark/Java consumers và cân bằng tải consumer group.

---

## C. Retention, cleanup, và dữ liệu lâu dài

### Đề xuất
- `orders_raw`: retention ngắn-trung bình (ví dụ 3–7 ngày) nếu đã đổ xuống MinIO Bronze đầy đủ.
- `orders_enriched`: retention trung bình (7–14 ngày) để hỗ trợ replay ngắn hạn.
- `revenue_metrics`: retention ngắn hơn nếu đã có MongoDB/MinIO lưu vết.
- `cleanup.policy=delete` cho luồng event append-only; cân nhắc `compact` cho topic dạng trạng thái (key latest-value).

### Mục đích
- Kafka là **buffer/log vận hành**, không thay thế data lake.
- Giảm chi phí lưu trữ broker, vẫn đảm bảo khả năng replay trong cửa sổ cần thiết.

---

## D. Producer semantics (Debezium/Java producer)

### Đề xuất
- Bật idempotent producer.
- `acks=all`.
- Giới hạn retry hợp lý + backoff.
- Với luồng cần exactly-once end-to-end: dùng transactional producer (khi phù hợp nghiệp vụ).

### Mục đích
- Tránh duplicate do retry.
- Tăng độ bền dữ liệu khi broker lỗi tạm thời.
- Nâng mức đảm bảo giao nhận cho pipeline tài chính/doanh thu.

---

## E. Consumer strategy (Spark + Java)

### Đề xuất
- Dùng **consumer groups** tách theo chức năng:
  - group cho Spark streaming,
  - group cho Java enrichment,
  - group cho service cảnh báo.
- Kiểm soát offset rõ ràng:
  - checkpoint (Spark),
  - commit theo batch/transaction boundary (Java service).
- `max.poll.records`, fetch size, concurrency được tuning theo latency mục tiêu.

### Mục đích
- Scale ngang dễ dàng.
- Hạn chế reprocessing không cần thiết.
- Giữ ổn định throughput khi tăng dữ liệu.

---

## F. Exactly-once và tính nhất quán

### Đề xuất
- Kafka layer: idempotence + transactional write (nếu cần).
- Spark layer: checkpoint bền vững trên MinIO, watermark cho late events.
- Sink layer (MongoDB): idempotent upsert theo khóa nghiệp vụ (`order_id`, `window_start+category`, ...).

### Mục đích
- Giảm duplicate ở nhiều tầng, không chỉ Kafka.
- Đảm bảo số liệu dashboard ít “nhảy sai” khi job restart/failover.

---

## G. Schema & contract dữ liệu

### Đề xuất
- Chuẩn hóa schema message (Avro/JSON Schema/Protobuf).
- Versioning schema theo backward compatibility.
- Quản lý contract tập trung (Schema Registry nếu có điều kiện).

### Mục đích
- Tránh lỗi vỡ schema khi nhiều team cùng publish/consume.
- Dễ mở rộng service Java/Spark về sau.

---

## H. Bảo mật & governance

### Đề xuất
- Dev local có thể dùng PLAINTEXT.
- Staging/prod: bật TLS + SASL, ACL theo principle of least privilege.
- Tách quyền produce/consume theo topic và service account.

### Mục đích
- Giảm rủi ro truy cập trái phép.
- Đáp ứng yêu cầu audit và vận hành chuẩn.

---

## I. Monitoring & vận hành

### Metrics cần theo dõi
- Consumer lag (quan trọng nhất).
- Throughput (messages/sec, bytes/sec).
- Produce/consume error rate.
- Broker health: disk usage, under-replicated partitions, request latency.

### Mục đích
- Phát hiện nghẽn pipeline sớm.
- Quyết định scale partitions/consumers dựa trên dữ liệu thực.

---

## J. Ánh xạ trực tiếp cho dự án của bạn

- Với scope môn học: giữ local Docker 1 broker để phát triển nhanh.
- Khi demo “gần production”: mô phỏng 3 broker (dù mini), tắt auto-create topic, quản lý topic chủ động.
- Kafka nên đóng vai trò:
  - **ingest bus** cho CDC từ Postgres/Debezium,
  - **stream backbone** cho Spark + Java enrichment,
  - **event handoff** trước khi dữ liệu xuống MinIO/MongoDB.

=> Cách này bám sát mục tiêu dự án: vừa đạt yêu cầu học thuật (streaming, exactly-once, watermarking, integration), vừa có nền tảng mở rộng thực tế.
