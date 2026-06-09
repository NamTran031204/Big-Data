# =====================================================================
# Big Data - Lambda Architecture (Olist)
# Chạy tại thư mục dự án. Docker targets dùng init/docker-compose.yml.
# K8s targets dùng minikube + thư mục k8s/.
# =====================================================================

NS              := bigdata
SPARK_PACKAGES  := org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.7.3
SILVER_APP      := /opt/project/spark-batch/transform_bronze_to_silver.py
GOLD_APP        := /opt/project/spark-batch/transform_silver_to_gold.py

.PHONY: help install-deps \
        docker-build docker-up docker-down seed-postgres register-connectors \
        run-silver run-gold airflow-trigger pipeline-docker \
        k8s-build-images k8s-code-configmaps k8s-up k8s-down seed-postgres-k8s \
        k8s-status k8s-test-minio k8s-test-kafka k8s-test-debezium k8s-test-postgres \
        k8s-test-mongo k8s-test-spark k8s-test-airflow k8s-test-all

help:
	@echo "===== DOCKER ====="
	@echo "  make install-deps        - Cài Python deps (local spark)"
	@echo "  make docker-build        - Build image custom (airflow + debezium s3-sink)"
	@echo "  make docker-up           - Start toàn bộ stack (build nếu cần)"
	@echo "  make docker-down         - Stop stack"
	@echo "  make seed-postgres       - Nạp lại CSV -> Postgres (chạy 02-load.sql)"
	@echo "  make register-connectors - Đăng ký Debezium source + S3 sink"
	@echo "  make run-silver          - Spark submit job Silver (trong spark-master)"
	@echo "  make run-gold            - Spark submit job Gold (3-sink)"
	@echo "  make airflow-trigger     - Trigger DAG batch_pipeline"
	@echo "  make pipeline-docker     - register-connectors -> silver -> gold"
	@echo "===== KUBERNETES (minikube) ====="
	@echo "  make k8s-build-images    - Build image custom vào minikube"
	@echo "  make k8s-code-configmaps - Tạo configmap code (spark/services/dags/pg-init)"
	@echo "  make k8s-up              - Deploy toàn bộ lên minikube"
	@echo "  make seed-postgres-k8s   - Nạp CSV -> Postgres trong cluster"
	@echo "  make k8s-status          - kubectl get pods"
	@echo "  make k8s-test-all        - Test lần lượt từng pod"
	@echo "  make k8s-down            - Xoá namespace"

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

airflow-trigger:
	docker exec -it airflow-scheduler airflow dags trigger batch_pipeline

pipeline-docker: register-connectors run-silver run-gold

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
	kubectl -n $(NS) create configmap services-code \
		--from-file=services/mongodb_connect/mongo_connector.py \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create configmap airflow-dags --from-file=airflow/dags/ \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(NS) create configmap pg-initdb \
		--from-file=init/postgres-init/01-schema.sql \
		--from-file=init/postgres-init/03-replica-identity.sql \
		--dry-run=client -o yaml | kubectl apply -f -

k8s-up:
	minikube status >/dev/null 2>&1 || minikube start --cpus=4 --memory=8192
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
	kubectl -n $(NS) exec sts/kafka -- kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null && echo "Kafka OK"
	kubectl -n $(NS) exec sts/kafka -- kafka-topics --bootstrap-server localhost:9092 --list

k8s-test-debezium:
	kubectl -n $(NS) exec deploy/debezium-connect -- curl -sf http://localhost:8083/connectors && echo " <- connectors OK"

k8s-test-mongo:
	kubectl -n $(NS) exec sts/mongodb -- mongosh --quiet --eval "db.adminCommand('ping')"

k8s-test-spark:
	kubectl -n $(NS) exec deploy/spark-master -- /opt/spark/bin/spark-submit --version
	kubectl -n $(NS) exec deploy/spark-master -- sh -c "ls /opt/project/spark-batch" && echo "Spark code mounted OK"

k8s-test-airflow:
	kubectl -n $(NS) exec deploy/airflow-scheduler -- airflow jobs check --job-type SchedulerJob --hostname "$$(hostname)" || true
	kubectl -n $(NS) exec deploy/airflow-scheduler -- airflow dags list | grep batch_pipeline && echo "DAG loaded OK"

k8s-test-all: k8s-test-postgres k8s-test-minio k8s-test-kafka k8s-test-debezium k8s-test-mongo k8s-test-spark k8s-test-airflow
	@echo "✅ Đã test xong các pod"
