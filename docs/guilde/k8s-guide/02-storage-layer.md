# Phần 2: Xây Dựng Hệ Lưu Trữ (Storage Layer - MongoDB & MinIO)

Chúng ta nhận ra cả MongoDB và MinIO (S3 Object Storage) trong Big Data DataLake hay Database đều cần ghi dữ liệu *nhiều và không được phép mất*.

### 1. Dữ liệu trên K8s hoạt động ra sao?

Cả hai trong `docker-compose.yml` đều định nghĩa volume: `mongodb_data:/data/db` và `./data/minio:/data` qua volume mapping.

Trong K8s:
- Chúng ta yêu cầu K8s "cấp thẻ bộ nhớ" qua **PersistentVolumeClaim (PVC)**.
- K8s sẽ tự động cấp một Volume thật sự cho dự án thông qua chế độ `StorageClass` của cụm Minikube/Cluster.

## MongoDB (Database Metastore)
Khi chạy trên production, bạn hoàn toàn có thể tìm 1 **Helm Chart** từ bên thứ 3. Tuy nhiên, việc tự viết sẽ mang tính học thuật cao nhất.
Vì Mongo *cần trạng thái*, K8s Component phù hợp sẽ là: `StatefulSet`.

### Bước 1: Khởi tạo biến nhạy cảm (K8s Secret)

Ở Compose bạn truyền từ file `.env` qua `${MONGO_PASSWORD}`.
Trong K8s, ta "nén" nó vào 1 Object Secret. Tạo file `k8s-guide/manifests/storage/mongodb-secret.yaml` và áp dụng lệnh:
```sh
kubectl apply -f manifests/storage/mongodb-secret.yaml
```

### Bước 2: Tạo Service (K8s Service)

Service giống như "cổng router nội bộ". Service giúp các Pod DB có tên miền nội bộ (VD: `mongodb.default.svc.cluster.local`) để dự án có thể gọi thay vì gọi IP ảo liên tục bị đổi. Tạo file `k8s-guide/manifests/storage/mongodb-service.yaml` và áp dụng lệnh:
```sh
kubectl apply -f manifests/storage/mongodb-service.yaml
```

### Bước 3: Tạo ổ đĩa và StatefulSet MongoDB

Giờ ta sẽ đưa `container mongo:7.0` lên K8s. File này sẽ kèm theo cả yêu cầu cấp ổ đĩa. Tạo file `k8s-guide/manifests/storage/mongodb-statefulset.yaml`. Trọng tâm: Ta dùng StatefulSet cùng thuộc tính `volumeClaimTemplates` có dung lượng (ví dụ 5Gi) để cấp phát `mongodb_data`. Áp dụng lệnh:
```sh
kubectl apply -f manifests/storage/mongodb-statefulset.yaml
```

## MinIO (Object Storage Data Lake)

Trong `docker-compose.yml`, MinIO cực kỳ đặc biệt với các thuộc tính:
```yaml
ports:
  - "9000:9000" # API
  - "9001:9001" # Web UI
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
deploy: limits ...
```
K8s có cách dịch 1:1 cho tất cả.

### Bước 4: Tạo tài khoản MinIO qua K8s Secret & Service

Tương tự MongoDB, ta cần `minio-secret.yaml` cho `MINIO_ROOT_USER`, cấu hình Storage và `minio-service.yaml` trỏ tới `9000` (API) & `9001` (Admin Console). Lưu ý rằng Service được cấu hình type là `NodePort` nếu bạn muốn test truy cập MinIO từ trình duyệt localhost (như lúc xài Compose `localhost:9001`).

```sh
kubectl apply -f manifests/storage/minio-secret.yaml
kubectl apply -f manifests/storage/minio-service.yaml
```

### Bước 5: Cấu hình giới hạn Resource & Check Sức Khỏe cho MinIO StatefulSet

Tại file `k8s-guide/manifests/storage/minio-statefulset.yaml`, bạn sẽ gặp 2 khái niệm mới thay thế cho Compose:
1. `livenessProbe` sẽ chạy curl check thay cho `healthcheck` của Docker compose. Nó giết Pod nếu MinIO đơ.
2. Nút thắt giới hạn CPU/Ram (Kế thừa từ cụm cày Data): 4GB RAM + 2 CPUs (cực kỳ tốt thực tế) bằng `resources.limits / requests`.

```sh
kubectl apply -f manifests/storage/minio-statefulset.yaml
```

---

*Lướt ngang thử xem các Component chạy ổn định chưa nha:*
```bash
kubectl get pods
kubectl get pvc
```
Nếu Pod báo `Running` sau 1-2 phút, bạn có thể gọi port mapping để thử Console của MinIO:
```bash
# Minikube sẽ tự tạo ra tunel HTTP tới K8s Service NodePort
minikube service minio-service
```
Hoặc dùng port-forward tĩnh:
```bash
kubectl port-forward svc/minio-service 9001:9001
```
Trình duyệt của bạn sẽ vào được giao diện MinIO y như file Docker Compose!

Phần tiếp theo, chúng ta vươn tới trái tim của Streaming (Event pipeline): [Phần 3: Hệ Sinh Thái Kafka (Zookeeper, Kafka, UI)](03-message-broker.md).