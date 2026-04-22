package com.example.BigData.kafka.consumer; // Khai báo package ở đây

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

@Service
public class KafkaConsumerService {

    // Lắng nghe topic từ Debezium (CDC)
    @KafkaListener(topics = "olist_cdc.olist.olist_orders", groupId = "olist-group")
    public void consumeCDC(String message) {
        System.out.println("=== NHẬN DỮ LIỆU TỪ POSTGRES (CDC) ===");
        System.out.println(message);
        // Sau này Thế sẽ viết code parse JSON và lưu vào Mongo ở đây
    }

    // Lắng nghe topic từ Java Producer (Thủ công)
    @KafkaListener(topics = "test-topic", groupId = "test-group")
    public void consumeTest(String message) {
        System.out.println("=== NHẬN DỮ LIỆU TỪ JAVA PRODUCER ===");
        System.out.println("Nội dung: " + message);
    }
}