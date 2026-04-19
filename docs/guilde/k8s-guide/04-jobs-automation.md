# Phần 4: Tự Động Hóa Với K8s Jobs (Thực Thi Script MinIO MC)

Bạn hãy nhìn lại trong `docker-compose.yml`, có một service tên là `mc`.
```yaml
  mc:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    volumes:
      - ./scripts/init-bucket.sh:/scripts/init-bucket.sh:ro
      - ./config:/config
    command: ["/scripts/init-bucket.sh"]
```
Service này vốn dĩ **không phải là hệ thống duy trì liên tục** (không phải Nginx hay database). Nó chỉ là một công cụ (Tool) chạy một đoạn script một lần duy nhất, tạo bucket, rồi Tắt Ngủ. Nếu để trong Compose, vòng đời của nó bị trói chung với hệ thống tổng.

K8s cung cấp công cụ gọi là **Jobs**. `Job` sinh ra Pod, chạy xong kịch bản thì đánh dấu trạng thái "Completed" và không Restart thêm nữa.

## 1. Biến script file thành ConfigMap

Làm sao để mount cái file vỏn vẹn trong ổ của bạn `[init/scripts/init-bucket.sh](../../init/scripts/init-bucket.sh)` vào Pod "trên chín tầng mây" K8s?

K8s cung cấp **ConfigMap**. Thay vì Volume cứng, ta tạo một ConfigMap dạng String Script.
Bạn sẽ phải chạy lệnh sau để kéo file shell kia thành ConfigMap:

```bash
# Đứng từ Folder gốc (Big-Data) gõ:
kubectl create configmap minio-init-script --from-file=init-bucket.sh=init/scripts/init-bucket.sh
```

## 2. Viết Job Manifest

Tạo file `k8s-guide/manifests/jobs/minio-mc-job.yaml`.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: minio-mc-init
spec:
  template:
    spec:
      restartPolicy: OnFailure # Nếu lỗi do minio chưa up thì nó thử lại, xong thì ngưng.
      containers:
        - name: mc
          image: minio/mc:latest
          command: ["/bin/sh", "/scripts/init-bucket.sh"]
...
```

Điểm hay ở đây là K8s sẽ ánh xạ `minio-init-script` ConfigMap lại thành cái File `/scripts/init-bucket.sh` ở trong máy.

```sh
kubectl apply -f manifests/jobs/minio-mc-job.yaml
```

Bạn dùng lệnh sau để kiểm tra quá trình tạo Bucket đã thông đồng bén giọt chưa:
```bash
kubectl logs job/minio-mc-init
```

---

Xin chúc mừng! Vậy là hoàn thành 90% kiến trúc của 1 Data Platform lên Kubernetes. Cuối cùng, chúng ta sẽ xem cách gom lại [Tại Phần 5](05-helm-intro.md).