package com.example.BigData.kafka.producer;

import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.example.BigData.util.ParquetConverter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

@Service
@Slf4j
@RequiredArgsConstructor
public class KafkaProducerService {

    // Kéo 2 "vòi xịt" từ KafkaProducerConfig sang
    private final KafkaTemplate<String, String> jsonKafkaTemplate;
    private final KafkaTemplate<String, byte[]> byteKafkaTemplate;

    private final ObjectMapper objectMapper;
    private final ParquetConverter parquetConverter;

    // Hàm chính để gửi Event đa định dạng
    public void sendOrderEvent(String topic, String key, OrderEvent event, BaseEvent.SerializationFormat format) {
        if (format == BaseEvent.SerializationFormat.PARQUET) {
            try {
                // 1. Nếu là Parquet -> Gọi ParquetConverter -> Dùng byteKafkaTemplate
                byte[] data = parquetConverter.convertToParquetBytes(event);
                log.info("📦 Đang gửi dữ liệu định dạng PARQUET...");

                CompletableFuture<SendResult<String, byte[]>> future = byteKafkaTemplate.send(topic, key, data);
                future.whenComplete((result, ex) -> {
                    if (ex == null) {
                        log.info("✅ [PARQUET] Sent to topic='{}', partition={}, offset={}",
                                result.getRecordMetadata().topic(), result.getRecordMetadata().partition(), result.getRecordMetadata().offset());
                    } else {
                        log.error("❌ [PARQUET] Failed with key='{}': {}", key, ex.getMessage());
                    }
                });
            } catch (Exception e) {
                log.error("❌ Lỗi nén Parquet: {}", e.getMessage());
            }
        } else {
            try {
                // 2. Nếu là JSON -> Ép chuỗi -> Dùng jsonKafkaTemplate
                String json = objectMapper.writeValueAsString(event);
                log.info("📝 Đang gửi dữ liệu định dạng JSON...");

                // Gắn thêm chữ "_json" vào đuôi topic để dễ phân biệt trên Kafka UI
                String jsonTopic = topic + "_json";
                CompletableFuture<SendResult<String, String>> future = jsonKafkaTemplate.send(jsonTopic, key, json);
                future.whenComplete((result, ex) -> {
                    if (ex == null) {
                        log.info("✅ [JSON] Sent to topic='{}', partition={}, offset={}",
                                result.getRecordMetadata().topic(), result.getRecordMetadata().partition(), result.getRecordMetadata().offset());
                    } else {
                        log.error("❌ [JSON] Failed with key='{}': {}", key, ex.getMessage());
                    }
                });
            } catch (Exception e) {
                log.error("❌ Lỗi ép JSON: {}", e.getMessage());
            }
        }
    }
}