package com.example.BigData.entity.kafka;

import com.example.BigData.entity.kafka.base.BaseEvent;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderEvent extends BaseEvent {
    private String eventId;
    private String eventType;        // ORDER_CREATED, ORDER_UPDATED, ORDER_DELIVERED
    private String orderId;
    private String customerId;
    private String orderStatus;
    private String eventTimestamp;
//    private Map<String, Object> payload;
}
