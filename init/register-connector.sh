#!/bin/bash

echo "⏳ Chờ Debezium sẵn sàng..."
sleep 2
echo "✅ Debezium sẵn sàng!"

echo "📡 Đăng ký connector..."
RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8083/connectors \
  -H "Accept:application/json" \
  -H "Content-Type:application/json" \
  -d '{
  "name": "olist-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "bigdata-postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "olist",
    "topic.prefix": "olist_cdc",
    "plugin.name": "pgoutput",
    "schema.include.list": "public",
    "slot.name": "debezium_slot"
  }
}')

if [ "$RESULT" = "201" ]; then
  echo "✅ Connector đăng ký thành công!"
elif [ "$RESULT" = "409" ]; then
  echo "⚠️ Connector đã tồn tại rồi (bỏ qua)"
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
echo "Format topic: olist_cdc.public.<tên_bảng>"