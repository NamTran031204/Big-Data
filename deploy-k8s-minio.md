# Hướng dẫn triển khai `minio` và `mc` từ Docker Compose lên Kubernetes

Tài liệu này bám theo cấu hình hiện có trong `init/docker-compose.yml`, cụ thể là 2 service:

- `init/docker-compose.yml:62` — `minio`
- `init/docker-compose.yml:95` — `mc`

Mục tiêu là chuyển 2 service này sang Kubernetes khi bạn đang dùng **Minikube** và mới bắt đầu học K8s.

---

## 1. Ý tưởng triển khai trên Kubernetes

Trong `docker-compose.yml` của bạn:

- `minio` là service chính, chạy lâu dài
- `mc` dùng để chạy script init bucket rồi thoát

Khi đổi sang Kubernetes, cách làm phù hợp là:

- `minio` → dùng **Deployment + Service + PersistentVolumeClaim**
- `mc` → dùng **Job** để chạy script một lần

Đây là mapping rất quan trọng giữa Docker Compose và K8s:

- container chạy lâu dài → `Deployment`
- expose port → `Service`
- lưu dữ liệu → `PersistentVolumeClaim`
- chạy script khởi tạo một lần → `Job`

---

## 2. Trích từ Docker Compose hiện tại

Trong `init/docker-compose.yml`, phần MinIO hiện tại có các điểm chính:

- image: `minio/minio:RELEASE.2025-06-13T11-33-47Z`
- ports: `9000`, `9001`
- env:
  - `MINIO_ROOT_USER`
  - `MINIO_ROOT_PASSWORD`
  - `MINIO_PROMETHEUS_AUTH_TYPE=public`
- volume dữ liệu: `minio-data:/data`
- command: `server /data --console-address ":9001"`
- healthcheck: `http://localhost:9000/minio/health/live`

Phần `mc` có:

- image: `minio/mc:latest`
- mount script `./scripts/init-bucket.sh`
- chạy `/bin/sh /scripts/init-bucket.sh`
- phụ thuộc vào `minio` healthy

Trong Kubernetes không có `depends_on` giống Compose, nên script init cần tự đợi MinIO sẵn sàng.

---

## 3. Cấu trúc file nên tạo

Bạn nên tạo một thư mục ví dụ như:

```text
k8s/minio/
```

và đặt các file sau:

1. `secret.yaml`
2. `pvc.yaml`
3. `deployment.yaml`
4. `service.yaml`
5. `mc-script-configmap.yaml`
6. `mc-job.yaml`

Nếu chưa muốn tách thư mục, bạn cũng có thể để các file này ở root project.

---

## 4. Secret cho tài khoản MinIO

File `secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: minio-secret
type: Opaque
stringData:
  MINIO_ROOT_USER: minioadmin
  MINIO_ROOT_PASSWORD: minioadmin123
```

### Giải thích

Trong Docker Compose, bạn đang dùng:

```yaml
environment:
  MINIO_ROOT_USER: ${MINIO_ROOT_USER}
  MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
```

Trong Kubernetes, cách chuẩn hơn là đưa các giá trị này vào `Secret`.

> Sau này bạn nên thay `minioadmin` và `minioadmin123` bằng giá trị thật của dự án.

---

## 5. PersistentVolumeClaim cho dữ liệu MinIO

File `pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

### Giải thích

PVC này tương đương với volume:

```yaml
minio-data:/data
```

trong `init/docker-compose.yml:73-75`.

Nó giúp dữ liệu MinIO không mất khi Pod bị restart hoặc recreate.

---

## 6. Deployment cho MinIO

File `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: minio/minio:RELEASE.2025-06-13T11-33-47Z
          args:
            - server
            - /data
            - --console-address
            - ":9001"
          envFrom:
            - secretRef:
                name: minio-secret
          env:
            - name: MINIO_PROMETHEUS_AUTH_TYPE
              value: "public"
          ports:
            - containerPort: 9000
            - containerPort: 9001
          volumeMounts:
            - name: minio-data
              mountPath: /data
          livenessProbe:
            httpGet:
              path: /minio/health/live
              port: 9000
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 20
            failureThreshold: 3
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2"
              memory: "4Gi"
      volumes:
        - name: minio-data
          persistentVolumeClaim:
            claimName: minio-data-pvc
