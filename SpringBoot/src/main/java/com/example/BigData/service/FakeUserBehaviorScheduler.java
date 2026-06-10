package com.example.BigData.service;

import com.example.BigData.entity.kafka.UserBehaviorEvent;
import com.example.BigData.entity.postgres.CustomerEntity;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.repository.postgres.CustomerJpaRepository;
import com.example.BigData.repository.postgres.OrderItemJpaRepository;
import com.example.BigData.repository.postgres.ProductJpaRepository;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

/**
 * Sinh user-behavior sessions và emit Kafka events (VIEW / CLICK / ADD_TO_CART / PURCHASE).
 *
 * userId lấy từ 5 customer THẬT trong DB (không dùng "user_XXX" giả).
 * Tất cả product và category đều load từ DB.
 * Khi event PURCHASE xảy ra: ngoài việc gửi Kafka còn INSERT order graph vào Postgres
 * (orders + order_items + order_payments) để CDC bắt được, dùng TransactionTemplate cho atomicity.
 */
@Slf4j
@Service
public class FakeUserBehaviorScheduler {

    private final ProductJpaRepository productRepo;
    private final OrderItemJpaRepository orderItemRepo;
    private final CustomerJpaRepository customerRepo;
    private final ReferenceDataService referenceDataService;
    private final JdbcTemplate jdbc;
    private final TransactionTemplate txTemplate;

    private static final String[] PAYMENT_TYPES = {"credit_card", "boleto", "voucher", "debit_card"};

    // Loaded once at startup — volatile for cross-thread visibility
    private volatile List<ProductEntity> allProducts = Collections.emptyList();
    private volatile Map<String, ProductEntity> productById = Collections.emptyMap();
    private volatile Map<String, List<ProductEntity>> productsByCategory = Collections.emptyMap();
    private volatile Map<String, List<String>> coPurchaseMap = Collections.emptyMap();
    private volatile Map<String, String> productSellerMap = Collections.emptyMap();
    private volatile int[] popularityWeights = new int[0];
    private volatile int totalWeight = 0;
    private volatile List<String> realCustomerIds = Collections.emptyList();
    private volatile boolean dataReady = false;

    public FakeUserBehaviorScheduler(
            ProductJpaRepository productRepo,
            OrderItemJpaRepository orderItemRepo,
            CustomerJpaRepository customerRepo,
            ReferenceDataService referenceDataService,
            JdbcTemplate jdbc,
            PlatformTransactionManager txManager) {
        this.productRepo = productRepo;
        this.orderItemRepo = orderItemRepo;
        this.customerRepo = customerRepo;
        this.referenceDataService = referenceDataService;
        this.jdbc = jdbc;
        this.txTemplate = new TransactionTemplate(txManager);
    }

    @PostConstruct
    public void loadReferenceData() {
        try {
            log.info("FakeUserBehaviorScheduler: loading reference data...");

            this.realCustomerIds = customerRepo.findAll(PageRequest.of(0, 5)).getContent()
                    .stream().map(CustomerEntity::getCustomerId)
                    .collect(Collectors.toUnmodifiableList());
            if (realCustomerIds.isEmpty()) {
                log.warn("FakeUserBehaviorScheduler: no real customers found.");
            }

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

            List<OrderItemJpaRepository.OrderItemSummary> sample =
                    orderItemRepo.findOrderItemSummaries(PageRequest.of(0, 5000));
            Map<String, Integer> purchaseCounts = new HashMap<>();
            Map<String, List<String>> orderToProducts = new HashMap<>();
            Map<String, String> pToSeller = new HashMap<>();
            for (OrderItemJpaRepository.OrderItemSummary s : sample) {
                purchaseCounts.merge(s.getProductId(), 1, Integer::sum);
                orderToProducts.computeIfAbsent(s.getOrderId(), k -> new ArrayList<>()).add(s.getProductId());
                pToSeller.putIfAbsent(s.getProductId(), s.getSellerId());
            }
            this.productSellerMap = Collections.unmodifiableMap(pToSeller);

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
            log.info("FakeUserBehaviorScheduler: ready. products={}, categories={}, customers={}, co-purchase pairs={}",
                    allProducts.size(), productsByCategory.size(), realCustomerIds.size(), coPurchaseMap.size());
        } catch (Exception e) {
            log.error("FakeUserBehaviorScheduler: failed to load reference data. Cause: {}", e.getMessage(), e);
        }
    }

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
            // lay userId tu db
            String userId = realCustomerIds.isEmpty()
                    ? "user_" + rng.nextInt(1, 501)
                    : realCustomerIds.get(rng.nextInt(realCustomerIds.size()));

