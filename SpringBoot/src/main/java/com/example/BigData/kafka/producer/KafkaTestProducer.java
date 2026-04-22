package com.example.BigData.kafka.producer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Component
public class KafkaTestProducer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(KafkaTestProducer.class);

    @Autowired
    private KafkaProducerService producerService;

    @Override
    public void run(String... args) throws Exception {
        log.info("🚀 Starting Kafka Producer Test...");

        // Test 1: Send simple messages
        for (int i = 1; i <= 5; i++) {
            String message = "Test message #" + i + " at " + LocalDateTime.now();
            producerService.sendMessage("test-topic", message);
            Thread.sleep(500); // delay 500ms between messages
        }

        // Test 2: Send messages with key
        String[] keys = {"user-1", "user-2", "user-3"};
        for (String key : keys) {
            producerService.sendMessageWithKey("test-topic", key,
                    "Hello from " + key + " at " + LocalDateTime.now());
        }

        // Test 3: Send JSON object
        Map<String, Object> orderEvent = new HashMap<>();
        orderEvent.put("orderId", "ORD-001");
        orderEvent.put("userId", "USR-123");
        orderEvent.put("amount", 99.99);
        orderEvent.put("status", "CREATED");
        orderEvent.put("timestamp", LocalDateTime.now().toString());

        producerService.sendObject("orders-topic", "ORD-001", orderEvent);

        log.info("✅ Kafka Producer Test completed!");
    }
}