package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.CustomerEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CustomerJpaRepository extends JpaRepository<CustomerEntity, String> {
    // JpaRepository đã có sẵn findById, dùng để tìm theo customer_id
}