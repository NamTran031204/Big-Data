package com.example.BigData.entity.postgres;



import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

// entity/postgres/OrderEntity.java
@Entity
@Table(name = "orders", indexes = {
        @Index(name = "idx_order_status", columnList = "order_status"),
        @Index(name = "idx_order_purchase_timestamp", columnList = "order_purchase_timestamp")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderEntity {

    @Id
    @Column(name = "order_id", length = 50)
    private String orderId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id", nullable = false)
    private CustomerEntity customer;

    @Enumerated(EnumType.STRING)
    @Column(name = "order_status", length = 20)
    private OrderStatus orderStatus;

    @Column(name = "order_purchase_timestamp")
    private LocalDateTime orderPurchaseTimestamp;

    @Column(name = "order_approved_at")
    private LocalDateTime orderApprovedAt;

    @Column(name = "order_delivered_carrier_date")
    private LocalDateTime orderDeliveredCarrierDate;

    @Column(name = "order_delivered_customer_date")
    private LocalDateTime orderDeliveredCustomerDate;

    @Column(name = "order_estimated_delivery_date")
    private LocalDateTime orderEstimatedDeliveryDate;

    // Relationships
    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<OrderItemEntity> orderItems = new ArrayList<>();

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<OrderPaymentEntity> payments = new ArrayList<>();

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<OrderReviewEntity> reviews = new ArrayList<>();

    // Enum bên trong
    public enum OrderStatus {
        created, approved, invoiced, processing,
        shipped, delivered, unavailable, canceled
    }
}