            // Session started 5–20 minutes ago
            long[] cursorMs = {Instant.now().minusSeconds(rng.nextLong(5 * 60, 20 * 60 + 1)).toEpochMilli()};

            // Browsing phase: VIEW competitors with low dwell
            for (ProductEntity comp : competitors) {
                long dwell = rng.nextLong(5_000, 25_001);
                emitEvent(sessionId, userId, "VIEW", comp, dwell, cursorMs, rng);
            }

            // Consideration: VIEW anchor with high dwell
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
                        // Lưu đơn hàng vào Postgres để CDC bắt được
                        savePurchaseOrder(userId, anchor, rng);

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

    private void savePurchaseOrder(String customerId, ProductEntity product, ThreadLocalRandom rng) {
        String sellerId = productSellerMap.get(product.getProductId());
        if (sellerId == null) {
            log.warn("FakeUserBehaviorScheduler: no seller for product {} — purchase order skipped.", product.getProductId());
            return;
        }
        String orderId = "sim_o_" + UUID.randomUUID().toString().replace("-", "");
        Instant purchase = Instant.now();
        double price   = Math.round(rng.nextDouble(10.0, 500.0) * 100.0) / 100.0;
        double freight = Math.round(rng.nextDouble(5.0,  50.0)  * 100.0) / 100.0;
        double total   = Math.round((price + freight) * 100.0) / 100.0;
        String paymentType = PAYMENT_TYPES[rng.nextInt(PAYMENT_TYPES.length)];
        int installments = rng.nextInt(1, 11);

        txTemplate.executeWithoutResult(status -> {
            jdbc.update(
                    "INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp, " +
                    "order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    orderId, customerId, "processing",
                    Timestamp.from(purchase),
                    Timestamp.from(purchase.plus(1, ChronoUnit.HOURS)),
                    Timestamp.from(purchase.plus(1, ChronoUnit.DAYS)),
                    Timestamp.from(purchase.plus(3, ChronoUnit.DAYS)),
                    Timestamp.from(purchase.plus(7, ChronoUnit.DAYS)));

            jdbc.update(
                    "INSERT INTO order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    orderId, 1, product.getProductId(), sellerId,
                    Timestamp.from(purchase.plus(2, ChronoUnit.DAYS)), price, freight);

            jdbc.update(
                    "INSERT INTO order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value) " +
                    "VALUES (?, ?, ?, ?, ?)",
                    orderId, 1, paymentType, installments, total);
        });

        log.info("FakeUserBehaviorScheduler: PURCHASE order {} saved for customer={}, product={}, total={}",
                orderId, customerId, product.getProductId(), total);
    }

    private ProductEntity pickWeightedProduct(ThreadLocalRandom rng) {
        int dart = rng.nextInt(totalWeight);
        int cumulative = 0;
        for (int i = 0; i < allProducts.size(); i++) {
            cumulative += popularityWeights[i];
            if (dart < cumulative) return allProducts.get(i);
        }
        return allProducts.get(allProducts.size() - 1);
    }

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

        log.info("event {}: {}", userId, event);
        referenceDataService.sendEvent(event);

        long gap = rng.nextLong(2_000, 10_001);
        cursorMs[0] += (dwellTimeMs != null ? dwellTimeMs : 0) + gap;
    }
}
