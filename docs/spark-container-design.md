# Báo Cáo Thiết Kế: Docker Container cho PySpark Batch & Streaming

**Phiên bản:** 1.0  
**Ngày:** 2026-05-23  
**Phạm vi:** Thiết kế Docker image và runtime topology cho `spark-batch` và `spark-streaming`  
**Ràng buộc cứng:** PySpark 3.5.8, stack hiện tại trong `init/docker-compose.yml`

---

## Mục Lục

1. [Phân Tích Vấn Đề Gốc Rễ](#1-phân-tích-vấn-đề-gốc-rễ)
2. [Quyết Định Kiến Trúc Image](#2-quyết-định-kiến-trúc-image)
3. [Thiết Kế Phân Lớp Docker Image](#3-thiết-kế-phân-lớp-docker-image)
4. [Thiết Kế Runtime Trigger](#4-thiết-kế-runtime-trigger)
5. [Thiết Kế Giao Tiếp Inter-container](#5-thiết-kế-giao-tiếp-inter-container)
6. [Triển Khai trên Kubernetes (Roadmap)](#6-triển-khai-trên-kubernetes-roadmap)

---

## 1. Phân Tích Vấn Đề Gốc Rễ

### 1.1 Tại Sao Windows Cần HADOOP_HOME

Khi PySpark thực thi, JVM của Spark cần tương tác với filesystem thông qua lớp trừu tượng **Hadoop FileSystem API**. Trên Linux, API này ánh xạ trực tiếp xuống POSIX system calls — không cần cài thêm gì. Trên Windows, kernel không hỗ trợ POSIX natively, nên Spark đòi hỏi `winutils.exe` — một binary giả lập các lệnh POSIX (`chmod`, `mkdir`, `ls`) để Spark có thể tạo temp directory và quản lý local file.

```
Windows path:
  Spark JVM → Hadoop FileSystem API → winutils.exe → Windows FS API

Linux path:
  Spark JVM → Hadoop FileSystem API → POSIX syscall → Linux Kernel
```

File `kafka_consumer.py` hiện hardcode đường dẫn này:
```python
os.environ["HADOOP_HOME"] = "C:\\hadoop"   # chỉ tồn tại trên Windows
os.environ["PATH"] += os.pathsep + "C:\\hadoop\\bin"
```

**Kết luận thiết kế:** Docker image chạy trên Linux kernel. Biến `HADOOP_HOME` và `winutils.exe` là **không cần thiết và phải loại bỏ** khỏi code khi containerize. Đây không phải workaround — đây là behavior đúng trên Linux.

### 1.2 Vấn Đề `spark.jars.packages` — Runtime Download

Code hiện tại dùng:
```python
.config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8,...")
```

Cơ chế này yêu cầu Spark kết nối Maven Central **lúc runtime** để tải JAR, giải nén, và nạp vào classpath. Đây là thiết kế phù hợp cho môi trường phát triển local nhưng có 3 vấn đề nghiêm trọng khi containerize:

| Vấn đề | Tác động |
|--------|----------|
| Cần internet khi container khởi động | Fail trong môi trường K8s production (thường air-gapped) |
| 30-60 giây overhead mỗi lần chạy | Airflow timeout nếu job khởi động chậm |
| Phụ thuộc tính khả dụng của Maven Central | Job fail nếu Maven Central down |

**Quyết định thiết kế:** JAR phải được **bake vào image lúc build**, không download lúc runtime. Chi phí: image nặng hơn ~100-200MB. Lợi ích: startup tức thì, không phụ thuộc network ngoài.

---

## 2. Quyết Định Kiến Trúc Image

### 2.1 Một Image hay Hai Image

Hai công việc — batch và streaming — chia sẻ runtime PySpark nhưng khác nhau về:

| Thành phần | spark-batch | spark-streaming |
|-----------|-------------|-----------------|
| PySpark 3.5.8 | Có | Có |
| Java 17 JRE | Có | Có |
| S3A JARs (MinIO) | Có | Có |
| Kafka Connector JARs | Không | Có |
| `kafka-python-ng` (Python) | Không | Có |
| `Faker` (mock data) | Không | Có |

Phương án **hai image riêng biệt** được chọn thay vì một image chung vì:
- Image streaming không cần Faker/kafka-python-ng trong môi trường production batch
- Tuân theo nguyên tắc **single responsibility** — mỗi image chỉ chứa đúng những gì nó cần
- Giảm attack surface và kích thước image production

### 2.2 Base Image: python:3.11-slim vs bitnami/spark

| Tiêu chí | `python:3.11-slim` | `bitnami/spark:3.5` |
|---------|-------------------|---------------------|
| Kích thước nền | ~130MB | ~800MB |
| Kiểm soát môi trường | Hoàn toàn | Hạn chế (Bitnami conventions) |
| Phù hợp Spark Standalone | Không (cần thêm) | Có sẵn |
| Phù hợp Spark on K8s | Có (flexible) | Có |
| PySpark version lock | Qua pip, dễ kiểm soát | Baked vào image tag |

**Chọn `python:3.11-slim`** vì dự án dùng `pip install pyspark==3.5.8` — khi cài PySpark qua pip, toàn bộ Spark binaries đi kèm trong package. Không cần cài Spark riêng. `bitnami/spark` phù hợp hơn cho mô hình Spark Standalone Cluster (Phương án 3 trong thảo luận kiến trúc), không phải cho mô hình container đơn mà thiết kế này hướng đến.

### 2.3 Chiến Lược Mount Code — Volume vs COPY

Hai cách đưa code Python vào container:

**COPY tại build time:**
```
Image chứa code → rebuild khi code thay đổi → image tag tương ứng với version code
```

**Volume mount tại runtime:**
```
Image chỉ chứa môi trường → code mount từ host → thay đổi code không cần rebuild
```

**Quyết định thiết kế:** Dùng **volume mount** trong giai đoạn phát triển (dev), chuyển sang **COPY** khi chuẩn bị deploy production/K8s. Lý do:

- Dev: code thay đổi liên tục, rebuild image mỗi lần thay đổi là không hợp lý
- Production/K8s: image phải self-contained, không phụ thuộc filesystem host. Mỗi image tag = một version code cụ thể, reproducible

---

## 3. Thiết Kế Phân Lớp Docker Image

### 3.1 Cấu Trúc Phân Lớp Chung

Docker build image theo từng lớp (layer), mỗi lớp được cache độc lập. Thứ tự lớp ảnh hưởng trực tiếp đến hiệu quả cache và thời gian rebuild.

```
┌─────────────────────────────────────────┐  ← Layer 5: Application code (thay đổi nhiều)
│  COPY . /opt/spark-batch/               │    Invalidate: khi code thay đổi
├─────────────────────────────────────────┤
│  Python packages (pip install)          │  ← Layer 4: Dependencies (thay đổi ít)
│  pyspark==3.5.8, kafka-python-ng...     │    Invalidate: khi requirements.txt thay đổi
├─────────────────────────────────────────┤
│  JAR files (wget từ Maven Central)      │  ← Layer 3: Runtime JARs (rất ít thay đổi)
│  hadoop-aws, aws-java-sdk, kafka...     │    Invalidate: khi cần đổi version JAR
├─────────────────────────────────────────┤
│  Java 17 JRE (apt-get install)          │  ← Layer 2: System runtime (gần như không đổi)
│  + wget                                 │    Invalidate: khi đổi JDK version
├─────────────────────────────────────────┤
│  python:3.11-slim (base image)          │  ← Layer 1: OS + Python (cố định)
└─────────────────────────────────────────┘
```

Nguyên tắc: **lớp ít thay đổi nhất nằm dưới cùng**. Khi code Python thay đổi, chỉ Layer 5 bị invalidate — 4 lớp còn lại vẫn dùng cache, tổng thời gian rebuild chỉ vài giây.

### 3.2 Image spark-batch

**Mục đích:** Chạy các job trong `spark-batch/` — đọc CSV/Kafka → transform → ghi Parquet vào MinIO.

**JAR cần thiết:**

| JAR | Version | Vai trò |
|-----|---------|---------|
| `hadoop-aws` | 3.3.4 | S3AFileSystem implementation — xử lý protocol `s3a://` |
| `aws-java-sdk-bundle` | 1.12.262 | AWS SDK dependency của hadoop-aws |

Version `hadoop-aws:3.3.4` được chọn vì đây là version Hadoop bundled trong Spark 3.5.x. Dùng version khác có thể gây xung đột classpath.

**Các thành phần KHÔNG cần:**
- Kafka JARs — batch job đọc CSV/ghi Parquet, không consume Kafka stream
- `Faker`, `kafka-python-ng` — chỉ dùng cho mock data generation ở streaming

### 3.3 Image spark-streaming

**Mục đích:** Chạy `kafka_consumer.py` — consume Kafka topic theo chế độ Structured Streaming, ghi kết quả lên MinIO.

**JAR cần thiết — phân tích dependency chain:**

```
spark-sql-kafka-0-10_2.12:3.5.0
    ├── spark-token-provider-kafka-0-10_2.12:3.5.0  (Kafka auth token)
    ├── kafka-clients:3.4.1                          (Kafka protocol implementation)
    └── commons-pool2:2.11.1                         (connection pooling)

hadoop-aws:3.3.4
    └── aws-java-sdk-bundle:1.12.262
```

Lý do phải liệt kê đủ dependency chain: `spark.jars.packages` tự resolve transitive dependencies qua Ivy. Khi bake JAR thủ công vào image, phải tự giải quyết dependency chain — không có gì tự động làm thay.

**Python packages bổ sung so với batch:**
- `kafka-python-ng==2.2.3` — pure Python Kafka client, dùng trong `producer.py` để gửi mock events
- `Faker==40.13.0` — sinh mock data trong `producer.py`
- `tzdata==2026.1` — timezone database, cần cho xử lý timestamp trong streaming window

`py4j` không cần khai báo riêng — được cài tự động cùng `pyspark`.

### 3.4 So Sánh Thành Phần Hai Image

```
spark-batch image (~900MB)          spark-streaming image (~950MB)
─────────────────────────────       ──────────────────────────────────
python:3.11-slim                    python:3.11-slim
Java 17 JRE                         Java 17 JRE
pyspark==3.5.8                      pyspark==3.5.8
hadoop-aws-3.3.4.jar        ←same→  hadoop-aws-3.3.4.jar
aws-java-sdk-bundle.jar     ←same→  aws-java-sdk-bundle.jar
                                    spark-sql-kafka-0-10.jar    ┐
                                    spark-token-provider.jar    │ Kafka
                                    kafka-clients-3.4.1.jar     ┤ JARs
                                    commons-pool2.jar           ┘
                                    kafka-python-ng==2.2.3
                                    Faker==40.13.0
                                    tzdata==2026.1
```

---

## 4. Thiết Kế Runtime Trigger

### 4.1 Use Case 1 — Chạy Container Trực Tiếp

Đây là trigger thủ công, phù hợp cho giai đoạn phát triển và kiểm thử.

**Cơ chế:**

```
Developer / CI Script
        │
        │  docker run (hoặc docker compose run)
        ▼
┌───────────────────────────────┐
│   spark-batch container       │
│   - Code được mount vào       │
│   - Chạy: python ingest.py    │
│   - Exit sau khi hoàn thành   │
└───────────────────────────────┘
        │
        │  s3a://
        ▼
    MinIO (minio-service:9000)
```

**Đặc điểm thiết kế:**
- Container có **lifecycle ngắn** — khởi động, chạy job, tắt. Không phải long-running service.
- Kết nối vào mạng `minio-network` và `kafka-network` của stack hiện tại để truy cập các service bằng tên DNS nội bộ.
- Biến cấu hình (endpoint, credentials) được truyền qua environment variables — không hardcode trong code.

**Entry point design:**
- Không dùng `CMD ["python", "ingest_bronze.py"]` cố định — sẽ hạn chế việc chạy các script khác từ cùng image.
- Dùng `ENTRYPOINT ["python"]` để có thể gọi `docker run spark-batch ingest_bronze.py` hoặc `docker run spark-batch transform_bronze_to_silver.py` từ cùng một image.

### 4.2 Use Case 2 — Airflow Trigger

Đây là trigger có lịch và orchestration, phù hợp cho production.

**Cơ chế:**

```
Airflow Scheduler (cron: 0 2 * * *)
        │
        │  SparkSubmitOperator / BashOperator
        ▼
Airflow Worker (container trong airflow-network)
        │
        │  Gọi spark-submit với --master spark://spark-master:7077
        │  HOẶC: docker exec vào spark-batch container
        ▼
Spark Job (Driver chạy, Workers thực thi)
        │
        │  s3a://
        ▼
    MinIO (minio-service:9000)
```

**Hai phương án trigger từ Airflow:**

**Phương án A — SparkSubmitOperator (Spark Standalone):**
Airflow submit job trực tiếp đến Spark Master. Yêu cầu triển khai thêm `spark-master` và `spark-worker` containers (Phương án 3 trong thảo luận kiến trúc). Airflow worker cần cài `apache-airflow-providers-apache-spark`.

**Phương án B — BashOperator với docker exec:**
Airflow worker gọi lệnh shell để chạy script trong container đã running. Đơn giản hơn, không cần Spark Standalone cluster. Phù hợp khi Spark chạy ở `local[*]` mode bên trong container.

| Tiêu chí | SparkSubmitOperator | BashOperator + docker exec |
|---------|--------------------|-----------------------------|
| Cần Spark Cluster | Có (spark-master + workers) | Không |
| Spark UI monitoring | Có | Không |
| Container complexity | Cao | Thấp |
| Phù hợp với mô hình hiện tại | Cần thêm service | Dùng được ngay |
| Migration lên K8s | Thẳng sang SparkKubernetesOperator | Cần refactor |

**Khuyến nghị:** Giai đoạn phát triển dùng **BashOperator**, giai đoạn production lên K8s dùng **SparkKubernetesOperator**.

**Luồng environment variables từ Airflow sang container:**

```
Airflow DAG
  └─ env_vars={
       "MINIO_ENDPOINT": "http://minio:9000",
       "MINIO_ACCESS_KEY": Variable.get("minio_key"),
       "KAFKA_BOOTSTRAP_SERVERS": "kafka:9094"
     }
        │
        ▼ inject vào shell environment
Container
  └─ Python code đọc os.getenv("MINIO_ENDPOINT")
```

Credentials **không được hardcode** trong DAG hay Dockerfile — luôn dùng Airflow Variables hoặc Connections để quản lý bí mật.

---

## 5. Thiết Kế Giao Tiếp Inter-container

### 5.1 Phân Tích Network Topology Hiện Tại

Stack hiện tại trong `init/docker-compose.yml` có **3 network riêng biệt**, mỗi network có mục đích isolation riêng:

```
kafka-network:
  ├── bigdata-postgres (CDC source)
  ├── kafka-zookeeper
  ├── kafka-broker
  ├── kafka-ui
  ├── debezium-connect
  └── pgadmin

minio-network:
  ├── minio-service
  └── mc-minio (init container)

airflow-network:
  ├── airflow-webserver
  ├── airflow-scheduler
  ├── airflow-worker
  ├── airflow-triggerer
  ├── airflow-redis
  └── airflow-postgres
```

**Vấn đề:** Spark containers cần truy cập cả 3 networks — MinIO để ghi data, Kafka để consume stream, Airflow network để nhận lệnh từ Airflow worker. Docker Compose hỗ trợ một container thuộc nhiều network. Spark containers phải được attach vào `kafka-network`, `minio-network`, và `airflow-network` đồng thời.

### 5.2 Giao Tiếp với MinIO (S3A Protocol)

MinIO expose 2 port:
- `:9000` — S3-compatible API (Spark dùng cái này qua `s3a://`)
- `:9001` — Web Console (chỉ dùng cho UI)

Từ bên trong `minio-network`, Spark truy cập MinIO qua hostname `minio` (tên service trong docker-compose):

```python
spark.config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
```

DNS resolution hoạt động vì Docker Compose tự động tạo DNS entry cho mỗi service trong cùng network. `minio` resolves thành IP nội bộ của container `minio-service`.

**Lưu ý quan trọng:** Code hiện tại dùng `http://localhost:9000` — đây là địa chỉ từ **host machine**. Bên trong container, `localhost` chỉ đến chính container đó, không phải MinIO container. **Phải đổi thành `http://minio:9000`** khi containerize.

Cấu hình S3A đầy đủ cần thiết:

```
fs.s3a.endpoint           = http://minio:9000      (nội bộ Docker network)
fs.s3a.access.key         = <từ env var>
fs.s3a.secret.key         = <từ env var>
fs.s3a.path.style.access  = true                   (MinIO không dùng virtual-hosted style)
fs.s3a.impl               = org.apache.hadoop.fs.s3a.S3AFileSystem
fs.s3a.connection.ssl.enabled = false              (MinIO dev không có TLS)
```

### 5.3 Giao Tiếp với Kafka

Kafka broker được cấu hình với **2 listener riêng biệt** trong docker-compose:

```yaml
KAFKA_LISTENERS: INTERNAL://0.0.0.0:9094,EXTERNAL://0.0.0.0:9092
KAFKA_ADVERTISED_LISTENERS: INTERNAL://kafka:9094,EXTERNAL://localhost:9092
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT
KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
```

Đây là cấu hình chuẩn cho Kafka trong Docker để phục vụ 2 loại client:

```
Host machine (developer):
  kafka-python, Kafka UI → localhost:9092 (EXTERNAL listener)

Containers trong kafka-network:
  Spark, Debezium, Spring Boot → kafka:9094 (INTERNAL listener)
```

**Kết luận thiết kế:** Spark streaming container phải dùng `kafka:9094`, không phải `localhost:9092`. Code hiện tại dùng `localhost:9092` — phải đổi.

Lý do có 2 listener: Kafka broker quảng bá địa chỉ kết nối cho client sau khi kết nối ban đầu (metadata response). Nếu chỉ có 1 listener dùng `kafka:9094`, client từ host machine sẽ nhận được địa chỉ `kafka:9094` trong metadata — địa chỉ này không resolve được từ ngoài Docker network → connection fail.

### 5.4 Sơ Đồ Giao Tiếp Tổng Thể

```
┌────────────────────────────────────────────────────────────────────┐
│                         Docker Host                                │
│                                                                    │
│  ┌──────────────────────┐    ┌─────────────────────────────────┐  │
│  │   airflow-network    │    │         kafka-network           │  │
│  │                      │    │                                 │  │
│  │  airflow-webserver   │    │  kafka-broker (:9094 internal)  │  │
│  │  airflow-scheduler   │    │  kafka-zookeeper                │  │
│  │  airflow-worker ─────┼────┼──► spark-batch  ◄──────────────┼──│
│  │  airflow-redis       │    │      container                  │  │
│  │  airflow-postgres    │    │                                 │  │
│  └──────────────────────┘    └──────────────┬──────────────────┘  │
│                                             │                     │
│                              ┌──────────────▼──────────────────┐  │
│                              │         minio-network           │  │
│                              │                                 │  │
│                              │  minio-service (:9000)          │  │
│                              │       ▲                         │  │
│                              │  spark-batch container ─────────┤  │
│                              │  spark-streaming container      │  │
│                              └─────────────────────────────────┘  │
│                                                                    │
│  Host ports (cho developer):                                      │
│    localhost:9092 → Kafka EXTERNAL listener                       │
│    localhost:9000 → MinIO S3 API                                  │
│    localhost:9001 → MinIO Console                                 │
│    localhost:8080 → Kafka UI                                      │
│    localhost:8081 → Airflow UI                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Spark containers cần thuộc 3 network:** `kafka-network` (Kafka access), `minio-network` (MinIO access), `airflow-network` (Airflow trigger).

### 5.5 Thay Đổi Code Bắt Buộc Khi Containerize

| File | Dòng | Thay đổi |
|------|------|---------|
| `kafka_consumer.py` | 7-8 | Xóa `HADOOP_HOME` và `PATH` assignment |
| `kafka_consumer.py` | 15 | Xóa `spark.jars.packages` — JAR đã baked vào image |
| `kafka_consumer.py` | 16-17 | Xóa `spark.driver.host=127.0.0.1` — không dùng trong container |
| `kafka_consumer.py` | 22-23 | Đổi `localhost:9000` → `minio:9000` |
| `kafka_consumer.py` | 51 | Đổi `localhost:9092` → `kafka:9094` |
| `ingest_bronze.py` | 9 | Đổi `http://localhost:9000` → `http://minio:9000` |
| `ingest_kafka_to_bronze.py` | 6 | Xóa `spark.jars.packages` |
| `ingest_kafka_to_bronze.py` | 7 | Đổi `localhost:9000` → `minio:9000` |
| `ingest_kafka_to_bronze.py` | 19 | Đổi `localhost:9092` → `kafka:9094` |

Tất cả giá trị cấu hình (endpoint, credentials) nên đọc từ environment variables thay vì hardcode, để cùng image chạy được ở cả môi trường dev (docker-compose) và production (K8s với Secrets).

---

## 6. Triển Khai trên Kubernetes (Roadmap)

*Phần này mô tả chiến lược migration sau khi code đã ổn định và chạy tốt trên Docker Compose. Không áp dụng trong giai đoạn hiện tại.*

### 6.1 Ánh Xạ Khái Niệm Docker → Kubernetes

| Docker Compose | Kubernetes equivalent |
|---------------|----------------------|
| Service (long-running) | Deployment + Service |
| Container chạy 1 lần | Job |
| Volume mount (code) | ConfigMap (nhỏ) / PersistentVolumeClaim (lớn) |
| Environment variables | ConfigMap + Secret |
| Network (docker network) | Namespace + NetworkPolicy |
| `docker compose run` | `kubectl create job` |

### 6.2 Spark on Kubernetes — Điểm Khác Biệt Quan Trọng

Trên Docker Compose (Phương án 3 — Spark Standalone), cần triển khai `spark-master` và `spark-worker` như các container chạy thường trực. Trên K8s, Spark có **chế độ native** không cần spark-master:

```
K8s API Server thay thế vai trò spark-master:

spark-submit --master k8s://https://<api-server>:6443

Khi job được submit:
  1. Driver Pod được tạo → chạy code Python
  2. Driver yêu cầu K8s API tạo Executor Pods
  3. K8s spawn N Executor Pods trên các Node
  4. Sau khi job xong, tất cả Pods tự xóa
```

Đây là sự khác biệt căn bản: Docker Compose cần workers **thường trực**, K8s tạo Executors **theo yêu cầu** và tự dọn dẹp. Tài nguyên chỉ bị chiếm khi job đang chạy.

### 6.3 Airflow Integration trên K8s

Khi cả Airflow và Spark chạy trên K8s, operator phù hợp là `SparkKubernetesOperator` từ provider `apache-airflow-providers-cncf-kubernetes`:

```
Airflow Scheduler (Pod)
    └─ SparkKubernetesOperator
           │  tạo SparkApplication CRD
           ▼
    Spark Operator (K8s controller)
           │  quản lý lifecycle
           ├─ tạo Driver Pod
           └─ Driver tạo Executor Pods
```

Yêu cầu: cài **Spark Operator** (Kubernetes controller) vào cluster. Operator này watch `SparkApplication` custom resources và quản lý lifecycle của Spark jobs.

### 6.4 Docker Image Reuse Strategy

Image được build cho Docker Compose **dùng lại được trên K8s** mà không cần thay đổi. Toàn bộ thay đổi nằm ở cấp orchestration (Airflow operator, K8s manifests), không phải image.

```
Dev (Docker Compose):
  docker run --network kafka-network spark-batch:v1.0 python ingest_bronze.py

Production (K8s):
  spark-submit --master k8s://https://... \
               --conf spark.kubernetes.container.image=registry/spark-batch:v1.0 \
               --conf spark.kubernetes.namespace=spark \
               ingest_bronze.py
```

Cùng một image `spark-batch:v1.0`, chỉ khác `--master` flag và cách đưa code vào container (volume mount vs image COPY).

### 6.5 Điều Kiện Tiên Quyết Trước Khi Migrate K8s

- [ ] Code đã chạy ổn trên Docker Compose (tất cả `localhost` đã được đổi)
- [ ] Không còn hardcode path Windows trong bất kỳ file nào
- [ ] Credentials được quản lý qua environment variables
- [ ] Image đã được push lên container registry (Docker Hub / private registry)
- [ ] K8s cluster có Spark Operator được cài đặt
- [ ] MinIO và Kafka đã migrate sang K8s (hoặc vẫn dùng external endpoint)

---

## Phụ Lục: Ma Trận Quyết Định Thiết Kế

| Quyết định | Lựa chọn | Lý do |
|-----------|---------|-------|
| Base image | `python:3.11-slim` | Kiểm soát hoàn toàn, PySpark qua pip |
| Số lượng image | 2 image riêng | Single responsibility, kích thước tối ưu |
| JAR strategy | Baked vào image | Không phụ thuộc internet lúc runtime |
| Code strategy | Volume mount (dev) / COPY (prod) | Linh hoạt dev, reproducible prod |
| Airflow integration | BashOperator (hiện tại) → SparkKubernetesOperator (K8s) | Phù hợp từng giai đoạn |
| Network | Multi-network attachment | Truy cập Kafka + MinIO + Airflow |
| hadoop-aws version | 3.3.4 | Match Spark 3.5.x bundled Hadoop |
| Kafka client | spark-sql-kafka 3.5.0, Scala 2.12 | Match Spark 3.5.x Scala version |
