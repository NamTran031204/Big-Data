
# 1. Kế hoạch triển khai và feature bắt buộc cho Spark Structured Streaming

## 1.1. Mục tiêu

Xây một luồng realtime đọc **CDC từ Kafka**, xử lý theo thời gian thực hoặc theo cửa sổ **5–10 phút gần nhất**, rồi ghi kết quả ra **MinIO** và **MongoDB**. Luồng realtime **không đọc trực tiếp MinIO**; MinIO chỉ đóng vai trò output/archive/curated sink cho downstream và batch. Spark Structured Streaming có Kafka source riêng để đọc stream từ topic, còn file source phù hợp hơn với mô hình “file mới xuất hiện trong thư mục” thay vì CDC realtime. ([Apache Spark][1])

## 1.2. Phạm vi đầu vào và đầu ra

**Đầu vào chính** là các Kafka topic do Debezium PostgreSQL connector phát ra. Stream app subscribe đúng topic hoặc `subscribePattern` theo naming convention đã thống nhất. Nếu cần bootstrap một query mới từ “bây giờ trở đi”, dùng `startingOffsets=latest`; nếu cần dựng một query mới cho backfill hoặc bootstrap “5–10 phút gần nhất”, dùng `startingTimestamp` hoặc `startingOffsetsByTimestamp`. Các tùy chọn này chỉ áp dụng khi **khởi tạo query mới**; khi restart, Spark sẽ resume từ checkpoint thay vì dùng lại các offset khởi tạo. ([Apache Spark][1])

**Đầu ra chính** gồm:

* **MinIO**: lưu normalized/raw-curated output để đối soát, backfill và phục vụ batch.
* **MongoDB**: lưu serving data cho dashboard/Grafana.

Khi một query cần ghi ra nhiều sink, Structured Streaming nên dùng `foreachBatch`, vì Spark cho phép trong mỗi micro-batch tái sử dụng batch writer, ghi nhiều location, và có thể `persist()` để tránh recompute. ([Apache Spark][2])

## 1.3. Luồng xử lý chuẩn

### Bước 1: đọc Kafka như nguồn realtime duy nhất

Spark Structured Streaming đọc từ Kafka bằng Kafka source. Đây là “source of truth” cho realtime path. MinIO không tham gia vào khâu quyết định “dữ liệu nào là mới nhất” của realtime stream. ([Apache Spark][1])

### Bước 2: parse Debezium envelope

Mỗi event phải được parse đầy đủ các trường tối thiểu:

* primary key
* `before`
* `after`
* `op`
* `source.ts_ms`
* `lsn`

Debezium PostgreSQL connector phát ra data change events cho create, update, delete, và truncate; trong đó `payload.source.ts_ms` là thời điểm thay đổi xảy ra trong database, còn `payload.ts_ms` cho phép đo độ trễ từ DB tới Debezium. ([Debezium][3])

### Bước 3: xử lý theo event time, không theo processing time nghiệp vụ

Mọi logic 5–10 phút gần nhất phải dựa trên **event time** lấy từ `source.ts_ms`, không chỉ dựa trên lúc Spark nhận message. Điều này giúp dashboard phản ánh đúng thời điểm dữ liệu thay đổi trong DB, thay vì thời điểm pipeline bắt được event. ([Debezium][3])

### Bước 4: watermark + dedupe chặt chẽ

Bắt buộc dùng:

* `withWatermark(...)`
* `dropDuplicatesWithinWatermark(...)`

Khóa dedupe mặc định phải là **Primary Key + LSN**. Đây là quy ước chốt cứng cho CDC path, không dùng “business key đủ tốt” theo kiểu mơ hồ. Watermark phải đủ rộng để nuốt late events hợp lệ, nhưng đủ chặt để state store không phình quá mức. Spark hỗ trợ trực tiếp `dropDuplicatesWithinWatermark(...)` cho luồng streaming có watermark. ([Apache Spark][2])

### Bước 5: ghi MinIO và MongoDB bằng `foreachBatch`

Trong mỗi micro-batch:

1. persist dataset,
2. ghi MinIO,
3. ghi MongoDB,
4. unpersist dataset.

`foreachBatch` mặc định chỉ mang ngữ nghĩa **at-least-once**, nên sink layer phải có chiến lược dedupe bằng **`batchId`** hoặc khóa idempotent tương đương để tránh ghi trùng sau retry/restart. ([Apache Spark][2])

## 1.4. Feature bắt buộc

### 1) Kafka là source realtime duy nhất

