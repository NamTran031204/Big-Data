**1. Lấy dữ liệu từ Kafka thay vì MinIO**
Luồng realtime nên lấy dữ liệu từ Kafka, không nên lấy trực tiếp từ MinIO. Trong Spark, Kafka source là nguồn stream chuẩn cho Structured Streaming; còn file source là mô hình “file mới xuất hiện trong thư mục”, phù hợp hơn với ingest theo file chứ không phải CDC realtime.

**2. Checkpoint cố định và bền vững**
Structured Streaming phải có checkpointLocation cố định trên storage bền vững. Spark dùng checkpointing và write-ahead logs để lưu tiến độ, offset đã xử lý và state; khi restart, query sẽ tiếp tục từ checkpoint thay vì quay lại đọc từ đầu. Không nên đặt checkpoint tạm thời trong local disk.

**3. Quản lý Starting Offsets**
Nếu muốn lấy “từ bây giờ trở đi”, dùng `startingOffsets=latest` cho query mới. Nếu muốn bootstrap hoặc backfill “5–10 phút gần nhất”, dùng `startingTimestamp` hoặc `startingOffsetsByTimestamp`; nhưng các option này chỉ có ý nghĩa khi query được tạo mới, còn các lần resume sẽ tiếp tục từ checkpoint.

**4. Logic Event-time và CDC Metadata**
Với CDC từ Debezium, logic xử lý realtime nên dựa trên event time và metadata của event như `op`, `before/after`, `source.ts_ms`, `lsn`, thay vì chỉ nhìn thời điểm Spark nhận message. Debezium PostgreSQL connector phát ra data change events cho create, update, delete, truncate và có metadata transaction/source để downstream xử lý chính xác.

**5. Dùng foreachBatch cho nhiều sink**
Nếu stream phải ghi ra nhiều sink như MinIO và MongoDB, Structured Streaming nên dùng `foreachBatch`. Spark cho phép tái sử dụng writer batch, ghi ra nhiều đích trong cùng micro-batch, và khuyến nghị `persist()` để tránh recompute; mặc định `foreachBatch` chỉ cho at-least-once, nên cần dùng `batchId` để dedupe ở sink nếu muốn gần exactly-once hơn.

**6. Vai trò của Airflow**
Airflow nên đóng vai trò điều phối và vận hành, không phải data plane realtime. Airflow mạnh ở DAG, task, dependencies, schedule, callbacks và asset-aware scheduling; còn stream Kafka → Spark nên chạy dài hạn như một ứng dụng riêng.

**7. Watermarking và Khử trùng lặp (Deduplication) chặt chẽ**
Vì Kafka mặc định cung cấp ngữ nghĩa "ít nhất một lần" (at-least-once), sự cố mạng có thể khiến message bị gửi trùng. Bạn phải kết hợp `withWatermark(...)` (để Spark biết khi nào nên dọn dẹp state cũ) và `dropDuplicatesWithinWatermark(...)` dựa trên Primary Key + LSN (Log Sequence Number) của bản ghi. Điều này hạn chế bộ nhớ bị phình to (OOM) khi phải lưu giữ ma trận trạng thái (State Store) quá lâu, đồng thời lọc sạch bản ghi trùng lặp ở ngay tầng xử lý.

**8. Kiểm soát lưu lượng bằng maxOffsetsPerTrigger (Rate Control)**
Thiết lập các thông số như `maxOffsetsPerTrigger` trong tùy chọn của Kafka Source. Hệ thống CDC có thể đón nhận các đợt cập nhật dữ liệu ồ ạt. Tùy chọn này hoạt động như một "van an toàn" (backpressure), đảm bảo mỗi micro-batch chỉ tiêu thụ một lượng dữ liệu vừa sức với RAM của cụm Spark, ngăn chặn sập Executor.

**9. Chấp nhận "Fail-fast" với failOnDataLoss=true**
Luôn giữ mặc định cấu hình `failOnDataLoss=true` khi đọc Kafka CDC. Dữ liệu CDC đòi hỏi tính chính xác tuyệt đối và có thứ tự. Nếu một topic Kafka bị mất dữ liệu (do cấu hình retention ngắn hoặc offset bị out-of-range), hệ thống thà dừng lại ngay lập tức để cảnh báo kỹ sư, còn hơn là âm thầm chạy tiếp và ghi dữ liệu sai lệch vĩnh viễn vào MongoDB.

**10. Cô lập hoàn toàn kafka.group.id cho các truy vấn độc lập**
Không bao giờ tự ý thiết lập chung một `kafka.group.id` cho nhiều query Streaming khác nhau. Trong Kafka, mỗi phân vùng (partition) chỉ được xử lý bởi tối đa một consumer trong cùng một nhóm tiêu thụ tại một thời điểm. Nếu nhiều query dùng chung group ID, Kafka sẽ tự động cân bằng tải và chia chác phân vùng cho chúng, dẫn đến mỗi query chỉ đọc được một nửa hoặc một phần dữ liệu, gây sai lệch nghiêm trọng.

**11. Chiến lược gom tệp nhỏ (Compaction) trên MinIO bằng Airflow**
Việc sử dụng Spark Streaming ghi liên tục các micro-batch ra MinIO sẽ nhanh chóng sinh ra hàng chục ngàn tệp Parquet/JSON siêu nhỏ. Hãy bổ sung một tác vụ định kỳ ban đêm trên Airflow để gom (compact) các tệp nhỏ này thành các tệp lớn. Các hệ thống Object Storage (như MinIO hay S3) xử lý rất kém số lượng lớn các tệp nhỏ vì gây phình to metadata và làm chậm các truy vấn Batch.