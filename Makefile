# =====================================================================
# Big Data - Lambda Architecture (Olist)
# Chạy tại thư mục dự án. Docker targets dùng init/docker-compose.yml.
# K8s targets dùng minikube + thư mục k8s/.
# =====================================================================

ifeq ($(OS),Windows_NT)
  DEVNULL := NUL
else
  DEVNULL := /dev/null
endif

NS              := bigdata
SPARK_PACKAGES  := org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.7.3
SILVER_APP      := /opt/project/spark-batch/transform_bronze_to_silver.py
GOLD_APP        := /opt/project/spark-batch/transform_silver_to_gold.py
STREAM_APP      := /opt/project/spark-streaming/kafka_consumer.py
STREAM_PACKAGES := org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.postgresql:postgresql:42.7.3

.PHONY: help install-deps \
        docker-build docker-up docker-down seed-postgres seed-streaming-tables register-connectors \
        run-silver run-gold run-streaming airflow-trigger pipeline-docker \
        logs-silver logs-gold \
        k8s-build-images k8s-code-configmaps k8s-up k8s-down seed-postgres-k8s \
        k8s-status k8s-test-minio k8s-test-kafka k8s-test-debezium k8s-test-postgres \
        k8s-test-mongo k8s-test-spark k8s-test-airflow k8s-test-all \
        k8s-logs-bronze k8s-logs-silver k8s-logs-gold k8s-logs-streaming \
        k8s-airflow-trigger k8s-deploy-streaming \
        k8s-build-springboot k8s-deploy-springboot k8s-port-forward-local \
        k8s-register-connectors

help:
	@echo "===== DOCKER ====="
	@echo "  make install-deps        - Cài Python deps (local spark)"
	@echo "  make docker-build        - Build image custom (airflow + debezium s3-sink)"
	@echo "  make docker-up           - Start toàn bộ stack (build nếu cần)"
	@echo "  make docker-down         - Stop stack"
	@echo "  make seed-postgres       - Nạp lại CSV -> Postgres (chạy 02-load.sql)"
	@echo "  make seed-streaming-tables - Tạo bảng output streaming (04-streaming-tables.sql)"
	@echo "  make register-connectors - Đăng ký Debezium source + S3 sink"
	@echo "  make run-silver          - Spark submit job Silver (trong spark-master)"
	@echo "  make run-gold            - Spark submit job Gold (3-sink)"
	@echo "  make run-streaming       - Spark submit job Streaming user-behavior (kafka:9094)"
	@echo "  make airflow-trigger     - Trigger DAG batch_pipeline"
	@echo "  make pipeline-docker     - register-connectors -> silver -> gold"
	@echo "  make logs-silver         - Xem print() silver khi chạy qua Airflow Docker"
	@echo "  make logs-gold           - Xem print() gold khi chạy qua Airflow Docker"
	@echo "===== KUBERNETES (minikube) ====="
	@echo "  make k8s-build-images    - Build image custom vào minikube"
	@echo "  make k8s-code-configmaps - Tạo configmap code (spark/services/dags/pg-init)"
	@echo "  make k8s-up              - Deploy toàn bộ lên minikube"
	@echo "  make k8s-register-connectors - Đăng ký Debezium source + S3 sink trên k8s"
	@echo "  make seed-postgres-k8s   - Nạp CSV -> Postgres trong cluster"
	@echo "  make k8s-status          - kubectl get pods"
	@echo "  make k8s-test-all        - Test lần lượt từng pod"
	@echo "  make k8s-down            - Xoá namespace"
	@echo "  make k8s-logs-bronze     - Log Debezium S3 Sink (CDC -> MinIO bronze)"
	@echo "  make k8s-logs-silver     - Log spark-worker: job transform_bronze_to_silver"
	@echo "  make k8s-logs-gold       - Log spark-worker: job transform_silver_to_gold"
	@echo "  make k8s-logs-streaming  - Log spark-worker: kafka_consumer streaming (follow)"
	@echo "  make k8s-airflow-trigger - Trigger DAG batch_pipeline trong cluster k8s"
	@echo "===== SPRINGBOOT (k8s) ====="
	@echo "  make k8s-build-springboot  - Build image bigdata-springboot -> minikube"
	@echo "  make k8s-deploy-springboot - Build + apply k8s/70-springboot.yaml"
	@echo "  make k8s-port-forward-local- In lệnh port-forward cho profile k8s-local"

# ---------------------------------------------------------------- local
install-deps:
	pip install -r spark-streaming/requirements.txt

