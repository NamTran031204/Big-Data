package com.example.BigData.entity.postgres;


import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

// entity/postgres/OrderItemEntity.java
@Entity
@Table(name = "order_items")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderItemEntity {

    @EmbeddedId
    private OrderItemId id; // composite key

    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("orderId")
    @JoinColumn(name = "order_id")
    private OrderEntity order;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id")
    private ProductEntity product;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "seller_id")
    private SellerEntity seller;

    @Column(name = "shipping_limit_date")
    private LocalDateTime shippingLimitDate;

    @Column(name = "price", precision = 10, scale = 2)
    private BigDecimal price;

    @Column(name = "freight_value", precision = 10, scale = 2)
    private BigDecimal freightValue;

    // Composite Key
    @Embeddable
    @Data
    public static class OrderItemId implements Serializable {
        @Column(name = "order_id")
        private String orderId;

        @Column(name = "order_item_id")
        private Integer orderItemId;
    }
}