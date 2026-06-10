package com.example.BigData.controller;

import com.example.BigData.dto.ProductDetailDto;
import com.example.BigData.dto.ProductPageDto;
import com.example.BigData.dto.RecommendationResponseDto;
import com.example.BigData.service.ProductApiService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api")
public class ProductController {

    private final ProductApiService productApiService;

    public ProductController(ProductApiService productApiService) {
        this.productApiService = productApiService;
    }

    /** Danh sách sản phẩm phân trang. */
    @GetMapping("/products")
    public ProductPageDto getProducts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "8") int size) {
        log.debug("GET /api/products page={} size={}", page, size);
        return productApiService.getProductsPage(page, size);
    }

    /** Chi tiết một sản phẩm theo ID. */
    @GetMapping("/products/{productId}")
    public ProductDetailDto getProductDetail(@PathVariable String productId) {
        log.debug("GET /api/products/{}", productId);
        return productApiService.getProductDetail(productId);
    }

    /** Gợi ý sản phẩm: cá nhân hóa nếu userId có lịch sử, cold-start nếu không. */
    @GetMapping("/recommend")
    public RecommendationResponseDto getRecommendations(
            @RequestParam String userId) {
        log.debug("GET /api/recommend userId={}", userId);
        return productApiService.getRecommendations(userId);
    }
}
