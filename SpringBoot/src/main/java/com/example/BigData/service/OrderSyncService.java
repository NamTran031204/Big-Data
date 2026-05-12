package com.example.BigData.service;

import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument.ItemSummary;
import com.example.BigData.entity.postgres.OrderItemEntity;
import com.example.BigData.entity.postgres.ProductEntity;
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
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderSyncService {

    private final OrderAnalyticsMongoRepository mongoRepository;
    private final CustomerJpaRepository customerRepository;
    private final OrderItemJpaRepository itemRepository;

    public void syncOrderToMongo(CdcEvent cdcEvent) {
        if (cdcEvent.getPayload() == null) return;

        String op = cdcEvent.getPayload().getOp();
        Map<String, Object> data = ("d".equals(op)) 
                ? cdcEvent.getPayload().getBefore().getFields() 
                : cdcEvent.getPayload().getAfter().getFields();

        String orderId = (String) data.get("order_id");
        if (orderId == null) return;

        try {
            if ("d".equals(op)) {
                mongoRepository.deleteById(orderId);
                log.info("🗑️ [Gold] Đã xóa Order: {}", orderId);
                return;
            }
            handleSaveOrUpdate(orderId, data);
        } catch (Exception e) {
            log.error("❌ Lỗi xử lý Gold Layer cho Order {}: {}", orderId, e.getMessage());
        }
    }

    private void handleSaveOrUpdate(String orderId, Map<String, Object> data) {
        OrderAnalyticsDocument document = mongoRepository.findById(orderId)
                .orElse(new OrderAnalyticsDocument());

        // 1. Mapping thông tin cơ bản từ Kafka
        document.setOrderId(orderId);
        document.setCustomerId((String) data.get("customer_id"));
        document.setOrderStatus((String) data.get("order_status"));
        document.setPurchaseTimestamp(convertMicroTimestamp(data.get("order_purchase_timestamp")));
        document.setDeliveredDate(convertMicroTimestamp(data.get("order_delivered_customer_date")));
        document.setEstimatedDeliveryDate(convertMicroTimestamp(data.get("order_estimated_delivery_date")));

        // 2. DATA ENRICHMENT (Làm giàu dữ liệu từ Silver - PostgreSQL)
        
        // Làm giàu thông tin khách hàng
        customerRepository.findById(document.getCustomerId()).ifPresent(c -> {
            document.setCustomerCity(c.getCity());
            document.setCustomerState(c.getState());
        });

        // Làm giàu danh sách Items và thông tin Product (bao gồm Translation)
        List<OrderItemEntity> postgresItems = itemRepository.findByIdOrderId(orderId);
        
        List<ItemSummary> itemSummaries = postgresItems.stream().map(item -> {
            ItemSummary summary = new ItemSummary();
            ProductEntity product = item.getProduct();
            
            summary.setProductId(product.getProductId());
            summary.setSellerId(item.getSeller().getSellerId());
            summary.setPrice(item.getPrice());
            summary.setFreightValue(item.getFreightValue());
            
            // Lấy tên Category gốc (Bồ Đào Nha) từ ProductEntity
            summary.setCategoryName(product.getProductCategoryName());
            
            // Lấy tên Category dịch (Anh) từ ProductCategoryTranslationEntity
            if (product.getCategoryTranslation() != null) {
                summary.setCategoryNameEnglish(product.getCategoryTranslation().getProductCategoryNameEnglish());
            }
            
            return summary;
        }).collect(Collectors.toList());

        document.setItems(itemSummaries);

        // 3. COMPUTED FIELDS (Tính toán chỉ số Analytics)
        
        // Tính độ trễ giao hàng
        if (document.getDeliveredDate() != null && document.getEstimatedDeliveryDate() != null) {
            long delay = ChronoUnit.DAYS.between(document.getEstimatedDeliveryDate(), document.getDeliveredDate());
            document.setDeliveryDelayDays((int) delay);
        }

        // Tính tổng giá trị đơn hàng (Price + Freight)
        BigDecimal totalValue = itemSummaries.stream()
                .map(i -> i.getPrice().add(i.getFreightValue()))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        document.setTotalItemValue(totalValue);
        document.setItemCount(itemSummaries.size());

        // 4. Lưu vào Gold Layer (MongoDB)
        mongoRepository.save(document);
        log.info("⭐ [Gold] Đã tổng hợp dữ liệu thành công cho Order: {}", orderId);
    }

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