# Data Dictionary: Olist Brazilian E-commerce Dataset

Tài liệu này cung cấp chi tiết về cấu trúc dữ liệu của bộ dữ liệu Olist, bao gồm mô tả các bảng, các trường thông tin và mối quan hệ giữa chúng.

---

## 1. olist_customers_dataset
Chứa thông tin về khách hàng và vị trí của họ. Được sử dụng để phân tích hành vi khách hàng theo khu vực địa lý.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `customer_id` | Mã định danh khách hàng cho mỗi đơn hàng. | Mỗi đơn hàng có một `customer_id` duy nhất. |
| `customer_unique_id` | Mã định danh duy nhất của khách hàng. | Dùng để nhận diện khách hàng quay lại mua hàng. |
| `customer_zip_code_prefix` | 5 chữ số đầu của mã bưu điện khách hàng. | Dùng để join với bảng geolocation. |
| `customer_city` | Tên thành phố của khách hàng. | |
| `customer_state` | Bang của khách hàng. | |

---

## 2. olist_geolocation_dataset
Chứa thông tin tọa độ địa lý của các mã bưu điện tại Brazil.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `geolocation_zip_code_prefix` | 5 chữ số đầu của mã bưu điện. | Khóa chính để liên kết với địa chỉ. |
| `geolocation_lat` | Vĩ độ. | |
| `geolocation_lng` | Kinh độ. | |
| `geolocation_city` | Tên thành phố. | |
| `geolocation_state` | Bang. | |

---

## 3. olist_order_items_dataset
Chứa dữ liệu về các sản phẩm có trong mỗi đơn hàng.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `order_id` | Mã định danh duy nhất của đơn hàng. | |
| `order_item_id` | Số thứ tự của sản phẩm trong cùng một đơn hàng. | Ví dụ: 1, 2, 3... |
| `product_id` | Mã định danh duy nhất của sản phẩm. | |
| `seller_id` | Mã định danh duy nhất của người bán. | |
| `shipping_limit_date` | Hạn chót người bán phải bàn giao sản phẩm cho đơn vị vận chuyển. | |
| `price` | Giá của sản phẩm. | |
| `freight_value` | Phí vận chuyển của sản phẩm. | |

---

## 4. olist_order_payments_dataset
Chứa dữ liệu về các phương thức thanh toán của đơn hàng.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `order_id` | Mã định danh duy nhất của đơn hàng. | |
| `payment_sequential` | Thứ tự thanh toán (nếu khách hàng dùng nhiều phương thức). | |
| `payment_type` | Phương thức thanh toán. | credit_card, boleto, voucher, debit_card... |
| `payment_installments` | Số kỳ trả góp. | |
| `payment_value` | Tổng số tiền thanh toán. | |

---

## 5. olist_order_reviews_dataset
Chứa dữ liệu về các đánh giá của khách hàng.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `review_id` | Mã định danh duy nhất của đánh giá. | |
| `order_id` | Mã định danh duy nhất của đơn hàng. | |
| `review_score` | Điểm đánh giá (từ 1 đến 5). | |
| `review_comment_title` | Tiêu đề của đánh giá. | |
| `review_comment_message` | Nội dung tin nhắn đánh giá. | |
| `review_creation_date` | Ngày gửi khảo sát đánh giá. | |
| `review_answer_timestamp` | Thời điểm khách hàng trả lời đánh giá. | |

---

## 6. olist_orders_dataset
Đây là bảng chính, chứa thông tin cốt lõi về mọi đơn hàng.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `order_id` | Mã định danh duy nhất của đơn hàng. | |
| `customer_id` | Khóa ngoại kết nối với bảng khách hàng. | |
| `order_status` | Trạng thái đơn hàng. | delivered, shipped, canceled... |
| `order_purchase_timestamp` | Thời điểm đặt hàng. | |
| `order_approved_at` | Thời điểm phê duyệt thanh toán. | |
| `order_delivered_carrier_date` | Thời điểm bàn giao cho đơn vị vận chuyển. | |
| `order_delivered_customer_date` | Thời điểm thực tế khách hàng nhận hàng. | |
| `order_estimated_delivery_date` | Ngày dự kiến giao hàng. | |

---

## 7. olist_products_dataset
Chứa thông tin chi tiết về các sản phẩm được bán trên Olist.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `product_id` | Mã định danh duy nhất của sản phẩm. | |
| `product_category_name` | Tên danh mục sản phẩm (Tiếng Bồ Đào Nha). | |
| `product_name_lenght` | Số lượng ký tự trong tên sản phẩm. | |
| `product_description_lenght` | Số lượng ký tự trong mô tả sản phẩm. | |
| `product_photos_qty` | Số lượng ảnh của sản phẩm. | |
| `product_weight_g` | Trọng lượng sản phẩm (gram). | |
| `product_length_cm` | Chiều dài (cm). | |
| `product_height_cm` | Chiều cao (cm). | |
| `product_width_cm` | Chiều rộng (cm). | |

---

## 8. olist_sellers_dataset
Chứa thông tin về những người bán đã thực hiện đơn hàng trên Olist.

| Trường dữ liệu | Mô tả | Ghi chú |
| :--- | :--- | :--- |
| `seller_id` | Mã định danh duy nhất của người bán. | |
| `seller_zip_code_prefix` | Mã bưu điện của người bán. | |
| `seller_city` | Thành phố của người bán. | |
| `seller_state` | Bang của người bán. | |

---

## 9. product_category_name_translation
Bảng tra cứu để dịch tên danh mục từ tiếng Bồ Đào Nha sang tiếng Anh.

| Trường dữ liệu | Mô tả |
| :--- | :--- |
| `product_category_name` | Tên danh mục bằng tiếng Bồ Đào Nha. |
| `product_category_name_english` | Tên danh mục bằng tiếng Anh. |

---

## Sơ đồ quan hệ (Entity Relationship - Tóm tắt)
- **orders.customer_id** -> customers.customer_id
- **order_items.order_id** -> orders.order_id
- **order_items.product_id** -> products.product_id
- **order_items.seller_id** -> sellers.seller_id
- **order_payments.order_id** -> orders.order_id
- **order_reviews.order_id** -> orders.order_id
- **products.product_category_name** -> translation.product_category_name
