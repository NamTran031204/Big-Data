package com.example.BigData.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

@Configuration
public class KafkaProducerConfig {

    // Tạo topic tự động khi app start
    @Bean
    public NewTopic testTopic() {
        return TopicBuilder.name("test-topic")
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic ordersTopic() {
        return TopicBuilder.name("orders-topic")
                .partitions(3)
                .replicas(1)
                .build();
    }
}