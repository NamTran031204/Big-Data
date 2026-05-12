
# 2. Kế hoạch triển khai cho Kafka – Event Publisher – Airflow

## 2.1. Mục tiêu

Xây tầng ingest và orchestration sao cho:

1. **Event Publisher Service** phát sinh và publish các event hành vi người dùng lên Kafka,
2. **Kafka** là event backbone cho realtime path,
3. **Airflow** làm control plane cho vận hành, backfill, health-check, rollup và compaction, chứ không thay Spark Streaming làm data plane realtime.

Trong mô hình này, PostgreSQL không còn là nguồn CDC cho streaming nữa. Thay vào đó, PostgreSQL chỉ đóng vai trò **reference data store** để Event Publisher Service lấy danh sách khách hàng, sản phẩm, seller, category và các thuộc tính hợp lệ làm đầu vào sinh event.

## 2.2. Vai trò của từng thành phần

### Event Publisher Service

Event Publisher Service là nguồn phát sự kiện đầu vào cho realtime pipeline.

Nhiệm vụ của service này là:

* đọc dữ liệu tham chiếu từ PostgreSQL,
* chọn ra các `customer`, `product`, `seller`, `category` hợp lệ,
* sinh ra các hành vi giả lập như `search`, `view_product`, `like_product`, `product_dwell_time`,
* publish các event đó lên Kafka.

Service này **không phải là nơi xử lý analytics**, cũng không phải nơi lưu kết quả cuối cùng. Nó chỉ đóng vai trò producer cho event stream.

### Kafka

Kafka là lớp buffer và phân phối sự kiện giữa Event Publisher Service và Spark Structured Streaming.

Mỗi event hành vi được publish thành một message. Kafka giữ thứ tự trong từng partition, cung cấp offset để downstream resume, và là backbone để Spark Streaming tiêu thụ dữ liệu realtime một cách ổn định.

### Airflow

Airflow không xử lý từng event realtime. Thay vào đó, nó chịu trách nhiệm:

* deploy hoặc restart stream app,
* chạy backfill có kiểm soát,
* kiểm tra sức khỏe của Event Publisher Service, Kafka và Spark Streaming,
* chạy rollup định kỳ,
* chạy compaction file nhỏ trên MinIO,
* điều phối các workflow vận hành định kỳ.

Airflow vẫn là **control plane**, còn Spark Streaming vẫn là **data plane**.

## 2.3. Kế hoạch triển khai Kafka – Event Publisher

### Bước 1: chốt event contract

Phải thống nhất ở cấp hệ thống:

* topic nào chứa loại hành vi nào,
* event key là gì,
* event schema gồm những trường nào,
* event time lấy từ đâu,
* khóa nào dùng để dedupe downstream,
* metadata nào downstream bắt buộc phải có.

Khác với bản cũ dùng CDC contract, ở đây contract phải chuyển sang **behavior event contract**.

Ví dụ mỗi event nên có tối thiểu:

* `event_id`
* `event_type`
* `event_time`
* `user_id`
* `session_id`
* `product_id` nếu có
* `seller_id` nếu có
* `category` nếu có
* `search_term` nếu có
* `dwell_time_ms` nếu có
* `event_version`

Mục tiêu là để Spark Streaming không phải “đoán” semantics của dữ liệu đầu vào.

### Bước 2: chốt chiến lược reference data

Vì không còn Debezium snapshot/CDC, thay vào đó phải quyết định rõ:

* Event Publisher Service lấy reference data từ PostgreSQL theo cách nào,
* có cache in-memory hay snapshot reference nội bộ hay không,
* tần suất refresh reference data là bao lâu,
* khi reference data thay đổi thì service cập nhật như thế nào.

Mục tiêu là đảm bảo mọi event fake đều tham chiếu tới dữ liệu có thật trong hệ thống, nhưng không làm service phải query database liên tục với chi phí cao.

### Bước 3: chốt chiến lược topic

Cần quyết định topic organization theo một trong hai hướng:

**Hướng A: một topic chung cho mọi hành vi**

