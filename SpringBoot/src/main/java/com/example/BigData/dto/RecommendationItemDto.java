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
public class RecommendationItemDto {

    @JsonProperty("product_id")
    private String productId;

    @JsonProperty("category")
    private String category;

    @JsonProperty("category_english")
    private String categoryEnglish;

    @JsonProperty("score")
    private Double score;
}
