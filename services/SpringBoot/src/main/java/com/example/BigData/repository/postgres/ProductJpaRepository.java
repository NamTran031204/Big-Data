package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface ProductJpaRepository extends JpaRepository<ProductEntity, String> {

    @Query("SELECT p FROM ProductEntity p LEFT JOIN FETCH p.categoryTranslation WHERE p.productId = :id")
    Optional<ProductEntity> findByIdWithTranslation(@Param("id") String id);
}
