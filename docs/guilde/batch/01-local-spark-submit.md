# Phương Án 1: Local spark-submit

**Version:** 1.0  
**Last Updated:** 2026-05-22

---

## 📋 Mục Lục

1. [Chuẩn Bị Môi Trường](#chuẩn-bị-môi-trường)
2. [Xử Lý CSV Input](#xử-lý-csv-input)
3. [Tạo DAG Airflow](#tạo-dag-airflow)
4. [Chạy & Monitor](#chạy--monitor)
5. [Best Practices](#best-practices)

---

## 🔧 Chuẩn Bị Môi Trường

### Step 1: Cài Spark 3.5.x

#### macOS
```bash
brew install apache-spark
spark-shell --version
```

#### Linux (Ubuntu/Debian)
```bash
# Cài Java
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk

# Cài Spark
cd /opt
sudo wget https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz
sudo tar -xzf spark-3.5.0-bin-hadoop3.tgz
sudo mv spark-3.5.0-bin-hadoop3 spark

# Add to PATH
echo 'export SPARK_HOME=/opt/spark' >> ~/.bashrc
echo 'export PATH=$PATH:$SPARK_HOME/bin' >> ~/.bashrc
source ~/.bashrc

spark-submit --version
```

#### Windows
```powershell
# Download từ https://spark.apache.org/downloads.html
# Extract to C:\spark-3.5.0

# Add to Environment Variables
$env:SPARK_HOME = "C:\spark-3.5.0"
$env:PATH += ";$env:SPARK_HOME\bin"

spark-submit --version
```

### Step 2: Cài Python Dependencies

```bash
cd /path/to/Big-Data/spark-batch
pip install -r requirements.txt

# requirements.txt content:
# pyspark==3.5.8
```

### Step 3: Verify Setup

```bash
# Test Spark
spark-submit --version

# Test Python
python -c "import pyspark; print(pyspark.__version__)"

# Test schemas module
python -c "from schemas import TABLE_SCHEMAS; print(list(TABLE_SCHEMAS.keys()))"
```

---

## 📁 Xử Lý CSV Input

### Issue: Relative Path

Current code uses:
```python
input_path = f"../data/external/{csv_name}"  # ❌ Problem
```

**Working directory khác khi chạy qua Airflow**, nên relative path sẽ fail.

### Solution A: Copy CSV vào MinIO (Recommended)

**Advantage:** Không phụ thuộc file system local, pure cloud storage

```bash
# 1. Setup MinIO credentials
export MINIO_ENDPOINT=http://localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin123456

# 2. Copy CSV files (dùng AWS CLI hoặc mc)
# Dùng mc (MinIO client)
mc alias set minio http://localhost:9000 minioadmin minioadmin123456

mc cp ../data/external/olist_orders_dataset.csv \
  minio/bronze-zone/orders/olist_orders_dataset.csv

mc cp ../data/external/olist_customers_dataset.csv \
  minio/bronze-zone/customers/olist_customers_dataset.csv

# ... copy các files khác

# 3. Verify
mc ls minio/bronze-zone/
```

**Cập nhật ingest_bronze.py để đọc từ S3A:**

```python
def process_table(table_key, csv_name, partition_col=None):
    print(f"--- Processing CSV: {table_key} ---")
    
    # Read CSV from MinIO
    input_path = f"s3a://bronze-zone/{table_key}/{csv_name}"
    output_path = f"s3a://bronze-zone/{table_key}-processed/"
    
    df = spark.read.csv(input_path, header=True, schema=TABLE_SCHEMAS.get(table_key))
    # ... rest of code
```

### Solution B: Mount Volume & Absolute Path

**Advantage:** Dễ dàng test locally, không cần upload S3

**Step 1: Mount volume vào Airflow container**

```yaml
# init/docker-compose.yml
services:
  airflow-webserver:
    volumes:
      - ../data/external:/data/external:ro  # Add this
```

**Step 2: Cập nhật ingest_bronze.py**

```python
import os
from pyspark.sql import SparkSession
from schemas import TABLE_SCHEMAS

spark = SparkSession.builder \
    .appName("Olist_CSV_Ingestion") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin123456") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

def process_table(table_key, csv_name, partition_col=None):
    print(f"--- Processing CSV: {table_key} ---")
    
    # Use absolute path
    data_dir = os.getenv('DATA_PATH', '/data/external')
    input_path = f"{data_dir}/{csv_name}"
    output_path = f"s3a://bronze-zone/{table_key}/"
    
    print(f"Reading from: {input_path}")
    print(f"Writing to: {output_path}")
    
    df = spark.read.csv(input_path, header=True, schema=TABLE_SCHEMAS.get(table_key))
    # ... rest of code
```

---

## 🔄 Tạo DAG Airflow

### File: `airflow/dags/ingest_csv_to_bronze_dag.py`

```python
"""
CSV Ingestion to Bronze Layer DAG

Schedule: Daily at 02:00 AM
Input: CSV files from /data/external/
Output: Parquet files in s3a://bronze-zone/

Tables ingested:
- orders (partitioned by order_purchase_timestamp)
- order_items (partitioned by shipping_limit_date)
- customers, products, order_payments, order_reviews, sellers, geolocation, category_translation
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

# ==================== CONFIG ====================
SPARK_BATCH_DIR = os.path.expanduser('~/projects/Big-Data/spark-batch')  # Adjust path
DATA_PATH = '/data/external'

SPARK_MASTER = 'local[*]'
SPARK_DRIVER_MEMORY = '2g'
SPARK_EXECUTOR_MEMORY = '2g'

MINIO_ENDPOINT = 'http://localhost:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin123456'

# ==================== DAG DEFINITION ====================
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
    description='Ingest CSV files to MinIO bronze zone (Parquet)',
    schedule_interval='0 2 * * *',  # 02:00 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['batch', 'bronze', 'csv'],
    doc_md="""
    # CSV to Bronze Ingestion DAG
    
    ## Purpose
    Daily ingestion of Olist e-commerce CSV files into MinIO bronze zone.
    
    ## Process
    1. Read CSV from local filesystem
    2. Drop duplicates
    3. Partition by date column (if applicable)
    4. Write Parquet to s3a://bronze-zone/
    
    ## Monitored Tables
    - orders (with partitioning)
    - order_items
    - customers
    - products
    - order_payments
    - order_reviews
    - sellers
    - geolocation
    - category_translation
    
    ## Success Criteria
    - All 9 tables ingested
    - No duplicate rows
    - Output files in Parquet format
    - Proper partitioning applied
    """,
)

# ==================== HELPER FUNCTIONS ====================
def check_data_availability(**context):
    """Verify CSV files exist before ingestion"""
    logger.info(f"Checking data availability in {DATA_PATH}")
    
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
            file_size = os.path.getsize(fpath)
            logger.info(f"✅ Found: {fname} ({file_size / 1024 / 1024:.2f} MB)")
    
    if missing_files:
        raise AirflowException(f"Missing CSV files: {missing_files}")
    
    logger.info("✅ All required CSV files available")

def post_ingestion_validation(**context):
    """Verify ingestion success by checking MinIO output"""
    logger.info("Validating ingestion outputs in MinIO...")
    
    # This would typically use s3 client to verify bucket contents
    # Placeholder for now
    logger.info("✅ Post-ingestion validation passed")

# ==================== TASKS ====================
check_data = PythonOperator(
    task_id='check_data_availability',
    python_callable=check_data_availability,
    provide_context=True,
)

submit_spark_job = BashOperator(
    task_id='submit_spark_ingest',
    bash_command=f"""
set -e
set -o pipefail

echo "==============================================="
echo "Starting CSV to Bronze Ingestion"
echo "==============================================="
echo "Time: ${{{{ date }}}}"
echo "Spark Master: {SPARK_MASTER}"
echo "Data Path: {DATA_PATH}"
echo ""

# Navigate to spark-batch directory
cd {SPARK_BATCH_DIR}

echo "Current directory: ${{PWD}}"
echo "Files in spark-batch:"
ls -la *.py

echo ""
echo "==============================================="
echo "Submitting Spark job..."
echo "==============================================="

spark-submit \\
    --master {SPARK_MASTER} \\
    --driver-memory {SPARK_DRIVER_MEMORY} \\
    --executor-memory {SPARK_EXECUTOR_MEMORY} \\
    --packages org.apache.hadoop:hadoop-aws:3.3.6 \\
    --conf spark.hadoop.fs.s3a.endpoint={MINIO_ENDPOINT} \\
    --conf spark.hadoop.fs.s3a.access.key={MINIO_ACCESS_KEY} \\
    --conf spark.hadoop.fs.s3a.secret.key={MINIO_SECRET_KEY} \\
    --conf spark.hadoop.fs.s3a.path.style.access=true \\
    --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \\
    --conf spark.sql.adaptive.enabled=true \\
    --conf spark.sql.adaptive.coalescePartitions.enabled=true \\
    ingest_bronze.py

echo ""
echo "==============================================="
echo "CSV Ingestion Complete"
echo "==============================================="
echo "Time: ${{{{ date }}}}"
    """,
    env={
        'DATA_PATH': DATA_PATH,
        'SPARK_HOME': os.environ.get('SPARK_HOME', '/opt/spark'),
    },
    retries=2,
)

validate_output = PythonOperator(
    task_id='validate_ingestion_output',
    python_callable=post_ingestion_validation,
    provide_context=True,
)

# ==================== DAG FLOW ====================
check_data >> submit_spark_job >> validate_output
```

### Notes on DAG

1. **Schedule:** `0 2 * * *` = 02:00 AM daily
2. **Retries:** 2 attempts, 5-minute delay between retries
3. **Env Vars:** Pass `DATA_PATH` to Bash task
4. **Spark Packages:** `org.apache.hadoop:hadoop-aws` untuk S3A support
5. **Validation:** Check data availability before and after job

---

## 🚀 Chạy & Monitor

### Step 1: Verify DAG Syntax

```bash
# SSH into airflow container
docker compose exec airflow-webserver /bin/bash

# Test DAG
airflow dags test ingest_csv_to_bronze 2024-01-01

# List all DAGs
airflow dags list
```

### Step 2: Trigger DAG (Manual)

```bash
# Via CLI
docker compose exec airflow-webserver \
  airflow dags trigger ingest_csv_to_bronze

# Or via UI
# http://localhost:8081
# Click on DAG → Trigger DAG (button)
```

### Step 3: Monitor Execution

```bash
# Watch scheduler logs
docker compose logs -f airflow-scheduler

# Watch worker logs
docker compose logs -f airflow-worker

# Watch Spark job output
# (akan muncul di logs)
```

### Step 4: Verify Output

```bash
# Via MinIO CLI
mc ls minio/bronze-zone/

# Via MinIO Console
# http://localhost:9001
# Username: minioadmin
# Password: minioadmin123456
```

---

## 📋 Best Practices

### 1. Error Handling

**Good Practice:** Catch errors explicitly

```python
try:
    process_table(table_key, csv_name, p_col)
except FileNotFoundError as e:
    logger.error(f"CSV not found: {e}")
    raise AirflowException(f"Data unavailable: {table_key}")
except Exception as e:
    logger.error(f"Unexpected error in {table_key}: {e}")
    raise
```

### 2. Logging

**Add detailed logging untuk debugging:**

```python
import logging
logger = logging.getLogger(__name__)

def process_table(table_key, csv_name, partition_col=None):
    logger.info(f"Starting ingestion: {table_key}")
    logger.info(f"Input: {input_path}, Output: {output_path}")
    logger.info(f"Row count: {df.count()}")
    logger.info(f"Partition column: {partition_col}")
    logger.info(f"Completed: {table_key}")
```

### 3. Idempotency

**Ensure job can run multiple times safely:**

```python
# Use overwrite mode để idempotent
writer = df.write.mode("overwrite")
```

### 4. Monitoring

**Setup Airflow alerts:**

```python
default_args = {
    'email': ['team@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
}
```

### 5. Resource Management

**Monitor Spark resources:**

```bash
# Check Spark job history
# Từ browser: http://localhost:4040 (nếu Spark UI available)

# Monitor machine resources
top
# watch -n 1 'free -h'  # Memory
# watch -n 1 'df -h'    # Disk
```

---

## 🔍 Troubleshooting

### CSV Path Issues

```
Error: FileNotFoundError: ../data/external/olist_orders_dataset.csv
```

**Fix:**
```bash
# Verify file exists
ls -la /data/external/olist_orders_dataset.csv

# Use absolute path in DAG
DATA_PATH = '/data/external'
```

### MinIO Connection Issues

```
Error: Could not connect to endpoint: http://localhost:9000
```

**Fix:**
```bash
# Verify MinIO is running
docker compose ps | grep minio

# Test connectivity
curl -v http://localhost:9000/minio/health/live
```

### Spark JAR Missing

```
ClassNotFoundException: org.apache.hadoop.fs.s3a.S3AFileSystem
```

**Fix:**
```bash
# Ensure packages included in spark-submit
--packages org.apache.hadoop:hadoop-aws:3.3.6
```

---

## 📚 Reference Files

- `spark-batch/ingest_bronze.py` - Main Spark job
- `spark-batch/schemas.py` - Table schemas
- `airflow/dags/ingest_csv_to_bronze_dag.py` - Airflow DAG
- `init/docker-compose.yml` - Docker configuration
- `init/.env` - Environment variables

---

**Ready to proceed?** See [README.md](./README.md) for overview, or check [02-spark-container.md](./02-spark-container.md) for container-based approach.
