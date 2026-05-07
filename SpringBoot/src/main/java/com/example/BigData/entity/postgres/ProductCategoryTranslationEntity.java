package com.example.BigData.entity.postgres;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.*;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "product_category_name_translation")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProductCategoryTranslationEntity {

    @Id
    @Column(name = "product_category_name", length = 100)
    private String productCategoryName;

    @Column(name = "product_category_name_english", length = 100)
    private String productCategoryNameEnglish;
}