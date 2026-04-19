# Phần 3: Trái Tim Streaming (Zookeeper, Kafka & Kafka UI)

Phần này rất hay vì bạn sẽ thấy K8s giải quyết bài toán giao tiếp nội bộ + giao tiếp ngoại bộ cực đỉnh cho Kafka.

Trong `docker-compose.yml`, để Code Java hay Python ở dưới máy local (host) có thể Consume gói tin, bạn phải cấu hình biến môi trường dài dằng dặc:
`KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092...`

K8s có Service tên là **NodePort / LoadBalancer** để giải quyết việc này, giúp Kafka Node có 1 IP/Domain cố định.

## Zookeeper
Trạm điều phối cụm Kafka. Dù bạn có 1 node hay 3 nodes Kafka, Zookeeper vẫn cần lưu log của chính mình.
- Dùng `StatefulSet` + `Service (ClusterIP)`.
- Chạy lần lượt các file YAML từ `manifests/kafka/zookeeper-*`.

```sh
kubectl apply -f manifests/kafka/zookeeper-service.yaml
kubectl apply -f manifests/kafka/zookeeper-statefulset.yaml
```

## Kafka Broker
Thành phần Streaming. Khác với Zookeeper, ta cần mở cổng `9092` cho bên ngoài K8s gọi vào (VD máy host Localhost dùng tool gửi message) và `9094` cho bên trong K8s (như Pod Kafka-UI gọi nội bộ).

### 1. Cấu hình Kafka Service
Tạo `kafka-service.yaml`. Hãy để ý `NodePort` mở cổng `30092`.
Host sẽ bắn packet Data Pipeline vào IP của Minikube trên cổng `30092`.

### 2. Khởi tạo Kafka StatefulSet
File `kafka-statefulset.yaml`. Trong đó biến `KAFKA_ADVERTISED_LISTENERS` sẽ phải chép hệt như compose, nhưng ta sửa `localhost:9092` thành môi trường K8s.

Đặc biệt K8s có tính năng **Init Container** để giả lập lệnh `depends_on: zookeeper` (Chờ zookeeper live thì tao mới live).
Vì ZK lưu trữ ở cổng 2181, InitContainer là 1 script gọi ping liên tục vào DNS `zookeeper.default.svc.cluster.local:2181`.

```sh
kubectl apply -f manifests/kafka/kafka-service.yaml
kubectl apply -f manifests/kafka/kafka-statefulset.yaml
```

## Kafka-UI (Stateless)
Đây là Component nhẹ nhất. Vì nó chỉ là cái Frontend (Web Giao diện) soi và quản lý Kafka, đụng vào nó không sợ mất dữ liệu. Nó chết K8s tự sinh lại là xong.
Do đó K8s có `Deployment`. Deployment là anh em của StatefulSet nhưng dọn dẹp nhẹ nhàng hơn, không cần cắm Cứng ID theo ổ đĩa.

```sh
kubectl apply -f manifests/kafka/kafka-ui-service.yaml
kubectl apply -f manifests/kafka/kafka-ui-deployment.yaml
```
Biến môi trường `KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS` giờ đây nối vào `kafka.default.svc.cluster.local:9094` (Mạng DNS của cụm).

Đợi 2-3 phút, sau đó mở Kafka UI trên Windows bằng:
```bash
minikube service kafka-ui-service 
```
Hoặc NodePort tĩnh `30080`.

Sau khi Kafka đã chạy, nếu bạn nhớ trong compose còn 1 phần cấu hình tạo Bucket tự động cho MinIO qua `mc`. Chúng ta qua [Phần 4: Tự động hóa với Job](04-jobs-automation.md).
