-- =====================================================================
-- REPLICA IDENTITY FULL: để Debezium gửi đủ giá trị before/after khi
-- UPDATE/DELETE (không chỉ primary key). Cần cho CDC chính xác.
-- =====================================================================

ALTER TABLE customers            REPLICA IDENTITY FULL;
ALTER TABLE geolocation          REPLICA IDENTITY FULL;
ALTER TABLE sellers              REPLICA IDENTITY FULL;
ALTER TABLE products             REPLICA IDENTITY FULL;
ALTER TABLE category_translation REPLICA IDENTITY FULL;
ALTER TABLE orders               REPLICA IDENTITY FULL;
ALTER TABLE order_items          REPLICA IDENTITY FULL;
ALTER TABLE order_payments       REPLICA IDENTITY FULL;
ALTER TABLE order_reviews        REPLICA IDENTITY FULL;
