"""
Checkpoint / watermark helper cho luồng batch incremental.

Lưu "high-water mark" = max(__ts_ms) (epoch milliseconds do Debezium gắn) đã xử lý
thành công, dưới dạng JSON 1 dòng {"ts_ms": <long>} trong bucket MinIO `checkpoint`:
    s3a://checkpoint/silver_watermark/   (Silver)
    s3a://checkpoint/gold_watermark/     (Gold)

Đọc/ghi bằng CHÍNH Spark qua s3a (không dùng boto3) vì image spark không cài boto3,
còn cấu hình s3a đã được set sẵn trong SparkSession của mỗi job.
"""


def read_watermark(spark, path):
    """Trả về watermark (int, epoch ms) hoặc None nếu chưa có checkpoint (first run)."""
    try:
        row = spark.read.json(path).first()
    except Exception:
        # path chưa tồn tại / chưa ghi lần nào -> coi như first run
        return None
    if row is None or row["ts_ms"] is None:
        return None
    return int(row["ts_ms"])


def write_watermark(spark, path, ts_ms):
    """Ghi đè watermark mới. Raise nếu lỗi để job fail -> watermark không tiến."""
    (
        spark.createDataFrame([(int(ts_ms),)], "ts_ms long")
        .coalesce(1)
        .write.mode("overwrite")
        .json(path)
    )
