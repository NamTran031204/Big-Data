package com.example.BigData.kafka.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class UserBehaviorEventComsumer {

    private final ObjectMapper objectMapper;

    public UserBehaviorEventComsumer(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @KafkaListener(
            topics = "user_behavior_events",
            groupId = "user-behavior-group"
    )
    public void consume(String message) {

        try {

            log.info("Received raw message: {}", message);

            JsonNode jsonNode = objectMapper.readTree(message);

            log.info(
                    "Formatted JSON:\n{}",
                    objectMapper.writerWithDefaultPrettyPrinter()
                            .writeValueAsString(jsonNode)
            );

            /*
             * Đọc dữ liệu từ JSON
             */

            String userId = jsonNode.has("user_id")
                    ? jsonNode.get("user_id").asText()
                    : null;

            String eventType = jsonNode.has("event_type")
                    ? jsonNode.get("event_type").asText()
                    : null;

            String productId = jsonNode.has("product_id")
                    ? jsonNode.get("product_id").asText()
                    : null;

            String timestamp = jsonNode.has("timestamp")
                    ? jsonNode.get("timestamp").asText()
                    : null;

            log.info("========== USER BEHAVIOR EVENT ==========");
            log.info("User ID     : {}", userId);
            log.info("Event Type  : {}", eventType);
            log.info("Product ID  : {}", productId);
            log.info("Timestamp   : {}", timestamp);
            log.info("=========================================");

            /*
             * TODO:
             * - Lưu MongoDB
             * - Đẩy MinIO
             * - Spark Streaming
             * - Analytics
             */

        } catch (Exception e) {

            log.error("Error while consuming user_behavior_event", e);
        }
    }
}
