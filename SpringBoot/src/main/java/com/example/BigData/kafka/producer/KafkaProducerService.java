package com.example.BigData.kafka.producer;

import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import com.fasterxml.jackson.databind.ObjectMapper;

import ch.qos.logback.classic.Logger;

import com.example.BigData.util.ParquetConverter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.apache.log4j.spi.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

@Service
@Slf4j
@RequiredArgsConstructor
public class KafkaProducerService {

    private static final Logger log = LoggerFactory.getLogger(KafkaProducerService.class);

    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    @Autowired
    private ObjectMapper objectMapper;

    // Send simple string message
    public void sendMessage(String topic, String message) {
        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(topic, message);

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("✅ Sent message='{}' to topic='{}', partition={}, offset={}",
                        message,
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
            } else {
                log.error("❌ Failed to send message='{}' due to: {}", message, ex.getMessage());
            }
        });
    }

    // Send message with key (for partitioning)
    public void sendMessageWithKey(String topic, String key, String message) {
        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(topic, key, message);

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("✅ Sent key='{}' message='{}' to topic='{}'", key, message, topic);
            } else {
                log.error("❌ Failed to send message with key='{}': {}", key, ex.getMessage());
            }
        });
    }

    // Send object as JSON
    public void sendObject(String topic, String key, Object payload) {
        try {

            ObjectMapper mapper = new ObjectMapper(new com.fasterxml.jackson.core.JsonFactory());

            String json = mapper.writeValueAsString(payload);

            System.out.println("DEBUG - CHUỖI JSON GỬI ĐI: " + json);

            sendMessageWithKey(topic, key, json);
        } catch (Exception e) {
            log.error("❌ Lỗi Serialize: {}", e.getMessage());
        }
    }
}