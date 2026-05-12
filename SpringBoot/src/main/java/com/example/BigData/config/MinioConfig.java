package com.example.BigData.config;
<<<<<<< HEAD
=======

>>>>>>> 8317f0299da9174784a416cc5efc72e9b9870f2a
import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MinioConfig {
<<<<<<< HEAD
    @Value("${minio.url}")
    private String url;
    @Value("${minio.access-key}")
    private String accessKey;
    @Value("${minio.secret-key}")
=======

    @Value("${spring.minio.url}")
    private String url;

    @Value("${spring.minio.access-key}")
    private String accessKey;

    @Value("${spring.minio.secret-key}")
>>>>>>> 8317f0299da9174784a416cc5efc72e9b9870f2a
    private String secretKey;

    @Bean
    public MinioClient minioClient() {
        return MinioClient.builder()
                .endpoint(url)
                .credentials(accessKey, secretKey)
                .build();
    }
}