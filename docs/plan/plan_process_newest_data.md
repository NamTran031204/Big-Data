# Incremental Batch theo CDC (watermark `__ts_ms`) — ĐÃ TRIỂN KHAI

## Context

Pipeline ban đầu đọc lại TOÀN BỘ bronze mỗi lần chạy (full `overwrite`): `transform_bronze_to_silver.py`
join 8 chiều ở grain order_item rồi ghi đè toàn bộ silver; Gold cũng đọc lại toàn bộ silver. Khi
Debezium bắt được dữ liệu mới, Spark không biết đâu là phần mới → xử lý lại tất cả, tốn tài nguyên.

Mục tiêu: chỉ xử lý **những đơn hàng thực sự thay đổi** theo CDC, đồng thời giữ kết quả đúng và
idempotent (chạy lại không sai, không trùng).

> **Lưu ý lịch sử:** bản nháp trước của doc này đề xuất `TimeBasedPartitioner` + Silver
> `partitionBy("purchase_date")` + dynamic overwrite. Cách đó **gây mất dữ liệu**: một lần chạy
> incremental chỉ chạm vài đơn của một `purchase_date` sẽ ghi đè và xoá hết phần còn lại của ngày
> đó (vì `purchase_date` của đơn ≠ ngày CDC, và nhiều đơn cùng một `purchase_date` được xử lý ở
> các lần chạy khác nhau). Bản triển khai dưới đây dùng **merge theo `order_id`** để tránh lỗi này
> và **không cần đổi S3 sink connector**.

---

## Approach đã chọn — watermark `__ts_ms` + merge theo `order_id`

Debezium gắn `__ts_ms` (thời điểm commit CDC) vào mỗi bản ghi bronze qua
`transforms.unwrap.add.fields=op,ts_ms`. Dùng nó làm **high-water mark**.

- **Watermark** = `max(__ts_ms)` đã xử lý thành công, lưu JSON `{"ts_ms": <long>}` trong bucket
  `checkpoint` (đã tạo sẵn, trước đây chưa dùng):
  - `s3a://checkpoint/silver_watermark`
  - `s3a://checkpoint/gold_watermark`
  - Đọc/ghi bằng **chính Spark qua s3a** (không dùng boto3 — image `bigdata-spark` không cài).

- **Silver (incremental + merge theo order_id):**
  1. Đọc watermark `wm`. Đọc bronze 4 bảng fact (orders, order_items, order_payments,
     order_reviews) một lần (cache).
  2. `affected_ids` = distinct `order_id` có `__ts_ms > wm` ở **bất kỳ** bảng fact nào
     (first run `wm=None` → tất cả order_id).
  3. Nếu incremental và `affected_ids` rỗng → **bỏ qua Silver** (không ghi, không tiến watermark).
  4. Mỗi bảng fact: `inner-join broadcast(affected_ids)` theo `order_id` **trước** rồi mới
     `dedup_cdc` (dedup chỉ chạy trên đơn thay đổi). Các chiều (customers/products/sellers/geo/
     category) vẫn đọc full + broadcast.
  5. Join 8 chiều → `slice_df` (chỉ các đơn thay đổi, đã ở current-state).
  6. **Merge**: `existing = read(SILVER_OUT)`; `out = existing.left_anti(affected_ids) ∪ slice_df`
     → ghi qua `SILVER_TMP` rồi overwrite `SILVER_OUT` (tránh đọc-ghi cùng path). First run /
     silver chưa tồn tại → ghi thẳng `slice_df`.
  7. Ghi watermark = `new_wm` (max `__ts_ms` toàn bộ fact) **sau khi** ghi silver thành công.

  → Silver luôn = current-state (1 dòng / order_item) nên **Gold không phải đổi logic**.

- **Gold (chỉ chạy khi có thay đổi):**
  - So `silver_wm` với `gold_wm`; bằng nhau → **bỏ qua Gold**.
  - Khác → chạy `create_gold_metrics()` **y như cũ** (đọc all silver — cần cho RFM/seller rank
    toàn cục; Mongo `bulk_upsert` đã idempotent), rồi ghi `gold_wm = silver_wm`.

- **Recovery:** watermark chỉ tiến SAU KHI ghi thành công → job fail thì watermark không đổi →
  lần retry tự cover lại. Idempotent nhờ merge theo order_id (Silver) + bulk_upsert (Gold).

---

## Files

| File | Vai trò |
|------|---------|
| `spark-batch/checkpoint.py` | **(mới)** `read_watermark`/`write_watermark` — JSON trên `s3a://checkpoint` bằng Spark |
| `spark-batch/transform_bronze_to_silver.py` | detect `affected order_id` theo `__ts_ms` → rebuild slice → merge `left_anti`+`union` → overwrite → ghi watermark; skip khi không có thay đổi |
| `spark-batch/transform_silver_to_gold.py` | cổng skip (so `silver_wm` vs `gold_wm`) + ghi `gold_wm`; **giữ nguyên** aggregation |

Không đổi: S3 sink connector (giữ `DefaultPartitioner`), DAG, Makefile (configmap
`spark-batch-code` tự gồm `checkpoint.py`).

---

## Edge cases

| Tình huống | Hành vi |
|---|---|
| First run (chưa có watermark) | xử lý toàn bộ → set watermark = `max(__ts_ms)` |
| Không có CDC mới | Silver skip; Gold skip (watermark bằng nhau) |
| Silver OK, Gold fail | `silver_wm` tiến, `gold_wm` không → retry chỉ chạy lại Gold (idempotent) |
| Silver fail | watermark không tiến → retry cover lại window |
| Update đơn cũ (status/payment đổi, item không đổi) | đơn vào `affected_ids` (orders/payments có `__ts_ms` mới) → rebuild đúng current-state cho cả các item của đơn |
| Event có `__ts_ms` == watermark hiện tại | lọc `> wm` nên có thể bỏ sót event cùng mili-giây ranh giới (rủi ro nhỏ; thay đổi sau của cùng đơn sẽ bắt lại) |

---

## Verification

Xem mục **A9** trong `docs/huong-dan-test.md` (chạy lần đầu → kiểm tra watermark; chạy lại khi
không có data → skip; insert đơn mới vào Postgres → chạy lại → chỉ đơn mới được xử lý, đơn cũ
không mất; idempotency).
