package com.example.BigData.service;

import com.example.BigData.entity.kafka.UserBehaviorEvent;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.repository.postgres.OrderItemJpaRepository;
import com.example.BigData.repository.postgres.ProductJpaRepository;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

@Slf4j
@Service
public class FakeUserBehaviorScheduler {

    private final ProductJpaRepository productRepo;
    private final OrderItemJpaRepository orderItemRepo;
    private final ReferenceDataService referenceDataService;

    // Loaded once at startup — all volatile for cross-thread visibility
    private volatile List<ProductEntity> allProducts = Collections.emptyList();
    private volatile Map<String, ProductEntity> productById = Collections.emptyMap();
    private volatile Map<String, List<ProductEntity>> productsByCategory = Collections.emptyMap();
    private volatile Map<String, List<String>> coPurchaseMap = Collections.emptyMap();
    private volatile Map<String, String> productSellerMap = Collections.emptyMap();
    private volatile int[] popularityWeights = new int[0];
    private volatile int totalWeight = 0;
    private volatile boolean dataReady = false;

    public FakeUserBehaviorScheduler(
            ProductJpaRepository productRepo,
            OrderItemJpaRepository orderItemRepo,
            ReferenceDataService referenceDataService) {
        this.productRepo = productRepo;
        this.orderItemRepo = orderItemRepo;
        this.referenceDataService = referenceDataService;
    }

    @PostConstruct
    public void loadReferenceData() {
        try {
            log.info("FakeUserBehaviorScheduler: loading reference data...");

            List<ProductEntity> products = productRepo.findAll();
            if (products.isEmpty()) {
                log.warn("FakeUserBehaviorScheduler: no products found — scheduler will be skipped.");
                return;
            }
            this.allProducts = Collections.unmodifiableList(products);

            this.productById = products.stream()
                    .collect(Collectors.toUnmodifiableMap(ProductEntity::getProductId, p -> p));

            this.productsByCategory = products.stream()
                    .filter(p -> p.getProductCategoryName() != null)
                    .collect(Collectors.groupingBy(
                            ProductEntity::getProductCategoryName,
                            Collectors.toUnmodifiableList()));

            // Sample 5000 order items — JPQL projection avoids N+1 / lazy init issues
            List<OrderItemJpaRepository.OrderItemSummary> sample =
                    orderItemRepo.findOrderItemSummaries(PageRequest.of(0, 5000));

            Map<String, Integer> purchaseCounts = new HashMap<>();
            Map<String, List<String>> orderToProducts = new HashMap<>();
            Map<String, String> pToSeller = new HashMap<>();

            for (OrderItemJpaRepository.OrderItemSummary s : sample) {
                purchaseCounts.merge(s.getProductId(), 1, (a, b) -> a + b);
                orderToProducts.computeIfAbsent(s.getOrderId(), k -> new ArrayList<>())
                               .add(s.getProductId());
                pToSeller.putIfAbsent(s.getProductId(), s.getSellerId());
            }
            this.productSellerMap = Collections.unmodifiableMap(pToSeller);

            // Build co-purchase map: products appearing together in same order
            Map<String, List<String>> coPurchase = new HashMap<>();
            for (List<String> orderProducts : orderToProducts.values()) {
                if (orderProducts.size() < 2) continue;
                for (int i = 0; i < orderProducts.size(); i++) {
                    for (int j = 0; j < orderProducts.size(); j++) {
                        if (i != j) {
                            coPurchase.computeIfAbsent(orderProducts.get(i), k -> new ArrayList<>())
                                      .add(orderProducts.get(j));
                        }
                    }
                }
            }
            this.coPurchaseMap = Collections.unmodifiableMap(coPurchase);

            // Build popularity weight array aligned with allProducts index
            int[] weights = new int[allProducts.size()];
            int total = 0;
            for (int i = 0; i < allProducts.size(); i++) {
                int w = purchaseCounts.getOrDefault(allProducts.get(i).getProductId(), 0) + 1;
                weights[i] = w;
                total += w;
            }
            this.popularityWeights = weights;
            this.totalWeight = total;

            this.dataReady = true;
            log.info("FakeUserBehaviorScheduler: ready. {} products, {} categories, {} co-purchase pairs loaded.",
                    allProducts.size(), productsByCategory.size(), coPurchaseMap.size());

        } catch (Exception e) {
            log.error("FakeUserBehaviorScheduler: failed to load reference data — scheduler disabled. Cause: {}", e.getMessage(), e);
        }
    }

