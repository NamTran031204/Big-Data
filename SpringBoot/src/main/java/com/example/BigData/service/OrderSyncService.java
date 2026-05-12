package com.example.BigData.service;

import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import com.example.BigData.kafka.producer.KafkaProducerService;
import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import com.example.BigData.repository.mongodb.OrderAnalyticsMongoRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderSyncService {

    private final OrderAnalyticsMongoRepository mongoRepository;
    private final KafkaProducerService kafkaProducerService;

    public void syncOrderToMongo(CdcEvent cdcEvent) {
        if (cdcEvent.getPayload() == null || cdcEvent.getPayload().getAfter() == null || cdcEvent.getPayload().getAfter().getFields().isEmpty()) {
            log.warn("Bỏ qua bản tin vì không có dữ liệu 'after'");
            return;
        }

        Map<String, Object> afterData = cdcEvent.getPayload().getAfter().getFields();
        String op = cdcEvent.getPayload().getOp();
        String orderId = (String) afterData.get("order_id");

        try {
            OrderAnalyticsDocument document = mongoRepository.findById(orderId)
                    .orElse(new OrderAnalyticsDocument());

            document.setOrderId(orderId);
            document.setCustomerId((String) afterData.get("customer_id"));
            document.setOrderStatus((String) afterData.get("order_status"));

            Object purchaseTs = afterData.get("order_purchase_timestamp");
            if (purchaseTs != null) {
                document.setPurchaseTimestamp(convertMicroTimestamp((Long) purchaseTs));
            }

            mongoRepository.save(document);
            log.info("✅ Đã đồng bộ Order {} sang MongoDB Atlas", orderId);

            OrderEvent cleanEvent = new OrderEvent();
            cleanEvent.setEventId(UUID.randomUUID().toString());

            if ("c".equals(op)) {
                cleanEvent.setEventType("ORDER_CREATED");
            } else if ("u".equals(op)) {
                cleanEvent.setEventType("ORDER_UPDATED");
            } else {
                cleanEvent.setEventType("ORDER_DELETED");
            }

            cleanEvent.setOrderId(orderId);
            cleanEvent.setCustomerId((String) afterData.get("customer_id"));
            cleanEvent.setOrderStatus((String) afterData.get("order_status"));
            cleanEvent.setEventTimestamp(LocalDateTime.now().toString());

            String topic = "olist_orders"; // Chỉ cần tên gốc, bên service sẽ tự thêm _json nếu cần

            kafkaProducerService.sendOrderEvent(topic, orderId, cleanEvent, BaseEvent.SerializationFormat.PARQUET);
            kafkaProducerService.sendOrderEvent(topic, orderId, cleanEvent, BaseEvent.SerializationFormat.JSON);

        } catch (Exception e) {
            log.error("❌ Lỗi Pipeline xử lý Order {}: {}", orderId, e.getMessage());
        }
    }

    private LocalDateTime convertMicroTimestamp(Long microTs) {
        return LocalDateTime.ofInstant(Instant.ofEpochMilli(microTs / 1000), ZoneId.systemDefault());
    }
}