#!/bin/bash
# =====================================================================
# Đăng ký Debezium PostgreSQL source connector.
# Topics tạo ra: olist_cdc.public.<tên_bảng>
# Chạy từ host (port 8083 đã map) hoặc trong mạng kafka-network.
# Lưu ý quan trọng:
#  - decimal.handling.mode=double  -> price/payment_value ra DOUBLE
#    (mặc định 'precise' sẽ encode base64 gây hỏng dữ liệu ở bronze/silver).
#  - Converter để mặc định của worker (JsonConverter, schemas.enable=true)
#    để S3 Sink ParquetFormat có Connect schema mà ghi parquet.
# =====================================================================

CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
DB_HOSTNAME="${DB_HOSTNAME:-bigdata-postgres}"

echo "⏳ Chờ Debezium Connect sẵn sàng tại ${CONNECT_URL}..."
until curl -sf "${CONNECT_URL}/connectors" > /dev/null 2>&1; do
  echo "   ...thử lại sau 5s"
  sleep 5
done
echo "✅ Debezium sẵn sàng!"

echo "📡 Đăng ký source connector olist-connector..."
RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${CONNECT_URL}/connectors" \
  -H "Accept:application/json" \
  -H "Content-Type:application/json" \
  -d @- <<EOF
{
  "name": "olist-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "${DB_HOSTNAME}",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "olist",
    "topic.prefix": "olist_cdc",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_slot",
    "publication.name": "dbz_publication",
    "publication.autocreate.mode": "filtered",
    "schema.include.list": "public",
    "table.include.list": "public.customers,public.geolocation,public.sellers,public.products,public.category_translation,public.orders,public.order_items,public.order_payments,public.order_reviews",
    "snapshot.mode": "initial",
    "decimal.handling.mode": "double",
    "heartbeat.interval.ms": "10000",
    "tombstones.on.delete": "false"
  }
}
EOF
)

if [ "$RESULT" = "201" ]; then
  echo "✅ Source connector đăng ký thành công!"
elif [ "$RESULT" = "409" ]; then
  echo "⚠️ Source connector đã tồn tại (bỏ qua)"
else
  echo "❌ Lỗi HTTP: $RESULT"
  exit 1
fi

echo ""
echo "📋 Status:"
curl -s "${CONNECT_URL}/connectors/olist-connector/status" | python3 -m json.tool 2>/dev/null || \
curl -s "${CONNECT_URL}/connectors/olist-connector/status"

echo ""
echo "🎉 Xong! Topics: olist_cdc.public.<tên_bảng> — xem tại http://localhost:8080"