# ---------------------------------------------------------------- docker
docker-build:
	cd init && docker compose build

docker-up:
	cd init && docker compose up -d --build

docker-down:
	cd init && docker compose down

# Nạp lại dữ liệu (initdb chỉ chạy lần đầu khi volume rỗng)
seed-postgres:
	docker exec -i bigdata-postgres psql -U postgres -d olist -f /docker-entrypoint-initdb.d/02-load.sql

# Tạo bảng output của luồng streaming (user_preference / user_recommendation).
# initdb chỉ chạy khi volume rỗng -> với stack đang chạy sẵn thì gọi target này thủ công.
seed-streaming-tables:
	docker exec -i bigdata-postgres psql -U postgres -d olist -f /docker-entrypoint-initdb.d/04-streaming-tables.sql

register-connectors:
	cd init && bash register-connector.sh
	cd init && bash register-s3-sink.sh

run-silver:
	docker exec -i spark-master /opt/spark/bin/spark-submit \
		--master spark://spark-master:7077 \
		--packages $(SPARK_PACKAGES) \
		$(SILVER_APP)

run-gold:
	docker exec -i spark-master /opt/spark/bin/spark-submit \
		--master spark://spark-master:7077 \
		--packages $(SPARK_PACKAGES) \
		$(GOLD_APP)

# Streaming user-behavior -> Postgres (broker INTERNAL kafka:9094). Ctrl+C để dừng.
# Chạy --master local[2]: driver tự chạy executor trong process ngay tại container spark-master,
# KHÔNG chiếm spark-worker -> batch (spark://spark-master:7077) chạy song song không bị block.
run-streaming:
	docker exec -i \
		-e KAFKA_BOOTSTRAP=kafka:9094 \
		-e PG_HOST=postgres \
		-e PG_URL=jdbc:postgresql://postgres:5432/olist \
		spark-master /opt/spark/bin/spark-submit \
		--master "local[2]" \
		--packages $(STREAM_PACKAGES) \
		$(STREAM_APP)

airflow-trigger:
	docker exec -it airflow-scheduler airflow dags trigger batch_pipeline

pipeline-docker: register-connectors run-silver run-gold

# Log print() của Airflow task silver/gold (deploy_mode=client -> log nằm trong airflow-scheduler)
logs-silver:
	docker exec airflow-scheduler bash -c \
	  "tail -f \$$(find /opt/airflow/logs/dag_id=batch_pipeline -name '*.log' -path '*/task_id=silver/*' 2>/dev/null | sort | tail -1) 2>/dev/null \
	   || echo 'Chua co log silver. Chay: make airflow-trigger roi thu lai.'"

logs-gold:
	docker exec airflow-scheduler bash -c \
	  "tail -f \$$(find /opt/airflow/logs/dag_id=batch_pipeline -name '*.log' -path '*/task_id=gold/*' 2>/dev/null | sort | tail -1) 2>/dev/null \
	   || echo 'Chua co log gold. Chay: make airflow-trigger roi thu lai.'"

# ---------------------------------------------------------------- k8s
# Build image custom trực tiếp vào docker daemon của minikube
k8s-build-images:
	@echo "Building images locally then loading into minikube..."
	docker build -t bigdata-debezium:2.4   -f init/Dockerfile        init
	docker build -t bigdata-airflow:2.11.2 -f init/airflow.Dockerfile init
	docker build -t bigdata-spark:3.5.1    -f init/spark.Dockerfile   init
	minikube image load bigdata-debezium:2.4
	minikube image load bigdata-airflow:2.11.2
	minikube image load bigdata-spark:3.5.1
	@echo "Images loaded into minikube."

# Tạo configmap chứa code (mount vào spark + airflow). pg-initdb chỉ gồm schema
# + replica-identity (KHÔNG có 02-load.sql để initdb không lỗi do thiếu /csv).
k8s-code-configmaps:
	kubectl -n $(NS) create configmap spark-batch-code --from-file=spark-batch/ \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create configmap spark-streaming-code --from-file=spark-streaming/ \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create configmap services-code \
		--from-file=services/mongodb_connect/mongo_connector.py \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create configmap airflow-dags --from-file=airflow/dags/ \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create configmap pg-initdb \
		--from-file=init/postgres-init/01-schema.sql \
		--from-file=init/postgres-init/03-replica-identity.sql \
		--from-file=init/postgres-init/04-streaming-tables.sql \
		--dry-run=client -o yaml | kubectl apply -f -

