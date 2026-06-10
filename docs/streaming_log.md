# Streaming Layer — Tài liệu kỹ thuật

> Cập nhật lần cuối: 2026-06-09

---

## 1. Overview kiến trúc luồng streaming

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Spring Boot (port 8085)                       │
│                                                                       │
│  @PostConstruct                                                        │
│  FakeUserBehaviorScheduler ──load──► PostgreSQL (products,            │
│       │                                          order_items)         │
│       │  @Scheduled(fixedDelay=5000ms)                                │
│       │  sinh 1 session mỗi 5 giây                                    │
│       ▼                                                               │
│  ReferenceDataService.sendEvent(UserBehaviorEvent)                    │
│       │  serialize → JSON String                                       │
│       │  KafkaTemplate<String,String> "userBehaviorKafkaTemplate"     │
└───────┼───────────────────────────────────────────────────────────────┘
        │
        ▼  topic: user_behavior_events  (3 partitions, 1 replica)
┌───────────────┐
│     Kafka     │  bootstrap: localhost:9092 (local) / kafka:9094 (container)
└───────┬───────┘
        │
        ▼  subscribe (chưa implement — cần tạo kafka_consumer_recommend.py)
┌─────────────────────────────────────────────────────────────────────┐
│              Spark Structured Streaming                               │
│                                                                       │
│  readStream("kafka") → parse JSON → foreachBatch                     │
│     ├─ self-join theo sessionId → đếm co-view/co-purchase pairs      │
│     └─ weighted score: PURCHASE=5, ADD_TO_CART=3, CLICK=2, VIEW=1   │
│          × bonus nếu dwellTimeMs > 30000                             │
│                                                                       │
│  top-K per source_product_id → upsert 3 sinks                        │
└──────────┬────────────────────────┬────────────────────────┬─────────┘
           │                        │                        │
           ▼                        ▼                        ▼
  PostgreSQL                   MongoDB                   MinIO
  table:                       collection:               s3a://gold-zone/
  product_recommendations      streaming_recommendations  streaming/
  (SINK CHÍNH — webapp đọc)    (view / Grafana)           recommendations/
           │
           ▼
  Spring Boot Controller
  GET /api/products/{id}/recommendations
           │
           ▼
  Webapp e-commerce (phản hồi milliseconds)
```

### Phân loại latency

| Chiều | Latency | Ghi chú |
|---|---|---|
| User bấm sản phẩm → nhận recommend | ~milliseconds | Index lookup trên bảng pre-computed |
| Event mới → recommend được cập nhật | ~30–60 giây | Spark micro-batch trigger |

Recommend là **pre-computed**, không compute on-demand khi user click.

---

## 2. Fake data — cách sinh và lý do

### Vì sao cần fake data

Olist dataset (nguồn dữ liệu thật) chỉ có **lịch sử đơn hàng đã hoàn thành** — không có dữ liệu click, view, hay browse. Để demo luồng streaming, Spring Boot sinh fake behavioral event được **anchor vào data Olist thật** thay vì random thuần túy.

### Chiến lược sinh event (FakeUserBehaviorScheduler.java)

**Khởi động một lần (`@PostConstruct`):**
```
1. Load toàn bộ products từ Postgres (ProductEntity)
   → group by productCategoryName → Map<category, List<ProductEntity>>
   → index by productId → Map<productId, ProductEntity>

2. Load 5000 order_items mẫu (JPQL projection, không lazy load)
   → purchaseCounts: Map<productId, Int>          — độ phổ biến
   → orderToProducts: Map<orderId, List<productId>> — dùng build co-purchase
   → productSellerMap: Map<productId, sellerId>

3. Build co-purchase map:
   Với mỗi order có ≥ 2 sản phẩm:
     mọi cặp (A, B) → coPurchaseMap[A].add(B), coPurchaseMap[B].add(A)

4. Build popularity weights[]:
   weights[i] = purchaseCounts(product_i) + 1   (floor 1, mọi product đều có cơ hội)
   totalWeight = sum(weights)
```

**Mỗi 5 giây (`@Scheduled fixedDelay=5000`):**
```
1. Pick anchor product — weighted random theo popularity
   (sản phẩm bán chạy xuất hiện thường xuyên hơn)

2. Pick 2–3 competitors cùng category với anchor

3. Tạo session:
   sessionId = UUID mới
   userId    = "user_" + random(1..500)
   sessionStart = Instant.now() - random(5..20 phút)   ← mô phỏng thời gian thực tế

4. Emit events theo thứ tự thời gian:
   a. VIEW mỗi competitor    dwell 5–25s   (browsing/compare)
   b. VIEW anchor            dwell 60–180s (cân nhắc kỹ)
   c. 60%: CLICK anchor      dwell null
   d. 30%: ADD_TO_CART anchor dwell null
   e. 15%: PURCHASE anchor   dwell null
   f.   └─ 40%: VIEW 1 sản phẩm từ coPurchaseMap(anchor)  dwell 10–40s

