package com.example.BigData.entity.mongodb;


import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Document(collection = "seller_performance")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SellerPerformanceDocument {

    @Id
    private String sellerId;

    private String sellerCity;
    private String sellerState;

    // Aggregated metrics
    private Integer totalOrders;
    private BigDecimal totalRevenue;
    private Double avgReviewScore;
    private Integer totalProductsSold;
    private Double onTimeDeliveryRate;

    private LocalDateTime lastUpdated;
}
