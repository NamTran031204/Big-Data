package com.example.BigData.controller;


import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import com.example.BigData.repository.mongodb.OrderAnalyticsMongoRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/analytics/orders")
@RequiredArgsConstructor
public class OrderAnalyticsController {

    private final OrderAnalyticsMongoRepository mongoRepository;

    // GET /api/analytics/orders
    @GetMapping
    public ResponseEntity<List<OrderAnalyticsDocument>> getAllOrders() {
        return ResponseEntity.ok(mongoRepository.findAll());
    }

    // GET /api/analytics/orders/{id}
    @GetMapping("/{id}")
    public ResponseEntity<OrderAnalyticsDocument> getOrderById(@PathVariable String id) {
        return mongoRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}