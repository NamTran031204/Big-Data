package com.example.BigData.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProductDetailDto {

    @JsonProperty("product_id")
    private String productId;

    @JsonProperty("product_category_name")
    private String productCategoryName;

    @JsonProperty("product_category_name_english")
    private String productCategoryNameEnglish;

    // Giữ nguyên typo "lenght" để match field name frontend đang dùng
    @JsonProperty("product_name_lenght")
    private Integer productNameLength;

    // Frontend dùng "product_description_length" (không typo)
    @JsonProperty("product_description_length")
    private Integer productDescriptionLength;

    @JsonProperty("product_photos_qty")
    private Integer productPhotosQty;

    @JsonProperty("product_weight_g")
    private Integer productWeightG;

    @JsonProperty("product_length_cm")
    private Integer productLengthCm;

    @JsonProperty("product_height_cm")
    private Integer productHeightCm;

    @JsonProperty("product_width_cm")
    private Integer productWidthCm;
}
