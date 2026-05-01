package com.example.BigData.entity.postgres;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "geolocation")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class GeolocationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "geolocation_zip_code_prefix", length = 5)
    private String zipCodePrefix;

    @Column(name = "geolocation_lat")
    private Double lat;

    @Column(name = "geolocation_lng")
    private Double lng;

    @Column(name = "geolocation_city", length = 100)
    private String city;

    @Column(name = "geolocation_state", length = 2)
    private String state;
}