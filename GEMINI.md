# Gemini.md

This file provides guidance to Gemini Code (Gemini.ai/code) when working with code in this repository.

## Project Overview

Lambda Architecture big data platform for an e-commerce system (Olist dataset). Source data lives in **PostgreSQL (OLTP)** and flows out via **Debezium CDC**. The initial OLTP load comes from the CSVs in `data/external/` (imported once by `init/postgres-init/*.sql`); continuous fake-insert from SpringBoot is a later phase.

Bronze ingestion is done by the **Debezium Confluent S3 Sink Connector** (not Spark). Gold-layer aggregations are written to **three sinks**: MinIO (`gold-zone`, parquet), the **local MongoDB container** (`bigdata-mongodb`), and **MongoDB Atlas** (skipped automatically when `MONGO_ATLAS_URI` is empty). The Spark streaming speed layer (user-behavior → next-product recommendation, sink to PostgreSQL) is a later phase — see `docs/chua-implement-phase-nay.md`.

## Common Commands

All commands are run from the project root (`Big-Data/`). See `docs/huong-dan-test.md` for the full end-to-end test guide.

```bash
# Infrastructure (builds custom images: debezium+s3sink, airflow+spark, spark+pymongo)
make docker-up            # cd init && docker compose up -d --build
make docker-down

# One-time / re-seed CSV -> Postgres (initdb runs automatically on empty volume)
make seed-postgres

# Register Debezium source + S3 sink connectors
make register-connectors

# Run batch Spark jobs inside the spark-master container (client mode)
make run-silver           # transform_bronze_to_silver.py
make run-gold             # transform_silver_to_gold.py  (writes to 3 sinks)

# Or orchestrate via Airflow
make airflow-trigger      # trigger DAG batch_pipeline

# Kubernetes (minikube)
make k8s-up               # build images + configmaps + apply k8s/
make seed-postgres-k8s
make k8s-test-all
make k8s-down
```

Spark application paths inside containers are under **`/opt/project`** (e.g. `/opt/project/spark-batch/transform_silver_to_gold.py`), with `PYTHONPATH=/opt/project` so jobs can `import services.mongodb_connect`.

## Architecture

### Medallion / Lambda Architecture

```
data/external/*.csv ──(init/postgres-init)──► PostgreSQL (OLTP, wal_level=logical)
                                                    │
                                          Debezium source connector
                                                    ▼
                              Kafka topics: olist_cdc.public.<table>
                                                    │
                                   Debezium Confluent S3 Sink (unwrap)
                                                    ▼
                              Bronze Zone (MinIO s3a://bronze-zone/cdc/olist_cdc.public.<table>/)
                                                    │
                                   Spark: transform_bronze_to_silver.py
                                                    ▼
                              Silver Zone (MinIO s3a://silver-zone/olist_unified_silver/)
                                                    │
                                   Spark: transform_silver_to_gold.py
                                                    ▼
                  Gold ──► MinIO s3a://gold-zone/<collection>/   (parquet)
                       ──► MongoDB local  (bigdata-mongodb, db olist_gold)
                       ──► MongoDB Atlas  (MONGO_ATLAS_URI; skipped if empty)
              Orchestration: Airflow DAG `batch_pipeline` (SparkSubmitOperator, cluster mode)
```

**Speed layer (later phase):** Kafka → `spark-streaming/kafka_consumer.py` → window aggregations → (planned) PostgreSQL. Not in the current batch flow.

### Key Directory Map

| Path | Purpose |
|------|---------|
| `init/docker-compose.yml` | Full infrastructure stack (custom builds for debezium/airflow/spark) |
| `init/.env` | All service credentials |
| `init/Dockerfile` | Debezium connect + Confluent S3 Sink plugin |
| `init/airflow.Dockerfile` | Airflow + JDK17 + Spark 3.5.1 + spark provider |
| `init/spark.Dockerfile` | apache/spark 3.5.1 + pymongo (gold driver) |
| `init/postgres-init/*.sql` | Schema + CSV COPY + REPLICA IDENTITY (Postgres seeding) |
| `init/register-connector.sh`, `init/register-s3-sink.sh` | Register Debezium source / S3 sink |
| `spark-batch/` | Batch PySpark jobs |
| `spark-streaming/` | Streaming PySpark jobs + Kafka producer (later phase) |
| `services/mongodb_connect/mongo_connector.py` | `MongoConnector` — PyMongo bulk upsert (local + Atlas) |
| `airflow/dags/batch_pipeline_dag.py` | TaskFlow DAG: ensure_connectors → wait_bronze → silver → gold |
| `data/external/` | Raw Olist CSV source files (9 tables) |
| `docs/` | Architecture docs, test guide, deferred-work doc (Vietnamese) |
| `k8s/` | Kubernetes manifests for minikube (namespace `bigdata`) |

