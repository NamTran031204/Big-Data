package com.example.BigData.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecommendationResponseDto {

    @JsonProperty("user_id")
    private String userId;

    /** "personalized" nếu user có lịch sử, "popular" nếu cold-start. */
    @JsonProperty("source")
    private String source;

    @JsonProperty("recommendations")
    private List<RecommendationItemDto> recommendations;
}
