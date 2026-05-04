package com.example.BigData.entity.postgres;


import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;


import java.util.ArrayList;
import java.util.List;

// entity/postgres/ProductEntity.java
@Entity
@Table(name = "products")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProductEntity {

    @Id
    @Column(name = "product_id", length = 50)
    private String productId;

    @Column(name = "product_category_name", length = 100)
    private String productCategoryName;

    @Column(name = "product_name_lenght")
    private Integer productNameLength;

    @Column(name = "product_description_lenght")
    private Integer productDescriptionLength;

    @Column(name = "product_photos_qty")
    private Integer productPhotosQty;

    @Column(name = "product_weight_g")
    private Integer productWeightG;

    @Column(name = "product_length_cm")
    private Integer productLengthCm;

    @Column(name = "product_height_cm")
    private Integer productHeightCm;

    @Column(name = "product_width_cm")
    private Integer productWidthCm;

    // Join với translation
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_category_name",
            referencedColumnName = "product_category_name",
            insertable = false, updatable = false)
    private ProductCategoryTranslationEntity categoryTranslation;

    @OneToMany(mappedBy = "product", fetch = FetchType.LAZY)
    @JsonIgnore
    private List<OrderItemEntity> orderItems = new ArrayList<>();
}