package com.example.BigData.service;

import com.example.BigData.entity.kafka.UserBehaviorEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class ReferenceDataService {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    public ReferenceDataService(
            @Qualifier("userBehaviorKafkaTemplate") KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    public void sendEvent(UserBehaviorEvent event) {
        try {
            String json = objectMapper.writeValueAsString(event);
            kafkaTemplate.send("user_behavior_events", event.getUserId(), json);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize UserBehaviorEvent: {}", e.getMessage());
        }
    }
}