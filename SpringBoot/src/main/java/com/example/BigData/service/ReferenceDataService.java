package com.example.BigData.service;

import com.example.BigData.entity.kafka.UserBehaviorEvent;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class ReferenceDataService {

    private final KafkaTemplate<String, UserBehaviorEvent> kafkaTemplate;

    public ReferenceDataService(@Qualifier("userBehaviorKafkaTemplate") KafkaTemplate<String, UserBehaviorEvent> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void sendEvent(UserBehaviorEvent event) {
        kafkaTemplate.send("user-behavior-topic", event.getUserId(), event);
    }
}