    // One session every 5 seconds (after previous session completes)
    @Scheduled(fixedDelay = 5000)
    public void generateSession() {
        if (!dataReady || allProducts.isEmpty()) return;

        try {
            ThreadLocalRandom rng = ThreadLocalRandom.current();

            ProductEntity anchor = pickWeightedProduct(rng);
            String anchorCategory = anchor.getProductCategoryName();

            List<ProductEntity> categoryPeers = productsByCategory.getOrDefault(anchorCategory, allProducts);
            List<ProductEntity> competitors = pickCompetitors(categoryPeers, anchor.getProductId(), rng, 2, 3);

            String sessionId = UUID.randomUUID().toString();
            String userId = "user_" + rng.nextInt(1, 501);

            // Session started 5–20 minutes ago
            long[] cursorMs = { Instant.now().minusSeconds(rng.nextLong(5 * 60, 20 * 60 + 1)).toEpochMilli() };

            // Browsing/comparison phase: VIEW competitors with low dwell
            for (ProductEntity comp : competitors) {
                long dwell = rng.nextLong(5_000, 25_001);
                emitEvent(sessionId, userId, "VIEW", comp, dwell, cursorMs, rng);
            }

            // Serious consideration: VIEW anchor with high dwell
            long anchorDwell = rng.nextLong(60_000, 180_001);
            emitEvent(sessionId, userId, "VIEW", anchor, anchorDwell, cursorMs, rng);

            // Funnel: CLICK (60%) → ADD_TO_CART (30%) → PURCHASE (15%)
            double roll = rng.nextDouble();
            if (roll < 0.60) {
                emitEvent(sessionId, userId, "CLICK", anchor, null, cursorMs, rng);

                if (roll < 0.30) {
                    emitEvent(sessionId, userId, "ADD_TO_CART", anchor, null, cursorMs, rng);

                    if (roll < 0.15) {
                        emitEvent(sessionId, userId, "PURCHASE", anchor, null, cursorMs, rng);

                        // 40% chance: VIEW a co-purchased product after buying
                        if (rng.nextDouble() < 0.40) {
                            List<String> coPurchased = coPurchaseMap.get(anchor.getProductId());
                            if (coPurchased != null && !coPurchased.isEmpty()) {
                                String coProdId = coPurchased.get(rng.nextInt(coPurchased.size()));
                                ProductEntity coProd = productById.get(coProdId);
                                if (coProd != null) {
                                    long coDwell = rng.nextLong(10_000, 40_001);
                                    emitEvent(sessionId, userId, "VIEW", coProd, coDwell, cursorMs, rng);
                                }
                            }
                        }
                    }
                }
            }

            log.debug("FakeUserBehaviorScheduler: session {} | user {} | anchor {}",
                    sessionId, userId, anchor.getProductId());

        } catch (Exception e) {
            log.error("FakeUserBehaviorScheduler: error generating session: {}", e.getMessage(), e);
        }
    }

    // Weighted random pick from allProducts by purchase popularity
    private ProductEntity pickWeightedProduct(ThreadLocalRandom rng) {
        int dart = rng.nextInt(totalWeight);
        int cumulative = 0;
        for (int i = 0; i < allProducts.size(); i++) {
            cumulative += popularityWeights[i];
            if (dart < cumulative) return allProducts.get(i);
        }
        return allProducts.get(allProducts.size() - 1);
    }

    // Pick 2–3 competitors from same category, excluding the anchor product
    private List<ProductEntity> pickCompetitors(
            List<ProductEntity> pool, String excludeId,
            ThreadLocalRandom rng, int minCount, int maxCount) {

        List<ProductEntity> candidates = pool.stream()
                .filter(p -> !p.getProductId().equals(excludeId))
                .collect(Collectors.toCollection(ArrayList::new));

        Collections.shuffle(candidates, rng);

        int count = Math.min(rng.nextInt(minCount, maxCount + 1), candidates.size());
        return candidates.subList(0, count);
    }

    // Build and send one UserBehaviorEvent, then advance the session time cursor
    private void emitEvent(
            String sessionId, String userId,
            String eventType, ProductEntity product,
            Long dwellTimeMs, long[] cursorMs, ThreadLocalRandom rng) {

        UserBehaviorEvent event = UserBehaviorEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType(eventType)
                .eventTime(LocalDateTime.now())
                .userId(userId)
                .sessionId(sessionId)
                .productId(product.getProductId())
                .sellerId(productSellerMap.get(product.getProductId()))
                .category(product.getProductCategoryName())
                .dwellTimeMs(dwellTimeMs)
                .searchTerm(null)
                .build();

        log.info("event {}: {}",userId, event);

        referenceDataService.sendEvent(event);

        // Advance cursor: dwell time (for VIEW) + inter-event gap of 2–10s
        long gap = rng.nextLong(2_000, 10_001);
        cursorMs[0] += (dwellTimeMs != null ? dwellTimeMs : 0) + gap;
    }
}
