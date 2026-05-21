#!/bin/bash
# Chạy 1 lần duy nhất sau khi docker-compose up -d

set -e

# Load biến từ .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}

echo "⏳ Chờ Debezium sẵn sàng..."
until curl -sf http://localhost:8083/connectors > /dev/null 2>&1; do
  echo "   ...chưa sẵn sàng, thử lại sau 5 giây"
  sleep 5
done
echo "✅ Debezium sẵn sàng!"

echo ""
echo "📡 Đăng ký connector..."
RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"olist-connector\",
    \"config\": {
      \"connector.class\": \"io.debezium.connector.postgresql.PostgresConnector\",
      \"plugin.name\": \"pgoutput\",
      \"database.hostname\": \"postgres\",
      \"database.port\": \"5432\",
      \"database.user\": \"${POSTGRES_USER}\",
      \"database.password\": \"${POSTGRES_PASSWORD}\",
      \"database.dbname\": \"olist\",
      \"topic.prefix\": \"olist_cdc\",
      \"schema.include.list\": \"public\",
      \"snapshot.mode\": \"initial\",
      \"heartbeat.interval.ms\": \"5000\"
    }
  }")

if [ "$RESULT" = "201" ]; then
  echo "✅ Connector đăng ký thành công!"
elif [ "$RESULT" = "409" ]; then
  echo "⚠️  Connector đã tồn tại rồi (bỏ qua)"
else
  echo "❌ Lỗi HTTP: $RESULT"
  exit 1
fi

echo ""
echo "📋 Kiểm tra status:"
curl -s http://localhost:8083/connectors/olist-connector/status | python3 -m json.tool 2>/dev/null || \
curl -s http://localhost:8083/connectors/olist-connector/status

echo ""
echo "🎉 Xong! Xem topics tại http://localhost:8080"
echo "   Format topic: olist_cdc.public.<tên_bảng>"