### Spark Batch Pipeline (ordered execution)

Bronze is produced by the **S3 Sink connector**, not Spark. The Spark batch jobs are:

1. **`spark-batch/transform_bronze_to_silver.py`** — reads the unwrapped CDC parquet from `s3a://bronze-zone/cdc/olist_cdc.public.<table>/`, does CDC dedup (latest by `__ts_ms`, drop `__deleted`), converts Debezium micro-timestamps via `timestamp_micros()`, aggregates payments to order grain (avoids row multiplication), joins to a unified table at **order_item grain** with broadcast joins, applies basic DQ, and writes `s3a://silver-zone/olist_unified_silver/`.
2. **`spark-batch/transform_silver_to_gold.py`** — produces the 5 UC tables from `docs/data-view/gold-data-requirment.md` plus breakdown collections (SQL/Window/Pivot/UDF only; ML/GraphFrames columns are `null` TODO). Writes each collection to **MinIO + local Mongo + Atlas** via `write_to_gold()` reusing `MongoConnector.bulk_upsert()`.

`spark-batch/schemas.py` and `spark-batch/ingest_kafka_to_bronze.py` remain in the tree but are **no longer part of the batch flow** (kept for reference / streaming phase).

### MongoDB: three Gold sinks

Gold is written to MinIO and BOTH MongoDB targets. `MongoConnector` accepts any URI, so the same class drives the local container and Atlas. URIs come from env (`MONGO_LOCAL_URI`, `MONGO_ATLAS_URI`); an empty `MONGO_ATLAS_URI` is skipped so the pipeline runs before Atlas is configured. DB name `olist_gold`.

### CDC Flow

PostgreSQL has WAL logical replication (`wal_level=logical`); tables have `REPLICA IDENTITY FULL`. Debezium Connect (port 8083) publishes row changes to `olist_cdc.public.<table>` with `decimal.handling.mode=double`. The **Confluent S3 Sink** (same Connect cluster) consumes those topics with `value.converter.schemas.enable=true` (required for `ParquetFormat`), applies `ExtractNewRecordState` to flatten `payload.after`, and writes snappy parquet to `bronze-zone/cdc/...`. The `debezium` service must be on both `kafka-network` and `minio-network`.

### Infrastructure Ports

| Service | Port |
|---------|------|
| PostgreSQL (olist) | host 5433 → container 5432 (host map tránh PG native; trong network vẫn `postgres:5432`) |
| pgAdmin | 5050 |
| Kafka | 9092 (external) / 9094 (internal) |
| Kafka UI | 8080 |
| Debezium Connect | 8083 |
| Spark Master UI | 8082 |
| Spark Master RPC | 7077 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
| Airflow Webserver | 8081 |
| MongoDB | 27017 |

### Spark Submit Package Dependency

Batch jobs require hadoop-aws for S3A access to MinIO; passed via `--packages` (and set in code for local runs):
```
--packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.7.3
```
First run needs internet for Ivy to resolve these (cluster mode resolves on the worker).

## What Is Not Yet Implemented

See `docs/chua-implement-phase-nay.md` for the full list. Highlights:
- Streaming speed layer (user-behavior cleaning, next-product recommendation, sink → PostgreSQL)
- SpringBoot continuous fake-insert into PostgreSQL (CDC realtime demo)
- Gold ML/GraphFrames/NLP columns (churn, CLV, ALS recommend, sentiment, PageRank, fraud, delivery prediction, revenue_5min/hourly) — currently `null`
- Incremental (non-overwrite) Silver/Gold, Airflow retry/alert/SLA
- Grafana monitoring, real minikube validation, secret management, CI/CD
