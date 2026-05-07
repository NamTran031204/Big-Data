package com.example.BigData.repository.mongodb;




import com.example.BigData.entity.mongodb.OrderAnalyticsDocument;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface OrderAnalyticsMongoRepository extends MongoRepository<OrderAnalyticsDocument, String> {
}