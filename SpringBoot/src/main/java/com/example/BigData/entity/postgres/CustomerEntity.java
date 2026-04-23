package com.example.BigData.entity.postgres;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;


import java.util.ArrayList;
import java.util.List;

// entity/postgres/CustomerEntity.java
@Entity
@Table(name = "customers")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerEntity {

    @Id
    @Column(name = "customer_id", length = 50)
    private String customerId;

    @Column(name = "customer_unique_id", length = 50, nullable = false)
    private String customerUniqueId;

    @Column(name = "customer_zip_code_prefix", length = 5)
    private String customerZipCodePrefix;

    @Column(name = "customer_city", length = 100)
    private String customerCity;

    @Column(name = "customer_state", length = 2)
    private String customerState;

    // Relationship: 1 customer -> nhiều orders
    @OneToMany(mappedBy = "customer", fetch = FetchType.LAZY)
    @JsonIgnore
    private List<OrderEntity> orders = new ArrayList<>();
}