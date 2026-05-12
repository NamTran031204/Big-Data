package com.example.BigData.kafka.producer;

import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.UUID;

//@Component
public class KafkaTestProducer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(KafkaTestProducer.class);

    @Autowired
    private KafkaProducerService producerService;

    @Override
    public void run(String... args) throws Exception {
        log.info("🚀 Starting Kafka Producer Test...");

        // 1. Tạo một đơn hàng giả (Mock Data) chuẩn theo form OrderEvent
        OrderEvent mockEvent = new OrderEvent();
        mockEvent.setEventId(UUID.randomUUID().toString());
        mockEvent.setEventType("TEST_ORDER");
        mockEvent.setOrderId("ORD-TEST-999");
        mockEvent.setCustomerId("CUST-PRO-VIP");
        mockEvent.setOrderStatus("delivered");
        mockEvent.setEventTimestamp(LocalDateTime.now().toString());

        // 2. Test bắn bằng vòi xịt JSON
        log.info("▶️ Đang test bắn dữ liệu JSON...");
        producerService.sendOrderEvent("test_orders", mockEvent.getOrderId(), mockEvent, BaseEvent.SerializationFormat.JSON);

        // 3. Test bắn bằng vòi xịt PARQUET
        log.info("▶️ Đang test bắn dữ liệu PARQUET...");
        producerService.sendOrderEvent("test_orders", mockEvent.getOrderId(), mockEvent, BaseEvent.SerializationFormat.PARQUET);

        log.info("✅ Kafka Producer Test completed!");
    }
}