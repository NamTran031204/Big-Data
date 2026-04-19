# Phần 1: Các Khái Niệm Cốt Lõi K8s (Docker Compose vs Kubernetes)

Cấu trúc trong `init/docker-compose.yml` đang có là kiến trúc cơ bản cho một nền tảng Data pipeline xử lý dòng (streaming processing) và Data Lake lưu trữ.
Thay vì học mớ lý thuyết khô khan của K8s, chúng ta sẽ bắt đầu từ những gì bạn đã biết.

## 1. Dịch thuật thành phần từ Docker sang K8s

Dưới đây là một bảng tham chiếu nhanh (Reference Table) để hiểu khái niệm K8s sẽ đóng vai trò gì thay thế cho cấu hình Docker Compose hiện tại của bạn:

| Tính năng trong `docker-compose.yml` | Khái niệm Kubernetes (K8s) tương đương (Resources) | Giải thích (Context) |
| --- | --- | --- |
| `services: mongodb, kafka, minio` | **Pod** | Về logic, 1 service trong compose sẽ chạy 1 Docker Container. Mặc dù Pod trong K8s có thể chạy nhiều container, nhưng thường thiết kế là tỉ lệ 1:1. |
| `restart: unless-stopped`, `deploy: resources` | **Deployments** / **StatefulSets** | K8s không chạy trực tiếp Pod, mà dùng "trình quản lý" (Controller). Với các service *CÓ LƯU DỮ LIỆU* (như Mongo, Kafka, Zookeeper, MinIO) -> Cần dùng **StatefulSet**. Với Kafka UI (Không trạng thái) -> Dùng **Deployment**. |
| `ports: - "27017:27017"` | **Services (NodePort / LoadBalancer)** | Để kết nối từ máy ảo / host (PC của bạn) vào ứng dụng bên trong K8s. |
| `networks:` | **Services (ClusterIP) & DNS nội bộ** | K8s sử dụng dịch vụ nội bộ có sẵn DNS tên domain (VD: `mongodb.default.svc.cluster.local`) để Pod này gọi API Pod kia. Bạn không cần tự khai báo network. |
| `environment: MONGO_INITDB_ROOT_PASSWORD` | **ConfigMaps / Secrets** | Tách riêng các biến môi trường thay vì dính cứng trong file config. ConfigMap cho biến an toàn (user), Secret cho biến nhạy cảm (passwords). |
| `volumes: - mongodb_data:/data/db` | **PersistentVolume (PV) & PersistentVolumeClaim (PVC)** | Việc quản lý phân vùng ổ cứng (Lưu trữ vật lý bên trong cụm server thật). PV là ổ cứng vật lý, PVC là Ticket "xin cấp thẻ nhớ". |
| `depends_on`, `condition: service_healthy` | **InitContainers, Readiness / Liveness Probes** | Khai báo kịch bản khởi động K8s. VD Kafka cần chờ ZK Ready. K8s sẽ check sức khỏe (Probe) để chuyển rào chắn (healthcheck). |

---

## 2. Kiến trúc (Architecture Blueprint)

Hãy hình dung xem `docker-compose` hiện tại chia làm mấy Layer (Lớp) trên K8s:

1. **Storage Layer (Stateful) - [Phần 2]**: 
   - MinIO (Object Storage ~ S3): Nơi chứa Data DataLake thô.
   - MongoDB (Document DB): Hệ thống metadata quản lý.
   => Layer này cần **PVCs (Ổ cứng bền vững)** & **StatefulSets**.
   
2. **Messaging/Streaming Layer (Stateful) - [Phần 3]**:
   - Zookeeper (Quản lý trạng thái Kafka cluster).
   - Kafka (Nhận và đọc ghi Event Data theo Real-time).
   => Layer siêu nhạy cảm về Data Network, cần **StatefulSet** với tính danh định (identities) chắc chắn để Broker ID không bị loạn vòng.

3. **Application/UI Layer (Stateless) - [Phần 3]**:
   - Kafka UI (Theo dõi stream).
   => Bản chất phi trạng thái. Chết thì tự tạo lại, chạy **Deployment** là đủ. 

4. **Kịch bản tự động hóa (Script) - [Phần 4]**: 
   - `mc` command để `init-bucket` khi MinIO vừa dựng xong.
   => Tạo Bucket 1 lần duy nhất bằng **K8s Job**. Không chạy thành service lưu cữu như Compose.

Bây giờ bạn đã sẵn sàng cho việc bắt tay vào thiết lập ổ đĩa cứng, và deploy cụm Storage Layer!

Chuyển sang: [Phần 2: Triển khai Storage layer (MongoDB & MinIO)](02-storage-layer.md)
