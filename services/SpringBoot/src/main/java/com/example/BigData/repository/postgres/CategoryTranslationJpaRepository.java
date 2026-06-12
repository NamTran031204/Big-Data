package com.example.BigData.repository.postgres;

import com.example.BigData.entity.postgres.ProductCategoryTranslationEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CategoryTranslationJpaRepository extends JpaRepository<ProductCategoryTranslationEntity, String> {
}
