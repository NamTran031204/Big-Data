
# 2. Kế hoạch triển khai cho Kafka – Debezium – Airflow

## 2.1. Mục tiêu

Xây tầng ingest và orchestration sao cho:

1. **Debezium** lấy CDC từ PostgreSQL,
2. **Kafka** là event backbone cho realtime path,
3. **Airflow** làm control plane cho vận hành, backfill, health-check, rollup và compaction, chứ không thay Spark Streaming làm data plane realtime. Airflow là nền tảng để author, schedule, monitor workflows; có thể trigger DAG thủ công, backfill lịch sử và kết hợp asset-aware scheduling với time-based schedules. ([Apache Airflow][4])

## 2.2. Vai trò của từng thành phần

### Debezium

Debezium PostgreSQL connector theo dõi thay đổi từ database, phát ra change events với metadata đủ để downstream xử lý chính xác. Nó hỗ trợ snapshot ban đầu và tiếp tục streaming các thay đổi sau snapshot. ([Debezium][3])

### Kafka

Kafka là lớp buffer và phân phối sự kiện giữa Debezium và Spark. Mỗi record trong một partition có offset riêng; trong một consumer group, mỗi partition chỉ được giao cho đúng một consumer tại một thời điểm. Điều này quyết định trực tiếp mức song song hữu ích của downstream. ([Kafka][5])

### Airflow

Airflow không xử lý từng sự kiện realtime. Thay vào đó, nó chịu trách nhiệm:

* deploy/restart stream app,
* backfill có kiểm soát,
* kiểm tra health của Debezium/Kafka/stream,
* chạy rollup định kỳ,
* chạy compaction file nhỏ trên MinIO,
* làm lịch vận hành định kỳ và event-driven ở mức workflow. ([Apache Airflow][4])

## 2.3. Kế hoạch triển khai Kafka – Debezium

### Bước 1: chốt contract CDC

Phải thống nhất ở cấp hệ thống:

* topic nào chứa dữ liệu của bảng nào,
* event key là gì,
* `op` có ý nghĩa gì,
* delete/truncate xử lý ra sao,
* `source.ts_ms` và `lsn` được downstream dùng như thế nào.

Đây là lớp contract bắt buộc để Spark streaming không phải “đoán” semantics của event. Debezium PostgreSQL connector cung cấp change event với metadata transaction/source đủ cho downstream xử lý. ([Debezium][3])

### Bước 2: chốt snapshot strategy

Phải quyết định ngay từ đầu:

* có chạy initial snapshot không,
* snapshot toàn bảng hay chọn lọc,
* khi nào dùng ad hoc snapshot để bootstrap hoặc sửa dữ liệu lịch sử.

Mục tiêu là tránh để downstream phải tự backfill bằng cách quét MinIO hoặc DB một cách thiếu kiểm soát. ([Debezium][3])

### Bước 3: cấu hình Kafka theo hướng an toàn

Nếu có thể chạy nhiều broker, ưu tiên cấu hình theo hướng bền vững:

* producer `acks=all`
* topic `min.insync.replicas` phù hợp
* replication factor đủ lớn trong phạm vi tài nguyên

Kafka docs mô tả `acks=all` là mức durability mạnh nhất ở producer side, và nếu muốn ép một số lượng replica tối thiểu phải ack thì cần `min.insync.replicas`. ([Kafka][6])

### Bước 4: chọn số partition thực dụng

Số partition phải đủ để downstream scale song song, nhưng không nên nhiều vô ích. Vì trong một consumer group, mỗi partition chỉ thuộc về một consumer tại một thời điểm, số partition là trần song song hữu ích cho mỗi topic. Với đồ án hoặc hệ thống nhỏ, bắt đầu vừa phải rồi tăng khi có lag là hợp lý hơn đẩy partition lên quá cao ngay từ đầu. ([Kafka][5])

### Bước 5: retention phục vụ recovery

Retention của topic CDC phải dài hơn thời gian downtime tối đa bạn chấp nhận cộng thêm cửa sổ backfill mong muốn. Nếu retention quá ngắn, Spark có thể gặp data loss và fail-fast theo đúng cấu hình `failOnDataLoss=true`. ([Apache Spark][1])

## 2.4. Feature bắt buộc cho Kafka – Debezium

### 1) Kafka là backbone cho realtime path

Kafka là tầng ingest duy nhất cho realtime processing. MinIO không thay thế Kafka trong CDC realtime. ([Apache Spark][1])

