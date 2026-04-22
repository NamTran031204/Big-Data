package com.example.BigData.controller;

import com.example.BigData.kafka.producer.KafkaProducerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/kafka")
public class KafkaTestController {

    @Autowired
    private KafkaProducerService producerService;

    // POST /api/kafka/send?topic=test-topic&message=hello
    @PostMapping("/send")
    public ResponseEntity<String> sendMessage(
            @RequestParam String topic,
            @RequestParam String message) {
        producerService.sendMessage(topic, message);
        return ResponseEntity.ok("Message sent to topic: " + topic);
    }

    // POST /api/kafka/send-event
    @PostMapping("/send-event")
    public ResponseEntity<String> sendEvent(@RequestBody Map<String, Object> payload) {
        String topic = (String) payload.getOrDefault("topic", "test-topic");
        String key = (String) payload.getOrDefault("key", "default-key");
        payload.put("timestamp", LocalDateTime.now().toString());
        producerService.sendObject(topic, key, payload);
        return ResponseEntity.ok("Event sent successfully");
    }

    // GET /api/kafka/test - Quick test
    @GetMapping("/test")
    public ResponseEntity<String> quickTest() {
        for (int i = 1; i <= 3; i++) {
            producerService.sendMessage("test-topic",
                    "Quick test message #" + i + " - " + LocalDateTime.now());
        }
        return ResponseEntity.ok("3 test messages sent to test-topic");
    }
}