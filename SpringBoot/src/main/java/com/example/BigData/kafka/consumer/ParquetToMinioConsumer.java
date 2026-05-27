package com.example.BigData.kafka.consumer;

import com.example.BigData.service.MinioService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Service;

import java.time.LocalDate;

@Service
@RequiredArgsConstructor
@Slf4j
public class ParquetToMinioConsumer {

    private final MinioService minioService;

    // Chú ý: Lắng nghe topic olist_orders (dành riêng cho luồng Parquet)
    @KafkaListener(topics = "olist_orders", groupId = "lakehouse-writer-group")
    public void consumeAndUpload(
            @Payload(required = false) byte[] parquetData,
            @Header(KafkaHeaders.RECEIVED_KEY) String orderId) {

        if (parquetData == null || parquetData.length == 0) {
            log.warn("⚠️ Bỏ qua file Parquet rỗng/null (có thể là tombstone message) cho orderId: {}", orderId);
            return;
        }

        // Tạo cấu trúc thư mục theo chuẩn Data Lake (phân chia theo năm/tháng/ngày)
        // Ví dụ: raw_zone/2026-05-14/order_a1b2c3.parquet
        LocalDate today = LocalDate.now();
        String s3Path = String.format("raw_zone/year=%d/month=%02d/day=%02d/order_%s.parquet",
                today.getYear(),
                today.getMonthValue(),
                today.getDayOfMonth(),
                orderId);

        // Gọi thợ khuân vác lên MinIO
        minioService.uploadParquetFile(s3Path, parquetData);
    }
}