```

### Giải thích

Deployment này bám trực tiếp theo cấu hình Compose:

- `image` giống `init/docker-compose.yml:63`
- `args` giống `init/docker-compose.yml:76`
- `envFrom` thay cho `${MINIO_ROOT_USER}` và `${MINIO_ROOT_PASSWORD}`
- `MINIO_PROMETHEUS_AUTH_TYPE=public` giống `init/docker-compose.yml:72`
- `livenessProbe` tương đương phần `healthcheck` ở `init/docker-compose.yml:77-82`
- `resources` chuyển từ phần `deploy.resources` ở `init/docker-compose.yml:86-93`

---

## 7. Service cho MinIO

File `service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: minio-service
spec:
  selector:
    app: minio
  ports:
    - name: api
      port: 9000
      targetPort: 9000
    - name: console
      port: 9001
      targetPort: 9001
  type: NodePort
```

### Giải thích

Service này thay cho phần `ports` trong Docker Compose.

Nhờ Service, các Pod khác trong cluster có thể gọi MinIO bằng hostname nội bộ:

```text
minio-service:9000
```

---

## 8. ConfigMap chứa script `init-bucket.sh`

Trong Compose, `mc` mount file:

- `init/docker-compose.yml:106` — `./scripts/init-bucket.sh:/scripts/init-bucket.sh:ro`

Sang Kubernetes, cách đơn giản nhất là đưa script vào `ConfigMap`.

File `mc-script-configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: minio-init-script
data:
  init-bucket.sh: |
    #!/bin/sh
    set -e

    until mc alias set myminio http://minio-service:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"; do
      echo "Waiting for MinIO..."
      sleep 5
    done

    mc mb myminio/my-bucket || true
    mc anonymous set public myminio/my-bucket || true

    echo "MinIO bucket init completed."
```

### Giải thích

Ở đây có 2 ý rất quan trọng:

1. `mc` không gọi `http://minio:9000` như trong Compose nữa, mà nên gọi qua `Service`:

```text
http://minio-service:9000
```

2. Vì Kubernetes không có `depends_on`, script phải tự đợi MinIO sẵn sàng bằng vòng lặp `until ... sleep 5`.

> `my-bucket` chỉ là ví dụ. Khi có nội dung thật của `init/scripts/init-bucket.sh`, bạn nên thay cho đúng bucket, policy và logic init của dự án.

---

## 9. Job cho `mc`

File `mc-job.yaml`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: minio-mc-init
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
        - name: mc
          image: minio/mc:latest
          command: ["/bin/sh", "/scripts/init-bucket.sh"]
          envFrom:
            - secretRef:
                name: minio-secret
          volumeMounts:
            - name: init-script
              mountPath: /scripts
      volumes:
        - name: init-script
          configMap:
            name: minio-init-script
            defaultMode: 0755
```

### Giải thích

`mc` trong dự án của bạn không phải service chạy mãi. Nó chỉ chạy script init rồi kết thúc.

Vì vậy trên K8s nên dùng `Job` thay vì `Deployment`.

Job này sẽ:

- dùng image `minio/mc:latest`
- mount script từ `ConfigMap`
- lấy credential từ `Secret`
- chạy script init bucket
- nếu thất bại thì thử lại theo `restartPolicy: OnFailure`

---

## 10. Thứ tự triển khai

Chạy theo thứ tự sau:

```bash
kubectl apply -f secret.yaml
kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

Kiểm tra MinIO đã chạy chưa:

```bash
kubectl get pods
kubectl get svc
kubectl logs deployment/minio
```

Khi MinIO đã ổn, apply tiếp phần `mc`:

```bash
kubectl apply -f mc-script-configmap.yaml
kubectl apply -f mc-job.yaml
```

Kiểm tra Job:

```bash
kubectl get jobs
kubectl get pods
kubectl logs job/minio-mc-init
```

---

## 11. Cách truy cập MinIO từ máy local

Cách dễ nhất khi dùng Minikube là `port-forward`:

```bash
kubectl port-forward svc/minio-service 9000:9000 9001:9001
```

Sau đó mở:

- Console: `http://localhost:9001`
- API: `http://localhost:9000`

Đăng nhập bằng:

- user: `minioadmin`
- password: `minioadmin123`

---

## 12. Giải thích luồng hoạt động hoàn chỉnh

