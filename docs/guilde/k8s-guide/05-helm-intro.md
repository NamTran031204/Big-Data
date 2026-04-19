# Phần 5: Tổng Kết Và Bước Tới Helm Charts

Bạn đã trải qua quá trình tháo dỡ kiến trúc `docker-compose.yml` từng dòng lệnh một sang các thành phần cực kỳ chi tiết của K8s:
- **Persistent Volume Claim** (Lưu trữ).
- **StatefulSet** (Kafka/MongoDB/MinIO).
- **Deployment** (Kafka UI).
- **Services** (NodePort để giao tiếp với Host và ClusterIP cho mảng nội bộ DNS).
- **Jobs** (Công cụ tự động hóa chạy một lần như MinIO MC shell).

Bạn có thể tự hỏi: _"Mỗi lần tạo cụm là tôi phải `kubectl apply -f ...` chạy 20 cái file nhỏ nhỏ này sao?"_

`docker-compose up` thật tuyệt vời vì gom mọi thứ vào 1 tệp, nhưng đừng lo. K8s đã giải xong bài toán này bằng **Helm**.

## 1. Giới thiệu khái niệm Helm

Helm là **Trình quản lý gói cho K8s** (Package Manager).
Thay vì tạo file tĩnh YAML như những gì chúng ta học qua 4 bài (rất khổ nếu thay đổi `replicas: 3` thành `4` hay đổi Username/Password cho MongoDB), Helm tạo ra "**Chart**" (Bản đồ) YAML dựa trên các biến (Variables).

Nói dễ hiểu: `Helm Chart` là chiếc Zip nén tổng đài 20 cái Manifest kia, còn một tệp tên là `values.yaml` nó đóng vai trò y như thằng `.env` hiện tại trong bạn.

## 2. Cấu trúc mà Helm gom dự án Đại học (BigData BTL) vào

Nếu bạn đóng gói hệ thống dưới dạng Helm Chart `bigdata-platform`, cấu trúc thư mục của nó sẽ trông chuyên nghiệp thế này:

```
bigdata-platform/
  Chart.yaml            # = package.json: Chứa metadata (version 1.0, tác giả)
  values.yaml           # = File '.env': Nơi lưu Username: rootUser, password: XYZ
  templates/            # Chứa tệp YAML K8s từ Bài 2, nhưng thay thế # bằng tham số
    mongodb.yaml
    minio.yaml
    zookeeper.yaml 
    kafka.yaml
    kafka-ui.yaml
    mc-job.yaml
```

Bạn chỉ cần nhập đúng `1 LỆNH` từ terminal của Windows:

```bash
helm install btl-bigdata ./bigdata-platform
```
Toàn bộ cụm MinIO, Kafka, Mongo của bạn sẽ khởi chạy trong chớp mắt giống như `docker-compose up` vậy.

## 3. Hãy vươn lên ở mức ứng dụng

Bây giờ bạn đã biết bản chất K8s. **Cách tốt nhất là không nên tự viết lại từ đầu bằng YAML** cho Database/S3/Kafka nữa cho đỡ vất vả (Những thứ chúng ta làm chỉ để HỌC BẢN CHẤT).
Cộng đồng mã nguồn mở Bitnami/Confluent đã viết sẵn Helm Charts cho những công cụ đình đám này (chuẩn bảo mật ngầu gấp 10 lần tự viết YAML).

Để bắt đầu học công nghiệp (Enterprise DevOps):
1. `helm repo add bitnami https://charts.bitnami.com/bitnami`
2. `helm install my-kafka bitnami/kafka`
3. `helm install my-mongodb bitnami/mongodb`

Đó mới thực sự là K8s Production!
Chúc bạn một bài tập lớn BigData thành công rực rỡ và vững tin với môi trường Data Pipeline thực thụ chạy trên Kubernetes Architecture!