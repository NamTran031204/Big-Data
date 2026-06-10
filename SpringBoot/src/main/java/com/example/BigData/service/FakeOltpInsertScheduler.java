package com.example.BigData.service;

import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.repository.postgres.OrderItemJpaRepository;
import com.example.BigData.repository.postgres.ProductJpaRepository;
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
import java.util.concurrent.ThreadLocalRandom;

/**
 * Sinh "đơn hàng giả" liên tục INSERT vào Postgres OLTP (olist) để demo CDC realtime.
 * Mỗi lần chạy ghi 1 order graph nhất quán: customers -> orders -> order_items -> order_payments,
 * tham chiếu product/seller THẬT. Debezium bắt insert -> bronze -> (re-run) silver/gold.
 *
 * Dùng JdbcTemplate (không dùng JPA entity) để tránh rắc rối composite-key / @ManyToOne managed,
 * và đảm bảo thứ tự / nội dung INSERT cố định cho CDC. @Transactional để mỗi graph commit nguyên khối.
 *
 * Bật/tắt qua property fakeoltp.enabled (mặc định true), nhịp qua fakeoltp.interval-ms (mặc định 8000).
 * Khác với {@link FakeUserBehaviorScheduler} (sinh sự kiện Kafka cho luồng streaming) — bean này nuôi luồng batch/CDC.
 */
@Slf4j
@Service
public class FakeOltpInsertScheduler {

    private static final String[] PAYMENT_TYPES = {"credit_card", "boleto", "voucher", "debit_card"};
    private static final String[] STATES = {"SP", "RJ", "MG", "RS", "PR", "SC", "BA"};

    private final ProductJpaRepository productRepo;
    private final OrderItemJpaRepository orderItemRepo;
    private final JdbcTemplate jdbc;

    @Value("${fakeoltp.enabled:true}")
    private boolean enabled;

    /** Tuple sản phẩm hợp lệ để tham chiếu khi sinh order_items. */
    private record ProductRef(String productId, String sellerId, String category) {}

    private volatile List<ProductRef> refs = Collections.emptyList();
    private volatile boolean dataReady = false;

    public FakeOltpInsertScheduler(
            ProductJpaRepository productRepo,
            OrderItemJpaRepository orderItemRepo,
            JdbcTemplate jdbc) {
        this.productRepo = productRepo;
        this.orderItemRepo = orderItemRepo;
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

            // category theo productId (từ products thật)
            Map<String, String> categoryById = new HashMap<>();
            for (ProductEntity p : productRepo.findAll()) {
                categoryById.put(p.getProductId(), p.getProductCategoryName());
            }

            // (productId, sellerId) từ mẫu order_items -> ghép category
            List<OrderItemJpaRepository.OrderItemSummary> sample =
                    orderItemRepo.findOrderItemSummaries(PageRequest.of(0, 5000));

            Map<String, ProductRef> byProduct = new LinkedHashMap<>();
            for (OrderItemJpaRepository.OrderItemSummary s : sample) {
                String cat = categoryById.get(s.getProductId());
                if (cat == null) continue;
                byProduct.putIfAbsent(s.getProductId(),
                        new ProductRef(s.getProductId(), s.getSellerId(), cat));
            }

            this.refs = List.copyOf(byProduct.values());
            if (refs.isEmpty()) {
                log.warn("FakeOltpInsertScheduler: no product/seller refs found — scheduler skipped.");
                return;
            }
            this.dataReady = true;
            log.info("FakeOltpInsertScheduler: ready. {} product refs loaded.", refs.size());

        } catch (Exception e) {
            log.error("FakeOltpInsertScheduler: failed to load reference data — disabled. Cause: {}", e.getMessage(), e);
        }
    }

    @Scheduled(fixedDelayString = "${fakeoltp.interval-ms:8000}")
    @Transactional
    public void insertOrderGraph() {
        if (!enabled || !dataReady || refs.isEmpty()) return;

        try {
            ThreadLocalRandom rng = ThreadLocalRandom.current();

            String suffix = UUID.randomUUID().toString().replace("-", "");
            String customerId = "sim_c_" + suffix;
            String orderId = "sim_o_" + suffix;

            // 1) customers
            jdbc.update(
                    "INSERT INTO customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state) " +
                    "VALUES (?, ?, ?, ?, ?)",
                    customerId,
                    "sim_u_" + suffix,
                    rng.nextInt(1000, 99999),
                    "sim_city",
                    STATES[rng.nextInt(STATES.length)]);

            // 2) orders (đặt mua "ngay bây giờ", giao trong vài ngày)
            Instant purchase = Instant.now();
            jdbc.update(
                    "INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp, " +
                    "order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    orderId,
                    customerId,
                    "delivered",
                    Timestamp.from(purchase),
                    Timestamp.from(purchase.plus(1, ChronoUnit.HOURS)),
                    Timestamp.from(purchase.plus(1, ChronoUnit.DAYS)),
                    Timestamp.from(purchase.plus(3, ChronoUnit.DAYS)),
                    Timestamp.from(purchase.plus(7, ChronoUnit.DAYS)));

            // 3) order_items (1–3 dòng) + tính tổng tiền
            int itemCount = rng.nextInt(1, 4);
            double total = 0.0;
            for (int i = 1; i <= itemCount; i++) {
                ProductRef ref = refs.get(rng.nextInt(refs.size()));
                double price = Math.round(rng.nextDouble(10.0, 500.0) * 100.0) / 100.0;
                double freight = Math.round(rng.nextDouble(5.0, 50.0) * 100.0) / 100.0;
                total += price + freight;
                jdbc.update(
                        "INSERT INTO order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        orderId, i, ref.productId(), ref.sellerId(),
                        Timestamp.from(purchase.plus(2, ChronoUnit.DAYS)), price, freight);
            }

            // 4) order_payments (1 dòng, tổng = sum item price+freight)
            jdbc.update(
                    "INSERT INTO order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value) " +
                    "VALUES (?, ?, ?, ?, ?)",
                    orderId, 1,
                    PAYMENT_TYPES[rng.nextInt(PAYMENT_TYPES.length)],
                    rng.nextInt(1, 11),
                    Math.round(total * 100.0) / 100.0);

            log.info("FakeOltpInsertScheduler: inserted order {} ({} items, total {}).", orderId, itemCount, total);

        } catch (Exception e) {
            log.error("FakeOltpInsertScheduler: error inserting order graph: {}", e.getMessage(), e);
        }
    }
}
