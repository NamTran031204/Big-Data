import json
import time
import random
from kafka import KafkaProducer
from faker import Faker

fake = Faker()

# Khởi tạo Kafka Producer kết nối đến Kafka Broker đang chạy ở cổng 9092
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

print("Đang khởi động máy phát dữ liệu ảo...")
print("Bấm Ctrl + C nếu bạn muốn dừng phát.\n")

try:
    while True:
        # Tạo dữ liệu 1 đơn hàng ảo
        order = {
            "order_id": fake.uuid4(),
            "user_id": random.randint(100, 999),
            "amount": round(random.uniform(10.5, 500.0), 2),
            "timestamp": time.time()
        }
        
        # Đẩy đơn hàng vào topic có tên là 'orders_topic' trong Kafka
        producer.send('orders_topic', order)
        print(f"Đã gửi: {order}")
        
        time.sleep(1) 
        
except KeyboardInterrupt:
    print("\nĐã dừng phát dữ liệu.")
    producer.close()