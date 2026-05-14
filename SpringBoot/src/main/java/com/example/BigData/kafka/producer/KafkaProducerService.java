package com.example.BigData.kafka.producer;

import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import lombok.extern.slf4j.Slf4j;

@Service
@Slf4j
public class KafkaProducerService {

    private final KafkaTemplate<String, String> jsonKafkaTemplate;
    private final KafkaTemplate<String, byte[]> byteKafkaTemplate;

    // Tiêm chính xác các Template đã cấu hình trong KafkaProducerConfig
    public KafkaProducerService(
            @Qualifier("jsonKafkaTemplate") KafkaTemplate<String, String> jsonKafkaTemplate,
            @Qualifier("byteKafkaTemplate") KafkaTemplate<String, byte[]> byteKafkaTemplate) {
        this.jsonKafkaTemplate = jsonKafkaTemplate;
        this.byteKafkaTemplate = byteKafkaTemplate;
    }

    // Hàm cũ bạn đang dùng cho các mục đích khác
    public void sendMessage(String topic, String key, String message) {
        jsonKafkaTemplate.send(topic, key, message);
    }

    // HÀM MỚI: Fix lỗi "cannot find symbol" cho OrderSyncService
    public void sendOrderEvent(String topic, String key, OrderEvent event, BaseEvent.SerializationFormat format) {
        try {
            if (format == BaseEvent.SerializationFormat.PARQUET) {
                // Nếu là Parquet, dùng byteKafkaTemplate để gửi mảng byte
                byte[] data = event.getPayload(); // Giả định OrderEvent có hàm getPayload trả về byte[]
                byteKafkaTemplate.send(topic, key, data);
                log.info("📤 Sent Parquet event to topic: {}", topic);
            } else {
                // Mặc định gửi JSON bằng jsonKafkaTemplate
                // Bạn có thể dùng ObjectMapper để convert event thành String nếu cần,
                // hoặc gửi raw string nếu OrderSyncService đã convert rồi.
                jsonKafkaTemplate.send(topic + "_json", key, event.toString());
                log.info("📤 Sent JSON event to topic: {}", topic + "_json");
            }
        } catch (Exception e) {
            log.error("❌ Error sending OrderEvent: {}", e.getMessage());
        }
    }
}