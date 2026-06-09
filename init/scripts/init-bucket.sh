#!/bin/sh
# =====================================================================
# Khởi tạo MinIO: kết nối + tạo các bucket cần cho pipeline.
#   bronze-zone : dữ liệu CDC thô (S3 Sink ghi vào)
#   silver-zone : dữ liệu đã join/clean
#   gold-zone   : gold metrics (parquet)
#   checkpoint  : checkpoint cho Spark streaming
# =====================================================================
set -e

MINIO_HOST="http://minio:9000"
ALIAS_NAME="myminio"
BUCKETS="bronze-zone silver-zone gold-zone checkpoint"

echo "============================================"
echo "  MinIO Initialization"
echo "============================================"

# 1) Kết nối (retry tới khi MinIO sẵn sàng)
MAX_RETRIES=30
RETRY_COUNT=0
echo "[1/2] Kết nối MinIO ${MINIO_HOST}..."
while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
    if mc alias set ${ALIAS_NAME} ${MINIO_HOST} "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; then
        echo "      ✓ Kết nối thành công!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "      Đang chờ MinIO... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done

if [ ${RETRY_COUNT} -eq ${MAX_RETRIES} ]; then
    echo "      ✗ Không thể kết nối MinIO sau ${MAX_RETRIES} lần!"
    exit 1
fi

# 2) Tạo bucket (idempotent)
echo "[2/2] Tạo các bucket..."
for bucket in ${BUCKETS}; do
    if mc ls ${ALIAS_NAME}/${bucket} >/dev/null 2>&1; then
        echo "      ✓ '${bucket}' đã tồn tại."
    else
        mc mb ${ALIAS_NAME}/${bucket}
        echo "      ✓ '${bucket}' đã tạo."
    fi
done

echo ""
echo "============================================"
echo "  ✓ Khởi tạo MinIO hoàn tất! Buckets: ${BUCKETS}"
echo "============================================"
exit 0
