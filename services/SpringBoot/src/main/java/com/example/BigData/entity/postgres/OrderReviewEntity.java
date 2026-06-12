package com.example.BigData.entity.postgres;



import jakarta.persistence.*;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;


import java.time.LocalDateTime;


@Entity
@Table(name = "order_reviews")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OrderReviewEntity {

    @Id
    @Column(name = "review_id", length = 50)
    private String reviewId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id")
    private OrderEntity order;

    @Column(name = "review_score")
    @Min(1) @Max(5)
    private Integer reviewScore;

    @Column(name = "review_comment_title", length = 255)
    private String reviewCommentTitle;

    @Column(name = "review_comment_message", columnDefinition = "TEXT")
    private String reviewCommentMessage;

    @Column(name = "review_creation_date")
    private LocalDateTime reviewCreationDate;

    @Column(name = "review_answer_timestamp")
    private LocalDateTime reviewAnswerTimestamp;
}