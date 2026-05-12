from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys
import os

sys.path.append('/opt/airflow/scripts')

from ingest_bronze import run_full_ingestion 
from generate_report import run_quality_check

def on_failure_callback(context):
    
    exception = context.get('exception')
    task_id = context.get('task_instance').task_id
    print(f"❌ Task {task_id} failed! Error: {exception}")

default_args = {
    'owner': 'Duy Quang',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,                        # Thử lại 2 lần nếu lỗi
    'retry_delay': timedelta(minutes=5), # Đợi 5 phút trước khi thử lại
    'on_failure_callback': on_failure_callback
}


with DAG(
    'olist_batch_ingestion',
    default_args=default_args,
    description='Pipeline nạp dữ liệu Olist từ CSV sang Bronze Layer (MinIO)',
    schedule_interval='@daily',          # Chạy hàng ngày vào lúc 00:00
    start_date=days_ago(1),
    catchup=False,                       # Không chạy bù các ngày trong quá khứ
    tags=['bigdata', 'olist', 'bronze'],
) as dag:

    # Task 1: Nạp dữ liệu vào Bronze
    ingest_task = PythonOperator(
        task_id='ingest_csv_to_bronze',
        python_callable=run_full_ingestion,
    )

    # Task 2: Kiểm tra chất lượng dữ liệu và tạo Report
    quality_check_task = PythonOperator(
        task_id='data_quality_profiling',
        python_callable=run_quality_check,
    )

    # Thiết lập thứ tự chạy: Ingest xong mới Check Quality
    ingest_task >> quality_check_task