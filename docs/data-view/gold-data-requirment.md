
## 📦 Gold Data — Danh sách đầy đủ

---

### UC1: Real-time Revenue Dashboard

**Gold Table: `gold_revenue_metrics`**

| Metric | Mô tả | Spark Operation |
|---|---|---|
| `revenue_5min` | Doanh thu mỗi 5 phút | Streaming + Tumbling Window |
| `revenue_hourly` | Doanh thu theo giờ | Sliding Window |
| `revenue_daily` | Doanh thu theo ngày | Batch aggregation |
| `revenue_by_category` | Doanh thu theo danh mục sản phẩm | GroupBy + Join |
| `revenue_by_state` | Doanh thu theo bang/tỉnh | GroupBy + Geo join |
| `revenue_by_payment_type` | Doanh thu theo hình thức thanh toán | GroupBy |
| `avg_order_value` | Giá trị đơn hàng trung bình (AOV) | Agg function |
| `order_count` | Số lượng đơn hàng theo kỳ | Count + Window |
| `revenue_growth_rate` | Tốc độ tăng trưởng doanh thu (%) | Window LAG function |
| `revenue_spike_flag` | Flag đơn hàng bất thường | UDF + Threshold |

---

### UC2: Customer Behavior Analysis

**Gold Table: `gold_customer_rfm`**

| Metric | Mô tả | Spark Operation |
|---|---|---|
| `recency_days` | Số ngày kể từ lần mua cuối | DateDiff + Window |
| `frequency` | Số lần mua trong kỳ | Count + GroupBy |
| `monetary` | Tổng giá trị đã chi tiêu | Sum + GroupBy |
| `rfm_score` | Điểm RFM tổng hợp (1-5 mỗi chiều) | Custom UDF |
| `customer_segment` | Phân khúc: Champion/Loyal/At Risk/Lost | UDF on RFM score |
| `new_customer_count` | Số khách hàng mới theo ngày | First purchase detection |
| `returning_customer_count` | Số khách quay lại | Window + dedup |
| `churn_probability` | Xác suất rời bỏ (0-1) | **MLlib: Logistic Regression** |
| `clv_predicted` | Customer Lifetime Value dự đoán | **MLlib: Regression** |

---

### UC3: Product Performance Analytics

**Gold Table: `gold_product_metrics`**

| Metric | Mô tả | Spark Operation |
|---|---|---|
| `top_products_daily` | Top 10 sản phẩm bán chạy mỗi ngày | Window RANK() |
| `sales_by_category` | Doanh số theo category | Pivot operation |
| `avg_review_score` | Điểm đánh giá trung bình | Avg + GroupBy |
| `review_sentiment` | Tỷ lệ review tích cực/tiêu cực | **UDF NLP / MLlib** |
| `product_return_rate` | Tỷ lệ hủy đơn theo sản phẩm | GroupBy + filter |
| `recommended_products` | Ma trận gợi ý sản phẩm | **MLlib: ALS Collaborative Filtering** |
| `category_growth_rank` | Xếp hạng tăng trưởng category | Window DENSE_RANK() |
| `low_stock_alert` | Sản phẩm bán nhiều nhưng ít đơn gần đây | Window LAG + UDF |

---

### UC4: Seller Network Analysis

**Gold Table: `gold_seller_metrics`**

| Metric | Mô tả | Spark Operation |
|---|---|---|
| `seller_revenue_rank` | Xếp hạng doanh thu seller | Window RANK() |
| `seller_order_count` | Số đơn hàng mỗi seller | GroupBy |
| `seller_avg_delivery_days` | Thời gian giao hàng trung bình | DateDiff + Avg |
| `seller_review_avg` | Điểm review trung bình | Join + Avg |
| `seller_fulfillment_rate` | Tỷ lệ giao hàng đúng hạn | Filter + ratio |
| `seller_network_centrality` | Độ ảnh hưởng trong mạng lưới | **GraphFrames: PageRank** |
| `seller_cluster` | Nhóm seller tương đồng | **GraphFrames: Connected Components** |
| `fraud_risk_score` | Điểm rủi ro gian lận | **MLlib: Anomaly Detection** |
| `geographic_coverage` | Phân bố địa lý seller | GeoJoin + GroupBy |

---

### UC5: Delivery Performance Monitoring

**Gold Table: `gold_delivery_metrics`**

| Metric | Mô tả | Spark Operation |
|---|---|---|
| `on_time_delivery_rate` | Tỷ lệ giao hàng đúng hạn (%) | Filter + ratio |
| `avg_delivery_time_days` | Thời gian giao trung bình theo route | DateDiff + GroupBy |
| `late_delivery_count` | Số đơn giao trễ theo ngày | Filter + Window |
| `late_delivery_by_state` | Tỷ lệ trễ theo bang | GroupBy + Join Geo |
| `predicted_delivery_days` | Dự đoán thời gian giao | **MLlib: Random Forest** |
| `delivery_hotspot` | Vùng địa lý có nhiều đơn trễ | GeoJoin + Heatmap |

---

### Pipeline xử lý để đạt Gold data

```
Bronze (raw CSV)
    ↓ Silver: clean, join, dedup
    ├── orders + order_items + payments + customers (join 4 tables)
    ├── + products + category_translation
    ├── + sellers + geolocation
    └── + reviews
    ↓ Gold: aggregate, compute, ML predict
    ├── Revenue metrics     → MongoDB: gold_revenue_metrics
    ├── Customer RFM        → MongoDB: gold_customer_rfm
    ├── Product metrics     → MongoDB: gold_product_metrics
    ├── Seller network      → MongoDB: gold_seller_metrics
    └── Delivery metrics    → MongoDB: gold_delivery_metrics
```

---

### Mapping với yêu cầu Spark

| Yêu cầu Spark | Gold data thực hiện |
|---|---|
| Window functions | Revenue growth, Top products ranking |
| Pivot/Unpivot | Sales by category matrix |
| Broadcast join | Products (nhỏ) join Orders (lớn) |
| Sort-merge join | Geolocation join Orders (cả 2 lớn) |
| Custom UDF | RFM scoring, fraud flag, sentiment |
| MLlib | Churn prediction, CLV, ALS recommendation, delivery prediction |
| GraphFrames | Seller network PageRank, Connected Components |
| Streaming | Revenue 5-min window, real-time order count |
| Watermarking | Xử lý late delivery events |