5. Mỗi event: referenceDataService.sendEvent() → Kafka
   cursor thời gian tiến: += dwellTimeMs + gap(2–10s)
```

### Conversion rate mô phỏng

```
100 session → 100 VIEW (competitors, low dwell)
           → 100 VIEW (anchor, high dwell)
           →  60 CLICK
           →  18 ADD_TO_CART   (30% of 60)
           →   2.7 PURCHASE    (15% of 18)
           →   1.1 VIEW co-purchased  (40% of 2.7)
```

---

## 3. Schema bản tin Kafka

### Topic

```
Name:       user_behavior_events
Partitions: 3
Replicas:   1
Key:        userId (String) — đảm bảo cùng user vào cùng partition
Value:      JSON String (UTF-8)
```

### JSON payload (UserBehaviorEvent)

```json
{
  "eventId":     "550e8400-e29b-41d4-a716-446655440000",
  "eventType":   "VIEW",
  "eventTime":   "2026-06-09T10:23:45.123Z",
  "userId":      "user_42",
  "sessionId":   "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "productId":   "aca2eb7d84577f7a5e5a01cc44c78cf4",
  "sellerId":    "6560211a19b47992efcd523434a7b734",
  "category":    "cama_mesa_banho",
  "dwellTimeMs": 87432,
  "searchTerm":  null
}
```

### Giá trị hợp lệ của `eventType`

| eventType | Ý nghĩa | dwellTimeMs |
|---|---|---|
| `VIEW` | User xem trang sản phẩm | Long (ms) — thời gian ở lại trang |
| `CLICK` | User click vào sản phẩm | `null` |
| `ADD_TO_CART` | User thêm vào giỏ | `null` |
| `PURCHASE` | User hoàn tất mua | `null` |

`searchTerm` hiện luôn `null` — reserved cho phase sau khi có luồng tìm kiếm thực.

---

## 4. Yêu cầu xử lý Spark Streaming (kafka_consumer_recommend.py — chưa implement)

### Input

```python
spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9094") \      # container host
    .option("subscribe", "user_behavior_events") \
    .option("startingOffsets", "latest") \
    .option("maxOffsetsPerTrigger", 10000) \
    .option("failOnDataLoss", "true") \
    .load()
```

### Schema parse JSON

```python
schema = StructType([
    StructField("eventId",     StringType()),
    StructField("eventType",   StringType()),
    StructField("eventTime",   TimestampType()),   # ISO-8601 string → timestamp
    StructField("userId",      StringType()),
    StructField("sessionId",   StringType()),
    StructField("productId",   StringType()),
    StructField("sellerId",    StringType()),
    StructField("category",    StringType()),
    StructField("dwellTimeMs", LongType()),
    StructField("searchTerm",  StringType()),
])
```

### Logic xử lý trong foreachBatch

```
Mỗi micro-batch (trigger 30–60s):

1. Gán trọng số theo eventType:
   PURCHASE     → weight = 5
   ADD_TO_CART  → weight = 3
   CLICK        → weight = 2
   VIEW         → weight = 1
   VIEW với dwellTimeMs > 30000 → weight = 2 (bonus)

2. Self-join trong cùng sessionId:
   batch_df.alias("a").join(batch_df.alias("b"),
       on = ["sessionId"] + [a.productId != b.productId]
   )
   → sinh cặp (source_product_id=a.productId, recommended_product_id=b.productId)

3. Tính score tổng hợp:
   score(A→B) = sum(weight_A × weight_B)  group by (source_product_id, recommended_product_id)

4. Lấy top 5 per source_product_id (rank theo score DESC)

5. Upsert vào 3 sinks (xem mục 5)
```

### Checkpoint và cấu hình bền vững

```
checkpointLocation: s3a://checkpoint/streaming_recommend
trigger: ProcessingTime("30 seconds")
outputMode: foreachBatch (không dùng complete/append trực tiếp vì multi-sink)
```

### Lưu ý kỹ thuật

- Self-join **không hỗ trợ trực tiếp** trên Streaming DataFrame → bắt buộc dùng `foreachBatch` để convert sang static DataFrame rồi join
- Trong `foreachBatch`: `persist()` batch_df trước khi ghi nhiều sink, `unpersist()` sau
- `dedupe` theo `(source_product_id, recommended_product_id)` trong cùng batch bằng `dropDuplicates` trước khi upsert

---

## 5. Bảng `product_recommendations` trong PostgreSQL

### DDL

```sql
CREATE TABLE IF NOT EXISTS product_recommendations (
    source_product_id      VARCHAR(64)  NOT NULL,
    recommended_product_id VARCHAR(64)  NOT NULL,
    score                  DOUBLE PRECISION NOT NULL DEFAULT 0,
    rank                   INTEGER      NOT NULL,
    updated_at             TIMESTAMP    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_product_id, recommended_product_id)
);

