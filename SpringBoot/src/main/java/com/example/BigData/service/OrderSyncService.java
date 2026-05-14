package com.example.BigData.service;

import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import com.example.BigData.entity.mongodb.OrderAnalyticsDocument.ItemSummary;
import com.example.BigData.entity.postgres.OrderItemEntity;
import com.example.BigData.entity.postgres.ProductEntity;
import com.example.BigData.entity.kafka.OrderEvent;
import com.example.BigData.entity.kafka.base.BaseEvent;
import com.example.BigData.kafka.producer.KafkaProducerService;
import com.example.BigData.repository.mongodb.OrderAnalyticsMongoRepository;
import com.example.BigData.repository.postgres.CustomerJpaRepository;
import com.example.BigData.repository.postgres.OrderItemJpaRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.avro.Schema;
import org.apache.avro.SchemaBuilder;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericRecord;
import org.apache.hadoop.conf.Configuration;
import org.apache.parquet.avro.AvroParquetWriter;
import org.apache.parquet.hadoop.ParquetWriter;
import org.apache.parquet.hadoop.metadata.CompressionCodecName;
import org.apache.parquet.io.OutputFile;
import org.apache.parquet.io.PositionOutputStream;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderSyncService {

    private final OrderAnalyticsMongoRepository mongoRepository;
    private final KafkaProducerService kafkaProducerService;
    private final CustomerJpaRepository customerRepository;
    private final OrderItemJpaRepository itemRepository;

    // Avro schema cho OrderEvent (dùng để ghi Parquet)
    private static final Schema ORDER_EVENT_SCHEMA = SchemaBuilder.record("OrderEvent")
            .namespace("com.example.BigData")
            .fields()
            .requiredString("eventId")
            .requiredString("eventType")
            .requiredString("orderId")
            .optionalString("customerId")
            .optionalString("orderStatus")
            .requiredString("eventTimestamp")
            .endRecord();

    public void syncOrderToMongo(CdcEvent cdcEvent) {
        if (cdcEvent.getPayload() == null) return;

        String op = cdcEvent.getPayload().getOp();
        Map<String, Object> data = ("d".equals(op))
                ? cdcEvent.getPayload().getBefore().getFields()
                : cdcEvent.getPayload().getAfter().getFields();

        if (data == null) return;

        String orderId = (String) data.get("order_id");
        if (orderId == null) return;

        try {
            if ("d".equals(op)) {
                mongoRepository.deleteById(orderId);
                log.info("🗑️ [Gold] Đã xóa Order: {}", orderId);
                sendToKafka(orderId, data, "ORDER_DELETED");
                return;
            }
            handleSaveOrUpdate(orderId, data, op);
        } catch (Exception e) {
            log.error("❌ Lỗi xử lý Gold Layer / Kafka cho Order {}: {}", orderId, e.getMessage());
        }
    }

    private void handleSaveOrUpdate(String orderId, Map<String, Object> data, String op) {
        OrderAnalyticsDocument document = mongoRepository.findById(orderId)
                .orElse(new OrderAnalyticsDocument());

        document.setOrderId(orderId);
        document.setCustomerId((String) data.get("customer_id"));
        document.setOrderStatus((String) data.get("order_status"));
        document.setPurchaseTimestamp(convertMicroTimestamp(data.get("order_purchase_timestamp")));
        document.setDeliveredDate(convertMicroTimestamp(data.get("order_delivered_customer_date")));
        document.setEstimatedDeliveryDate(convertMicroTimestamp(data.get("order_estimated_delivery_date")));

        customerRepository.findById(document.getCustomerId()).ifPresent(c -> {
            document.setCustomerCity(c.getCity());
            document.setCustomerState(c.getState());
        });

        List<OrderItemEntity> postgresItems = itemRepository.findByIdOrderId(orderId);

        List<ItemSummary> itemSummaries = postgresItems.stream().map(item -> {
            ItemSummary summary = new ItemSummary();
            ProductEntity product = item.getProduct();
            summary.setProductId(product.getProductId());
            summary.setSellerId(item.getSeller().getSellerId());
            summary.setPrice(item.getPrice());
            summary.setFreightValue(item.getFreightValue());
            summary.setCategoryName(product.getProductCategoryName());
            if (product.getCategoryTranslation() != null) {
                summary.setCategoryNameEnglish(product.getCategoryTranslation().getProductCategoryNameEnglish());
            }
            return summary;
        }).collect(Collectors.toList());

        document.setItems(itemSummaries);

        if (document.getDeliveredDate() != null && document.getEstimatedDeliveryDate() != null) {
            long delay = ChronoUnit.DAYS.between(document.getEstimatedDeliveryDate(), document.getDeliveredDate());
            document.setDeliveryDelayDays((int) delay);
        }

        BigDecimal totalValue = itemSummaries.stream()
                .map(i -> i.getPrice().add(i.getFreightValue()))
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        document.setTotalItemValue(totalValue);
        document.setItemCount(itemSummaries.size());

        mongoRepository.save(document);
        log.info("⭐ [Gold] Đã tổng hợp dữ liệu thành công cho Order: {}", orderId);

        String eventType = "c".equals(op) ? "ORDER_CREATED" : "ORDER_UPDATED";
        sendToKafka(orderId, data, eventType);
    }

    private void sendToKafka(String orderId, Map<String, Object> data, String eventType) {
        try {
            String eventId = UUID.randomUUID().toString();
            String customerId = (String) data.get("customer_id");
            String orderStatus = (String) data.get("order_status");
            String eventTimestamp = LocalDateTime.now().toString();

            // =========================================================
            // FIX: Serialize OrderEvent thành Parquet bytes trước khi gửi
            // =========================================================
            byte[] parquetBytes = serializeToParquet(eventId, eventType, orderId,
                    customerId, orderStatus, eventTimestamp);

            if (parquetBytes == null || parquetBytes.length == 0) {
                log.error("❌ Parquet bytes rỗng cho Order {}, bỏ qua gửi Kafka", orderId);
                return;
            }
            log.debug("📦 Parquet data size: {} bytes cho Order: {}", parquetBytes.length, orderId);

            // Gửi Parquet
            OrderEvent parquetEvent = new OrderEvent();
            parquetEvent.setEventId(eventId);
            parquetEvent.setEventType(eventType);
            parquetEvent.setOrderId(orderId);
            parquetEvent.setCustomerId(customerId);
            parquetEvent.setOrderStatus(orderStatus);
            parquetEvent.setEventTimestamp(eventTimestamp);
            parquetEvent.setPayload(parquetBytes); // ✅ Set payload đúng chỗ

            kafkaProducerService.sendOrderEvent("olist_orders", orderId, parquetEvent,
                    BaseEvent.SerializationFormat.PARQUET);

            // Gửi JSON (payload không cần thiết cho JSON)
            OrderEvent jsonEvent = new OrderEvent();
            jsonEvent.setEventId(eventId);
            jsonEvent.setEventType(eventType);
            jsonEvent.setOrderId(orderId);
            jsonEvent.setCustomerId(customerId);
            jsonEvent.setOrderStatus(orderStatus);
            jsonEvent.setEventTimestamp(eventTimestamp);

            kafkaProducerService.sendOrderEvent("olist_orders", orderId, jsonEvent,
                    BaseEvent.SerializationFormat.JSON);

        } catch (Exception e) {
            log.error("❌ Lỗi khi nén và đẩy Parquet cho Order {}: {}", orderId, e.getMessage());
        }
    }

    /**
     * Serialize một OrderEvent thành Parquet bytes dùng Avro + in-memory OutputFile.
     */
    private byte[] serializeToParquet(String eventId, String eventType, String orderId,
                                      String customerId, String orderStatus,
                                      String eventTimestamp) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();

        // OutputFile in-memory để không cần ghi ra disk
        OutputFile outputFile = new OutputFile() {
            @Override
            public PositionOutputStream create(long blockSizeHint) {
                return new PositionOutputStream() {
                    long pos = 0;
                    @Override public long getPos() { return pos; }
                    @Override public void write(int b) { baos.write(b); pos++; }
                    @Override public void write(byte[] b, int off, int len) {
                        baos.write(b, off, len); pos += len;
                    }
                    @Override public void flush() {}
                    @Override public void close() {}
                };
            }

            @Override
            public PositionOutputStream createOrOverwrite(long blockSizeHint) {
                return create(blockSizeHint);
            }

            @Override
            public boolean supportsBlockSize() { return false; }
            @Override
            public long defaultBlockSize() { return 0; }
        };

        // Tạo GenericRecord theo schema
        GenericRecord record = new GenericData.Record(ORDER_EVENT_SCHEMA);
        record.put("eventId", eventId);
        record.put("eventType", eventType);
        record.put("orderId", orderId);
        record.put("customerId", customerId);
        record.put("orderStatus", orderStatus);
        record.put("eventTimestamp", eventTimestamp);

        // Ghi Parquet
        try (ParquetWriter<GenericRecord> writer = AvroParquetWriter.<GenericRecord>builder(outputFile)
                .withSchema(ORDER_EVENT_SCHEMA)
                .withCompressionCodec(CompressionCodecName.SNAPPY)
                .withConf(new Configuration())
                .build()) {
            writer.write(record);
        }

        return baos.toByteArray();
    }

    private LocalDateTime convertMicroTimestamp(Object ts) {
        if (ts == null) return null;
        try {
            long micros = Long.parseLong(ts.toString());
            return LocalDateTime.ofInstant(Instant.ofEpochMilli(micros / 1000), ZoneId.systemDefault());
        } catch (Exception e) {
            return null;
        }
    }
}