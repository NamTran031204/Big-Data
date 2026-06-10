-- =====================================================================
-- Bảng OUTPUT của luồng Streaming (speed layer).
-- Spark streaming (spark-streaming/kafka_consumer.py) đọc user_behavior_events,
-- cộng dồn điểm ưa thích theo (user, category) -> user_preference,
-- rồi tính top-N gợi ý sản phẩm -> user_recommendation.
--
-- LƯU Ý: 3 bảng này KHÔNG nằm trong table.include.list của Debezium
-- (init/register-connector.sh) và KHÔNG đặt REPLICA IDENTITY -> không bị CDC
-- bắt ngược vào bronze (tránh loopback). Đừng thêm chúng vào 03-replica-identity.sql.
-- =====================================================================

CREATE TABLE IF NOT EXISTS user_preference (
    user_id    VARCHAR(64),
    category   VARCHAR(128),
    score      DOUBLE PRECISION,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, category)
);

CREATE TABLE IF NOT EXISTS user_recommendation (
    user_id              VARCHAR(64),
    product_id           VARCHAR(64),
    sequence_no          INTEGER,
    recommendation_score DOUBLE PRECISION,
    updated_at           TIMESTAMP,
    PRIMARY KEY (user_id, sequence_no)
);

-- Bảng staging được Spark JDBC ghi đè (overwrite) mỗi micro-batch -> không cần DDL.
-- DROP để re-run sạch (tránh lệch schema nếu chạy lại nhiều lần).
DROP TABLE IF EXISTS user_preference_staging;