k8s-up:
	minikube status >$(DEVNULL) 2>&1 || minikube start --cpus=4 --memory=8192
	kubectl apply -f k8s/00-namespace.yaml
	kubectl apply -f k8s/01-secrets.yaml
	$(MAKE) k8s-build-images
	$(MAKE) k8s-code-configmaps
	kubectl apply -f k8s/10-minio.yaml
	kubectl apply -f k8s/11-mongodb.yaml
	kubectl apply -f k8s/20-kafka.yaml
	kubectl apply -f k8s/30-postgres.yaml
	kubectl apply -f k8s/40-debezium.yaml
	kubectl apply -f k8s/50-spark.yaml
	kubectl apply -f k8s/60-airflow.yaml
	@echo "⏳ Đợi pods Ready: kubectl -n $(NS) get pods -w"

k8s-register-connectors:
	$(eval POD := $(shell kubectl -n $(NS) get pod -l app=debezium-connect -o jsonpath='{.items[0].metadata.name}'))
	@echo "🚀 Đang chuyển script vào Pod: $(POD)..."
	kubectl -n $(NS) cp init/register-connector.sh $(POD):/tmp/register-connector.sh
	kubectl -n $(NS) cp init/register-s3-sink.sh $(POD):/tmp/register-s3-sink.sh
	@echo "⚙️ Đang thực thi đăng ký connector bên trong Pod (xử lý lỗi CRLF)..."
	kubectl -n $(NS) exec $(POD) -- sh -c "tr -d '\r' < /tmp/register-connector.sh > /tmp/clean-register-connector.sh"
	kubectl -n $(NS) exec $(POD) -- sh -c "tr -d '\r' < /tmp/register-s3-sink.sh > /tmp/clean-register-s3-sink.sh"
	kubectl -n $(NS) exec $(POD) -- chmod +x /tmp/clean-register-connector.sh /tmp/clean-register-s3-sink.sh
	kubectl -n $(NS) exec $(POD) -- sh -c "CONNECT_URL=http://localhost:8083 DB_HOSTNAME=postgres /tmp/clean-register-connector.sh"
	kubectl -n $(NS) exec $(POD) -- sh -c "CONNECT_URL=http://localhost:8083 /tmp/clean-register-s3-sink.sh"
	@echo "✅ Đã đăng ký xong!"

# Nạp CSV vào Postgres trong cluster: copy CSV vào pod rồi chạy 02-load.sql
seed-postgres-k8s:
	$(eval POD := $(shell kubectl -n $(NS) get pod -l app=postgres -o jsonpath='{.items[0].metadata.name}'))
	kubectl -n $(NS) exec $(POD) -- mkdir -p /csv
	kubectl -n $(NS) cp data/external $(POD):/csv-src
	kubectl -n $(NS) exec $(POD) -- sh -c 'cp /csv-src/*.csv /csv/'
	kubectl -n $(NS) cp init/postgres-init/02-load.sql $(POD):/tmp/02-load.sql
	kubectl -n $(NS) exec $(POD) -- psql -U postgres -d olist -f /tmp/02-load.sql

k8s-status:
	kubectl -n $(NS) get pods -o wide

k8s-down:
	kubectl delete namespace $(NS) --ignore-not-found

# ---------- test từng pod ----------
k8s-test-postgres:
	kubectl -n $(NS) exec deploy/postgres -- pg_isready -U postgres -d olist
	kubectl -n $(NS) exec deploy/postgres -- psql -U postgres -d olist -c "SELECT 'orders='||count(*) FROM orders;"

k8s-test-minio:
	kubectl -n $(NS) wait --for=condition=ready pod -l app=minio --timeout=120s
	kubectl -n $(NS) exec sts/minio -- ls -1 /data && echo "MinIO OK (buckets ở trên)"

k8s-test-kafka:
	kubectl -n $(NS) exec sts/kafka -- kafka-broker-api-versions --bootstrap-server localhost:9092 >$(DEVNULL) && echo "Kafka OK"
	kubectl -n $(NS) exec sts/kafka -- kafka-topics --bootstrap-server localhost:9092 --list

k8s-test-debezium:
	kubectl -n $(NS) exec deploy/debezium-connect -- curl -sf http://localhost:8083/connectors && echo " <- connectors OK"

k8s-test-mongo:
	kubectl -n $(NS) exec sts/mongodb -- mongosh --quiet --eval "db.adminCommand('ping')"

k8s-test-spark:
	kubectl -n $(NS) exec deploy/spark-master -- /opt/spark/bin/spark-submit --version
	kubectl -n $(NS) exec deploy/spark-master -- sh -c "ls /opt/project/spark-batch" && echo "Spark code mounted OK"

