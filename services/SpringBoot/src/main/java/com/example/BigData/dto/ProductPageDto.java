package com.example.BigData.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProductPageDto {

    @JsonProperty("data")
    private List<ProductSummaryDto> data;

    @JsonProperty("total")
    private long total;

    @JsonProperty("page")
    private int page;
}
