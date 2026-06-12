package com.example.BigData.service;

import com.example.BigData.dto.*;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.repository.postgres.ProductJpaRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Slf4j
@Service
public class ProductApiService {

    private static final String SQL_PERSONALIZED = """
            SELECT p.product_id,
                   p.product_category_name,
                   ct.product_category_name_english,
                   ur.recommendation_score
            FROM user_recommendation ur
            JOIN products p ON ur.product_id = p.product_id
            LEFT JOIN category_translation ct
                   ON p.product_category_name = ct.product_category_name
            WHERE ur.user_id = ?
            ORDER BY ur.sequence_no ASC
            LIMIT 10
            """;

    private static final String SQL_COLD_START = """
            SELECT p.product_id,
                   p.product_category_name,
                   ct.product_category_name_english,
                   COUNT(*) AS cnt
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            LEFT JOIN category_translation ct
                   ON p.product_category_name = ct.product_category_name
            GROUP BY p.product_id, p.product_category_name, ct.product_category_name_english
            ORDER BY cnt DESC
            LIMIT 10
            """;

    private static final String SQL_COUNT_REC = """
            SELECT COUNT(*) FROM user_recommendation WHERE user_id = ?
            """;

    private final ProductJpaRepository productRepo;
    private final JdbcTemplate jdbc;

    public ProductApiService(ProductJpaRepository productRepo, JdbcTemplate jdbc) {
        this.productRepo = productRepo;
        this.jdbc = jdbc;
    }

    public ProductPageDto getProductsPage(int page, int size) {
        Page<ProductEntity> result = productRepo.findAll(PageRequest.of(page - 1, size));
        List<ProductSummaryDto> data = result.getContent().stream()
                .map(p -> new ProductSummaryDto(p.getProductId(), p.getProductCategoryName()))
                .toList();
        return new ProductPageDto(data, result.getTotalElements(), page);
    }

    @Transactional(readOnly = true)
    public ProductDetailDto getProductDetail(String productId) {
        ProductEntity p = productRepo.findByIdWithTranslation(productId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Product not found: " + productId));

        String englishName = (p.getCategoryTranslation() != null)
                ? p.getCategoryTranslation().getProductCategoryNameEnglish()
                : null;

        return ProductDetailDto.builder()
                .productId(p.getProductId())
                .productCategoryName(p.getProductCategoryName())
                .productCategoryNameEnglish(englishName)
                .productNameLength(p.getProductNameLength())
                .productDescriptionLength(p.getProductDescriptionLength())
                .productPhotosQty(p.getProductPhotosQty())
                .productWeightG(p.getProductWeightG())
                .productLengthCm(p.getProductLengthCm())
                .productHeightCm(p.getProductHeightCm())
                .productWidthCm(p.getProductWidthCm())
                .build();
    }

    public RecommendationResponseDto getRecommendations(String userId) {
        Integer count = jdbc.queryForObject(SQL_COUNT_REC, Integer.class, userId);
        boolean hasHistory = count != null && count > 0;

        if (hasHistory) {
            List<RecommendationItemDto> items = jdbc.query(SQL_PERSONALIZED,
                    (rs, rowNum) -> RecommendationItemDto.builder()
                            .productId(rs.getString("product_id"))
                            .category(rs.getString("product_category_name"))
                            .categoryEnglish(rs.getString("product_category_name_english"))
                            .score(rs.getDouble("recommendation_score"))
                            .build(),
                    userId);
            log.info("Recommendations: userId={} source=personalized items={}", userId, items.size());
            return RecommendationResponseDto.builder()
                    .userId(userId)
                    .source("personalized")
                    .recommendations(items)
                    .build();
        }

        List<RecommendationItemDto> items = jdbc.query(SQL_COLD_START,
                (rs, rowNum) -> RecommendationItemDto.builder()
                        .productId(rs.getString("product_id"))
                        .category(rs.getString("product_category_name"))
                        .categoryEnglish(rs.getString("product_category_name_english"))
                        .score(null)
                        .build());
        log.info("Recommendations: userId={} source=popular (cold-start) items={}", userId, items.size());
        return RecommendationResponseDto.builder()
                .userId(userId)
                .source("popular")
                .recommendations(items)
                .build();
    }
}