k8s-test-airflow:
	-kubectl -n $(NS) exec deploy/airflow-scheduler -- airflow jobs check --job-type SchedulerJob --hostname "$$(hostname)"
	kubectl -n $(NS) exec deploy/airflow-scheduler -- sh -c "airflow dags list | grep batch_pipeline" && echo "DAG loaded OK"

k8s-test-all: k8s-test-postgres k8s-test-minio k8s-test-kafka k8s-test-debezium k8s-test-mongo k8s-test-spark k8s-test-airflow
	@echo "✅ Đã test xong các pod"

# ---------- logs từng tiến trình ----------
# Bronze: Debezium S3 Sink Connector là thành phần ingest dữ liệu vào bronze-zone.
k8s-logs-bronze:
	kubectl -n $(NS) logs -f -l app=debezium-connect --tail=100

# Silver: deploy_mode=client -> driver chạy trong airflow-scheduler.
# print() của Python xuất hiện trong Airflow task log, không phải spark-worker.
# Target này exec vào scheduler và tail log file của task silver gần nhất.
k8s-logs-silver:
	kubectl -n $(NS) exec deploy/airflow-scheduler -- bash -c \
	  "tail -f \$$(find /opt/airflow/logs/dag_id=batch_pipeline -name '*.log' -path '*/task_id=silver/*' 2>/dev/null | sort | tail -1) 2>/dev/null \
	   || echo 'Chua co log silver. Chay: make airflow-trigger-k8s roi thu lai.'"

# Gold: tương tự silver, deploy_mode=client -> log nằm trong airflow-scheduler.
k8s-logs-gold:
	kubectl -n $(NS) exec deploy/airflow-scheduler -- bash -c \
	  "tail -f \$$(find /opt/airflow/logs/dag_id=batch_pipeline -name '*.log' -path '*/task_id=gold/*' 2>/dev/null | sort | tail -1) 2>/dev/null \
	   || echo 'Chua co log gold. Chay: make airflow-trigger-k8s roi thu lai.'"

# Streaming: kafka_consumer.py chạy trong pod spark-streaming riêng.
k8s-logs-streaming:
	kubectl -n $(NS) logs -f -l app=spark-streaming --tail=500

k8s-deploy-streaming:
	$(MAKE) k8s-code-configmaps
	kubectl apply -f k8s/75-spark-streaming.yaml
	@echo "Streaming pod deployed. Log: make k8s-logs-streaming"

k8s-airflow-trigger:
	kubectl -n $(NS) exec deploy/airflow-scheduler -- airflow dags trigger batch_pipeline

# ---------------------------------------------------------------- springboot k8s
# Build Docker image từ SpringBoot/ rồi load vào minikube (imagePullPolicy: Never)
k8s-build-springboot:
	docker build -t bigdata-springboot:latest SpringBoot/
	minikube image load bigdata-springboot:latest
	@echo "✅ bigdata-springboot:latest loaded into minikube"

# Build image + apply k8s manifest (Deployment + Service)
k8s-deploy-springboot: k8s-build-springboot
	kubectl apply -f k8s/70-springboot.yaml
	@echo "✅ springboot-app deployed. Xem log: kubectl -n $(NS) logs -f deploy/springboot-app"

# Hướng dẫn chạy Spring Boot + Frontend LOCAL, kết nối vào k8s pods qua port-forward.
# Không cần build Docker image. Yêu cầu: minikube đang chạy + namespace bigdata đã up.
k8s-port-forward-local:
	@echo "==================================================================="
	@echo " Chạy local (Spring + Frontend) <-> k8s pods (Postgres + Kafka)"
	@echo "==================================================================="
	@echo ""
	@echo "[Terminal 1] Port-forward Postgres:"
	@echo "  kubectl -n $(NS) port-forward svc/postgres 5433:5432"
	@echo ""
	@echo "[Terminal 2] Port-forward Kafka:"
	@echo "  kubectl -n $(NS) port-forward svc/kafka 9092:9092"
	@echo ""
	@echo "[Terminal 3] Spring Boot (profile k8s-local):"
	@echo "  cd SpringBoot && mvn spring-boot:run -Dspring-boot.run.profiles=k8s-local"
	@echo ""
	@echo "[Terminal 4] Frontend:"
	@echo "  cd services/product-web && npm install && npm run dev"
	@echo ""
	@echo "  Spring API : http://localhost:8085/api"
	@echo "  Frontend   : http://localhost:5173"
	@echo "==================================================================="
