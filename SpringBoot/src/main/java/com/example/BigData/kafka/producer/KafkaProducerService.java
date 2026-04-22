package com.example.BigData.kafka.producer;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

@Service
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
            String json = objectMapper.writeValueAsString(payload);
            sendMessageWithKey(topic, key, json);
        } catch (Exception e) {
            log.error("❌ Failed to serialize object: {}", e.getMessage());
        }
    }
}