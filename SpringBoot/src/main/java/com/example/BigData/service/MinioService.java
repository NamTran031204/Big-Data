package com.example.BigData.service;

import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;

@Service
public class MinioService {

    @Autowired
    private MinioClient minioClient;

    @Value("${minio.bucket}")
    private String defaultBucket;

    /**
     * Đẩy dữ liệu chuỗi (JSON) lên MinIO
     * @param path Đường dẫn file (vd: bronze/orders/2024/05/order_1.json)
     * @param content Nội dung file
     */
    public void uploadJson(String path, String content) {
        try {
            // Kiểm tra và tạo bucket nếu chưa có
            boolean found = minioClient.bucketExists(BucketExistsArgs.builder().bucket(defaultBucket).build());
            if (!found) {
                minioClient.makeBucket(MakeBucketArgs.builder().bucket(defaultBucket).build());
            }

            byte[] data = content.getBytes();
            minioClient.putObject(
                PutObjectArgs.builder()
                    .bucket(defaultBucket)
                    .object(path)
                    .stream(new ByteArrayInputStream(data), data.length, -1)
                    .contentType("application/json")
                    .build()
            );
        } catch (Exception e) {
            throw new RuntimeException("Lỗi khi upload lên MinIO: " + e.getMessage());
        }
    }
}