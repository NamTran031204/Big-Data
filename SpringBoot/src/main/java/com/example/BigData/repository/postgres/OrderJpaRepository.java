package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.OrderEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface OrderJpaRepository extends JpaRepository<OrderEntity, String> {
    // Có thể viết thêm hàm tìm kiếm nếu cần, ví dụ:
    // List<OrderEntity> findByOrderStatus(OrderEntity.OrderStatus status);
}