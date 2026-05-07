# #!/bin/bash
set -e
MINIO_HOST="http://minio:9000"
BUCKET_NAME="bigdata"
ACCESS_FILE="/config/access.txt"
ALIAS_NAME="myminio"

echo "============================================"
echo "  MinIO Initialization Script"
echo "============================================"

# ========== BƯỚC 1: Kết nối MinIO ==========
echo ""
echo "[1/4] Đang kết nối tới MinIO..."
echo "      Host: ${MINIO_HOST}"

MAX_RETRIES=30
RETRY_COUNT=0

while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
    if mc alias set ${ALIAS_NAME} ${MINIO_HOST} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} >/dev/null 2>&1; then
        echo "      ✓ Kết nối thành công!"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "      Đang chờ MinIO... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done

if [ ${RETRY_COUNT} -eq ${MAX_RETRIES} ]; then
    echo "      ✗ Không thể kết nối tới MinIO sau ${MAX_RETRIES} lần thử!"
    exit 1
fi

# ========== BƯỚC 2: Tạo Bucket ==========
echo ""
echo "[2/4] Kiểm tra và tạo bucket '${BUCKET_NAME}'..."

if mc ls ${ALIAS_NAME}/${BUCKET_NAME} >/dev/null 2>&1; then
    echo "      ✓ Bucket '${BUCKET_NAME}' đã tồn tại."
else
    echo "      Đang tạo bucket '${BUCKET_NAME}'..."
    mc mb ${ALIAS_NAME}/${BUCKET_NAME}
    echo "      ✓ Bucket '${BUCKET_NAME}' đã được tạo."
fi

# ========== BƯỚC 3: Generate Access Key ==========
echo ""
echo "[3/4] Đang tạo Service Account (Access Key)..."

# Tạo service account và lấy output JSON
ACCESS_KEY_OUTPUT=$(mc admin user svcacct add ${ALIAS_NAME} ${MINIO_ROOT_USER} --json 2>/dev/null)

echo ACCESS_KEY_OUTPUT > ACCESS_FILE

if [ -z "${ACCESS_KEY_OUTPUT}" ]; then
    echo "      ✗ Không thể tạo access key!"
    echo "      Output: ${ACCESS_KEY_OUTPUT}"
    exit 1
fi

echo "      ✓ Access Key đã được tạo."
echo "      Access Key: ${ACCESS_KEY}"

# ========== BƯỚC 4: Ghi vào file ==========
echo ""
echo "[4/4] Đang ghi credentials vào ${ACCESS_FILE}..."

# Tạo thư mục nếu chưa tồn tại
mkdir -p "$(dirname ${ACCESS_FILE})"

# Ghi credentials vào file
cat > ${ACCESS_FILE} << EOF
EOF

# Đảm bảo file có quyền đọc
chmod 644 ${ACCESS_FILE}

echo "      ✓ Credentials đã được ghi vào ${ACCESS_FILE}"

# ========== HOÀN TẤT ==========
echo ""
echo "============================================"
echo "  ✓ Khởi tạo MinIO hoàn tất!"
echo "============================================"
echo ""
echo "Thông tin kết nối:"
echo "  - Endpoint:    ${MINIO_HOST}"
echo "  - Console:     http://localhost:9001"
echo "  - Bucket:      ${BUCKET_NAME}"
echo "  - Access Key:  ${ACCESS_KEY}"
echo "  - Secret Key:  ${ACCESS_KEY_OUTPUT} (xem trong ${ACCESS_FILE})"
echo ""
echo "============================================"

exit 0