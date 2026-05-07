package com.example.BigData.kafka.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.example.BigData.entity.kafka.CdcEvent;
import com.example.BigData.service.OrderSyncService;
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

    @KafkaListener(topics = "olist_cdc.olist.olist_orders", groupId = "olist-group")
    public void consumeOrderChanges(String message) {
        try {
            // 1. Chuyển chuỗi JSON thô thành đối tượng CdcEvent
            CdcEvent event = objectMapper.readValue(message, CdcEvent.class);

            log.info("🔥 Bắt được sự kiện CDC: Lệnh [ {} ] trên bảng Order", event.getPayload());

            // 2. Gọi Service để xử lý và lưu vào Mongo
            orderSyncService.syncOrderToMongo(event);

        } catch (Exception e) {
            log.error("❌ Lỗi khi bóc tách bản tin CDC: {}", e.getMessage());
            // TODO: Bắn tin nhắn lỗi này sang một Topic khác (Dead Letter Queue)
        }
    }
}