Sau khi triển khai, hệ thống hoạt động như sau:

1. Kubernetes tạo Pod MinIO từ `Deployment`
2. Pod MinIO mount volume vào `/data`
3. `Service` tên `minio-service` expose MinIO trong cluster
4. `Job` `minio-mc-init` được tạo
5. `mc` trong Job đợi MinIO sẵn sàng
6. `mc` kết nối đến `http://minio-service:9000`
7. `mc` tạo bucket và cấu hình policy nếu cần
8. Job hoàn tất và dừng

Đây là cách triển khai rất điển hình trong Kubernetes cho mô hình “service chính + script khởi tạo một lần”.

---

## 13. Điểm khác giữa Docker Compose và Kubernetes

### Docker Compose

Bạn có thể dùng:

```yaml
depends_on:
  minio:
    condition: service_healthy
```

### Kubernetes

Kubernetes không có `depends_on` kiểu này.

Thay vào đó:

- hoặc ứng dụng phải tự retry
- hoặc script init phải tự chờ bằng `until ... sleep ...`

Vì vậy phần đợi MinIO trong script `mc` là bắt buộc nếu muốn chạy ổn định.

---

## 14. Còn volume `./config` trong Compose thì sao?

Trong Compose của bạn có:

- `init/docker-compose.yml:75` — `./config:/root/.minio`
- `init/docker-compose.yml:108` — `./config:/config`

Hiện trong hướng dẫn này mình **chưa chuyển phần `./config` sang K8s**, vì còn phụ thuộc nội dung thật của script `init/scripts/init-bucket.sh`.

Có 2 trường hợp:

### Trường hợp 1: script chỉ tạo bucket

Nếu script chỉ:

- cấu hình alias
- tạo bucket
- set policy

thì bạn **không cần mount `/config`** trên Kubernetes.

### Trường hợp 2: script có ghi file vào `/config`

Nếu script thật sự tạo file như `access.txt` hoặc lưu thông tin cấu hình, thì trên K8s bạn cần thêm volume riêng cho `/config`, ví dụ:

- `emptyDir` nếu chỉ cần dùng tạm
- hoặc `PersistentVolumeClaim` nếu muốn giữ file sau khi Pod/Job kết thúc

Muốn làm chính xác phần này, bạn cần xem nội dung file:

```text
init/scripts/init-bucket.sh
```

---

## 15. Các lệnh kiểm tra quan trọng

### Xem Pod

```bash
kubectl get pods
```

### Xem Service

```bash
kubectl get svc
```

### Xem Job

```bash
kubectl get jobs
```

### Xem log MinIO

```bash
kubectl logs deployment/minio
```

### Xem log Job `mc`

```bash
kubectl logs job/minio-mc-init
```

### Xem chi tiết Pod nếu lỗi

```bash
kubectl describe pod <pod-name>
```

---

## 16. Những lỗi hay gặp

### Pod MinIO không chạy

Kiểm tra:

```bash
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Không truy cập được MinIO

Nguyên nhân thường là:

- quên `port-forward`
- Pod chưa sẵn sàng
- Service sai port

### Job `mc` bị lỗi

Nguyên nhân thường là:

- MinIO chưa sẵn sàng
- sai username/password
- script init bucket chưa đúng

Xem log bằng:

```bash
kubectl logs job/minio-mc-init
```

### Dữ liệu bị mất khi restart

Nguyên nhân là chưa mount PVC vào `/data`.

---

## 17. Tóm tắt ngắn gọn

Để chuyển 2 service `minio` và `mc` từ `docker-compose.yml` sang Kubernetes:

- `minio` → `Secret + PVC + Deployment + Service`
- `mc` → `ConfigMap + Job`

Đây là bản triển khai phù hợp nhất với cách hoạt động hiện tại của dự án.

---

## 18. Bước tiếp theo nên làm

Bước tiếp theo tốt nhất là đọc file:

```text
init/scripts/init-bucket.sh
```

vì file này sẽ quyết định:

- bucket nào cần tạo
- có cần tạo user/policy không
- có cần ghi file ra `/config` không
- có cần thêm volume cho `mc` trên K8s không

Khi có nội dung script đó, bạn có thể chỉnh `mc-script-configmap.yaml` và `mc-job.yaml` để bám sát hoàn toàn theo dự án hiện tại.
