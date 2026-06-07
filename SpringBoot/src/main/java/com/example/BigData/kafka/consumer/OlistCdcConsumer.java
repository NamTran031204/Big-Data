package com.example.BigData.kafka.consumer; // Sửa lỗi "The declared package does not match"

import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.service.MinioService;
import com.example.BigData.service.OrderSyncService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class OlistCdcConsumer {

    private final ObjectMapper objectMapper;
    private final OrderSyncService orderSyncService;
    private final MinioService minioService; // 

    @KafkaListener(topics = "olist_cdc.public.olist_orders", groupId = "olist-group")
    public void consumeOrderChanges(String message) {
        String timestamp = String.valueOf(System.currentTimeMillis());
        try {
            // Lưu message nguyên bản từ Kafka lên MinIO, không quan tâm nội dung là gì.
            String bronzePath = "bronze/orders/" + timestamp + ".json";
            minioService.uploadJson(bronzePath, message);
            log.info(" [Bronze] Đã lưu dữ liệu thô vào MinIO: {}", bronzePath);

            //  Chuyển chuỗi JSON thành đối tượng Java
            CdcEvent event = objectMapper.readValue(message, CdcEvent.class);

            //  lưu vào PostgreSQL để phục vụ các câu lệnh SQL.
            // Hoặc lưu bản đã lọc lên MinIO tầng Silver.
            if (event.getPayload() != null) {
                String silverPath = "silver/orders/" + event.getPayload().getOp() + "_" + timestamp + ".json";
                minioService.uploadJson(silverPath, objectMapper.writeValueAsString(event.getPayload()));
                
                // Đồng bộ sang PostgreSQL (Silver)
                // orderJpaRepository.save(event.toEntity()); 
                log.info("✨ [Silver] Đã làm sạch và cấu trúc hóa dữ liệu");
            }

            //  gọi service hiện tại để lưu vào MongoDB hoặc tính toán chỉ số.
            orderSyncService.syncOrderToMongo(event);
            log.info(" [Gold] Đã cập nhật báo cáo/analytics vào MongoDB");

        } catch (Exception e) {
            log.error(" Lỗi Pipeline: {}", e.getMessage());
            
        }
    }
}