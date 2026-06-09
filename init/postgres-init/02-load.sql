-- =====================================================================
-- Nạp dữ liệu Olist từ CSV (mount tại /csv) vào các bảng.
-- COPY ... HEADER true: bỏ qua dòng header (khớp theo THỨ TỰ cột,
-- không theo tên header) -> BOM ở product_category_name_translation.csv
-- không ảnh hưởng.
-- Trường rỗng (vd ngày giao hàng thiếu) -> NULL theo mặc định COPY CSV.
-- TRUNCATE để target `make seed-postgres` chạy lại được (idempotent).
-- =====================================================================

TRUNCATE customers, geolocation, sellers, products, category_translation,
         orders, order_items, order_payments, order_reviews RESTART IDENTITY;

COPY customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
    FROM '/csv/olist_customers_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
    FROM '/csv/olist_geolocation_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state)
    FROM '/csv/olist_sellers_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY products (product_id, product_category_name, product_name_lenght, product_description_lenght,
               product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
    FROM '/csv/olist_products_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY category_translation (product_category_name, product_category_name_english)
    FROM '/csv/product_category_name_translation.csv' WITH (FORMAT csv, HEADER true);

COPY orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at,
             order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)
    FROM '/csv/olist_orders_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
    FROM '/csv/olist_order_items_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value)
    FROM '/csv/olist_order_payments_dataset.csv' WITH (FORMAT csv, HEADER true);

COPY order_reviews (review_id, order_id, review_score, review_comment_title, review_comment_message,
                    review_creation_date, review_answer_timestamp)
    FROM '/csv/olist_order_reviews_dataset.csv' WITH (FORMAT csv, HEADER true);

-- Tóm tắt số dòng đã nạp
DO $$
BEGIN
    RAISE NOTICE 'customers=%   geolocation=%   sellers=%   products=%   category=%',
        (SELECT count(*) FROM customers), (SELECT count(*) FROM geolocation),
        (SELECT count(*) FROM sellers), (SELECT count(*) FROM products),
        (SELECT count(*) FROM category_translation);
    RAISE NOTICE 'orders=%   order_items=%   order_payments=%   order_reviews=%',
        (SELECT count(*) FROM orders), (SELECT count(*) FROM order_items),
        (SELECT count(*) FROM order_payments), (SELECT count(*) FROM order_reviews);
END $$;
