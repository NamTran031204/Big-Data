package com.example.BigData.entity.mongodb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

// entity/mongodb/OrderAnalyticsDocument.java
@Document(collection = "order_analytics")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderAnalyticsDocument {

    @Id
    private String orderId;

    // Customer info (denormalized)
    private String customerId;
    private String customerState;
    private String customerCity;

    // Order info
    private String orderStatus;
    private LocalDateTime purchaseTimestamp;
    private LocalDateTime deliveredDate;
    private LocalDateTime estimatedDeliveryDate;

    // Items (embedded)
    private List<ItemSummary> items = new ArrayList<>();

    // Payment summary
    private BigDecimal totalPaymentValue;
    private String primaryPaymentType;

    // Review
    private Integer reviewScore;

    // Computed fields
    private Integer deliveryDelayDays;    // actual vs estimated
    private BigDecimal totalItemValue;
    private Integer itemCount;

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    public static class ItemSummary {
        private String productId;
        private String categoryName;
        private String categoryNameEnglish;
        private String sellerId;
        private BigDecimal price;
        private BigDecimal freightValue;
    }
}