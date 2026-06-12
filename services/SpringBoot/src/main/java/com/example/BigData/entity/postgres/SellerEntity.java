package com.example.BigData.entity.postgres;



import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;


import java.util.ArrayList;
import java.util.List;

// entity/postgres/SellerEntity.java
@Entity
@Table(name = "sellers")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SellerEntity {

    @Id
    @Column(name = "seller_id", length = 50)
    private String sellerId;

    @Column(name = "seller_zip_code_prefix", length = 5)
    private String sellerZipCodePrefix;

    @Column(name = "seller_city", length = 100)
    private String sellerCity;

    @Column(name = "seller_state", length = 2)
    private String sellerState;

    @OneToMany(mappedBy = "seller", fetch = FetchType.LAZY)
    @JsonIgnore
    private List<OrderItemEntity> orderItems = new ArrayList<>();
}