# Hướng Dẫn Query Gold Layer Trên MongoDB Atlas

**Version:** 2.0  
**Last Updated:** 2026-06-10  
**Status:** Production-Ready

---

## Mục Lục

1. [Tổng Quan Thay Đổi Kiến Trúc](#1-tổng-quan-thay-đổi-kiến-trúc)
2. [Cấu Trúc Collection Mới](#2-cấu-trúc-collection-mới)
3. [Hai Trường Thời Gian Quan Trọng](#3-hai-trường-thời-gian-quan-trọng)
4. [Hướng Dẫn Query Theo SellerID](#4-hướng-dẫn-query-theo-sellerid)
5. [Hướng Dẫn Query Theo Date Range](#5-hướng-dẫn-query-theo-date-range)
6. [Query Kết Hợp SellerID + Date Range](#6-query-kết-hợp-sellerid--date-range)
7. [Chỉ Số Tỷ Lệ — Cách Đọc Đúng](#7-chỉ-số-tỷ-lệ--cách-đọc-đúng)
8. [Hướng Dẫn Dựng Chart Trên Atlas Charts](#8-hướng-dẫn-dựng-chart-trên-atlas-charts)
9. [Phân Quyền Admin vs Seller](#9-phân-quyền-admin-vs-seller)
10. [Tham Chiếu Nhanh Tất Cả Collection](#10-tham-chiếu-nhanh-tất-cả-collection)
11. [Checklist Sau Khi Chạy Job Mới](#11-checklist-sau-khi-chạy-job-mới)

---

## 1. Tổng Quan Thay Đổi Kiến Trúc

### Vấn Đề Của Luồng Cũ

Trước đây, Gold layer được thiết kế để xem **tổng hợp toàn thời gian** — mỗi collection chỉ có 1 document cho mỗi thực thể (1 doc/category, 1 doc/state, 1 doc/seller). Điều này dẫn đến hai hạn chế:

1. **Không lọc được theo ngày**: không có trường date trong phần lớn collection, nên không thể xem doanh thu tháng 1 khác tháng 6 như thế nào.
2. **Seller không xem được dashboard riêng**: chỉ có `gold_seller_metrics` là có `seller_id`, và chỉ là tổng lifetime — seller không thể xem "tuần này tôi bán được gì".

### Kiến Trúc Mới

Luồng mới chuyển sang **daily grain**: mỗi document đại diện cho **1 ngày** của 1 thực thể. Điều này cho phép:

- Filter theo `date range` bằng cách thêm điều kiện `ingest_date` vào query.
- Filter theo `seller_id` trực tiếp trên 2 collection dành cho seller.
- Vẫn tính được tổng cho cả range bằng cách `$sum` trong aggregation pipeline hoặc Calculated Field trong Charts.

```
LUỒNG CŨ                          LUỒNG MỚI
────────────────────────────────   ───────────────────────────────────────
gold_revenue_by_category:          gold_revenue_by_category:
  { category: "electronics",         { ingest_date: "2017-01-15",
    revenue: 500000 }    ← TỔNG        date: ISODate("2017-01-15"),
                                       category: "electronics",
                                       revenue: 1200 }  ← TỪNG NGÀY

gold_seller_metrics:               gold_seller_metrics:   ← giữ nguyên (thẻ tổng)
  { seller_id: "abc",              gold_seller_daily:     ← MỚI
    seller_revenue: 80000 }          { seller_id: "abc",
    ← không có date                   ingest_date: "2017-03-05",
                                       date: ISODate("2017-03-05"),
                                       revenue: 340 }
```

### Hai Collection Hoàn Toàn Mới (Dành Cho Seller)

| Collection | Mục đích | Key |
|---|---|---|
| `gold_seller_daily` | Doanh thu, đơn hàng, giao hàng của seller theo từng ngày | `seller_id` + `ingest_date` |
| `gold_seller_product_daily` | Top sản phẩm của seller theo từng ngày | `seller_id` + `product_id` + `ingest_date` |

---

## 2. Cấu Trúc Collection Mới

### 2.1 `gold_seller_daily` — Dashboard Chính Của Seller

Đây là collection quan trọng nhất cho seller view. Mỗi document = 1 ngày bán hàng của 1 seller.

```json
{
  "seller_id": "3442f8959a84dea7ee197c632cb2df15",
  "ingest_date": "2017-06-15",
  "date": ISODate("2017-06-15T00:00:00Z"),

  "revenue": 450.80,
  "order_count": 3,
  "items_sold": 5,

  "review_score_sum": 12,
  "review_count": 4,
  "avg_review": 3.00,

  "on_time_count": 2,
  "delivered_count": 3,
  "sum_delivery_days": 25,
  "on_time_rate": 0.6667,
  "avg_delivery_days": 8.33
}
```

**Giải thích các trường:**

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `seller_id` | String | ID của seller — dùng để filter |
| `ingest_date` | String (yyyy-MM-dd) | Ngày mua hàng — dùng để filter range |
| `date` | ISODate | Cùng ngày với `ingest_date`, dạng datetime — dùng cho trục thời gian Atlas Charts |
| `revenue` | Double | Tổng doanh thu trong ngày (price + freight_value) |
| `order_count` | Long | Số đơn hàng distinct trong ngày |
| `items_sold` | Long | Số lượng item (có thể > order_count nếu 1 đơn nhiều sản phẩm) |
| `review_score_sum` | Long | Tổng điểm review — cộng được qua nhiều ngày |
| `review_count` | Long | Số review — cộng được qua nhiều ngày |
| `avg_review` | Double | Điểm trung bình ngày đó — chỉ dùng cho trend ngày |
| `on_time_count` | Long | Số đơn giao đúng hạn — cộng được |
| `delivered_count` | Long | Tổng đơn đã giao — cộng được |
| `sum_delivery_days` | Long | Tổng số ngày giao — cộng được |
| `on_time_rate` | Double | Tỷ lệ đúng hạn ngày đó — chỉ dùng cho trend ngày |
| `avg_delivery_days` | Double | Ngày giao trung bình ngày đó — chỉ dùng cho trend ngày |

---

### 2.2 `gold_seller_product_daily` — Top Sản Phẩm Của Seller

```json
{
  "seller_id": "3442f8959a84dea7ee197c632cb2df15",
  "product_id": "e5f2d52b...",
  "product_category_name_english": "bed_bath_table",
  "ingest_date": "2017-06-15",
  "date": ISODate("2017-06-15T00:00:00Z"),

  "revenue": 189.90,
  "qty": 2,
  "order_count": 2,
  "review_score_sum": 8,
  "review_count": 2,
  "avg_review": 4.00,
  "canceled_count": 0
}
```

---

### 2.3 Collection Admin — Schema Thay Đổi

Collection cũ **tổng toàn thời gian** nay có thêm `ingest_date` và `date`. Ví dụ `gold_revenue_by_category`:

```json
// TRƯỚC (1 doc cho cả lịch sử)
{ "product_category_name_english": "electronics", "revenue": 1500000, "order_count": 800 }

// SAU (1 doc mỗi ngày)
{
  "ingest_date": "2017-06-15",
  "date": ISODate("2017-06-15T00:00:00Z"),
  "product_category_name_english": "electronics",
  "revenue": 4200.50,
  "order_count": 12
}
```

**Collection đã được cập nhật:** `gold_revenue_by_category`, `gold_revenue_by_state`, `gold_revenue_by_payment_type`, `gold_product_metrics`, `gold_sales_by_category`, `gold_category_rank`, `gold_delivery_metrics`, `gold_revenue_metrics`, `gold_customer_acquisition`, `gold_top_products_daily`.

**Collection giữ nguyên (không có date):** `gold_customer_rfm` (snapshot RFM), `gold_seller_metrics` (thẻ tổng lifetime của seller).

---

## 3. Hai Trường Thời Gian Quan Trọng

Mọi collection daily đều có **hai trường thời gian** với mục đích khác nhau:

| Trường | Kiểu dữ liệu | Dùng cho | Ví dụ |
|---|---|---|---|
| `ingest_date` | String | Filter, key upsert, dùng trong Mongo shell query | `"2017-06-15"` |
| `date` | ISODate (datetime) | Trục thời gian Atlas Charts, date-range widget | `ISODate("2017-06-15T00:00:00Z")` |

**Quy tắc:**
- Trong **Mongo shell / code**: dùng `ingest_date` với string comparison (`$gte`, `$lte`).
- Trong **Atlas Charts** (UI kéo thả): dùng trường `date` (kiểu ISODate) làm X-axis hoặc date filter widget.

---

## 4. Hướng Dẫn Query Theo SellerID

### 4.1 Xem Tổng Quan Một Seller (Lifetime)

Collection `gold_seller_metrics` vẫn giữ nguyên — xem tổng hợp toàn bộ lịch sử:

```javascript
// Mongo Shell
db.gold_seller_metrics.findOne({ seller_id: "3442f8959a84dea7ee197c632cb2df15" })
```

Kết quả trả về:
```json
{
  "seller_id": "3442f8959a84dea7ee197c632cb2df15",
  "s_state": "SP",
  "s_city": "sao paulo",
  "seller_revenue": 89420.50,
  "seller_order_count": 245,
  "seller_review_avg": 3.8,
  "geographic_coverage": 12,
  "seller_revenue_rank": 37,
  "seller_avg_delivery_days": 11.4,
  "seller_fulfillment_rate": 0.8735,
  "seller_network_centrality": null,
  "seller_cluster": null,
  "fraud_risk_score": null
}
```

### 4.2 Xem Tất Cả Ngày Bán Của Một Seller

```javascript
// Toàn bộ lịch sử, sắp xếp theo ngày mới nhất
db.gold_seller_daily.find(
  { seller_id: "3442f8959a84dea7ee197c632cb2df15" }
).sort({ ingest_date: -1 })
```

### 4.3 Xem Top 10 Sản Phẩm Bán Chạy Nhất Của Seller (Tổng Lifetime)

```javascript
db.gold_seller_product_daily.aggregate([
  { $match: { seller_id: "3442f8959a84dea7ee197c632cb2df15" } },
  {
    $group: {
      _id: { product_id: "$product_id", category: "$product_category_name_english" },
      total_revenue: { $sum: "$revenue" },
      total_qty: { $sum: "$qty" },
      total_orders: { $sum: "$order_count" },
      review_score_sum: { $sum: "$review_score_sum" },
      review_count: { $sum: "$review_count" }
    }
  },
  {
    $addFields: {
      avg_review: {
        $cond: [
          { $gt: ["$review_count", 0] },
          { $round: [{ $divide: ["$review_score_sum", "$review_count"] }, 2] },
          null
        ]
      }
    }
  },
  { $sort: { total_revenue: -1 } },
  { $limit: 10 }
])
```

---

## 5. Hướng Dẫn Query Theo Date Range

### 5.1 Cú Pháp Filter Date Range

Dùng trường `ingest_date` (String) với toán tử `$gte` (greater than or equal) và `$lte` (less than or equal). String comparison hoạt động đúng vì format `yyyy-MM-dd` có thứ tự từ điển trùng thứ tự thời gian.

```javascript
// Template
{ ingest_date: { $gte: "YYYY-MM-DD", $lte: "YYYY-MM-DD" } }
```

### 5.2 Ví Dụ: Doanh Thu Theo Danh Mục Trong Quý 1/2017

```javascript
db.gold_revenue_by_category.aggregate([
  {
    $match: {
      ingest_date: { $gte: "2017-01-01", $lte: "2017-03-31" }
    }
  },
  {
    $group: {
      _id: "$product_category_name_english",
      total_revenue: { $sum: "$revenue" },
      total_orders: { $sum: "$order_count" }
    }
  },
  { $sort: { total_revenue: -1 } },
  { $limit: 20 }
])
```

### 5.3 Ví Dụ: Tỷ Lệ Giao Hàng Đúng Hạn Theo Bang Trong Tháng 6/2017

```javascript
// Dùng thành phần cộng được để tính tỷ lệ đúng cho cả range
db.gold_delivery_metrics.aggregate([
  {
    $match: {
      ingest_date: { $gte: "2017-06-01", $lte: "2017-06-30" }
    }
  },
  {
    $group: {
      _id: "$c_state",
      on_time_count: { $sum: "$on_time_count" },
      delivered_count: { $sum: "$delivered_count" },
      late_count: { $sum: "$late_delivery_count" },
      sum_days: { $sum: "$sum_delivery_days" }
    }
  },
  {
    $addFields: {
      on_time_rate: {
        $cond: [
          { $gt: ["$delivered_count", 0] },
          { $round: [{ $divide: ["$on_time_count", "$delivered_count"] }, 4] },
          0
        ]
      },
      avg_delivery_days: {
        $cond: [
          { $gt: ["$delivered_count", 0] },
          { $round: [{ $divide: ["$sum_days", "$delivered_count"] }, 2] },
          null
        ]
      }
    }
  },
  { $sort: { on_time_rate: -1 } }
])
```

### 5.4 Ví Dụ: Doanh Thu Hệ Thống Theo Ngày Trong 1 Tháng

```javascript
db.gold_revenue_metrics.find(
  { ingest_date: { $gte: "2017-06-01", $lte: "2017-06-30" } },
  { ingest_date: 1, revenue_daily: 1, order_count: 1, revenue_spike_flag: 1, _id: 0 }
).sort({ ingest_date: 1 })
```

---

## 6. Query Kết Hợp SellerID + Date Range

### 6.1 Doanh Thu Của Seller Trong Khoảng Thời Gian

```javascript
db.gold_seller_daily.find({
  seller_id: "3442f8959a84dea7ee197c632cb2df15",
  ingest_date: { $gte: "2017-01-01", $lte: "2017-06-30" }
}).sort({ ingest_date: 1 })
```

### 6.2 Tổng Kết Seller Trong 6 Tháng (Tính Lại Tỷ Lệ Đúng)

```javascript
db.gold_seller_daily.aggregate([
  {
    $match: {
      seller_id: "3442f8959a84dea7ee197c632cb2df15",
      ingest_date: { $gte: "2017-01-01", $lte: "2017-06-30" }
    }
  },
  {
    $group: {
      _id: "$seller_id",
      total_revenue: { $sum: "$revenue" },
      total_orders: { $sum: "$order_count" },
      total_items: { $sum: "$items_sold" },
      review_score_sum: { $sum: "$review_score_sum" },
      review_count: { $sum: "$review_count" },
      on_time_count: { $sum: "$on_time_count" },
      delivered_count: { $sum: "$delivered_count" },
      sum_delivery_days: { $sum: "$sum_delivery_days" }
    }
  },
  {
    $addFields: {
      avg_review: {
        $cond: [
          { $gt: ["$review_count", 0] },
          { $round: [{ $divide: ["$review_score_sum", "$review_count"] }, 2] },
          null
        ]
      },
      on_time_rate: {
        $cond: [
          { $gt: ["$delivered_count", 0] },
          { $round: [{ $divide: ["$on_time_count", "$delivered_count"] }, 4] },
          0
        ]
      },
      avg_delivery_days: {
        $cond: [
          { $gt: ["$delivered_count", 0] },
          { $round: [{ $divide: ["$sum_delivery_days", "$delivered_count"] }, 2] },
          null
        ]
      }
    }
  }
])
```

### 6.3 Top Sản Phẩm Của Seller Trong Quý

```javascript
db.gold_seller_product_daily.aggregate([
  {
    $match: {
      seller_id: "3442f8959a84dea7ee197c632cb2df15",
      ingest_date: { $gte: "2017-04-01", $lte: "2017-06-30" }
    }
  },
  {
    $group: {
      _id: {
        product_id: "$product_id",
        category: "$product_category_name_english"
      },
      revenue: { $sum: "$revenue" },
      qty: { $sum: "$qty" },
      orders: { $sum: "$order_count" },
      canceled: { $sum: "$canceled_count" },
      review_score_sum: { $sum: "$review_score_sum" },
      review_count: { $sum: "$review_count" }
    }
  },
  {
    $addFields: {
      avg_review: {
        $cond: [
          { $gt: ["$review_count", 0] },
          { $round: [{ $divide: ["$review_score_sum", "$review_count"] }, 2] },
          null
        ]
      },
      return_rate: {
        $cond: [
          { $gt: ["$orders", 0] },
          { $round: [{ $divide: ["$canceled", "$orders"] }, 4] },
          0
        ]
      }
    }
  },
  { $sort: { revenue: -1 } },
  { $limit: 10 }
])
```

### 6.4 Doanh Thu Seller Theo Từng Tháng (Group By Month)

```javascript
db.gold_seller_daily.aggregate([
  {
    $match: {
      seller_id: "3442f8959a84dea7ee197c632cb2df15",
      ingest_date: { $gte: "2017-01-01", $lte: "2017-12-31" }
    }
  },
  {
    $group: {
      _id: { $substr: ["$ingest_date", 0, 7] },   // "yyyy-MM"
      revenue: { $sum: "$revenue" },
      orders: { $sum: "$order_count" }
    }
  },
  { $sort: { _id: 1 } }
])
```

---

## 7. Chỉ Số Tỷ Lệ — Cách Đọc Đúng

Các chỉ số dạng tỷ lệ (`on_time_rate`, `avg_review`, `avg_delivery_days`, `product_return_rate`) được lưu ở **hai dạng**:

### Dạng 1: Giá trị ngày (chỉ dùng cho trend)

Tên trường `avg_*`, `on_time_rate`, `on_time_delivery_rate` — là giá trị **chỉ cho riêng ngày đó**. Dùng để vẽ biểu đồ xu hướng theo ngày.

```
Không nên: SUM(on_time_delivery_rate) / COUNT(days) → sai thống kê
```

### Dạng 2: Thành phần cộng được (dùng để tính tổng cho range)

| Chỉ số muốn tính | Công thức |
|---|---|
| Tỷ lệ giao đúng hạn của range | `SUM(on_time_count) / SUM(delivered_count)` |
| Điểm review trung bình của range | `SUM(review_score_sum) / SUM(review_count)` |
| Ngày giao trung bình của range | `SUM(sum_delivery_days) / SUM(delivered_count)` |
| Tỷ lệ hủy của range | `SUM(canceled_count) / SUM(order_count)` |

Các collection có thành phần cộng được: `gold_seller_daily`, `gold_seller_product_daily`, `gold_delivery_metrics`, `gold_product_metrics`.

---

## 8. Hướng Dẫn Dựng Chart Trên Atlas Charts

### 8.1 Kết Nối Data Source

1. Vào **Atlas Charts** → **Data Sources** → **Add Data Source**
2. Chọn cluster → database `olist_gold`
3. Thêm từng collection cần dùng làm data source riêng

### 8.2 Chart Xu Hướng Doanh Thu Seller Theo Ngày

**Mục tiêu:** Line chart doanh thu theo ngày cho 1 seller cụ thể.

1. Tạo chart mới → **Line Chart**
2. Data source: `gold_seller_daily`
3. **X Axis**: trường `date` (kiểu ISODate) → Granularity: Day
4. **Y Axis**: trường `revenue` → Aggregate: Sum
5. **Filter** (tab Filters): thêm filter `seller_id` = `"<id của seller>"`
6. Tùy chọn thêm **Date Range** filter để user có thể kéo chọn khoảng thời gian

### 8.3 Chart Top Sản Phẩm Của Seller

**Mục tiêu:** Bar chart top 10 sản phẩm theo doanh thu.

1. Tạo chart → **Bar Chart**
2. Data source: `gold_seller_product_daily`
3. **X Axis**: trường `_id.product_id` hoặc `product_category_name_english`
4. **Y Axis**: trường `revenue` → Aggregate: Sum
5. **Filter**: `seller_id` = `"<id>"`; thêm date filter nếu cần
6. **Sort**: Y Axis descending; **Limit**: 10

### 8.4 Chart Tỷ Lệ Giao Đúng Hạn (Dùng Calculated Field)

**Mục tiêu:** Tỷ lệ giao đúng hạn tổng hợp cho date range.

1. Tạo chart → **Number Chart** (hoặc Gauge)
2. Data source: `gold_seller_daily`
3. Tạo **Calculated Field**:
   - Tên: `on_time_rate_total`
   - Công thức: `$sum(on_time_count) / $sum(delivered_count)`
4. **Y Axis**: `on_time_rate_total`
5. **Filter**: `seller_id` + date range
6. Format: Percent

### 8.5 Dashboard Date Range Widget

Để toàn bộ dashboard filter theo date range cùng lúc:

1. Mở Dashboard → **Add Filter** → **Date** filter
2. Liên kết field: chọn trường `date` (ISODate) từ mỗi collection
3. Khi user kéo date range picker, tất cả chart trong dashboard sẽ cập nhật

> **Lưu ý**: phải dùng trường `date` (ISODate) cho date filter widget của Charts, không dùng `ingest_date` (String). Atlas Charts date picker chỉ hoạt động với kiểu ISODate.

### 8.6 Dashboard Seller — Bố Cục Gợi Ý

```
┌─────────────────────────────────────────────────────────┐
│  Seller Dashboard                     [Date Range Picker]│
│  Seller: [dropdown chọn seller_id]                       │
├───────────────┬─────────────────┬───────────────────────┤
│ Total Revenue │  Total Orders   │  On-Time Rate         │
│ SUM(revenue)  │  SUM(order_cnt) │  SUM(on_time)/        │
│               │                 │  SUM(delivered)       │
├───────────────┴─────────────────┴───────────────────────┤
│           Line Chart: Doanh thu theo ngày                │
│           (X=date, Y=revenue, filter=seller_id)          │
├──────────────────────────┬──────────────────────────────┤
│  Top 10 Sản Phẩm         │  Avg Delivery Days           │
│  (bar, seller_product)   │  (SUM(sum_delivery_days)/    │
│                          │   SUM(delivered_count))      │
└──────────────────────────┴──────────────────────────────┘
```

---

## 9. Phân Quyền Admin vs Seller

### Collection Admin (Toàn Hệ Thống)

Seller **không nên có quyền đọc** các collection sau — đây là dữ liệu hệ thống:

| Collection | Nội dung | Lý do hạn chế |
|---|---|---|
| `gold_revenue_metrics` | Doanh thu toàn platform theo ngày | Thông tin kinh doanh tổng thể |
| `gold_revenue_by_category` | Doanh thu theo category | Bao gồm revenue của seller khác |
| `gold_revenue_by_state` | Doanh thu theo bang | Tương tự |
| `gold_revenue_by_payment_type` | Theo phương thức thanh toán | Tương tự |
| `gold_customer_rfm` | Phân khúc khách hàng | Thông tin khách hàng private |
| `gold_customer_acquisition` | User mới / quay lại theo ngày | Metric nội bộ |
| `gold_product_metrics` | Toàn bộ sản phẩm trên platform | Bao gồm sản phẩm của seller khác |
| `gold_top_products_daily` | Top 10 toàn platform | Tương tự |
| `gold_sales_by_category` | Pivot category × bang | Tổng hợp toàn hệ thống |
| `gold_category_rank` | Xếp hạng category | Tương tự |
| `gold_delivery_metrics` | Giao hàng theo bang | Metric vận hành nội bộ |

### Collection Seller (Dữ Liệu Cá Nhân Của Seller)

Seller chỉ đọc được doc có `seller_id` = id của chính họ:

| Collection | Nội dung | Filter bắt buộc |
|---|---|---|
| `gold_seller_metrics` | Thẻ tổng quan lifetime | `seller_id = own_id` |
| `gold_seller_daily` | Doanh thu, giao hàng theo ngày | `seller_id = own_id` |
| `gold_seller_product_daily` | Sản phẩm theo ngày | `seller_id = own_id` |

> **Lưu ý triển khai**: Hiện tại Gold layer lưu dữ liệu tất cả seller trong cùng collection. Phân quyền phải được enforce ở tầng **API / Atlas App Services** (Row-Level Security), không phải ở tầng storage. Seller không được query trực tiếp lên MongoDB Atlas mà phải qua API có xác thực.

---

## 10. Tham Chiếu Nhanh Tất Cả Collection

| Collection | Key Fields | Date? | Seller? | Dùng cho |
|---|---|---|---|---|
| `gold_revenue_metrics` | `ingest_date` | ✅ | ❌ | Doanh thu platform ngày |
| `gold_revenue_by_category` | `ingest_date`, `category` | ✅ | ❌ | Doanh thu theo danh mục |
| `gold_revenue_by_state` | `ingest_date`, `c_state` | ✅ | ❌ | Doanh thu theo bang |
| `gold_revenue_by_payment_type` | `ingest_date`, `payment_type` | ✅ | ❌ | Doanh thu theo thanh toán |
| `gold_customer_rfm` | `customer_unique_id` | ❌ | ❌ | Phân khúc khách hàng |
| `gold_customer_acquisition` | `ingest_date` | ✅ | ❌ | User mới / quay lại |
| `gold_product_metrics` | `ingest_date`, `product_id` | ✅ | ❌ | Hiệu suất sản phẩm |
| `gold_top_products_daily` | `ingest_date`, `product_id` | ✅ | ❌ | Top 10 sản phẩm |
| `gold_sales_by_category` | `ingest_date`, `category` | ✅ | ❌ | Pivot category × state |
| `gold_category_rank` | `ingest_date`, `category` | ✅ | ❌ | Xếp hạng category |
| `gold_seller_metrics` | `seller_id` | ❌ | ✅ | Thẻ tổng lifetime seller |
| `gold_delivery_metrics` | `ingest_date`, `c_state` | ✅ | ❌ | Giao hàng theo bang |
| `gold_seller_daily` | `seller_id`, `ingest_date` | ✅ | ✅ | Dashboard chính seller |
| `gold_seller_product_daily` | `seller_id`, `product_id`, `ingest_date` | ✅ | ✅ | Top sản phẩm seller |

---

## 11. Checklist Sau Khi Chạy Job Mới

Sau khi chạy `make run-gold` với code mới, xác nhận các điểm sau:

### Kiểm Tra Cấu Trúc

```javascript
// 1. Collection seller mới đã có dữ liệu
db.gold_seller_daily.countDocuments()          // phải > 0
db.gold_seller_product_daily.countDocuments()  // phải > 0

// 2. Trường date là ISODate (không phải string)
db.gold_seller_daily.findOne({}, { date: 1 })
// Kết quả đúng: { date: ISODate("2017-06-15T00:00:00.000Z") }
// Kết quả sai: { date: "2017-06-15" }

// 3. Collection admin đã có ingest_date
db.gold_revenue_by_category.findOne({}, { ingest_date: 1, date: 1 })
// Phải có cả hai trường

// 4. Delivery metrics có thành phần cộng được
db.gold_delivery_metrics.findOne({}, { on_time_count: 1, delivered_count: 1 })
// Phải có cả hai trường (không null)
```

### Kiểm Tra Số Liệu

```javascript
// 5. Tổng revenue seller daily ≈ seller_revenue trong gold_seller_metrics
// Chọn 1 seller bất kỳ
const sid = db.gold_seller_metrics.findOne({}, { seller_id: 1 }).seller_id
const lifetime = db.gold_seller_metrics.findOne({ seller_id: sid }).seller_revenue
const fromDaily = db.gold_seller_daily.aggregate([
  { $match: { seller_id: sid } },
  { $group: { _id: null, total: { $sum: "$revenue" } } }
]).toArray()[0].total
// lifetime và fromDaily phải gần bằng nhau (chênh lệch < 1% do làm tròn)
print(`Lifetime: ${lifetime}, From daily: ${fromDaily}`)

// 6. Kiểm tra date range query trả nhiều dòng (không phải 1 dòng tổng)
db.gold_revenue_by_category.countDocuments({
  ingest_date: { $gte: "2017-01-01", $lte: "2017-03-31" }
})
// Phải >> số lượng category vì mỗi category có nhiều ngày
```

### Kiểm Tra Index

```javascript
// 7. Index đã được tạo
db.gold_seller_daily.getIndexes()
// Phải có index trên { seller_id: 1, ingest_date: 1 }

db.gold_seller_product_daily.getIndexes()
// Phải có index trên { seller_id: 1, product_id: 1, ingest_date: 1 }
```

---

*Tài liệu này tương ứng với code tại [spark-batch/transform_silver_to_gold.py](../../spark-batch/transform_silver_to_gold.py) — phiên bản thêm seller_id + date range (2026-06-10).*
