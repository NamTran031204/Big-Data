package com.example.BigData.entity.kafka;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserBehaviorEvent {
    private String eventId;

    private String eventType;

    private Instant eventTime;

    private String userId;

    private String sessionId;

    private String productId;

    private String sellerId;

    private String category;

    private Long dwellTimeMs;

    private String searchTerm;
}
