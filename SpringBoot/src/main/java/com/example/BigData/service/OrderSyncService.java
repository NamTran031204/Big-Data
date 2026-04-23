package com.example.BigData.service;



import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import com.example.BigData.repository.mongodb.OrderAnalyticsMongoRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderSyncService {

    private final OrderAnalyticsMongoRepository mongoRepository;

    public void syncOrderToMongo(CdcEvent cdcEvent) {
        if (cdcEvent.getPayload() == null || cdcEvent.getPayload().getAfter() == null || cdcEvent.getPayload().getAfter().getFields().isEmpty()) {
            log.warn("Bỏ qua bản tin vì không có dữ liệu 'after'");
            return;
        }

// Thay đổi chỗ lấy afterData
        Map<String, Object> afterData = cdcEvent.getPayload().getAfter().getFields();
        String op = cdcEvent.getPayload().getOp(); // Lấy toán tử u, c, d

        String orderId = (String) afterData.get("order_id");

        // Tạo hoặc cập nhật Document
        OrderAnalyticsDocument document = mongoRepository.findById(orderId)
                .orElse(new OrderAnalyticsDocument());

        document.setOrderId(orderId);
        document.setCustomerId((String) afterData.get("customer_id"));
        document.setOrderStatus((String) afterData.get("order_status"));

        // Xử lý Timestamp (Debezium gửi timestamp dưới dạng Long)
        Object purchaseTs = afterData.get("order_purchase_timestamp");
        if (purchaseTs != null) {
            document.setPurchaseTimestamp(convertMicroTimestamp((Long) purchaseTs));
        }

        mongoRepository.save(document);
        log.info("✅ Đã đồng bộ Order {} sang MongoDB Atlas", orderId);
    }

    // Hàm phụ trợ chuyển đổi thời gian của Debezium
    private LocalDateTime convertMicroTimestamp(Long microTs) {
        return LocalDateTime.ofInstant(Instant.ofEpochMilli(microTs / 1000), ZoneId.systemDefault());
    }
}