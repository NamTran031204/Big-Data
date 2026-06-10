package com.example.BigData.service;

import com.example.BigData.entity.postgres.CustomerEntity;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.entity.postgres.SellerEntity;
import com.example.BigData.repository.postgres.CustomerJpaRepository;
import com.example.BigData.repository.postgres.OrderItemJpaRepository;
import com.example.BigData.repository.postgres.ProductJpaRepository;
import com.example.BigData.repository.postgres.SellerJpaRepository;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

/**
 * Sinh fake data vào Postgres OLTP để demo CDC realtime.
 *
 * Ba scheduler độc lập:
 *   - insertNewCustomer  : 1 user mới / 10 phút
 *   - insertNewProduct   : 1 product mới / 5 phút  (gắn seller thật, không tạo category mới)
 *   - insertNewOrder     : 1 đơn hàng / 30 giây    (dùng customer thật/sim, product thật)
 *
 * Dùng JdbcTemplate (không JPA) để tránh rắc rối composite-key và đảm bảo thứ tự INSERT cho CDC.
 * insertNewOrder dùng @Transactional để 4 bước INSERT luôn commit nguyên khối.
 * insertNewCustomer / insertNewProduct KHÔNG @Transactional — auto-commit từng INSERT trước
 * khi thêm vào pool in-memory, tránh race condition FK khi insertNewOrder pick ID vừa thêm.
 */
@Slf4j
@Service
public class FakeOltpInsertScheduler {

    private static final String[] PAYMENT_TYPES = {"credit_card", "boleto", "voucher", "debit_card"};
    private static final String[] STATES = {"SP", "RJ", "MG", "RS", "PR", "SC", "BA"};

    private final ProductJpaRepository productRepo;
    private final OrderItemJpaRepository orderItemRepo;
    private final CustomerJpaRepository customerRepo;
    private final SellerJpaRepository sellerRepo;
    private final JdbcTemplate jdbc;

    @Value("${fakeoltp.enabled:true}")
    private boolean enabled;

    private record ProductRef(String productId, String sellerId, String category) {}

    // Grow over time: real + sim customers; real + sim products. CopyOnWriteArrayList: reads cheap, writes rare.
    private final CopyOnWriteArrayList<ProductRef> refs = new CopyOnWriteArrayList<>();
    private final CopyOnWriteArrayList<String> customerIds = new CopyOnWriteArrayList<>();
    private volatile List<String> sellerIds = Collections.emptyList();
    private volatile List<String> categoryNames = Collections.emptyList();
    private volatile boolean dataReady = false;

    public FakeOltpInsertScheduler(
            ProductJpaRepository productRepo,
            OrderItemJpaRepository orderItemRepo,
            CustomerJpaRepository customerRepo,
            SellerJpaRepository sellerRepo,
            JdbcTemplate jdbc) {
        this.productRepo = productRepo;
        this.orderItemRepo = orderItemRepo;
        this.customerRepo = customerRepo;
        this.sellerRepo = sellerRepo;
        this.jdbc = jdbc;
    }

    @PostConstruct
    public void loadReferenceData() {
        if (!enabled) {
            log.info("FakeOltpInsertScheduler: disabled (fakeoltp.enabled=false) — skipping.");
            return;
        }
        try {
            log.info("FakeOltpInsertScheduler: loading reference data...");

            customerRepo.findAll(PageRequest.of(0, 5)).getContent()
                    .stream().map(CustomerEntity::getCustomerId).forEach(customerIds::add);

            this.sellerIds = sellerRepo.findAll(PageRequest.of(0, 500)).getContent()
                    .stream().map(SellerEntity::getSellerId)
                    .collect(Collectors.toUnmodifiableList());

            Map<String, String> categoryById = new HashMap<>();
            for (ProductEntity p : productRepo.findAll()) {
                categoryById.put(p.getProductId(), p.getProductCategoryName());
            }
            this.categoryNames = categoryById.values().stream()
                    .filter(Objects::nonNull).distinct()
                    .collect(Collectors.toUnmodifiableList());

            List<OrderItemJpaRepository.OrderItemSummary> sample =
                    orderItemRepo.findOrderItemSummaries(PageRequest.of(0, 5000));
            Map<String, ProductRef> byProduct = new LinkedHashMap<>();
            for (OrderItemJpaRepository.OrderItemSummary s : sample) {
                String cat = categoryById.get(s.getProductId());
                if (cat == null) continue;
                byProduct.putIfAbsent(s.getProductId(),
                        new ProductRef(s.getProductId(), s.getSellerId(), cat));
            }
            refs.addAll(byProduct.values());

            if (refs.isEmpty()) {
                log.warn("FakeOltpInsertScheduler: no product/seller refs — scheduler skipped.");
                return;
            }
            this.dataReady = true;
            log.info("FakeOltpInsertScheduler: ready. refs={}, customers={}, sellers={}, categories={}",
                    refs.size(), customerIds.size(), sellerIds.size(), categoryNames.size());
        } catch (Exception e) {
            log.error("FakeOltpInsertScheduler: failed to load reference data. Cause: {}", e.getMessage(), e);
        }
    }

