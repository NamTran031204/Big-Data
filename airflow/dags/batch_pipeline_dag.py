"""
DAG điều phối luồng BATCH (Lambda Architecture - Olist).

Luồng:
    ensure_connectors  ->  wait_bronze  ->  silver  ->  gold

- ensure_connectors: đảm bảo Debezium source + S3 sink đã đăng ký (idempotent,
  PUT config tới Kafka Connect REST). Nếu đã có thì cập nhật/không đổi.
- wait_bronze: kiểm tra MinIO bronze-zone đã có dữ liệu parquet (best-effort).
- silver/gold: SparkSubmitOperator submit job tới spark://spark-master:7077
  (deploy-mode cluster: driver chạy trong cluster -> nối được Kafka/MinIO/Mongo).

Dùng TaskFlow API (@dag / @task) theo yêu cầu.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

# ----------------------------------------------------------------------
# Hằng số / cấu hình
# ----------------------------------------------------------------------
CONNECT_URL = os.environ.get("CONNECT_URL", "http://debezium-connect:8083")
SPARK_CONN_ID = "spark_default"
PROJECT_DIR = "/opt/project"

SPARK_PACKAGES = (
    "org.apache.hadoop:hadoop-aws:3.3.4,"
    "com.amazonaws:aws-java-sdk-bundle:1.12.262,"
    "org.postgresql:postgresql:42.7.3"
)

MINIO_ENV = {
    "MINIO_ENDPOINT": os.environ.get("MINIO_ENDPOINT", "http://minio:9000"),
    "MINIO_ACCESS_KEY": os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
    "MINIO_SECRET_KEY": os.environ.get("MINIO_SECRET_KEY", "minioadmin123456"),
}
MONGO_ENV = {
    "MONGO_LOCAL_URI": os.environ.get(
        "MONGO_LOCAL_URI", "mongodb://admin:admin123456@bigdata-mongodb:27017/?authSource=admin"
    ),
    "MONGO_ATLAS_URI": os.environ.get("MONGO_ATLAS_URI", ""),
    "MONGO_DB": os.environ.get("MONGO_DB", "olist_gold"),
}

SOURCE_CONFIG = {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    # docker: bigdata-postgres | k8s: postgres  (đặt qua env DEBEZIUM_DB_HOST)
    "database.hostname": os.environ.get("DEBEZIUM_DB_HOST", "bigdata-postgres"),
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "olist",
    "topic.prefix": "olist_cdc",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_slot",
    "publication.name": "dbz_publication",
    "publication.autocreate.mode": "filtered",
    "schema.include.list": "public",
    "table.include.list": (
        "public.customers,public.geolocation,public.sellers,public.products,"
        "public.category_translation,public.orders,public.order_items,"
        "public.order_payments,public.order_reviews"
    ),
    "snapshot.mode": "initial",
    "decimal.handling.mode": "double",
    "heartbeat.interval.ms": "10000",
    "tombstones.on.delete": "false",
}

SINK_CONFIG = {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "tasks.max": "1",
    "topics.regex": r"olist_cdc\.public\..*",
    "s3.bucket.name": "bronze-zone",
    "topics.dir": "cdc",
    "s3.region": "us-east-1",
    "store.url": "http://minio:9000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "s3.part.size": "5242880",
    "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
    "parquet.codec": "snappy",
    "schema.compatibility": "NONE",
    "partitioner.class": "io.confluent.connect.storage.partitioner.DefaultPartitioner",
    "flush.size": "1000",
    "rotate.schedule.interval.ms": "60000",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "key.converter.schemas.enable": "false",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "true",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "true",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "transforms.unwrap.add.fields": "op,ts_ms",
    "behavior.on.null.values": "ignore",
    "aws.access.key.id": os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
    "aws.secret.access.key": os.environ.get("MINIO_SECRET_KEY", "minioadmin123456"),
}


def _put_connector(name: str, config: dict) -> None:
    """PUT /connectors/<name>/config — tạo mới hoặc cập nhật (idempotent)."""
    url = f"{CONNECT_URL}/connectors/{name}/config"
    data = json.dumps(config).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="PUT", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"[{name}] HTTP {resp.status}")


default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="batch_pipeline",
    description="Olist batch: CDC -> Bronze -> Silver -> Gold (MinIO + Mongo x2)",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["olist", "batch", "medallion"],
)
def batch_pipeline():
    @task
    def ensure_connectors():
        _put_connector("olist-connector", SOURCE_CONFIG)
        _put_connector("s3-sink-bronze", SINK_CONFIG)
        return "connectors-ready"

    @task.short_circuit
    def wait_bronze() -> bool:
        """Best-effort: kiểm tra bronze-zone đã có object chưa (nếu có boto3)."""
        try:
            import boto3
            from botocore.client import Config

            s3 = boto3.client(
                "s3",
                endpoint_url=MINIO_ENV["MINIO_ENDPOINT"],
                aws_access_key_id=MINIO_ENV["MINIO_ACCESS_KEY"],
                aws_secret_access_key=MINIO_ENV["MINIO_SECRET_KEY"],
                config=Config(signature_version="s3v4"),
            )
            resp = s3.list_objects_v2(Bucket="bronze-zone", Prefix="cdc/", MaxKeys=1)
            has = resp.get("KeyCount", 0) > 0
            print(f"bronze-zone/cdc objects present: {has}")
            return has
        except Exception as e:  # noqa: BLE001
            print(f"Bỏ qua kiểm tra bronze (lý do: {e}) -> tiếp tục")
            return True

    silver = SparkSubmitOperator(
        task_id="silver",
        conn_id=SPARK_CONN_ID,
        application=f"{PROJECT_DIR}/spark-batch/transform_bronze_to_silver.py",
        name="olist_bronze_to_silver",
        deploy_mode="client",
        packages=SPARK_PACKAGES,
        conf={
            "spark.driver.memory": "2g",
            "spark.executor.memory": "2g",
            "spark.executor.cores": "2",
        },
        env_vars=MINIO_ENV,
        verbose=False,
    )

    gold = SparkSubmitOperator(
        task_id="gold",
        conn_id=SPARK_CONN_ID,
        application=f"{PROJECT_DIR}/spark-batch/transform_silver_to_gold.py",
        name="olist_silver_to_gold",
        deploy_mode="client",
        packages=SPARK_PACKAGES,
        conf={
            "spark.driver.memory": "2g",
            "spark.executor.memory": "2g",
            "spark.executor.cores": "2",
        },
        env_vars={**MINIO_ENV, **MONGO_ENV},
        verbose=False,
    )

    ensure_connectors() >> wait_bronze() >> silver >> gold


batch_pipeline()
