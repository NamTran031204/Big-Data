package com.example.BigData.entity.kafka;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderEvent {
    private String eventId;
    private String eventType;        // ORDER_CREATED, ORDER_UPDATED, ORDER_DELIVERED
    private String orderId;
    private String customerId;
    private String orderStatus;
    private LocalDateTime eventTimestamp;
    private Map<String, Object> payload;
}
