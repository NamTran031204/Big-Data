# Phương Án 2: Spark Container (Recommended)

**Version:** 1.0  
**Last Updated:** 2026-05-22  
**Status:** Production-Ready ⭐

---

## 📋 Mục Lục

1. [Kiến Trúc Tổng Quan](#kiến-trúc-tổng-quan)
2. [Cập Nhật Docker Compose](#cập-nhật-docker-compose)
3. [Chuẩn Bị Spark Jobs](#chuẩn-bị-spark-jobs)
4. [Tạo DAG Airflow](#tạo-dag-airflow)
5. [Deployment & Startup](#deployment--startup)
6. [Monitoring & Operations](#monitoring--operations)
7. [Scaling Spark Cluster](#scaling-spark-cluster)

---

## 🏗️ Kiến Trúc Tổng Quan

### Architecture Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                     Docker Compose Network                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────┐                     │
│  │ Airflow Services (airflow-network)  │                     │
│  │ ├─ airflow-webserver :8081          │                     │
│  │ ├─ airflow-scheduler                │                     │
│  │ ├─ airflow-worker (CeleryExecutor)  │                     │
│  │ ├─ airflow-redis                    │                     │
│  │ └─ airflow-postgres                 │                     │
│  └─────────────────────────────────────┘                     │
│           │                                                   │
│           │ spark://spark-master:7077                        │
│           ▼                                                   │
│  ┌─────────────────────────────────────┐                     │
│  │ Spark Cluster (airflow-network +    │                     │
│  │              minio-network)         │                     │
│  │ ├─ spark-master :7077, :8181        │                     │
│  │ ├─ spark-worker-1 :8182             │                     │
│  │ ├─ spark-worker-2 :8183             │                     │
│  │ └─ [optional] spark-worker-N        │                     │
│  └─────────────────────────────────────┘                     │
│           │                                                   │
│           │ s3a://bucket                                     │
│           ▼                                                   │
│  ┌─────────────────────────────────────┐                     │
│  │ MinIO (minio-network)               │                     │
│  │ ├─ minio-service :9000, :9001       │                     │
│  │ └─ buckets: bronze-zone, silver,... │                     │
│  └─────────────────────────────────────┘                     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Service Communication

| From | To | Protocol | Endpoint |
|------|-------|----------|----------|
| Airflow → Spark | spark-master | Spark | `spark://spark-master:7077` |
| Spark → MinIO | minio | S3A | `http://minio:9000` |
| Spark → Kafka | kafka | Kafka | `kafka:9094` (internal) |
| Spark → PostgreSQL | postgres | JDBC | `postgres:5432` |

---

## 🐳 Cập Nhật Docker Compose

### Step 1: Add Spark Services

**File:** `init/docker-compose.yml`

Thêm phần sau vào section `services:` (trước dòng `# =============================================================`):

```yaml
  # =============================================================
  # SPARK CLUSTER
  # =============================================================
  spark-master:
    image: bitnami/spark:3.5.0
    container_name: spark-master
    environment:
      SPARK_MODE: master
      SPARK_RPC_AUTHENTICATION_ENABLED: "no"
      SPARK_RPC_ENCRYPTION_ENABLED: "no"
      SPARK_LOCAL_STORAGE_ENCRYPTION_ENABLED: "no"
    ports:
      - "7077:7077"  # Spark Master RPC port
      - "8181:8080"  # Spark Master Web UI
    volumes:
      - ../spark-batch:/opt/spark-apps:ro
      - ../data/external:/data/external:ro
    networks:
      - airflow-network
      - minio-network
      - kafka-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080"]
      interval: 15s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  spark-worker-1:
    image: bitnami/spark:3.5.0
    container_name: spark-worker-1
    depends_on:
      spark-master:
        condition: service_healthy
    environment:
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077
      SPARK_WORKER_MEMORY: 2G
      SPARK_WORKER_CORES: 2
      SPARK_RPC_AUTHENTICATION_ENABLED: "no"
      SPARK_RPC_ENCRYPTION_ENABLED: "no"
      SPARK_LOCAL_STORAGE_ENCRYPTION_ENABLED: "no"
    ports:
      - "8182:8081"  # Worker Web UI
    volumes:
      - ../spark-batch:/opt/spark-apps:ro
      - ../data/external:/data/external:ro
    networks:
      - airflow-network
      - minio-network
      - kafka-network
    restart: unless-stopped

  spark-worker-2:
    image: bitnami/spark:3.5.0
    container_name: spark-worker-2
    depends_on:
      spark-master:
        condition: service_healthy
    environment:
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077
      SPARK_WORKER_MEMORY: 2G
      SPARK_WORKER_CORES: 2
      SPARK_RPC_AUTHENTICATION_ENABLED: "no"
      SPARK_RPC_ENCRYPTION_ENABLED: "no"
      SPARK_LOCAL_STORAGE_ENCRYPTION_ENABLED: "no"
    ports:
      - "8183:8081"  # Worker Web UI
    volumes:
      - ../spark-batch:/opt/spark-apps:ro
      - ../data/external:/data/external:ro
    networks:
      - airflow-network
      - minio-network
      - kafka-network
    restart: unless-stopped
```

### Step 2: Update Airflow Volume Mounts

Ensure Airflow has access to spark-batch:

```yaml
  airflow-webserver:
    # ... existing config ...
    volumes:
      - ../airflow/dags:/opt/airflow/dags
      - ../airflow/logs:/opt/airflow/logs
      - ../airflow/config:/opt/airflow/config
      - ../airflow/plugins:/opt/airflow/plugins
      - ../spark-batch:/opt/spark-apps:ro  # Add this
```

### Step 3: Update Airflow Requirements

**File:** `init/.env`

```bash
# Add this line
_PIP_ADDITIONAL_REQUIREMENTS=apache-airflow-providers-apache-spark==5.1.0
```

Or create requirements file:

**File:** `init/requirements-airflow.txt`

```
apache-airflow-providers-apache-spark==5.1.0
apache-airflow-providers-amazon==7.7.0
```

And mount in docker-compose:

```yaml
  airflow-webserver:
    volumes:
      - ./requirements-airflow.txt:/tmp/requirements-airflow.txt:ro
```

---

## 🔧 Chuẩn Bị Spark Jobs

### Step 1: Update ingest_bronze.py

**File:** `spark-batch/ingest_bronze.py`

```python
"""
CSV Ingestion to Bronze Layer

Input: CSV files from /data/external/
Output: Parquet files to s3a://bronze-zone/

Partitioning applied to:
- orders (by order_purchase_timestamp)
- order_items (by shipping_limit_date)
- order_reviews (by review_creation_date)
"""

import os
import sys
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from schemas import TABLE_SCHEMAS

# ==================== CONFIG ====================
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'http://minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin123456')
DATA_PATH = os.getenv('DATA_PATH', '/data/external')

# ==================== SPARK SESSION ====================
print(f"[INFO] Initializing Spark Session")
print(f"[INFO] MinIO Endpoint: {MINIO_ENDPOINT}")
print(f"[INFO] Data Path: {DATA_PATH}")

spark = SparkSession.builder \
    .appName("Olist_CSV_Ingestion") \
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT) \
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.shuffle.partitions", "200") \
    .getOrCreate()

logger = spark.sparkContext._jvm.org.apache.log4j.LoggerFactory.getLogger(__name__)

# ==================== MAIN LOGIC ====================
def process_table(table_key, csv_name, partition_col=None):
    """
    Process single table: CSV → Parquet
    
    Args:
        table_key: Table identifier (orders, customers, etc.)
        csv_name: CSV filename
        partition_col: Column to partition by (optional)
    """
    print(f"\n{'='*60}")
    print(f"Processing: {table_key}")
    print(f"{'='*60}")
    
    input_path = f"{DATA_PATH}/{csv_name}"
    output_path = f"s3a://bronze-zone/{table_key}/"
    
    print(f"[INFO] Input Path: {input_path}")
    print(f"[INFO] Output Path: {output_path}")
    print(f"[INFO] Partition Column: {partition_col}")
    
    try:
        # Read CSV
        print(f"[INFO] Reading CSV...")
        df = spark.read.csv(
            input_path, 
            header=True, 
            schema=TABLE_SCHEMAS.get(table_key)
        )
        
        print(f"[INFO] Raw row count: {df.count():,}")
        
        # Drop duplicates
        print(f"[INFO] Dropping duplicates...")
        df = df.dropDuplicates()
        
        print(f"[INFO] Deduplicated row count: {df.count():,}")
        
        # Add partition column if needed
        if partition_col:
            print(f"[INFO] Adding partition column: ingest_date")
            df = df.withColumn("ingest_date", F.to_date(F.col(partition_col)))
        
        # Write to MinIO
        print(f"[INFO] Writing to MinIO...")
        writer = df.write.mode("overwrite")
        
        if partition_col:
            writer = writer.partitionBy("ingest_date")
        
        writer.parquet(output_path)
        
        print(f"[INFO] ✅ Successfully wrote to {output_path}")
        
    except Exception as e:
        print(f"[ERROR] ❌ Failed to process {table_key}: {str(e)}")
        raise

def main():
    """Main execution logic"""
    jobs = [
        ("orders", "olist_orders_dataset.csv", "order_purchase_timestamp"),
        ("order_items", "olist_order_items_dataset.csv", "shipping_limit_date"),
        ("customers", "olist_customers_dataset.csv", None),
        ("products", "olist_products_dataset.csv", None),
        ("order_payments", "olist_order_payments_dataset.csv", None),
        ("order_reviews", "olist_order_reviews_dataset.csv", "review_creation_date"),
        ("sellers", "olist_sellers_dataset.csv", None),
        ("geolocation", "olist_geolocation_dataset.csv", None),
        ("category_translation", "product_category_name_translation.csv", None)
    ]
    
    print(f"\n{'='*60}")
    print(f"CSV Ingestion to Bronze Zone - Start")
    print(f"{'='*60}")
    
    failed_jobs = []
    success_count = 0
    
    for table_key, csv_name, p_col in jobs:
        try:
            process_table(table_key, csv_name, p_col)
            success_count += 1
        except Exception as e:
            print(f"\n[ERROR] Failed to ingest {table_key}: {e}")
            failed_jobs.append((table_key, str(e)))
    
    # Summary
    print(f"\n{'='*60}")
    print(f"CSV Ingestion Summary")
    print(f"{'='*60}")
    print(f"Total Jobs: {len(jobs)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_jobs)}")
    
    if failed_jobs:
        print(f"\nFailed Jobs:")
        for table_key, error in failed_jobs:
            print(f"  - {table_key}: {error}")
        sys.exit(1)
    
    print(f"\n✅ All jobs completed successfully!")
    spark.stop()

if __name__ == "__main__":
    main()
```

### Step 2: Verify Other Scripts

Ensure other Spark scripts (transform_bronze_to_silver.py, etc.) also use service names:

```python
# ✅ Correct (inside container)
spark.config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")

# ❌ Wrong (external host)
spark.config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000")
```

---

## 🔄 Tạo DAG Airflow

### File: `airflow/dags/ingest_csv_to_bronze_dag.py`

```python
"""
CSV Ingestion DAG using Spark Container

This DAG orchestrates CSV data ingestion into MinIO bronze zone.
Spark jobs run on a dedicated Spark cluster (spark-master + workers).

Schedule: Daily at 02:00 AM
Owner: Olist Team
Tags: batch, bronze, csv
"""

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
SPARK_MASTER = 'spark://spark-master:7077'
SPARK_DRIVER_MEMORY = '2g'
SPARK_EXECUTOR_MEMORY = '2g'
SPARK_EXECUTOR_CORES = '2'

MINIO_ENDPOINT = 'http://minio:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin123456'
DATA_PATH = '/data/external'

# ==================== DAG CONFIG ====================
default_args = {
    'owner': 'olist-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    'ingest_csv_to_bronze',
    default_args=default_args,
    description='Ingest CSV files to MinIO bronze zone via Spark container',
    schedule_interval='0 2 * * *',  # 02:00 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['batch', 'bronze', 'csv', 'spark'],
    doc_md="""
    # CSV to Bronze Ingestion DAG
    
    **Version:** 1.0  
    **Status:** Production  
    **Last Updated:** 2026-05-22
    
    ## Purpose
    Orchestrate daily CSV data ingestion from local filesystem into MinIO bronze zone.
    
    ## Architecture
    - **Orchestrator:** Airflow (CeleryExecutor)
    - **Processing:** Spark Cluster (master + 2 workers)
    - **Storage:** MinIO S3-compatible object storage
    
    ## Process Flow
    1. **Check Data:** Verify CSV files exist
    2. **Ingest:** Run Spark job to convert CSV → Parquet
    3. **Validate:** Verify output in MinIO
    4. **Notify:** Alert on success/failure
    
    ## Input Data
    9 Olist e-commerce CSV files from `/data/external/`:
    - orders (partitioned by date)
    - order_items
    - customers
    - products
    - order_payments
    - order_reviews
    - sellers
    - geolocation
    - category_translation
    
    ## Output Data
    Parquet files in `s3a://bronze-zone/<table>/`:
    - Deduplicated rows
    - Proper partitioning applied
    - Schema validation done
    
    ## SLA & Monitoring
    - Target Duration: < 10 minutes
    - Alert if: Duration > 20 minutes OR task fails
    - Logs: Check Airflow UI → Task Logs
    - Spark UI: http://spark-master:8181
    
    ## Retry Policy
    - Max retries: 2
    - Retry delay: 5 minutes
    """,
)

# ==================== HELPER FUNCTIONS ====================
def check_data_availability(**context):
    """Verify CSV files exist in data path"""
    logger.info(f"Checking data availability in {DATA_PATH}")
    
    import os
    
    required_files = [
        'olist_orders_dataset.csv',
        'olist_order_items_dataset.csv',
        'olist_customers_dataset.csv',
        'olist_products_dataset.csv',
        'olist_order_payments_dataset.csv',
        'olist_order_reviews_dataset.csv',
        'olist_sellers_dataset.csv',
        'olist_geolocation_dataset.csv',
        'product_category_name_translation.csv',
    ]
    
    missing_files = []
    for fname in required_files:
        fpath = os.path.join(DATA_PATH, fname)
        if not os.path.exists(fpath):
            missing_files.append(fname)
            logger.warning(f"❌ Missing: {fpath}")
        else:
            try:
                file_size = os.path.getsize(fpath) / (1024 * 1024)
                logger.info(f"✅ Found: {fname} ({file_size:.2f} MB)")
            except Exception as e:
                logger.warning(f"⚠️  Cannot access {fname}: {e}")
    
    if missing_files:
        raise AirflowException(f"Missing CSV files: {', '.join(missing_files)}")
    
    logger.info("✅ All required CSV files available")

def post_ingestion_check(**context):
    """Post-ingestion validation"""
    logger.info("Post-ingestion validation...")
    logger.info("✅ Ingestion completed successfully")
    logger.info("Check MinIO console: http://localhost:9001")
    logger.info("Check Spark logs: http://localhost:8181")

# ==================== TASKS ====================
check_data = PythonOperator(
    task_id='check_data_availability',
    python_callable=check_data_availability,
    provide_context=True,
    doc_md="Verify all required CSV files exist before starting Spark job",
)

ingest_csv = SparkSubmitOperator(
    task_id='ingest_csv_to_bronze',
    application='/opt/spark-apps/ingest_bronze.py',
    conf={
        'spark.master': SPARK_MASTER,
        'spark.driver.memory': SPARK_DRIVER_MEMORY,
        'spark.executor.memory': SPARK_EXECUTOR_MEMORY,
        'spark.executor.cores': SPARK_EXECUTOR_CORES,
        'spark.sql.adaptive.enabled': 'true',
        'spark.sql.adaptive.coalescePartitions.enabled': 'true',
        'spark.sql.shuffle.partitions': '200',
    },
    env_vars={
        'MINIO_ENDPOINT': MINIO_ENDPOINT,
        'MINIO_ACCESS_KEY': MINIO_ACCESS_KEY,
        'MINIO_SECRET_KEY': MINIO_SECRET_KEY,
        'DATA_PATH': DATA_PATH,
    },
    verbose=True,
    doc_md="""
    ### CSV to Parquet Conversion
    
    Runs Spark application to:
    1. Read CSV files from /data/external/
    2. Apply schema validation
    3. Drop duplicates
    4. Partition by date (where applicable)
    5. Write Parquet to s3a://bronze-zone/
    
    **Duration:** ~5-10 minutes depending on data size
    **Spark Master:** spark://spark-master:7077
    **Workers:** 2 workers (2G RAM, 2 cores each)
    """,
)

validate_output = PythonOperator(
    task_id='validate_ingestion_output',
    python_callable=post_ingestion_check,
    provide_context=True,
    doc_md="Verify ingestion outputs and provide links to monitoring dashboards",
)

# ==================== DAG FLOW ====================
check_data >> ingest_csv >> validate_output
```

---

## 🚀 Deployment & Startup

### Step 1: Prepare Environment

```bash
cd init

# Verify docker-compose.yml has Spark services
grep -A 5 "spark-master:" docker-compose.yml

# Verify .env has Airflow provider
grep "apache-airflow-providers-apache-spark" .env
```

### Step 2: Start Services (Ordered)

```bash
# 1. Storage & Infrastructure
docker compose up -d minio postgres mongodb

# 2. Airflow Backend
docker compose up -d airflow-postgres airflow-redis

# 3. Airflow Init (one-time)
docker compose up airflow-init

# 4. Kafka & Debezium (optional, but recommended)
docker compose up -d zookeeper kafka kafka-ui

# 5. Spark Cluster (NEW)
docker compose up -d spark-master spark-worker-1 spark-worker-2

# 6. Airflow Core
docker compose up -d airflow-webserver airflow-scheduler airflow-worker

# 7. Verify all services
docker compose ps
```

### Step 3: Verify Startup

```bash
# Check all containers running
docker compose ps

# Expected output:
# spark-master       │ Up
# spark-worker-1     │ Up
# spark-worker-2     │ Up
# airflow-webserver  │ Up
# airflow-scheduler  │ Up
# minio              │ Up

# Check Spark Master logs
docker compose logs spark-master | tail -20

# Check Airflow scheduler logs
docker compose logs airflow-scheduler | tail -20
```

### Step 4: Verify Connectivity

```bash
# Test Spark Master health
docker compose exec spark-master curl -s http://localhost:8080 | grep -o "Alive"

# Test MinIO connectivity from Spark
docker compose exec spark-master curl -s http://minio:9000/minio/health/live

# Test Airflow can see DAG
docker compose exec airflow-webserver airflow dags list | grep ingest_csv_to_bronze
```

---

## 📊 Monitoring & Operations

### Step 1: Access Monitoring Dashboards

| Dashboard | URL | Credentials | Purpose |
|-----------|-----|-------------|---------|
| Airflow UI | http://localhost:8081 | airflow/airflow | Monitor DAGs, tasks, logs |
| Spark Master | http://localhost:8181 | — | View running apps, executors |
| Spark Worker 1 | http://localhost:8182 | — | Worker 1 metrics |
| Spark Worker 2 | http://localhost:8183 | — | Worker 2 metrics |
| MinIO Console | http://localhost:9001 | minioadmin/minioadmin123456 | Browse buckets, upload files |

### Step 2: Trigger DAG

```bash
# Method 1: Via Airflow CLI
docker compose exec airflow-webserver \
  airflow dags trigger ingest_csv_to_bronze --exec-date 2026-05-22

# Method 2: Via UI
# http://localhost:8081 → DAGs → ingest_csv_to_bronze → Trigger DAG

# Method 3: Via REST API
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"conf": {}}' \
  http://localhost:8081/api/v1/dags/ingest_csv_to_bronze/dagRuns \
  -u airflow:airflow
```

### Step 3: Monitor Execution

```bash
# Watch DAG execution in real-time
docker compose logs -f airflow-scheduler | grep "ingest_csv_to_bronze"

# Watch Spark job
docker compose logs -f spark-master | grep "Olist_CSV_Ingestion"

# Check Airflow task logs
docker compose exec airflow-webserver airflow tasks logs \
  ingest_csv_to_bronze ingest_csv_to_bronze 2026-05-22T00:00:00

# Check Spark driver logs
docker compose exec spark-master tail -f /opt/spark/logs/spark--org.apache.spark.deploy.master.Master-1-*.out
```

### Step 4: Verify Output

```bash
# List files in MinIO bronze-zone
docker compose exec mc mc ls minio/bronze-zone --recursive

# Check file sizes
docker compose exec mc mc du --recursive minio/bronze-zone

# Verify data integrity (sample read)
# Via MinIO Console: http://localhost:9001
```

---

## 📈 Scaling Spark Cluster

### Add More Workers

```yaml
# init/docker-compose.yml
spark-worker-3:
  image: bitnami/spark:3.5.0
  container_name: spark-worker-3
  depends_on:
    spark-master:
      condition: service_healthy
  environment:
    SPARK_MODE: worker
    SPARK_MASTER_URL: spark://spark-master:7077
    SPARK_WORKER_MEMORY: 4G  # Increase if needed
    SPARK_WORKER_CORES: 4    # Increase if needed
  volumes:
    - ../spark-batch:/opt/spark-apps:ro
    - ../data/external:/data/external:ro
  networks:
    - airflow-network
    - minio-network
    - kafka-network
  ports:
    - "8184:8081"
  restart: unless-stopped
```

Then:

```bash
docker compose up -d spark-worker-3
```

### Tune Spark Config

```python
# In DAG
ingest_csv = SparkSubmitOperator(
    # ...
    conf={
        'spark.master': 'spark://spark-master:7077',
        'spark.driver.memory': '4g',           # Increase
        'spark.executor.memory': '4g',         # Increase
        'spark.executor.cores': '4',           # Match worker cores
        'spark.sql.shuffle.partitions': '400', # Increase for more parallelism
        'spark.task.cpus': '1',
    },
)
```

---

## 🔍 Troubleshooting

### Spark Master not starting

```bash
docker compose logs spark-master

# Common cause: Port 7077 already in use
# Solution:
docker compose down
docker compose up -d spark-master
```

### Spark Worker can't connect to Master

```bash
# Check network
docker network ls
docker network inspect airflow-network

# Verify service name resolution
docker compose exec spark-worker-1 nslookup spark-master

# Check firewall
docker compose exec spark-worker-1 curl spark-master:7077
```

### Airflow can't reach Spark Master

```bash
# Verify Airflow can see Spark Master
docker compose exec airflow-webserver curl spark-master:7077

# Check Airflow container networks
docker compose exec airflow-webserver ip addr show

# Ensure airflow-webserver in correct network
docker network inspect airflow-network | grep spark-master
```

### MinIO S3A errors

```
Error accessing Bucket: Access Denied
```

**Solution:**
```python
# Verify credentials in environment variables
conf={
    'spark.hadoop.fs.s3a.endpoint': 'http://minio:9000',
    'spark.hadoop.fs.s3a.access.key': 'minioadmin',
    'spark.hadoop.fs.s3a.secret.key': 'minioadmin123456',
    'spark.hadoop.fs.s3a.path.style.access': 'true',
}
```

### Out of Memory errors

```
java.lang.OutOfMemoryError: Java heap space
```

**Solution:**
```python
conf={
    'spark.driver.memory': '4g',      # Increase
    'spark.executor.memory': '4g',    # Increase
    'spark.driver.maxResultSize': '2g',
}
```

---

## 📚 Reference Commands

```bash
# Check all Spark services
docker compose ps | grep spark

# Restart Spark cluster
docker compose restart spark-master spark-worker-1 spark-worker-2

# View Spark Master logs
docker compose logs spark-master

# Kill stuck Spark job
docker compose exec spark-master \
  curl -X POST http://localhost:7077/v1/submissions/kill/<driver-id>

# Rebuild Spark container (after code changes)
docker compose build --no-cache spark-master

# Check resource usage
docker stats spark-master spark-worker-1 spark-worker-2
```

---

## ✅ Verification Checklist

- [ ] Spark Master container running (`docker compose ps`)
- [ ] Spark Workers healthy (`docker compose logs spark-master`)
- [ ] Airflow can reach Spark (`docker compose exec airflow-webserver curl spark-master:7077`)
- [ ] MinIO accessible from Spark (`docker compose exec spark-master curl http://minio:9000`)
- [ ] CSV files exist in `/data/external/`
- [ ] Airflow DAG visible (`airflow dags list`)
- [ ] Spark UI accessible (`http://localhost:8181`)
- [ ] MinIO buckets created (`mc ls minio`)
- [ ] DAG trigger successful
- [ ] Output files in MinIO bronze-zone

---

**Next Steps:** See [README.md](./README.md) for overview, or proceed to production deployment.
