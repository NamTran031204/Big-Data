package com.example.BigData.service;

import com.example.BigData.entity.kafka.UserBehaviorEvent;
import com.example.BigData.entity.postgres.CustomerEntity;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.repository.postgres.CustomerJpaRepository;
import com.example.BigData.repository.postgres.ProductJpaRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;


@Slf4j
@Service
@RequiredArgsConstructor
public class ReferenceDataService {
    private final CustomerJpaRepository customerRepository;
    private final ProductJpaRepository productRepository;
    private final KafkaTemplate<String, UserBehaviorEvent> kafkaTemplate;
    private final List<CustomerEntity> customerCache = new ArrayList<>();
    private final List<ProductEntity> productCache = new ArrayList<>();

    @PostConstruct
    public void loadReferenceData() {

        log.info("Loading customers...");

        customerCache.addAll(customerRepository.findAll());

        log.info("Loaded {} customers", customerCache.size());

        log.info("Loading products...");

        productCache.addAll(productRepository.findAll());

        log.info("Loaded {} products", productCache.size());
    }


    @Scheduled(fixedRate = 3000)
    public void publishFakeEvent() {

        if (customerCache.isEmpty() || productCache.isEmpty()) {

            log.warn("Reference cache empty");

            return;
        }

        CustomerEntity customer =
                customerCache.get(
                        ThreadLocalRandom.current()
                                .nextInt(customerCache.size())
                );

        ProductEntity product =
                productCache.get(
                        ThreadLocalRandom.current()
                                .nextInt(productCache.size())
                );

        String eventType = randomEventType();

        String category = product.getProductCategoryName();

        String searchTerm = null;

        if ("search".equals(eventType) && category != null) {

            searchTerm = category.contains("_")
                    ? category.substring(0, category.indexOf("_"))
                    : category;
        }

        UserBehaviorEvent event =
                UserBehaviorEvent.builder()
                        .eventId(UUID.randomUUID().toString())
                        .eventType(eventType)
                        .eventTime(Instant.now())
                        .userId(customer.getCustomerId())
                        .sessionId(UUID.randomUUID().toString())
                        .productId(product.getProductId())
                        .category(category)
                        .dwellTimeMs(
                                ThreadLocalRandom.current()
                                        .nextLong(1000, 20000)
                        )
                        .searchTerm(searchTerm)
                        .build();

        kafkaTemplate.send(
                "user_behavior_events",
                event.getUserId(),
                event
        );

        log.info("Published event: {}", event);
    }


    private String randomEventType() {

        List<String> eventTypes = List.of(
                "view_product",
                "like_product",
                "search",
                "add_to_cart"
        );

        return eventTypes.get(
                ThreadLocalRandom.current()
                        .nextInt(eventTypes.size())
        );
    }

}
