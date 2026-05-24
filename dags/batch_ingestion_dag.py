import sys
import os
from datetime import datetime, timedelta

scripts_path = '/opt/airflow/spark-batch'
if scripts_path not in sys.path:
    sys.path.append(scripts_path)
    
from airflow import DAG
from airflow.operators.python import PythonOperator

from ingest_csv_to_bronze import process_table 
from ingest_kafka_to_bronze import ingest_kafka
from transform_bronze_to_silver import process_to_silver
from transform_silver_to_gold import create_gold_metrics

default_args = {
    'owner': 'Duy Quang',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'olist_medallion_pipeline',
    default_args=default_args,
    start_date=datetime(2026, 4, 21),
    schedule_interval='@daily',
    catchup=False
) as dag:

    # 1. Nạp Bronze (Chạy song song)
    task_ingest_csv = PythonOperator(
        task_id='ingest_csv_to_bronze',
        python_callable=process_table # Lưu ý: Cần viết hàm wrapper để chạy hết list jobs
    )

    task_ingest_kafka = PythonOperator(
        task_id='ingest_kafka_to_bronze',
        python_callable=ingest_kafka
    )

    # 2. Chuyển sang Silver
    task_silver = PythonOperator(
        task_id='transform_bronze_to_silver',
        python_callable=process_to_silver
    )

    # 3. Chuyển sang Gold
    task_gold = PythonOperator(
        task_id='transform_silver_to_gold',
        python_callable=create_gold_metrics
    )

    # Thứ tự thực hiện
    [task_ingest_csv, task_ingest_kafka] >> task_silver >> task_gold