Realtime path chỉ đọc Kafka CDC. Không dùng MinIO như nguồn streaming để “tìm file mới nhất”. ([Apache Spark][1])

### 2) Checkpoint cố định trên storage bền vững

Mỗi query phải có `checkpointLocation` cố định, nằm trên storage bền vững. Không đặt checkpoint ở local disk tạm của pod/container. Khi query restart, Spark sẽ tiếp tục từ checkpoint thay vì đọc lại từ đầu. ([Apache Spark][2])

### 3) Offset bootstrap đúng semantics

* Query mới muốn chỉ lấy dữ liệu mới: `startingOffsets=latest`
* Query mới muốn bootstrap/backfill theo mốc thời gian: `startingTimestamp` hoặc `startingOffsetsByTimestamp`
* Query đã có checkpoint: luôn resume từ checkpoint

Đây là nguyên tắc bắt buộc để tránh hiểu sai “5–10 phút gần nhất”. ([Apache Spark][1])

### 4) Xử lý CDC dựa trên event time + metadata

Mọi transform nghiệp vụ phải nhìn vào `op`, `before/after`, `source.ts_ms`, `lsn`. Delete và truncate phải được xử lý có chủ đích, không bỏ qua âm thầm. ([Debezium][3])

### 5) Nhiều sink phải dùng `foreachBatch`

Nếu stream cần ghi đồng thời ra MinIO và MongoDB, phải dùng `foreachBatch`, kết hợp `persist()` và dedupe theo `batchId` ở sink nếu cần gần exactly-once hơn. ([Apache Spark][2])

### 6) Watermark + dedupe theo **Primary Key + LSN**

Đây là feature bắt buộc riêng, không gộp chung kiểu “đã có dedupe là đủ”. Mục tiêu là vừa lọc bản ghi trùng, vừa giới hạn kích thước state store theo watermark. ([Apache Spark][2])

### 7) Rate control bằng `maxOffsetsPerTrigger`

Phải cấu hình `maxOffsetsPerTrigger` để mỗi micro-batch chỉ đọc một lượng offset vừa sức với cluster. Đây là “van an toàn” chống backlog và chống executor bị quá tải khi có đợt cập nhật lớn từ Postgres. ([Apache Spark][1])

### 8) `failOnDataLoss=true`

Giữ mặc định fail-fast khi Kafka không còn giữ được offset cần đọc hoặc retention làm mất dữ liệu đầu vào. Với CDC, dừng lại để báo động tốt hơn nhiều so với âm thầm chạy tiếp và làm sai dashboard. ([Apache Spark][1])

### 9) Không dùng chung `kafka.group.id`

Không tự ý cấu hình chung một `kafka.group.id` cho nhiều query streaming độc lập. Spark mặc định tạo group riêng cho từng query; nếu dùng chung group, các query có thể can thiệp nhau và mỗi query chỉ đọc một phần dữ liệu. ([Apache Spark][1])

### 10) Trigger theo micro-batch ổn định

Ưu tiên ProcessingTime trigger ở mức 30 giây hoặc 1 phút cho realtime dashboard. Không cần continuous mode trong giai đoạn đầu. Đây là lựa chọn thực dụng cho CDC dashboard vì dễ vận hành và đủ nhanh. ([Apache Spark][2])

### 11) Quan sát lag và trạng thái query

Phải theo dõi tối thiểu:

* input rows / processed rows
* batch duration
* watermark
* state size
* chênh lệch `payload.ts_ms - payload.source.ts_ms`
* Kafka lag

Đây là điều kiện để biết stream còn “đuổi kịp” nguồn CDC hay không. Việc dùng `source.ts_ms` để đo lag đã được Debezium mô tả rõ. ([Debezium][3])

## 1.5. Kế hoạch triển khai theo giai đoạn

### Giai đoạn A — realtime tối thiểu

* đọc 1 topic CDC quan trọng nhất,
* parse Debezium envelope,
* checkpoint cố định,
* trigger 30–60 giây,
* ghi MongoDB trước,
* bật `maxOffsetsPerTrigger`, giữ `failOnDataLoss=true`. ([Apache Spark][1])

### Giai đoạn B — hoàn thiện analytics 5–10 phút

* thêm event-time window,
* thêm watermark,
* thêm dedupe theo Primary Key + LSN,
* ghi thêm curated output ra MinIO bằng `foreachBatch`. ([Apache Spark][2])

### Giai đoạn C — hardening

* thêm batchId-based dedupe ở sink,
* thêm lag monitoring,
* thêm quy trình bootstrap/backfill bằng query mới dùng timestamp-based offset khởi tạo. ([Apache Spark][1])

---