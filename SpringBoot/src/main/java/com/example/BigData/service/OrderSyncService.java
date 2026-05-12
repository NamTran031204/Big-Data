package com.example.BigData.service;

import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument.ItemSummary;
import com.example.BigData.entity.postgres.OrderItemEntity;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.kafka.producer.KafkaProducerService;
import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import com.example.BigData.repository.mongodb.OrderAnalyticsMongoRepository;
import com.example.BigData.repository.postgres.CustomerJpaRepository;
import com.example.BigData.repository.postgres.OrderItemJpaRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderSyncService {

    private final OrderAnalyticsMongoRepository mongoRepository;
    private final KafkaProducerService kafkaProducerService;
    private final CustomerJpaRepository customerRepository;
    private final OrderItemJpaRepository itemRepository;

    public void syncOrderToMongo(CdcEvent cdcEvent) {
        if (cdcEvent.getPayload() == null) return;

        String op = cdcEvent.getPayload().getOp();
        // Xác định lấy data từ after (tạo/sửa) hay before (xóa)
        Map<String, Object> data = ("d".equals(op)) 
                ? cdcEvent.getPayload().getBefore().getFields() 
                : cdcEvent.getPayload().getAfter().getFields();

        if (data == null) return;

        String orderId = (String) data.get("order_id");
        if (orderId == null) return;

        try {
            if ("d".equals(op)) {
                mongoRepository.deleteById(orderId);
                log.info("🗑️ [Gold] Đã xóa Order: {}", orderId);
                
                // Báo cho Kafka biết đơn hàng đã bị xóa
                sendToKafka(orderId, data, "ORDER_DELETED");
                return;
            }
            
            // Xử lý làm giàu dữ liệu và lưu Mongo, sau đó bắn Kafka
            handleSaveOrUpdate(orderId, data, op);
            
        } catch (Exception e) {
            log.error("❌ Lỗi xử lý Gold Layer / Kafka cho Order {}: {}", orderId, e.getMessage());
        }
    }

    private void handleSaveOrUpdate(String orderId, Map<String, Object> data, String op) {
        OrderAnalyticsDocument document = mongoRepository.findById(orderId)
                .orElse(new OrderAnalyticsDocument());

        // =========================================================
        // 1. Mapping thông tin cơ bản từ Kafka
        // =========================================================
        document.setOrderId(orderId);
        document.setCustomerId((String) data.get("customer_id"));
        document.setOrderStatus((String) data.get("order_status"));
        document.setPurchaseTimestamp(convertMicroTimestamp(data.get("order_purchase_timestamp")));
        document.setDeliveredDate(convertMicroTimestamp(data.get("order_delivered_customer_date")));
        document.setEstimatedDeliveryDate(convertMicroTimestamp(data.get("order_estimated_delivery_date")));

        // =========================================================
        // 2. DATA ENRICHMENT (Làm giàu dữ liệu từ Silver - PostgreSQL)
        // =========================================================
        customerRepository.findById(document.getCustomerId()).ifPresent(c -> {
            document.setCustomerCity(c.getCity());
            document.setCustomerState(c.getState());
        });

        List<OrderItemEntity> postgresItems = itemRepository.findByIdOrderId(orderId);
        
        List<ItemSummary> itemSummaries = postgresItems.stream().map(item -> {
            ItemSummary summary = new ItemSummary();
            ProductEntity product = item.getProduct();
            
            summary.setProductId(product.getProductId());
            summary.setSellerId(item.getSeller().getSellerId());
            summary.setPrice(item.getPrice());
            summary.setFreightValue(item.getFreightValue());
            
            summary.setCategoryName(product.getProductCategoryName());
            if (product.getCategoryTranslation() != null) {
                summary.setCategoryNameEnglish(product.getCategoryTranslation().getProductCategoryNameEnglish());
            }
            
            return summary;
        }).collect(Collectors.toList());

        document.setItems(itemSummaries);

        // =========================================================
        // 3. COMPUTED FIELDS (Tính toán chỉ số Analytics)
        // =========================================================
        if (document.getDeliveredDate() != null && document.getEstimatedDeliveryDate() != null) {
            long delay = ChronoUnit.DAYS.between(document.getEstimatedDeliveryDate(), document.getDeliveredDate());
            document.setDeliveryDelayDays((int) delay);
        }

        BigDecimal totalValue = itemSummaries.stream()
                .map(i -> i.getPrice().add(i.getFreightValue()))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        document.setTotalItemValue(totalValue);
        document.setItemCount(itemSummaries.size());

        // =========================================================
        // 4. Lưu vào Gold Layer (MongoDB)
        // =========================================================
        mongoRepository.save(document);
        log.info("⭐ [Gold] Đã tổng hợp dữ liệu thành công cho Order: {}", orderId);

        // =========================================================
        // 5. Bắn Event lên Kafka (Đã hợp nhất từ nhánh HEAD)
        // =========================================================
        String eventType = "c".equals(op) ? "ORDER_CREATED" : "ORDER_UPDATED";
        sendToKafka(orderId, data, eventType);
    }

    // Hàm phụ trợ được tách ra cho sạch code
    private void sendToKafka(String orderId, Map<String, Object> data, String eventType) {
        try {
            OrderEvent cleanEvent = new OrderEvent();
            cleanEvent.setEventId(UUID.randomUUID().toString());
            cleanEvent.setEventType(eventType);
            cleanEvent.setOrderId(orderId);
            cleanEvent.setCustomerId((String) data.get("customer_id"));
            cleanEvent.setOrderStatus((String) data.get("order_status"));
            cleanEvent.setEventTimestamp(LocalDateTime.now().toString());

            String topic = "olist_orders"; 
            kafkaProducerService.sendOrderEvent(topic, orderId, cleanEvent, BaseEvent.SerializationFormat.PARQUET);
            kafkaProducerService.sendOrderEvent(topic, orderId, cleanEvent, BaseEvent.SerializationFormat.JSON);
            
        } catch (Exception e) {
            log.error("❌ Lỗi khi nén và đẩy Parquet cho Order {}: {}", orderId, e.getMessage());
        }
    }

    // Sử dụng Object để xử lý linh hoạt timestamp
    private LocalDateTime convertMicroTimestamp(Object ts) {
        if (ts == null) return null;
        try {
            long micros = Long.parseLong(ts.toString());
            return LocalDateTime.ofInstant(Instant.ofEpochMilli(micros / 1000), ZoneId.systemDefault());
        } catch (Exception e) {
            return null;
        }
    }
}