* ví dụ `user_behavior_events`

**Hướng B: tách topic theo loại hành vi**

* `search_events`
* `product_view_events`
* `product_like_events`
* `product_engagement_events`

Nếu dự án còn nhỏ, một topic chung với `event_type` rõ ràng là đủ. Nếu muốn rõ pipeline và dễ scale về sau, nên tách topic theo nhóm hành vi.

### Bước 4: cấu hình Kafka theo hướng an toàn

Nếu có thể chạy nhiều broker, ưu tiên:

* producer `acks=all`
* bật idempotence ở producer
* topic `min.insync.replicas` phù hợp
* replication factor đủ lớn trong phạm vi tài nguyên

Nếu hệ thống chỉ có 1 broker vì giới hạn đồ án, chấp nhận không có HA thật, nhưng vẫn nên giữ contract event rõ ràng và retention đủ dài để replay khi cần.

### Bước 5: chọn số partition thực dụng

Số partition phải đủ để downstream scale song song, nhưng không nên nhiều vô ích.

Với hệ thống nhỏ, có thể bắt đầu:

* 2–4 partition cho topic hành vi chính
* tăng thêm khi Spark lag hoặc cần song song nhiều hơn

Vì trong một consumer group, mỗi partition chỉ được một consumer xử lý tại một thời điểm, số partition chính là trần song song hữu ích cho Spark Streaming.

### Bước 6: retention phục vụ recovery và replay

Retention của topic hành vi phải dài hơn:

* thời gian downtime tối đa bạn chấp nhận,
* cộng thêm cửa sổ backfill/replay mong muốn.

Vì luồng này là event publishing, retention Kafka bây giờ không còn để bảo vệ CDC path nữa, mà để:

* replay event giả lập khi Spark bị dừng,
* dựng lại dữ liệu serving,
* phục vụ backfill controlled job.

## 2.4. Feature bắt buộc cho Kafka – Event Publisher

### 1) Kafka là backbone cho realtime path

Kafka là tầng ingest duy nhất cho realtime processing. MinIO không thay thế Kafka trong realtime path.

### 2) Event contract rõ ràng

Mỗi topic phải có contract rõ ràng về:

* `event_type`
* `event_time`
* `event_id`
* `user_id`
* `session_id`
* `product_id`
* các field đặc thù như `search_term`, `dwell_time_ms`, `like_action`

Đây là điều kiện bắt buộc để Spark Streaming parse và xử lý ổn định.

### 3) Reference data strategy rõ ràng

Phải có chiến lược rõ ràng về cách Event Publisher Service lấy và refresh reference data từ PostgreSQL. Không để service phát event dựa trên dữ liệu tự chế không khớp với hệ thống thật.

### 4) Durability ở Kafka

Kafka producer/topic nên đi theo hướng bền vững nhất có thể trong phạm vi hạ tầng:

* `acks=all`
* `min.insync.replicas` phù hợp
* replication factor phù hợp
* retention đủ dài

### 5) Số partition phù hợp với mức song song

Topic phải có đủ partition để Spark Streaming scale executors khi cần, vì partition là đơn vị phân chia công việc ở tầng consumer group.

### 6) Event idempotency và khóa dedupe

Event Publisher Service nên sinh:

* `event_id` duy nhất,
* hoặc ít nhất một composite key đủ ổn định như `user_id + session_id + event_time + product_id + event_type`

Mục tiêu là để downstream có thể dedupe dễ dàng nếu có retry hoặc duplicate publish.

### 7) Tách biệt event hành vi với dữ liệu giao dịch

Search, view, like, dwell time phải được xem là **behavior events**, không được “nhét” vào các bảng orders/payments/reviews hiện có rồi mới stream ra lại. Điều này giữ kiến trúc sạch và đúng bản chất dữ liệu.

## 2.5. Kế hoạch triển khai Airflow

## Vai trò cốt lõi

Airflow là **control plane** của toàn pipeline data:

* quản lý DAG,
* schedule theo thời gian,
* trigger/backfill,
* health-check,
* callbacks,
* asset-aware scheduling nếu cần.

