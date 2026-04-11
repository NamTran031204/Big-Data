# Kubernetes (K8s) Learning Guide: Từ Docker Compose lên K8s

Chào mừng bạn đến với khóa học thực hành K8s dành cho dự án Big Data của chúng ta! 
Trong khóa học này, chúng ta sẽ lần lượt "dịch" toàn bộ kiến trúc từ `docker-compose.yml` sang các thành phần (resources) tương ứng trong Kubernetes. Chúng ta sẽ ưu tiên việc học thông qua thực hành trên **Minikube** (hoặc **Kind**), tập trung vào việc viết manifests `YAML` thủ công trước.

## Các giai đoạn (Phases) của khóa học:

- [Phần 1: Các khái niệm cốt lõi K8s (Ánh xạ từ Docker Compose)](01-core-concepts.md)
- [Phần 2: Triển khai Storage layer - MongoDB & MinIO](02-storage-layer.md)
- [Phần 3: Triển khai Message Broker - Zookeeper, Kafka, Kafka UI](03-message-broker.md)
- [Phần 4: Tự động hóa nội bộ với K8s Jobs - MinIO MC script](04-jobs-automation.md)
- [Phần 5: Review & Đóng gói với Helm Charts (Nâng cao)](05-helm-intro.md)

---

### Chuẩn bị môi trường (Pre-requisites)
Để thực hành, bạn cần chuẩn bị:
1. **Docker Desktop** (hoặc Docker Engine).
2. **Minikube** (Công cụ chạy cluster K8s nhỏ gọn trên máy cá nhân). Cài đặt qua: `choco install minikube` (Windows) hoặc tải file binary trực tiếp từ trang chủ K8s.
3. **kubectl**: Công cụ dòng lệnh (CLI) để điều khiển K8s cluster. Cài đặt qua: `choco install kubernetes-cli`.
4. Khởi động môi trường bằng lệnh:
```bash
minikube start --memory=8192 --cpus=4
```
*(Chúng ta cần cấp phát ít nhất 8GB RAM và 4 CPUs để chạy mượt mà Kafka, Zookeeper, MinIO, MongoDB).*

Sau khi đã bật cluster, chúng ta cùng tiến tới **Phần 1**!
