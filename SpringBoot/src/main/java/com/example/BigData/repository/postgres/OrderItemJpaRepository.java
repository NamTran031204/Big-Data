package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.OrderItemEntity;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface OrderItemJpaRepository extends JpaRepository<OrderItemEntity, OrderItemEntity.OrderItemId> {

    List<OrderItemEntity> findByIdOrderId(String orderId);

    interface OrderItemSummary {
        String getOrderId();
        String getProductId();
        String getSellerId();
    }

    @Query("SELECT oi.id.orderId AS orderId, " +
           "oi.product.productId AS productId, " +
           "oi.seller.sellerId AS sellerId " +
           "FROM OrderItemEntity oi " +
           "WHERE oi.product IS NOT NULL AND oi.seller IS NOT NULL")
    List<OrderItemSummary> findOrderItemSummaries(Pageable pageable);
}