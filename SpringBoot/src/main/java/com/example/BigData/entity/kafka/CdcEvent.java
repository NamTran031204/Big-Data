package com.example.BigData.entity.kafka;

import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.HashMap;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class CdcEvent {

    private PayloadData payload;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PayloadData {
        private CdcPayload before;
        private CdcPayload after;
        private String op;        // c=create, u=update, d=delete
        private Long ts_ms;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class CdcPayload {
        @JsonAnySetter
        private Map<String, Object> fields = new HashMap<>();
    }
}