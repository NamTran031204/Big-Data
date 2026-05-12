# Deploy Local Guide Template

This template is used by the skill to generate `k8s/deploy-local.md`.
Sections marked with `{{PLACEHOLDER}}` are replaced with project-specific values.

---

# 🚀 Hướng dẫn triển khai Minikube — Dự án Big Data

## Yêu cầu hệ thống

| Thành phần | Phiên bản | Kiểm tra |
|---|---|---|
| Docker Desktop | Latest | `docker version` |
| Minikube | >= 1.30 | `minikube version` |
| kubectl | >= 1.27 | `kubectl version --client` |
| Python | >= 3.8 | `python --version` |

## 1. Khởi tạo Minikube

```bash
# Khởi động Minikube với Docker driver
minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=30g

# Kiểm tra cluster
kubectl cluster-info
kubectl get nodes

# Bật addons cần thiết
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable storage-provisioner
```

## 2. Tạo Namespace và Secrets

```bash
# Tạo namespace
kubectl apply -f k8s/namespace.yaml

# Tạo secrets từ env files
# (Hoặc chạy script: ./k8s/scripts/create-secrets.sh)
kubectl apply -f k8s/secrets/ -n bigdata
kubectl apply -f k8s/configmaps/ -n bigdata
```

## 3. Triển khai theo thứ tự

Thứ tự rất quan trọng — các service phụ thuộc cần khởi động trước.

### 3.1. Storage (PersistentVolumeClaims)

```bash
kubectl apply -f k8s/storage/ -n bigdata
kubectl get pvc -n bigdata
```

### 3.2. Infrastructure Layer

```bash
# PostgreSQL (phải lên trước vì Debezium phụ thuộc)
kubectl apply -f k8s/infrastructure/postgres/ -n bigdata
kubectl wait --for=condition=ready pod -l app=postgres -n bigdata --timeout=120s

# Kafka + Zookeeper
kubectl apply -f k8s/infrastructure/kafka/ -n bigdata
kubectl wait --for=condition=ready pod -l app=zookeeper -n bigdata --timeout=120s
kubectl wait --for=condition=ready pod -l app=kafka -n bigdata --timeout=120s

# MongoDB
kubectl apply -f k8s/infrastructure/mongodb/ -n bigdata
kubectl wait --for=condition=ready pod -l app=mongodb -n bigdata --timeout=120s

# MinIO
kubectl apply -f k8s/infrastructure/minio/ -n bigdata
kubectl wait --for=condition=ready pod -l app=minio -n bigdata --timeout=120s
```

### 3.3. Pipeline Layer

```bash
# Debezium (Kafka Connect)
kubectl apply -f k8s/pipeline/debezium/ -n bigdata
kubectl wait --for=condition=ready pod -l app=debezium -n bigdata --timeout=120s

# Spark RBAC (required before Spark pods)
kubectl apply -f k8s/pipeline/spark/spark-rbac.yaml -n bigdata

# Spark Streaming (runs 24/7)
kubectl apply -f k8s/pipeline/spark/spark-streaming-deployment.yaml -n bigdata

# Airflow
kubectl apply -f k8s/pipeline/airflow/ -n bigdata
```

### 3.4. Monitoring Layer

```bash
# Prometheus
kubectl apply -f k8s/monitoring/prometheus/ -n bigdata

# Grafana
kubectl apply -f k8s/monitoring/grafana/ -n bigdata
```

### 3.5. Application Services

```bash
# Java Service (Spring Boot)
kubectl apply -f k8s/services/java-service/ -n bigdata
```

## 4. Đăng ký Debezium Connectors

Sau khi Debezium pod đã sẵn sàng:

```bash
# Port-forward Debezium REST API
kubectl port-forward svc/debezium-service 8083:8083 -n bigdata &

# Đăng ký Source connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @k8s/pipeline/debezium/connectors/source-postgres.json

# Đăng ký Sink connector (S3 → MinIO)
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @k8s/pipeline/debezium/connectors/sink-s3-bronze.json

# Kiểm tra
curl -s http://localhost:8083/connectors | jq .
```

## 5. Truy cập các UI

```bash
# Mở tất cả UI cần thiết
minikube service grafana-service -n bigdata    # Grafana
minikube service kafka-ui-service -n bigdata   # Kafka UI
minikube service minio-service -n bigdata      # MinIO Console
minikube service airflow-service -n bigdata    # Airflow
```

Hoặc dùng port-forward:

```bash
kubectl port-forward svc/grafana-service 3000:3000 -n bigdata &
kubectl port-forward svc/minio-service 9001:9001 -n bigdata &
kubectl port-forward svc/kafka-ui-service 8080:8080 -n bigdata &
```

## 6. Kiểm tra hệ thống

```bash
# Tổng quan tất cả pods
kubectl get pods -n bigdata -o wide

# Xem logs của một service
kubectl logs -f deployment/debezium-connect -n bigdata
kubectl logs -f deployment/spark-streaming -n bigdata

# Xem events
kubectl get events -n bigdata --sort-by='.lastTimestamp'
```

## 7. Teardown (Dọn dẹp)

```bash
# Xóa tất cả resources trong namespace
kubectl delete namespace bigdata

# Hoặc xóa từng layer (ngược thứ tự deploy)
kubectl delete -f k8s/services/ -n bigdata
kubectl delete -f k8s/monitoring/ -n bigdata
kubectl delete -f k8s/pipeline/ -n bigdata
kubectl delete -f k8s/infrastructure/ -n bigdata
kubectl delete -f k8s/storage/ -n bigdata
kubectl delete -f k8s/secrets/ -n bigdata
kubectl delete -f k8s/namespace.yaml

# Dừng Minikube
minikube stop

# Xóa hoàn toàn cluster (kể cả data)
minikube delete
```

## 8. Monitoring Commands

```bash
# Xem resource usage
kubectl top pods -n bigdata
kubectl top nodes

# Xem Spark Streaming liên tục
kubectl logs -f deployment/spark-streaming -n bigdata --tail=50

# Xem Kafka consumer lag
kubectl exec -it kafka-0 -n bigdata -- \
  kafka-consumer-groups --bootstrap-server localhost:9092 --describe --all-groups

# Xem MinIO Bronze data
kubectl exec -it deployment/minio -n bigdata -- \
  mc ls local/bigdata/bronze/ --recursive | head -20
```

## Troubleshooting

| Vấn đề | Lệnh kiểm tra | Giải pháp |
|---|---|---|
| Pod CrashLoopBackOff | `kubectl describe pod <name> -n bigdata` | Xem Events + container logs |
| PVC Pending | `kubectl get pvc -n bigdata` | Kiểm tra StorageClass |
| Service không truy cập được | `kubectl get svc -n bigdata` | Dùng `minikube service` thay port-forward |
| Minikube hết RAM | `minikube stop && minikube start --memory=10240` | Tăng memory allocation |
| Image pull error | `minikube image load <image>` | Load image trực tiếp vào Minikube |
