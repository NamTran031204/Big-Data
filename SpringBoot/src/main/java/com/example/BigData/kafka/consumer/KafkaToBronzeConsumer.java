package com.example.BigData.kafka.consumer;

import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class KafkaToBronzeConsumer {

    private static final Logger log = LoggerFactory.getLogger(KafkaToBronzeConsumer.class);

    @Autowired
    private MinioClient minioClient;

    @Value("${minio.buckets.bronze:bronze-zone}")
    private String bronzeBucket;

    @KafkaListener(topics = "orders-topic", groupId = "olist-data-group")
    public void consume(String msg) { // Đổi từ List<String> sang String
        if (msg == null || msg.isBlank())
            return;

        try {
            ObjectMapper mapper = new ObjectMapper();
            com.fasterxml.jackson.databind.JsonNode node = mapper.readTree(msg);

            if (node.isObject()) {
                String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS"));
                uploadToMinio("raw_data/olist_order_" + timestamp + ".json", msg);
                log.info("✅ Đã lưu một đơn hàng mới vào MinIO");
            } else {
                log.warn("⚠️ Bỏ qua dữ liệu không phải Object: {}", msg);
            }
        } catch (Exception e) {
            log.error("❌ Lỗi định dạng JSON: {}", msg);
        }
    }

    private void uploadToMinio(String fileName, String data) {
        try {
            byte[] dataBytes = data.getBytes(StandardCharsets.UTF_8);
            InputStream inputStream = new ByteArrayInputStream(dataBytes);

            minioClient.putObject(
                    PutObjectArgs.builder()
                            .bucket(bronzeBucket)
                            .object(fileName)
                            .stream(inputStream, dataBytes.length, -1)
                            .contentType("application/json")
                            .build());

            log.info("✅ Đã lưu thành công lô dữ liệu vào MinIO (Bronze): {}", fileName);

        } catch (Exception e) {
            log.error("❌ Lỗi khi upload dữ liệu lên MinIO: ", e);
        }
    }
}