CREATE INDEX IF NOT EXISTS idx_rec_source
    ON product_recommendations (source_product_id, rank);
```

### Ý nghĩa các cột

| Cột | Mô tả |
|---|---|
| `source_product_id` | Sản phẩm đang xem / điểm xuất phát |
| `recommended_product_id` | Sản phẩm được recommend |
| `score` | Điểm co-occurrence có trọng số — càng cao càng liên quan |
| `rank` | Thứ hạng trong nhóm `source_product_id` (1 = tốt nhất) |
| `updated_at` | Lần cuối Spark upsert |

### Ghi chú CDC loop

Bảng `product_recommendations` nằm trong cùng Postgres instance là nguồn CDC, nhưng **không** được set `REPLICA IDENTITY` → Debezium không capture bảng này → không có CDC loop.

---

## 6. API recommend — cách hoạt động

### Endpoint

```
GET /api/products/{productId}/recommendations?limit=5
```

### Luồng xử lý

```
1. Webapp gọi: GET /api/products/aca2eb7d.../recommendations?limit=5
2. Spring Boot controller nhận request
3. Query Postgres:
   SELECT recommended_product_id, score, rank
   FROM product_recommendations
   WHERE source_product_id = 'aca2eb7d...'
   ORDER BY rank ASC
   LIMIT 5
4. (Tuỳ chọn) JOIN thêm bảng products để lấy tên, category, ảnh
5. Trả JSON response
```

### Response mẫu

```json
{
  "sourceProductId": "aca2eb7d84577f7a5e5a01cc44c78cf4",
  "recommendations": [
    {
      "productId": "99a4788cb24856965c36a24a2aa19ad0",
      "category": "cama_mesa_banho",
      "score": 42.5,
      "rank": 1
    },
    {
      "productId": "bdbd71d6a4f07855c2a2fce2a99b0d06",
      "category": "cama_mesa_banho",
      "score": 31.0,
      "rank": 2
    }
  ]
}
```

### Fallback khi chưa có recommend

Nếu `product_recommendations` trống (Spark chưa chạy hoặc sản phẩm mới):
- Trả top sản phẩm phổ biến nhất cùng category từ bảng `order_items` (query batch)
- Hoặc trả `recommendations: []` kèm HTTP 200

---

## 7. Trạng thái triển khai hiện tại

### Đã hoàn thành

| Component | File | Ghi chú |
|---|---|---|
| Fake event schema | `entity/kafka/UserBehaviorEvent.java` | ✅ 10 fields đầy đủ |
| Kafka topic tự tạo | `config/KafkaProducerConfig.java` | ✅ `user_behavior_events` 3 partitions |
| Kafka producer | `service/ReferenceDataService.java` | ✅ Topic đã đồng nhất, serialize JSON String |
| Fake event generator | `service/FakeUserBehaviorScheduler.java` | ✅ Anchor trên Olist thật, funnel thực tế |
| Co-purchase data load | `repository/postgres/OrderItemJpaRepository.java` | ✅ JPQL projection tránh N+1 |
| Event consumer (debug) | `kafka/consumer/UserBehaviorEventComsumer.java` | ⚠️ Chỉ log |

### Chưa làm (cần implement tiếp)

| Component | File cần tạo | Ghi chú |
|---|---|---|
| Spark Streaming job | `spark-streaming/kafka_consumer_recommend.py` | Logic xử lý mục 4 |
| Postgres table | `init/postgres-init/04-recommendations.sql` | DDL mục 5 |
| REST API endpoint | `controller/RecommendationController.java` | Spec mục 6 |

---

## 8. Credentials và connection strings

> Tham chiếu từ `init/.env` và `init/docker-compose.yml`.

| Service | Host (local dev) | Host (trong container) | Credentials |
|---|---|---|---|
| Kafka | `localhost:9092` | `kafka:9094` | — |
| PostgreSQL | `localhost:5432` | `postgres:5432` | `postgres` / `postgres`, db: `postgres` |
| MongoDB | `localhost:27017` | `mongodb:27017` | `admin` / `admin123456` |
| MinIO | `localhost:9000` | `minio:9000` | `minioadmin` / `minioadmin123456` |

### Credentials đã sửa

| File | Vấn đề cũ | Đã sửa thành |
|---|---|---|
| `application.yaml` | `server.port: 8081` conflict với Airflow | `8085` |
| `application.yaml` | `datasource.url: localhost:5433/airflow` sai port+db | `localhost:5432/postgres` |
| `application.yaml` | `datasource username/password: airflow/airflow` | `postgres/postgres` |
| `application.yaml` | MinIO `admin`/`password123` | `minioadmin`/`minioadmin123456` |
| `application.yaml` | MongoDB URI không có auth | Thêm `admin:admin123456@` + `?authSource=admin` |
| `spark-streaming/kafka_consumer.py` | MinIO password `minioadmin123` | `minioadmin123456` |
