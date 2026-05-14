package com.example.BigData.util;



import com.example.BigData.entity.kafka.OrderEvent;
import org.apache.avro.reflect.ReflectData;
import org.apache.hadoop.fs.Path;
import org.apache.parquet.avro.AvroParquetWriter;
import org.apache.parquet.hadoop.ParquetWriter;
import org.apache.parquet.hadoop.metadata.CompressionCodecName;
import org.springframework.stereotype.Component;

import java.io.File;
import java.nio.file.Files;

@Component
public class ParquetConverter {

    public byte[] convertToParquetBytes(OrderEvent event) {
        try {
            // Tạo một file tạm trong bộ nhớ máy Mac để ghi Parquet
            File tempFile = File.createTempFile("temp_parquet", ".parquet");
            tempFile.delete();
            Path path = new Path(tempFile.getAbsolutePath());

            // Tự động suy luận Schema Avro từ class OrderEvent
            org.apache.avro.Schema schema = ReflectData.get().getSchema(OrderEvent.class);

            try (ParquetWriter<OrderEvent> writer = AvroParquetWriter.<OrderEvent>builder(path)
                    .withSchema(schema)
                    .withDataModel(ReflectData.get())
                    .withCompressionCodec(CompressionCodecName.SNAPPY)
                    .build()) {

                writer.write(event);
            }

            // Đọc lại file tạm thành mảng byte để gửi qua Kafka, sau đó xóa file tạm
            byte[] parquetBytes = Files.readAllBytes(tempFile.toPath());
            tempFile.delete();

            return parquetBytes;

        } catch (Exception e) {
            throw new RuntimeException("Lỗi khi chuyển đổi sang định dạng Parquet: " + e.getMessage(), e);
        }
    }
}