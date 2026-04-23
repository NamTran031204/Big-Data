package com.example.BigData.entity.kafka;


import com.fasterxml.jackson.annotation.JsonAnySetter;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CdcEvent {

    // Khai báo lớp vỏ payload để Jackson "đục" vào trong
    private PayloadData payload;

    @Data
    public static class PayloadData {
        private CdcPayload before;
        private CdcPayload after;
        private String op;        // c=create, u=update, d=delete
        private Long ts_ms;
        // Không cần map "source" nếu không dùng đến
    }

    @Data
    public static class CdcPayload {
        @JsonAnySetter
        private Map<String, Object> fields = new HashMap<>();
    }
}