package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductJpaRepository extends JpaRepository<ProductEntity, String> {
}
