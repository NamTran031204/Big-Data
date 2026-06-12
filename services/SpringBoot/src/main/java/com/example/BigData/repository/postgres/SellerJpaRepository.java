package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.SellerEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SellerJpaRepository extends JpaRepository<SellerEntity, String> {
}
