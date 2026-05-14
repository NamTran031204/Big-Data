package com.example.BigData.service;

import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

@Service
@RequiredArgsConstructor
@Slf4j
public class MinioService {

    private final MinioClient minioClient;

    @Value("${minio.bucket}")
    private String bucketName;

    // --- Hàm upload file Parquet (đã có) ---
    public void uploadParquetFile(String fileName, byte[] parquetData) {
        uploadToMinio(fileName, parquetData, "application/octet-stream");
    }

    // --- HÀM MỚI: Upload file JSON (Thêm hàm này để hết lỗi) ---
    public void uploadJson(String fileName, String jsonContent) {
        if (jsonContent == null) return;
        byte[] data = jsonContent.getBytes(StandardCharsets.UTF_8);
        uploadToMinio(fileName, data, "application/json");
    }

    // Hàm dùng chung để tối ưu code
    private void uploadToMinio(String fileName, byte[] data, String contentType) {
        try {
            boolean isExist = minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucketName).build());
            if (!isExist) {
                minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucketName).build());
            }

            InputStream stream = new ByteArrayInputStream(data);
            minioClient.putObject(
                    PutObjectArgs.builder()
                            .bucket(bucketName)
                            .object(fileName)
                            .stream(stream, data.length, -1)
                            .contentType(contentType)
                            .build()
            );
            log.info("🚀 [MINIO] Uploaded successfully: {}", fileName);
        } catch (Exception e) {
            log.error("❌ [MINIO] Error uploading {}: {}", fileName, e.getMessage());
        }
    }
}