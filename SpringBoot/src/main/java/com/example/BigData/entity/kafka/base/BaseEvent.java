package com.example.BigData.entity.kafka.base;

public abstract class BaseEvent {

    public enum SerializationFormat {
        JSON, PARQUET
    }

}