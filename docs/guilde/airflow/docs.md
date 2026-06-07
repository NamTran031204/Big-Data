
## **Thứ tự chạy container**
**Lưu ý** chạy `airflow-init` một lần để migrate DB và tạo user.

```powershell
cd init

# 1) Hạ tầng liên quan dữ liệu (nếu DAG cần MinIO)
docker compose up -d minio mc

# 2) Backend của Airflow
docker compose up -d airflow-postgres airflow-redis

# 3) Init Airflow (one-time)
docker compose up airflow-init

# 4) Core Airflow
docker compose up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer
```

- Kiểm tra nhanh: `docker compose ps`
- Xem log quan trọng: `docker compose logs -f airflow-scheduler`
- Dừng toàn bộ: `docker compose down`

**Lệnh Airflow cơ bản**
```powershell
# Liệt kê DAGs
docker compose exec airflow-webserver airflow dags list

# Trigger DAG thủ công
docker compose exec airflow-webserver airflow dags trigger <dag_id>

# Xem tasks trong DAG
docker compose exec airflow-webserver airflow tasks list <dag_id>

# Test một task
docker compose exec airflow-webserver airflow tasks test <dag_id> <task_id> 2026-05-11

# Pause/Unpause DAG
docker compose exec airflow-webserver airflow dags pause <dag_id>
docker compose exec airflow-webserver airflow dags unpause <dag_id>

# Xem Connections/Variables
docker compose exec airflow-webserver airflow connections list
docker compose exec airflow-webserver airflow variables list
```

- UI: `http://localhost:8081`
- Username/Password lấy từ biến `_AIRFLOW_WWW_USER_USERNAME` và `_AIRFLOW_WWW_USER_PASSWORD` trong .env

**Nạp và chạy code RAG trong Airflow**
- Đặt code RAG thành module Python mà scheduler/worker đọc được:
  - Ưu tiên để ngay trong dags hoặc plugins (dễ import).
- Cài dependency:
  - Cách nhanh: thêm vào `_PIP_ADDITIONAL_REQUIREMENTS` trong .env (ví dụ `langchain`, `openai`, `chromadb`, …).
  - Cách sạch: build custom image Airflow.
- Gọi trong DAG bằng `PythonOperator` (import function) hoặc `BashOperator` (chạy script).

Ví dụ skeleton (không có logic RAG):
```python
from airflow.decorators import dag, task

@dag(schedule=None, catchup=False)
def rag_pipeline():
    @task
    def run_rag():
        from my_rag_pipeline import run
        run()

    run_rag()

dag = rag_pipeline()
```

**Use case: batch bronze từ MinIO → Spark → MinIO (Airflow-focused)**
- Lưu ý kết nối mạng: hiện MinIO ở `minio-network`, còn Airflow ở `airflow-network`. Nếu Airflow cần đọc MinIO (sensor/metadata), hãy nối chúng vào cùng network.
- Thiết lập Connections trong Airflow:
  - `minio_s3` (Conn Type: Amazon S3)  
    - Host: `http://minio:9000`  
    - Extra (JSON): `{"endpoint_url": "http://minio:9000", "verify": false}`
  - `spark_default` (Conn Type: Spark) trỏ tới Spark cluster của bạn.

Luồng DAG đề xuất:
1) **Sensor** kiểm tra object mới trong MinIO (prefix bronze).
2) **SparkSubmitOperator** chạy job xử lý (chỉ truyền `input_prefix` và `output_prefix`).
3) **Sensor** kiểm tra output đã được ghi về MinIO.
4) (Tuỳ chọn) **TriggerDagRunOperator** hoặc `Dataset` để kích hoạt downstream.

Skeleton DAG (không có code Spark):
```python
from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime

with DAG(
    dag_id="bronze_to_silver_batch",
    start_date=datetime(2024, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
) as dag:

    wait_bronze = S3KeySensor(
        task_id="wait_bronze",
        bucket_name="bronze",
        bucket_key="orders/*",
        aws_conn_id="minio_s3",
    )

    spark_job = SparkSubmitOperator(
        task_id="spark_process",
        application="/path/to/your_spark_job.py",
        conn_id="spark_default",
        application_args=[
            "--input", "s3a://bronze/orders/",
            "--output", "s3a://silver/orders/",
        ],
    )

    verify_output = S3KeySensor(
        task_id="verify_output",
        bucket_name="silver",
        bucket_key="orders/*",
        aws_conn_id="minio_s3",
    )

    wait_bronze >> spark_job >> verify_output
```

Nếu bạn muốn, tôi có thể:
1) Tạo sẵn một DAG mẫu đúng theo repo của bạn (có placeholder).
2) Chỉnh network để Airflow truy cập được MinIO.
3) Thiết lập danh sách `_PIP_ADDITIONAL_REQUIREMENTS` phù hợp cho MinIO + Spark + RAG.