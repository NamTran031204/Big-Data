#!/bin/bash

set -e

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "⏳ Chờ Debezium sẵn sàng..."
until curl -sf http://localhost:8083/connectors > /dev/null 2>&1; do
  echo "   ...thử lại sau 5 giây"
  sleep 5
done
echo "✅ Debezium sẵn sàng!"

echo ""
echo "📡 Đăng ký S3 Sink Connector..."

RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"s3-sink-connector\",
    \"config\": {
      \"connector.class\": \"io.confluent.connect.s3.S3SinkConnector\",
      \"tasks.max\": \"1\",

      \"topics.regex\": \"olist_cdc\\\\.public\\\\.*\",

      \"s3.bucket.name\": \"raw-data\",
      \"s3.region\": \"us-east-1\",
      \"s3.part.size\": \"5242880\",
      \"store.url\": \"http://minio:9000\",
      \"storage.class\": \"io.confluent.connect.s3.storage.S3Storage\",

      \"format.class\": \"io.confluent.connect.s3.format.parquet.ParquetFormat\",
      \"parquet.codec\": \"snappy\",

      \"flush.size\": \"100\",
      \"rotate.interval.ms\": \"60000\",
      \"rotate.schedule.interval.ms\": \"60000\",

      \"timezone\": \"UTC\",
      \"locale\": \"en_US\",

      \"transforms\": \"unwrap\",
      \"transforms.unwrap.type\": \"io.debezium.transforms.ExtractNewRecordState\",
      \"transforms.unwrap.drop.tombstones\": \"false\",
      \"transforms.unwrap.delete.handling.mode\": \"rewrite\",
      \"transforms.unwrap.add.fields\": \"op,ts_ms\",

      \"key.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"key.converter.schemas.enable\": \"false\",
      \"value.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"value.converter.schemas.enable\": \"false\",

      \"s3.credentials.provider.class\": \"com.amazonaws.auth.EnvironmentVariableCredentialsProvider\"
    }
  }")

if [ "$RESULT" = "201" ]; then
  echo "✅ S3 Sink Connector đăng ký thành công!"
elif [ "$RESULT" = "409" ]; then
  echo "⚠️  Connector đã tồn tại (bỏ qua)"
else
  echo "❌ Lỗi HTTP: $RESULT"
  exit 1
fi

echo ""
echo "📋 Kiểm tra status:"
curl -s http://localhost:8083/connectors/s3-sink-connector/status | python3 -m json.tool

echo ""
echo "🎉 Xong! Data sẽ xuất hiện tại MinIO bucket: raw-data"
echo "   Path: raw-data/topics/olist_cdc.public.<tên_bảng>/partition=0/*.parquet"