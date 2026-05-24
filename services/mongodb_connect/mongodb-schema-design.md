# MongoDB Schema Design Document
## Olist Brazilian E-commerce Dataset

---

## 1. Giới thiệu

Tài liệu này mô tả cách thiết kế schema MongoDB cho bộ dữ liệu Olist Brazilian E-commerce.

### Mục tiêu:
- Tối ưu hiệu năng truy vấn
- Giảm số lượng join (lookup)
- Phù hợp với đặc trưng NoSQL
- Hỗ trợ phân tích dữ liệu lớn (Big Data)

---

## 2. Chiến lược thiết kế

MongoDB là cơ sở dữ liệu NoSQL nên không ưu tiên join như SQL. Do đó áp dụng:

### 2.1 Embedding
- Nhúng dữ liệu con vào document cha
- Dùng khi dữ liệu luôn truy vấn cùng nhau

### 2.2 Referencing
- Dùng khóa tham chiếu (_id)
- Áp dụng khi dữ liệu lớn hoặc dùng lại nhiều

### 2.3 Hybrid
- Kết hợp cả embedding và referencing

---

## 3. Thiết kế các Collection

---

### 3.1 customers

```json
{
  "_id": "customer_id",
  "customer_unique_id": "string",
  "zip_code_prefix": "string",
  "city": "string",
  "state": "string"
}
```
Giải thích:

- Mỗi khách hàng có thể có nhiều đơn hàng
- Không embed orders để tránh document lớn

### 3.2 geolocations
```json
{
  "_id": "zip_code_prefix",
  "lat": "number",
  "lng": "number",
  "city": "string",
  "state": "string"
}
```
Giải thích:

- Dùng để phân tích địa lý
- Có thể lookup khi cần
### 3.3 products
```json
{
  "_id": "product_id",
  "category_name": "string",
  "category_name_english": "string",
  "name_length": "number",
  "description_length": "number",
  "photos_qty": "number",
  "weight_g": "number",
  "dimensions": {
    "length_cm": "number",
    "height_cm": "number",
    "width_cm": "number"
  }
}
```
Giải thích:

- Embed luôn category translation để giảm lookup

### 3.4 seller
```json
{
  "_id": "seller_id",
  "zip_code_prefix": "string",
  "city": "string",
  "state": "string"
}
```

### 3.5 orders
```json
{
  "_id": "order_id",
  "customer_id": "string",
  "order_status": "string",
  "purchase_timestamp": "date",
  "approved_at": "date",
  "delivered_carrier_date": "date",
  "delivered_customer_date": "date",
  "estimated_delivery_date": "date",

  "items": [
    {
      "order_item_id": "number",
      "product_id": "string",
      "seller_id": "string",
      "price": "number",
      "freight_value": "number",
      "shipping_limit_date": "date"
    }
  ],

  "payments": [
    {
      "sequential": "number",
      "type": "string",
      "installments": "number",
      "value": "number"
    }
  ],

  "review": {
    "review_id": "string",
    "score": "number",
    "comment_title": "string",
    "comment_message": "string",
    "creation_date": "date",
    "answer_timestamp": "date"
  }
}
```
## 4. Giải thích thiết kế
### 4.1 Embedding

Các bảng được embed vào orders:

- order_items → items
- order_payments → payments
- order_reviews → review

Lý do:

- Luôn truy vấn cùng đơn hàng
- Quan hệ nhỏ (1-N, N nhỏ)
- Giảm số lần lookup
### 4.2 Referencing

Các trường dùng reference:

- customer_id
- product_id
- seller_id

Lý do:

- Dữ liệu lớn
- Dùng lại nhiều nơi
- Tránh duplication quá nhiều