    @Scheduled(fixedDelay = 600_000)
    public void insertNewCustomer() {
        if (!enabled || !dataReady) return;
        try {
            ThreadLocalRandom rng = ThreadLocalRandom.current();
            String suffix = UUID.randomUUID().toString().replace("-", "");
            String customerId = "sim_c_" + suffix;
            jdbc.update(
                    "INSERT INTO customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state) " +
                    "VALUES (?, ?, ?, ?, ?)",
                    customerId,
                    "sim_u_" + suffix,
                    rng.nextInt(10000, 99999),
                    "sim_city",
                    STATES[rng.nextInt(STATES.length)]);
            customerIds.add(customerId); // add after auto-commit to avoid FK race
            log.info("FakeOltpInsertScheduler: new customer {} inserted (pool={})", customerId, customerIds.size());
        } catch (Exception e) {
            log.error("FakeOltpInsertScheduler: error inserting customer: {}", e.getMessage(), e);
        }
    }

    @Scheduled(fixedDelay = 300_000)
    public void insertNewProduct() {
        if (!enabled || !dataReady || sellerIds.isEmpty() || categoryNames.isEmpty()) return;
        try {
            ThreadLocalRandom rng = ThreadLocalRandom.current();
            String productId = "sim_p_" + UUID.randomUUID().toString().replace("-", "");
            String category = categoryNames.get(rng.nextInt(categoryNames.size()));
            String sellerId  = sellerIds.get(rng.nextInt(sellerIds.size()));
            jdbc.update(
                    "INSERT INTO products (product_id, product_category_name, product_name_length, " +
                    "product_description_length, product_photos_qty, product_weight_g, " +
                    "product_length_cm, product_height_cm, product_width_cm) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    productId, category,
                    rng.nextInt(20, 100), rng.nextInt(100, 500), rng.nextInt(1, 10),
                    rng.nextInt(100, 5000), rng.nextInt(10, 100), rng.nextInt(5, 50), rng.nextInt(10, 100));
            refs.add(new ProductRef(productId, sellerId, category)); // add after auto-commit
            log.info("FakeOltpInsertScheduler: new product {} (cat={}, seller={}, refs={})",
                    productId, category, sellerId, refs.size());
        } catch (Exception e) {
            log.error("FakeOltpInsertScheduler: error inserting product: {}", e.getMessage(), e);
        }
    }

    @Scheduled(fixedDelayString = "${fakeoltp.order-interval-ms:30000}")
    @Transactional
    public void insertNewOrder() {
        if (!enabled || !dataReady || refs.isEmpty() || customerIds.isEmpty()) return;
        try {
            ThreadLocalRandom rng = ThreadLocalRandom.current();
            String customerId = customerIds.get(rng.nextInt(customerIds.size()));
            String orderId = "sim_o_" + UUID.randomUUID().toString().replace("-", "");
            Instant purchase = Instant.now();

            jdbc.update(
                    "INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp, " +
                    "order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    orderId, customerId, "delivered",
                    Timestamp.from(purchase),
                    Timestamp.from(purchase.plus(1, ChronoUnit.HOURS)),
                    Timestamp.from(purchase.plus(1, ChronoUnit.DAYS)),
                    Timestamp.from(purchase.plus(3, ChronoUnit.DAYS)),
                    Timestamp.from(purchase.plus(7, ChronoUnit.DAYS)));

            int itemCount = rng.nextInt(1, 4);
            double total = 0.0;
            for (int i = 1; i <= itemCount; i++) {
                ProductRef ref = refs.get(rng.nextInt(refs.size()));
                double price   = Math.round(rng.nextDouble(10.0, 500.0) * 100.0) / 100.0;
                double freight = Math.round(rng.nextDouble(5.0,  50.0)  * 100.0) / 100.0;
                total += price + freight;
                jdbc.update(
                        "INSERT INTO order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        orderId, i, ref.productId(), ref.sellerId(),
                        Timestamp.from(purchase.plus(2, ChronoUnit.DAYS)), price, freight);
            }

            jdbc.update(
                    "INSERT INTO order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value) " +
                    "VALUES (?, ?, ?, ?, ?)",
                    orderId, 1,
                    PAYMENT_TYPES[rng.nextInt(PAYMENT_TYPES.length)],
                    rng.nextInt(1, 11),
                    Math.round(total * 100.0) / 100.0);

            log.info("FakeOltpInsertScheduler: order {} for customer {} ({} items, total={})",
                    orderId, customerId, itemCount, total);
        } catch (Exception e) {
            log.error("FakeOltpInsertScheduler: error inserting order: {}", e.getMessage(), e);
        }
    }
}
