package com.example.BigData.entity.postgres;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;


// entity/postgres/OrderPaymentEntity.java
@Entity
@Table(name = "order_payments")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderPaymentEntity {

    @EmbeddedId
    private OrderPaymentId id;

    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("orderId")
    @JoinColumn(name = "order_id")
    private OrderEntity order;

    @Enumerated(EnumType.STRING)
    @Column(name = "payment_type", length = 20)
    private PaymentType paymentType;

    @Column(name = "payment_installments")
    private Integer paymentInstallments;

    @Column(name = "payment_value", precision = 10, scale = 2)
    private BigDecimal paymentValue;

    public enum PaymentType {
        credit_card, boleto, voucher, debit_card, not_defined
    }

    @Embeddable
    @Data
    public static class OrderPaymentId implements Serializable {
        @Column(name = "order_id")
        private String orderId;

        @Column(name = "payment_sequential")
        private Integer paymentSequential;
    }
}