### 2) Topic contract rõ ràng

Mỗi topic phải có contract CDC rõ ràng về key, `op`, `before/after`, `source.ts_ms`, `lsn`, delete/truncate. ([Debezium][3])

### 3) Snapshot strategy rõ ràng

Phải có chiến lược bootstrap/backfill ở tầng Debezium thay vì để downstream tự xử lý mơ hồ. ([Debezium][3])

### 4) Durability ở Kafka

Cấu hình producer/topic nên đi theo hướng bền vững nhất có thể trong phạm vi hạ tầng: `acks=all`, `min.insync.replicas`, replication factor phù hợp. ([Kafka][6])

### 5) Số partition phù hợp với mức song song

Topic phải có đủ partition để Spark streaming scale executors khi cần, vì partition là đơn vị phân chia công việc ở tầng consumer group. ([Kafka][5])

## 2.5. Kế hoạch triển khai Airflow

### Vai trò cốt lõi

Airflow là **control plane** của toàn pipeline data:

* quản lý DAG,
* schedule theo thời gian,
* trigger/backfill,
* health-check,
* callbacks,
* asset-aware scheduling khi cần.

Nó không thay thế stream app chạy dài hạn. ([Apache Airflow][4])

### Các DAG bắt buộc

#### DAG 1 — deploy/restart streaming app

DAG này chịu trách nhiệm start/restart Spark Structured Streaming với đúng topic, đúng checkpoint, đúng tham số thời gian khi cần bootstrap hoặc recovery. Airflow phù hợp cho kiểu workflow vận hành này vì hỗ trợ scheduling, trigger thủ công, monitor task status và backfill workflow runs. ([Apache Airflow][4])

#### DAG 2 — backfill có kiểm soát

DAG này tạo một job/query riêng để backfill theo timestamp hoặc khoảng thời gian cụ thể. Nó không được dùng chung checkpoint của production stream. Mục tiêu là giữ nguyên semantics của stream chính trong khi vẫn có lối xử lý dữ liệu lịch sử. ([Apache Spark][1])

#### DAG 3 — health-check hệ thống

DAG định kỳ kiểm tra:

* Debezium connector có còn phát event không,
* Kafka lag có tăng bất thường không,
* stream query có còn tiến lên không,
* sink MongoDB/MinIO có còn nhận dữ liệu không.

Đây là cách dùng đúng khả năng schedule + monitor workflows của Airflow cho data platform. ([Apache Airflow][4])

#### DAG 4 — rollup định kỳ

Nếu dashboard cần bảng tổng hợp theo 5 phút, 10 phút, giờ hoặc ngày, Airflow có thể chạy các batch rollup riêng dựa trên dữ liệu đã được stream ra MinIO/MongoDB, thay vì nhồi mọi aggregate stateful vào một query realtime duy nhất. Airflow hỗ trợ cả time-based scheduling và asset-aware scheduling để tổ chức các workflow kiểu này. ([Apache Airflow][7])

#### DAG 5 — compaction file nhỏ trên MinIO

Đây là phần đã được bổ sung để đủ 11/11. Khuyến nghị vận hành là phải có một DAG chạy định kỳ, thường vào ban đêm hoặc giờ ít tải, để:

* đọc các partition/output do stream đã ghi ra MinIO,
* gom nhiều file nhỏ thành ít file lớn hơn,
* ghi ra vùng compacted/curated theo chiến lược an toàn,
* dọn dữ liệu tạm nếu cần.

Đây là nhiệm vụ rất phù hợp với Airflow vì bản chất là một workflow định kỳ. Khuyến nghị này xuất phát từ thực tế stream ghi lặp lại theo micro-batch và việc Airflow mạnh ở scheduling/orchestration. ([Apache Airflow][4])

## 2.6. Kế hoạch triển khai theo giai đoạn

### Giai đoạn A — ingest ổn định

* Debezium lấy CDC từ Postgres,
* Kafka nhận event,
* chốt topic contract,
* chốt snapshot strategy,
* chốt retention cơ bản. ([Debezium][3])

### Giai đoạn B — orchestration tối thiểu

* dựng DAG deploy/restart,
* dựng DAG health-check,
* dựng DAG backfill riêng. ([Apache Airflow][4])

### Giai đoạn C — vận hành data lake

* thêm DAG rollup,
* thêm DAG compaction file nhỏ trên MinIO,
* chuẩn hóa lịch chạy và callback cảnh báo. ([Apache Airflow][7])

---
