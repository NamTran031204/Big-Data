package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.OrderItemEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface OrderItemJpaRepository extends JpaRepository<OrderItemEntity, OrderItemEntity.OrderItemId> {
    
    List<OrderItemEntity> findByIdOrderId(String orderId);
}