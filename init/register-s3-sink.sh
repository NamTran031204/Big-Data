#!/bin/bash
# =====================================================================
# Đăng ký Confluent S3 Sink Connector: Kafka (CDC topics) -> MinIO Bronze.
# Yêu cầu plugin kafka-connect-s3 (đã cài qua init/Dockerfile).
#
# QUAN TRỌNG (fix lỗi cũ): ParquetFormat BẮT BUỘC có Connect schema, nên
# value.converter.schemas.enable PHẢI = true (khớp với worker Debezium mặc định).
# SMT unwrap (ExtractNewRecordState) bóc payload.after thành cột phẳng.
#
# Output: s3a://bronze-zone/cdc/olist_cdc.public.<bảng>/partition=0/*.parquet
# =====================================================================

set -e

CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
MINIO_KEY="${MINIO_ROOT_USER:-minioadmin}"
MINIO_SECRET="${MINIO_ROOT_PASSWORD:-minioadmin123456}"

echo "⏳ Chờ Debezium Connect sẵn sàng tại ${CONNECT_URL}..."
until curl -sf "${CONNECT_URL}/connectors" > /dev/null 2>&1; do
  echo "   ...thử lại sau 5s"
  sleep 5
done
echo "✅ Debezium sẵn sàng!"

echo "📡 Đăng ký S3 Sink Connector (bronze-zone)..."
RESULT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${CONNECT_URL}/connectors" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"s3-sink-bronze\",
    \"config\": {
      \"connector.class\": \"io.confluent.connect.s3.S3SinkConnector\",
      \"tasks.max\": \"1\",

      \"topics.regex\": \"olist_cdc\\\\.public\\\\..*\",

      \"s3.bucket.name\": \"bronze-zone\",
      \"topics.dir\": \"cdc\",
      \"s3.region\": \"us-east-1\",
      \"store.url\": \"http://minio:9000\",
      \"storage.class\": \"io.confluent.connect.s3.storage.S3Storage\",
      \"s3.part.size\": \"5242880\",

      \"format.class\": \"io.confluent.connect.s3.format.parquet.ParquetFormat\",
      \"parquet.codec\": \"snappy\",
      \"schema.compatibility\": \"NONE\",

      \"partitioner.class\": \"io.confluent.connect.storage.partitioner.DefaultPartitioner\",

      \"flush.size\": \"1000\",
      \"rotate.schedule.interval.ms\": \"60000\",
      \"timezone\": \"UTC\",

      \"key.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"key.converter.schemas.enable\": \"false\",
      \"value.converter\": \"org.apache.kafka.connect.json.JsonConverter\",
      \"value.converter.schemas.enable\": \"true\",

      \"transforms\": \"unwrap\",
      \"transforms.unwrap.type\": \"io.debezium.transforms.ExtractNewRecordState\",
      \"transforms.unwrap.drop.tombstones\": \"true\",
      \"transforms.unwrap.delete.handling.mode\": \"rewrite\",
      \"transforms.unwrap.add.fields\": \"op,ts_ms\",

      \"behavior.on.null.values\": \"ignore\",

      \"aws.access.key.id\": \"${MINIO_KEY}\",
      \"aws.secret.access.key\": \"${MINIO_SECRET}\"
    }
  }")

if [ "$RESULT" = "201" ]; then
  echo "✅ S3 Sink Connector đăng ký thành công!"
elif [ "$RESULT" = "409" ]; then
  echo "⚠️  Connector đã tồn tại (bỏ qua)"
else
  echo "❌ Lỗi HTTP: $RESULT"
  curl -s "${CONNECT_URL}/connectors/s3-sink-bronze/status" || true
  exit 1
fi

echo ""
echo "📋 Status:"
curl -s "${CONNECT_URL}/connectors/s3-sink-bronze/status" | python3 -m json.tool 2>/dev/null || \
curl -s "${CONNECT_URL}/connectors/s3-sink-bronze/status"

echo ""
echo "🎉 Data sẽ xuất hiện ở MinIO: bronze-zone/cdc/olist_cdc.public.<bảng>/"