Nó không thay thế stream app chạy dài hạn.

## Các DAG bắt buộc

### DAG 1 — deploy/restart streaming app

DAG này chịu trách nhiệm:

* start hoặc restart Spark Structured Streaming,
* truyền đúng topic,
* truyền đúng checkpoint,
* truyền đúng tham số vận hành khi cần recovery.

### DAG 2 — điều phối Event Publisher Service

DAG này dùng để:

* khởi động hoặc restart fake event publisher khi cần,
* kiểm tra publisher còn phát event đều hay không,
* thay đổi mode phát event nếu cần chạy test scenario riêng,
* giám sát producer lag hoặc producer failure.

Với mô hình mới, đây là DAG thay thế cho phần theo dõi Debezium connector trong bản cũ.

### DAG 3 — backfill có kiểm soát

DAG này tạo một job/query riêng để backfill theo timestamp hoặc khoảng thời gian cụ thể. Nó không được dùng chung checkpoint của production stream.

Nếu cần dựng lại dữ liệu 5–10 phút gần nhất hoặc replay một đoạn event cũ, DAG này sẽ dùng retention Kafka để thực hiện replay có kiểm soát.

### DAG 4 — health-check hệ thống

DAG định kỳ kiểm tra:

* Event Publisher Service có còn phát event không,
* Kafka lag có tăng bất thường không,
* stream query có còn tiến lên không,
* sink MongoDB/MinIO có còn nhận dữ liệu không.

### DAG 5 — rollup định kỳ

Nếu dashboard cần bảng tổng hợp theo 5 phút, 10 phút, giờ hoặc ngày, Airflow có thể chạy các batch rollup riêng dựa trên dữ liệu đã được stream ra MinIO/MongoDB, thay vì nhồi mọi aggregate stateful vào một query realtime duy nhất.

### DAG 6 — compaction file nhỏ trên MinIO

Phải có một DAG chạy định kỳ, thường vào ban đêm hoặc giờ ít tải, để:

* đọc các partition/output do stream đã ghi ra MinIO,
* gom nhiều file nhỏ thành ít file lớn hơn,
* ghi ra vùng compacted/curated theo chiến lược an toàn,
* dọn dữ liệu tạm nếu cần.

Đây là một feature vận hành bắt buộc nếu stream ghi micro-batch liên tục ra object storage.

## 2.6. Kế hoạch triển khai theo giai đoạn

### Giai đoạn A — ingest ổn định

* xây Event Publisher Service,
* chốt event contract,
* chốt chiến lược reference data,
* tạo Kafka topics,
* chốt retention cơ bản,
* publish thử các event hành vi chuẩn.

### Giai đoạn B — orchestration tối thiểu

* dựng DAG deploy/restart stream app,
* dựng DAG điều phối publisher,
* dựng DAG health-check,
* dựng DAG backfill riêng.

### Giai đoạn C — vận hành data lake

* thêm DAG rollup,
* thêm DAG compaction file nhỏ trên MinIO,
* chuẩn hóa lịch chạy,
* chuẩn hóa callback cảnh báo,
* chuẩn hóa quy trình replay event khi cần dựng lại dữ liệu.

## 2.7. Kết quả mong muốn

Sau khi sửa theo mô hình mới, tầng ingest và orchestration sẽ là:

* **PostgreSQL**: giữ reference/master data
* **Event Publisher Service**: đọc reference data và phát event hành vi
* **Kafka**: backbone cho realtime events
* **Spark Structured Streaming**: xử lý realtime
* **Airflow**: điều phối vận hành, backfill, rollup, compaction

Kiến trúc này phù hợp hơn với bài toán fake data hành vi người dùng, vì nó mô phỏng đúng cách dữ liệu thao tác đi từ lớp client/event producer vào streaming pipeline, thay vì đi đường vòng qua CDC database.

Nếu bạn muốn, mình có thể viết tiếp cho bạn **bản kế hoạch số 1 cũng đồng bộ với mô hình publish event này**, để hai bản kế hoạch khớp hoàn toàn với nhau.
