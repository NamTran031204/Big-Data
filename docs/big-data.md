# KẾ HOẠCH TRIỂN KHAI DỰ ÁN BIG DATA

## Phân công vai trò cho 5 thành viên

##### **👨‍💼 Nam [Java + Python]**
**Vai trò:** Project Manager + Infrastructure Engineer + Java Backend Developer
**Kỹ năng:** Java, Python, Kafka, Kubernetes, System Integration

##### **👨‍💻 Thế - JAVA DEVELOPER [Java + Python]**
**Vai trò:** Java Backend Engineer + CDC Specialist
**Kỹ năng:** Java, Spring Boot, Kafka, PostgreSQL, Debezium

##### **👨‍💻 Quang - SPARK BATCH ENGINEER [Python]**
**Vai trò:** PySpark Batch Processing Specialist
**Kỹ năng:** PySpark, Data Transformation, Performance Optimization

##### **👨‍💻 Hoàng - SPARK STREAMING ENGINEER [Python]**
**Vai trò:** PySpark Streaming Specialist
**Kỹ năng:** Spark Structured Streaming, Real-time Processing, Watermarking

##### **👨‍💻 Huy - DATA SCIENTIST & VISUALIZATION [Python]**
**Vai trò:** ML Engineer + Data Analyst + Visualization Engineer
**Kỹ năng:** MLlib, GraphFrames, Grafana, MongoDB

---

## Kế hoạch chi tiết từng tuần (Song song)

---

### 📅 TUẦN 1: Foundation & Setup

#### **🎯 Mục tiêu tuần:**
- Toàn bộ môi trường development sẵn sàng
- Dataset Olist đầy đủ
- Planning và task breakdown hoàn chỉnh

#### **👨‍💼 Nam - Infrastructure Foundation**
- [ ] Setup Kafka cluster (Confluent Cloud hoặc Local với Docker)
  - [ ] Tạo topics: `orders_raw`, `orders_enriched`, `revenue_metrics`
  - [ ] Test producer/consumer
- [ ] Setup MongoDB Atlas
  - [ ] Tạo database `olist_analytics`
  - [ ] Tạo collections: `revenue_metrics`, `customer_segments`, `product_performance`
- [ ] Setup MinIO (S3-compatible storage)
  - [ ] Tạo buckets: `bronze`, `silver`, `gold`
  - [ ] Test upload/download
- [ ] Setup GitHub repository
  - [ ] Tạo folder structure theo README
  - [ ] Setup branch strategy (dev, feature branches)
- [ ] Document connection strings và credentials

**Deliverables:**
- ✅ Kafka topics ready
- ✅ MongoDB collections created
- ✅ MinIO buckets ready
- ✅ GitHub repo structure
- ✅ `config/` folder với connection configs

---

#### **👨‍💻 Thế (Java Developer) - PostgreSQL & Development Environment**
- [ ] Setup PostgreSQL database locally
  - [ ] Install PostgreSQL 15+
  - [ ] Enable WAL (Write-Ahead Logging) for CDC
  - [ ] Create database `olist_db`
- [ ] Create Java Spring Boot project structure
  - [ ] Initialize Maven/Gradle project
  - [ ] Add dependencies: Spring Boot, Kafka, MongoDB, PostgreSQL
  - [ ] Setup application.properties template
- [ ] Study Debezium CDC concepts
  - [ ] Read Debezium documentation
  - [ ] Prepare CDC configuration template
- [ ] Install development tools
  - [ ] Java 17, Maven, IntelliJ IDEA
  - [ ] Kafka command-line tools

**Deliverables:**
- ✅ PostgreSQL installed và configured for CDC
- ✅ Java Spring Boot project initialized
- ✅ Development environment ready

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Dataset & Spark Setup**
- [ ] Download full Olist dataset (9 CSV files)
  - [ ] Download từ Kaggle
  - [ ] Verify data integrity
  - [ ] Place in `data/external/`
- [ ] Setup PySpark environment
  - [ ] Install Java 17, Python 3.12, Spark 3.5.8
  - [ ] Configure SPARK_HOME, JAVA_HOME
  - [ ] Test Spark local mode
- [ ] Data exploration & profiling
  - [ ] Load all 9 CSV files
  - [ ] Check schema, nulls, data types
  - [ ] Create data dictionary
  - [ ] Write exploration notebook
- [ ] Create data augmentation script
  - [ ] Script to duplicate data 10x
  - [ ] Add timestamp variations
  - [ ] Target: 2-3GB dataset

**Deliverables:**
- ✅ All 9 CSV files downloaded
- ✅ PySpark working locally
- ✅ Data exploration report
- ✅ Data augmentation script

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Streaming Study & Prep**
- [ ] Study Spark Structured Streaming
  - [ ] Read official documentation
  - [ ] Complete streaming tutorials
  - [ ] Understand window operations
- [ ] Study Kafka integration with Spark
  - [ ] Kafka-Spark connector
  - [ ] Schema management
  - [ ] Offset management
- [ ] Prepare streaming test data generator
  - [ ] Python script to produce fake orders to Kafka
  - [ ] Configurable rate (orders/second)
- [ ] Install development tools
  - [ ] Python 3.12, PySpark 3.5.8
  - [ ] Kafka Python client

**Deliverables:**
- ✅ Streaming concepts documented
- ✅ Test data generator script ready
- ✅ Development environment ready

---

#### **👨‍💻 Huy (Data Scientist) - ML Study & MongoDB Setup**
- [ ] Study Spark MLlib
  - [ ] ALS for recommendation
  - [ ] Random Forest for classification
  - [ ] Regression models
- [ ] Study GraphFrames
  - [ ] PageRank algorithm
  - [ ] Connected Components
  - [ ] Graph construction
- [ ] Setup MongoDB connection from Python
  - [ ] Install pymongo
  - [ ] Test CRUD operations
  - [ ] Create MongoDB schema design document
- [ ] Install Grafana locally
  - [ ] Install Grafana
  - [ ] Connect to MongoDB
  - [ ] Create test dashboard

**Deliverables:**
- ✅ ML study notes
- ✅ MongoDB connection working from Python
- ✅ MongoDB schema design document
- ✅ Grafana installed and connected

---

### 📅 TUẦN 2: Infrastructure Services & Data Ingestion

#### **🎯 Mục tiêu tuần:**
- Kafka, MongoDB, MinIO, PostgreSQL hoạt động end-to-end
- Data được load vào PostgreSQL và Bronze layer
- Kubernetes setup (basic)

#### **👨‍💼 Nam - Kubernetes & Integration**
- [ ] Setup Minikube
  - [ ] Install Minikube
  - [ ] Start cluster
  - [ ] Verify kubectl working
- [ ] Create Kubernetes manifests
  - [ ] `deployment/k8s/namespace.yaml`
  - [ ] `deployment/k8s/debezium-deployment.yaml` (template)
  - [ ] `deployment/k8s/configmap.yaml`
- [ ] Setup Airflow (Docker)
  - [ ] docker-compose for Airflow
  - [ ] Access Airflow UI
  - [ ] Create first DAG (hello world)
- [ ] Integration testing
  - [ ] Test Kafka → MongoDB connectivity
  - [ ] Test MinIO read/write from Spark
- [ ] Code review setup
  - [ ] Setup PR template
  - [ ] Define code review process

**Deliverables:**
- ✅ Minikube running
- ✅ K8s manifests created
- ✅ Airflow operational
- ✅ Integration tests passing

---

#### **👨‍💻 Thế (Java Developer) - Data Loading & CDC Setup**
- [ ] Load Olist data vào PostgreSQL
  - [ ] Create tables schema (9 tables)
  - [ ] Write data loading scripts
  - [ ] Load augmented dataset (2-3GB)
  - [ ] Verify data integrity
- [ ] Setup Debezium CDC
  - [ ] Configure Debezium connector for PostgreSQL
  - [ ] Deploy Debezium trên Kubernetes (support Member 1)
  - [ ] Test CDC capturing changes
- [ ] Create Java Kafka Producer (test)
  - [ ] Simple producer để test Kafka
  - [ ] Send test messages
  - [ ] Verify messages in Kafka topic

**Deliverables:**
- ✅ PostgreSQL tables created and loaded with data
- ✅ Debezium CDC capturing changes
- ✅ Java Kafka producer working

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Bronze Layer Ingestion**
- [ ] Create `scripts/data_ingestion.py`
  - [ ] Read 9 CSV files
  - [ ] Validate schemas
  - [ ] Handle data quality issues
  - [ ] Write to Bronze layer (MinIO) as Parquet
  - [ ] Partition by date
- [ ] Create data quality framework
  - [ ] Check nulls, duplicates
  - [ ] Schema validation
  - [ ] Data profiling stats
  - [ ] Generate quality report
- [ ] Create Airflow DAG for batch ingestion
  - [ ] DAG: `batch_ingestion_dag.py`
  - [ ] Schedule: daily
  - [ ] Error handling
- [ ] Test incremental loading
  - [ ] Support append mode
  - [ ] Deduplication logic

**Deliverables:**
- ✅ Bronze layer populated with Parquet files
- ✅ Data quality report
- ✅ Airflow DAG working
- ✅ Incremental loading tested

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Kafka Consumer Setup**
- [ ] Create `services/spark-streaming/kafka_consumer.py`
  - [ ] Read from Kafka topic `orders_raw`
  - [ ] Parse JSON messages
  - [ ] Schema definition
  - [ ] Write to console (testing)
- [ ] Test streaming pipeline basics
  - [ ] Use test data generator
  - [ ] Verify Spark can read from Kafka
  - [ ] Check offset management
- [ ] Create checkpoint directory structure
  - [ ] Setup checkpoint location in MinIO
  - [ ] Test recovery after failure
- [ ] Document streaming architecture
  - [ ] Data flow diagram
  - [ ] Kafka topics mapping

**Deliverables:**
- ✅ Kafka consumer reading messages
- ✅ Checkpoint mechanism working
- ✅ Streaming architecture document

---

#### **👨‍💻 Huy (Data Scientist) - MongoDB Integration**
- [ ] Create `services/warehouse-nosql/mongo_connector.py`
  - [ ] Connection manager class
  - [ ] CRUD operations wrappers
  - [ ] Bulk insert optimizations
  - [ ] Upsert logic
- [ ] Create MongoDB indexes
  - [ ] Indexes on collections
  - [ ] Compound indexes for queries
  - [ ] TTL indexes for hot/cold data
- [ ] Write data quality checker
  - [ ] `scripts/data_quality.py`
  - [ ] Null checks
  - [ ] Duplicate detection
  - [ ] Outlier detection
  - [ ] Generate HTML report
- [ ] Test MongoDB write performance
  - [ ] Benchmark bulk inserts
  - [ ] Query performance testing
  - [ ] Document results

**Deliverables:**
- ✅ MongoDB connector working
- ✅ Indexes created
- ✅ Data quality checker ready
- ✅ Performance benchmark report

---

### 📅 TUẦN 3: Batch Processing Core

#### **🎯 Mục tiêu tuần:**
- Implement Broadcast Join và Sort-Merge Join
- Create UDFs
- Bronze → Silver transformations
- Aggregations for Gold layer

#### **👨‍💼 Nam - Monitoring & Code Review**
- [ ] Setup monitoring framework
  - [ ] Install Prometheus (optional)
  - [ ] Configure Spark metrics
  - [ ] Create metrics dashboard template
- [ ] Code review for all members
  - [ ] Review Spark code quality
  - [ ] Check naming conventions
  - [ ] Verify error handling
- [ ] Create integration test framework
  - [ ] `tests/integration/` structure
  - [ ] Pytest setup
  - [ ] Sample test cases
- [ ] Weekly progress meeting
  - [ ] Review deliverables
  - [ ] Identify blockers
  - [ ] Adjust timeline if needed

**Deliverables:**
- ✅ Monitoring framework setup
- ✅ Code reviews completed
- ✅ Integration test framework ready

---

#### **👨‍💻 Thế (Java Developer) - Assist Batch + Start Java Consumer**
- [ ] Assist Quang with Spark SQL queries
  - [ ] Review join strategies
  - [ ] Help debug performance issues
- [ ] Start Java Kafka Consumer project
  - [ ] `services/java-consumer/` project
  - [ ] Spring Boot + Kafka consumer
  - [ ] Deserialize messages from Kafka
  - [ ] Log messages (testing phase)
- [ ] Study MongoDB Java driver
  - [ ] Add MongoDB dependency
  - [ ] Create connection class
  - [ ] Test CRUD operations
- [ ] Create error handling framework
  - [ ] Dead letter queue (DLQ) pattern
  - [ ] Retry logic
  - [ ] Circuit breaker (Resilience4j)

**Deliverables:**
- ✅ Java Kafka Consumer reading messages
- ✅ MongoDB Java driver working
- ✅ Error handling framework implemented

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Joins & UDFs** ⭐
- [ ] Create `services/spark-batch/bronze_to_silver.py`
  - [ ] **Broadcast Join:** orders ⋈ product_categories (small table)
    ```python
    from pyspark.sql.functions import broadcast
    silver_df = orders_df.join(broadcast(categories_df), "category_id")
    ```
  - [ ] **Sort-Merge Join:** orders ⋈ order_items ⋈ products (large tables)
    ```python
    # Ensure data is sorted and partitioned
    orders_sorted = orders_df.repartition("order_id").sortWithinPartitions("order_id")
    items_sorted = items_df.repartition("order_id").sortWithinPartitions("order_id")
    result = orders_sorted.join(items_sorted, "order_id")
    ```
  - [ ] **Multiple Join:** orders ⋈ items ⋈ products ⋈ sellers ⋈ customers
  - [ ] Analyze execution plans (`.explain()`)
  
- [ ] Create custom UDFs
  - [ ] **UDF 1:** Calculate discount percentage
    ```python
    @udf(returnType=FloatType())
    def calculate_discount(price, original_price):
        if original_price == 0: return 0.0
        return ((original_price - price) / original_price) * 100
    ```
  - [ ] **UDF 2:** Classify delivery status
    ```python
    @udf(returnType=StringType())
    def delivery_status(estimated, actual):
        if actual is None: return "pending"
        diff = (actual - estimated).days
        if diff <= 0: return "on_time"
        elif diff <= 3: return "slight_delay"
        else: return "late"
    ```
  - [ ] **UDF 3:** Customer segment classifier
    ```python
    @udf(returnType=StringType())
    def customer_segment(recency, frequency, monetary):
        # RFM segmentation logic
        if recency < 30 and frequency > 10 and monetary > 1000:
            return "Champion"
        elif recency < 60 and frequency > 5:
            return "Loyal"
        # ... more logic
        return "At Risk"
    ```

- [ ] Write Silver layer to MinIO
  - [ ] Partition by year and month
  - [ ] Parquet format with Snappy compression
  - [ ] Schema evolution handling

**Deliverables:**
- ✅ Broadcast join implemented and working
- ✅ Sort-merge join implemented
- ✅ 3+ UDFs created and tested
- ✅ Silver layer data written
- ✅ Execution plan analysis document

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Assist Batch + Streaming Prep**
- [ ] Assist Quang with batch processing
  - [ ] Help debug join issues
  - [ ] Performance testing
- [ ] Prepare streaming transformations
  - [ ] Design window aggregations
  - [ ] Plan watermarking strategy
  - [ ] Schema for streaming data
- [ ] Create streaming data generator
  - [ ] Produce realistic order events to Kafka
  - [ ] Configurable event rate
  - [ ] Late arrival simulation (10% events delayed)
- [ ] Test Kafka-Spark streaming connection
  - [ ] Read from Kafka in streaming mode
  - [ ] Write to console
  - [ ] Verify latency

**Deliverables:**
- ✅ Batch processing support completed
- ✅ Streaming data generator ready
- ✅ Streaming connection tested

---

#### **👨‍💻 Huy (Data Scientist) - Gold Layer Aggregations**
- [ ] Create `services/spark-batch/silver_to_gold.py`
  - [ ] **Revenue Aggregations:**
    ```python
    revenue_by_category = silver_df.groupBy("category", "year_month") \
        .agg(
            sum("price").alias("total_revenue"),
            count("order_id").alias("order_count"),
            avg("price").alias("avg_order_value"),
            countDistinct("customer_id").alias("unique_customers")
        )
    ```
  - [ ] **RFM Segmentation:**
    ```python
    from pyspark.sql import Window
    from pyspark.sql.functions import datediff, max as max_, current_date
    
    # Recency
    recency = customer_orders.groupBy("customer_id") \
        .agg(datediff(current_date(), max_("order_date")).alias("recency"))
    
    # Frequency
    frequency = customer_orders.groupBy("customer_id") \
        .agg(count("order_id").alias("frequency"))
    
    # Monetary
    monetary = customer_orders.groupBy("customer_id") \
        .agg(sum("price").alias("monetary"))
    ```
  - [ ] **Product Performance Metrics:**
    - Top products by revenue
    - Products by review score
    - Conversion rate by product
  
- [ ] Write Gold data to MongoDB
  - [ ] Use mongo-spark connector
  - [ ] Upsert mode
  - [ ] Batch write optimization
  
- [ ] Create data quality dashboard
  - [ ] Grafana dashboard for data quality metrics
  - [ ] Null percentages
  - [ ] Record counts by table
  - [ ] Data freshness indicators

**Deliverables:**
- ✅ Gold layer aggregations created
- ✅ Data written to MongoDB
- ✅ Data quality dashboard in Grafana

---

### 📅 TUẦN 4: Batch Optimization & Advanced Transformations

#### **🎯 Mục tiêu tuần:**
- Window functions (rank, lead, lag)
- Pivot/Unpivot operations
- Partitioning & Bucketing
- Caching strategies
- Performance optimization

#### **👨‍💼 Nam - Performance Monitoring**
- [ ] Setup Spark UI monitoring
  - [ ] Access Spark UI (port 4040)
  - [ ] Analyze job stages
  - [ ] Identify shuffle operations
- [ ] Resource allocation tuning
  - [ ] Tune Spark configs:
    ```python
    .config("spark.executor.memory", "4g")
    .config("spark.executor.cores", "2")
    .config("spark.sql.shuffle.partitions", "200")
    .config("spark.sql.adaptive.enabled", "true")
    ```
  - [ ] Document optimal settings
- [ ] Cost analysis
  - [ ] Estimate cloud costs (if using cloud)
  - [ ] Resource usage report
  - [ ] Optimization recommendations
- [ ] Code review Quang's optimization work

**Deliverables:**
- ✅ Spark UI monitoring documented
- ✅ Optimal Spark configs identified
- ✅ Cost analysis report

---

#### **👨‍💻 Thế (Java Developer) - MongoDB Writer Service**
- [ ] Create MongoDB writer microservice
  - [ ] `services/java-mongodb-writer/` Spring Boot project
  - [ ] REST API to receive data
  - [ ] Kafka consumer to read from Kafka
  - [ ] Write to MongoDB collections
- [ ] Implement batch write optimization
  - [ ] Bulk insert API
  - [ ] Connection pooling
  - [ ] Retry mechanism
- [ ] Add health check endpoint
  - [ ] `/health` endpoint
  - [ ] Check Kafka connection
  - [ ] Check MongoDB connection
- [ ] Dockerize Java services
  - [ ] Create Dockerfile
  - [ ] docker-compose for local testing
  - [ ] Push to Docker Hub (optional)

**Deliverables:**
- ✅ Java MongoDB writer service working
- ✅ Kafka → Java → MongoDB pipeline operational
- ✅ Docker images created

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Advanced Transformations** ⭐
- [ ] Implement Window Functions
  - [ ] **Ranking:** Top 10 products per category
    ```python
    from pyspark.sql.window import Window
    from pyspark.sql.functions import rank, dense_rank, row_number
    
    window_spec = Window.partitionBy("category") \
        .orderBy(col("revenue").desc())
    
    top_products = products_df.withColumn("rank", rank().over(window_spec)) \
        .filter(col("rank") <= 10)
    ```
  - [ ] **Lead/Lag:** Month-over-month growth
    ```python
    from pyspark.sql.functions import lag, lead
    
    window_spec = Window.partitionBy("category") \
        .orderBy("year_month")
    
    df_with_mom = df.withColumn("prev_month_revenue", 
                                 lag("revenue", 1).over(window_spec))
    df_with_mom = df_with_mom.withColumn("mom_growth",
        (col("revenue") - col("prev_month_revenue")) / col("prev_month_revenue") * 100
    )
    ```
  - [ ] **Running Totals:**
    ```python
    from pyspark.sql.functions import sum as sum_
    window_spec = Window.partitionBy("customer_id") \
        .orderBy("order_date") \
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    cumulative = df.withColumn("cumulative_spend", 
                               sum_("price").over(window_spec))
    ```

- [ ] Implement Pivot/Unpivot
  - [ ] **Pivot:** Payment methods by state
    ```python
    payment_pivot = payments_df.groupBy("state") \
        .pivot("payment_type", ["credit_card", "debit_card", "boleto"]) \
        .agg(sum("payment_value"))
    ```
  - [ ] **Unpivot:** (using stack)
    ```python
    unpivoted = payment_pivot.select(
        "state",
        expr("stack(3, 'credit_card', credit_card, 'debit_card', debit_card, 'boleto', boleto) as (payment_type, amount)")
    )
    ```

- [ ] Implement Partitioning & Bucketing
  - [ ] **Partitioning:** Partition by year, month
    ```python
    df.write \
        .partitionBy("year", "month") \
        .parquet("s3://gold/orders_partitioned/")
    ```
  - [ ] **Bucketing:** Bucket frequently joined tables
    ```python
    df.write \
        .bucketBy(10, "customer_id") \
        .sortBy("order_date") \
        .saveAsTable("orders_bucketed")
    ```

- [ ] Implement Caching Strategies
  - [ ] Cache frequently accessed DataFrames
    ```python
    categories_df.cache()  # Small dimension table
    categories_df.count()  # Trigger caching
    ```
  - [ ] Persist with storage level
    ```python
    from pyspark import StorageLevel
    large_df.persist(StorageLevel.MEMORY_AND_DISK)
    ```
  - [ ] Unpersist when done
    ```python
    large_df.unpersist()
    ```

- [ ] Performance benchmarking
  - [ ] Benchmark before optimization
  - [ ] Apply optimizations
  - [ ] Benchmark after
  - [ ] Document improvements (execution time, shuffle size)

**Deliverables:**
- ✅ Window functions implemented (3+ examples)
- ✅ Pivot/Unpivot working
- ✅ Partitioned data in MinIO
- ✅ Bucketed tables created
- ✅ Caching strategies applied
- ✅ Performance improvement report (before/after metrics)

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Streaming Architecture**
- [ ] Design streaming architecture document
  - [ ] Data flow diagram
  - [ ] Topic naming conventions
  - [ ] Schema registry strategy
- [ ] Prepare watermarking test scenarios
  - [ ] Late data simulation
  - [ ] Different watermark thresholds
  - [ ] Impact analysis
- [ ] Create streaming monitoring dashboard template
  - [ ] Kafka lag metrics
  - [ ] Processing rate
  - [ ] Error rate
- [ ] Study stateful streaming
  - [ ] mapGroupsWithState API
  - [ ] flatMapGroupsWithState API
  - [ ] State timeout mechanisms

**Deliverables:**
- ✅ Streaming architecture document
- ✅ Test scenarios prepared
- ✅ Monitoring dashboard template
- ✅ Stateful streaming concepts documented

---

#### **👨‍💻 Huy (Data Scientist) - Feature Engineering for ML**
- [ ] Prepare ML datasets
  - [ ] **Recommendation dataset:**
    - User-item interaction matrix
    - Implicit feedback (purchases)
  - [ ] **Churn prediction dataset:**
    - Recency, Frequency, Monetary features
    - Days since last purchase
    - Average order value
    - Review scores
  - [ ] **Revenue forecasting dataset:**
    - Time series features (day of week, month, holiday)
    - Lagged features
    - Rolling averages
  
- [ ] Feature engineering pipeline
  - [ ] `services/ml/feature_engineering.py`
  - [ ] Scalers and encoders
  - [ ] Handle missing values
  - [ ] Train/test split
  
- [ ] Exploratory Data Analysis (EDA)
  - [ ] Correlation analysis
  - [ ] Distribution plots
  - [ ] Feature importance (preliminary)
  - [ ] Create EDA notebook
  
- [ ] Write features to MongoDB
  - [ ] Collection: `ml_features`
  - [ ] Versioning strategy

**Deliverables:**
- ✅ ML datasets prepared
- ✅ Feature engineering pipeline
- ✅ EDA notebook
- ✅ Features stored in MongoDB

---

### 📅 TUẦN 5: Streaming Foundation

#### **🎯 Mục tiêu tuần:**
- Kafka streaming pipeline working
- Basic window aggregations
- Write streaming results to MongoDB và MinIO

#### **👨‍💼 Nam - Airflow DAGs for Streaming**
- [ ] Create Airflow DAG for stream monitoring
  - [ ] Check Kafka consumer lag
  - [ ] Check Spark streaming job status
  - [ ] Alert if lag > threshold
- [ ] Integration testing
  - [ ] End-to-end test: Postgres → Kafka → Spark → MongoDB
  - [ ] Data consistency checks
  - [ ] Latency measurements
- [ ] Documentation
  - [ ] Update architecture diagram
  - [ ] Document data flows
  - [ ] API documentation (if any)

**Deliverables:**
- ✅ Airflow monitoring DAG
- ✅ Integration tests passing
- ✅ Documentation updated

---

#### **👨‍💻 Thế (Java Developer) - Kafka Producer Enhancement**
- [ ] Enhance Java Kafka Producer
  - [ ] Read from PostgreSQL periodically
  - [ ] Produce to Kafka topics
  - [ ] Transactional writes (exactly-once)
- [ ] Implement CDC listener (alternative to Debezium)
  - [ ] PostgreSQL logical replication
  - [ ] Capture INSERT/UPDATE/DELETE
  - [ ] Produce events to Kafka
- [ ] Add metrics
  - [ ] Prometheus metrics export
  - [ ] Messages produced per second
  - [ ] Error count
- [ ] Load testing
  - [ ] Generate high volume of events
  - [ ] Measure throughput
  - [ ] Identify bottlenecks

**Deliverables:**
- ✅ Kafka producer producing events
- ✅ Metrics exported
- ✅ Load testing results

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Support Streaming**
- [ ] Assist Hoàng with Spark Streaming
  - [ ] Debug streaming queries
  - [ ] Help with transformations
- [ ] Optimize batch jobs
  - [ ] Apply learnings from week 4
  - [ ] Refactor code for reusability
  - [ ] Add unit tests
- [ ] Create reusable Spark utilities
  - [ ] `utils/spark_utils.py`
  - [ ] Common transformations
  - [ ] UDF library
  - [ ] Configuration loader

**Deliverables:**
- ✅ Streaming support provided
- ✅ Batch jobs optimized
- ✅ Utility library created

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Basic Streaming** ⭐
- [ ] Create `services/spark-streaming/streaming_aggregations.py`
  - [ ] Read from Kafka topic `orders_raw`
    ```python
    streaming_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "orders_raw") \
        .option("startingOffsets", "latest") \
        .load()
    ```
  
  - [ ] Parse JSON messages
    ```python
    from pyspark.sql.functions import from_json, col
    
    parsed_df = streaming_df.selectExpr("CAST(value AS STRING) as json") \
        .select(from_json("json", schema).alias("data")) \
        .select("data.*")
    ```

  - [ ] **Tumbling Window:** Revenue per 5 minutes
    ```python
    from pyspark.sql.functions import window, sum as sum_
    
    windowed_revenue = parsed_df \
        .withWatermark("event_time", "10 minutes") \
        .groupBy(
            window("event_time", "5 minutes"),
            "category"
        ) \
        .agg(sum_("price").alias("revenue"))
    ```

  - [ ] **Sliding Window:** Moving 1-hour revenue (slide 10 minutes)
    ```python
    sliding_revenue = parsed_df \
        .withWatermark("event_time", "10 minutes") \
        .groupBy(
            window("event_time", "1 hour", "10 minutes"),
            "category"
        ) \
        .agg(sum_("price").alias("moving_revenue"))
    ```

- [ ] Write to MongoDB (streaming)
  ```python
  query = windowed_revenue.writeStream \
      .outputMode("update") \
      .foreachBatch(lambda batch_df, batch_id: 
          batch_df.write
              .format("mongo")
              .mode("append")
              .option("database", "olist_analytics")
              .option("collection", "revenue_metrics")
              .save()
      ) \
      .start()
  ```

- [ ] Write to MinIO (checkpoint + data)
  ```python
  query = parsed_df.writeStream \
      .format("parquet") \
      .option("path", "s3://bronze/streaming_orders/") \
      .option("checkpointLocation", "s3://checkpoints/streaming_orders/") \
      .trigger(processingTime="1 minute") \
      .start()
  ```

- [ ] Test different output modes
  - [ ] Append mode (only new rows)
  - [ ] Update mode (updated aggregations)
  - [ ] Complete mode (all aggregations)

**Deliverables:**
- ✅ Kafka → Spark Streaming working
- ✅ Tumbling window implemented
- ✅ Sliding window implemented
- ✅ Streaming → MongoDB working
- ✅ Streaming → MinIO working
- ✅ Output modes tested

---

#### **👨‍💻 Huy (Data Scientist) - MongoDB Query Optimization**
- [ ] Analyze query patterns
  - [ ] Slow query log analysis
  - [ ] Identify frequent queries
  - [ ] Measure query latency
- [ ] Create additional indexes
  - [ ] Compound indexes for common queries
  - [ ] Text indexes for search
  - [ ] Geospatial indexes (if needed)
- [ ] Implement aggregation pipelines
  - [ ] MongoDB aggregation for dashboards
  - [ ] Pre-compute heavy aggregations
  - [ ] Materialized views pattern
- [ ] Start Grafana dashboards
  - [ ] Dashboard 1: Business Metrics (draft)
  - [ ] Connect MongoDB as data source
  - [ ] Create basic panels

**Deliverables:**
- ✅ Query optimization completed
- ✅ Indexes created
- ✅ Aggregation pipelines implemented
- ✅ First Grafana dashboard (draft)

---

### 📅 TUẦN 6: Streaming Advanced Features

#### **🎯 Mục tiêu tuần:**
- Watermarking for late data
- Stateful streaming (mapGroupsWithState)
- Session windows
- Exactly-once semantics

#### **👨‍💼 Nam - Kubernetes Deployment**
- [ ] Deploy Spark Streaming on Kubernetes
  - [ ] Create Spark on K8s YAML
  - [ ] Deploy streaming job
  - [ ] Test auto-restart on failure
- [ ] Setup CI/CD pipeline (basic)
  - [ ] GitHub Actions for build
  - [ ] Automated tests
  - [ ] Docker image build
- [ ] Load testing streaming pipeline
  - [ ] Generate high event rate
  - [ ] Monitor Kafka lag
  - [ ] Measure end-to-end latency
- [ ] Document deployment process
  - [ ] Deployment guide
  - [ ] Troubleshooting tips

**Deliverables:**
- ✅ Streaming job on Kubernetes
- ✅ CI/CD pipeline (basic)
- ✅ Load testing results
- ✅ Deployment documentation

---

#### **👨‍💻 Thế (Java Developer) - Circuit Breaker & Resilience**
- [ ] Implement Circuit Breaker pattern
  - [ ] Use Resilience4j
  - [ ] Circuit breaker for MongoDB writes
  - [ ] Circuit breaker for Kafka producer
- [ ] Implement retry logic
  - [ ] Exponential backoff
  - [ ] Max retry attempts
  - [ ] Dead letter queue (DLQ)
- [ ] Add comprehensive logging
  - [ ] Structured logging (JSON)
  - [ ] Log levels configuration
  - [ ] Correlation IDs for tracing
- [ ] Integration testing
  - [ ] Test failure scenarios
  - [ ] Verify circuit breaker opens
  - [ ] Verify retry logic works

**Deliverables:**
- ✅ Circuit breaker implemented
- ✅ Retry logic working
- ✅ Comprehensive logging added
- ✅ Integration tests passing

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Testing & Documentation**
- [ ] Write unit tests for batch processing
  - [ ] Test UDFs
  - [ ] Test transformations
  - [ ] Test aggregations
  - [ ] Use pytest + pyspark test utils
- [ ] Write integration tests
  - [ ] End-to-end batch pipeline test
  - [ ] Data quality tests
  - [ ] Performance regression tests
- [ ] Code refactoring
  - [ ] Extract common functions
  - [ ] Improve code readability
  - [ ] Add docstrings
- [ ] Documentation
  - [ ] Batch processing guide
  - [ ] Performance tuning guide
  - [ ] API documentation

**Deliverables:**
- ✅ Unit tests (>80% coverage)
- ✅ Integration tests passing
- ✅ Code refactored
- ✅ Documentation completed

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Advanced Streaming** ⭐
- [ ] Implement Watermarking for late data
  ```python
  # Allow 10 minutes of late data
  df_with_watermark = parsed_df \
      .withWatermark("event_time", "10 minutes")
  ```
  - [ ] Test with late data injection
  - [ ] Measure data loss with different watermarks
  - [ ] Document watermark strategy

- [ ] Implement Session Windows
  ```python
  # Session window: gap of 30 minutes
  from pyspark.sql.functions import session_window
  
  session_aggregates = parsed_df \
      .withWatermark("event_time", "10 minutes") \
      .groupBy(
          session_window("event_time", "30 minutes"),
          "customer_id"
      ) \
      .agg(
          count("order_id").alias("session_orders"),
          sum("price").alias("session_revenue")
      )
  ```

- [ ] Implement Stateful Streaming (mapGroupsWithState)
  ```python
  from pyspark.sql.streaming import GroupState
  
  def update_user_session(key, values, state):
      # key: customer_id
      # values: Iterator of events
      # state: GroupState
      
      if state.exists:
          old_state = state.get
      else:
          old_state = {"total_spend": 0, "order_count": 0}
      
      for value in values:
          old_state["total_spend"] += value.price
          old_state["order_count"] += 1
      
      state.update(old_state)
      
      # Return updated state
      return (key, old_state["total_spend"], old_state["order_count"])
  
  stateful_df = parsed_df.groupByKey(lambda x: x.customer_id) \
      .mapGroupsWithState(update_user_session, 
                          timeout=GroupStateTimeout.ProcessingTimeTimeout)
  ```

- [ ] Implement Exactly-Once Semantics
  - [ ] Enable Kafka transactional writes
  - [ ] Configure idempotent writes to MongoDB
  - [ ] Test duplicate detection

- [ ] Checkpoint management
  - [ ] Optimize checkpoint interval
  - [ ] Test recovery from checkpoint
  - [ ] Monitor checkpoint size

**Deliverables:**
- ✅ Watermarking implemented and tested
- ✅ Session windows working
- ✅ Stateful streaming implemented
- ✅ Exactly-once semantics verified
- ✅ Checkpoint recovery tested

---

#### **👨‍💻 Huy (Data Scientist) - Grafana Dashboards Development**
- [ ] Create Dashboard 2: Customer Analytics
  - [ ] Customer segments pie chart
  - [ ] RFM heatmap
  - [ ] Top customers table
  - [ ] Customer lifetime value trend
- [ ] Create Dashboard 3: Product Performance
  - [ ] Top products bar chart
  - [ ] Product revenue trend
  - [ ] Review score distribution
  - [ ] Product category breakdown
- [ ] Add alerting rules
  - [ ] Alert if revenue drops > 20%
  - [ ] Alert if error rate > 5%
  - [ ] Alert if Kafka lag > 1000
- [ ] Dashboard optimization
  - [ ] Query optimization
  - [ ] Caching strategies
  - [ ] Auto-refresh configuration

**Deliverables:**
- ✅ Dashboard 2 completed
- ✅ Dashboard 3 completed
- ✅ Alerting rules configured
- ✅ Dashboards optimized

---

### 📅 TUẦN 7: Java Integration & System Integration

#### **🎯 Mục tiêu tuần:**
- Java services fully integrated
- End-to-end data flow working
- Service discovery and load balancing
- Error handling and resilience

#### **👨‍💼 Nam - Service Integration** ⭐
- [ ] Implement service discovery (if using K8s)
  - [ ] Kubernetes Services
  - [ ] Service mesh (optional - Istio)
  - [ ] DNS-based discovery
- [ ] Implement load balancing
  - [ ] Kafka partition assignment
  - [ ] Consumer group management
  - [ ] Load balancer config (if applicable)
- [ ] End-to-end integration testing
  - [ ] Test full pipeline: Postgres → Debezium → Kafka → Spark → MongoDB → Grafana
  - [ ] Data consistency validation
  - [ ] Performance testing
  - [ ] Failure recovery testing
- [ ] Create integration test suite
  - [ ] Automated E2E tests
  - [ ] Test data generator
  - [ ] Validation scripts

**Deliverables:**
- ✅ Service discovery working
- ✅ Load balancing configured
- ✅ E2E integration tests passing
- ✅ Integration test suite created

---

#### **👨‍💻 Thế (Java Developer) - Java Consumer & Producer** ⭐
- [ ] Complete Java Kafka Consumer
  - [ ] `services/java-consumer/`
  - [ ] Consume from multiple topics
  - [ ] Parallel processing (multi-threading)
  - [ ] Offset management
  - [ ] Consumer group configuration
  
- [ ] Complete Java MongoDB Writer
  - [ ] Batch writes
  - [ ] Bulk upsert operations
  - [ ] Connection pooling
  - [ ] Write performance optimization
  
- [ ] Implement data enrichment service
  - [ ] Read from Kafka
  - [ ] Enrich with reference data
  - [ ] Write enriched data to another Kafka topic
  - [ ] Example: Add product details to order events
  
- [ ] Add monitoring endpoints
  - [ ] `/metrics` for Prometheus
  - [ ] `/health` endpoint
  - [ ] `/info` endpoint
  - [ ] Consumer lag metrics
  
- [ ] Performance tuning
  - [ ] JVM tuning
  - [ ] Thread pool sizing
  - [ ] Memory management
  - [ ] Benchmark results

**Deliverables:**
- ✅ Java Kafka consumer operational
- ✅ Java MongoDB writer operational
- ✅ Data enrichment service working
- ✅ Monitoring endpoints available
- ✅ Performance tuning completed

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Batch-Stream Integration**
- [ ] Create unified data model
  - [ ] Reconcile batch and streaming schemas
  - [ ] Merge batch and streaming results in MongoDB
  - [ ] Deduplication logic
- [ ] Implement Lambda Architecture serving layer
  - [ ] Batch view + Real-time view merge
  - [ ] Query API (Python Flask/FastAPI)
  - [ ] Serve queries from MongoDB
- [ ] Create data reconciliation job
  - [ ] Compare batch and streaming results
  - [ ] Identify discrepancies
  - [ ] Generate reconciliation report
- [ ] Performance comparison
  - [ ] Batch vs streaming latency
  - [ ] Resource utilization
  - [ ] Cost analysis

**Deliverables:**
- ✅ Unified data model
- ✅ Lambda serving layer
- ✅ Reconciliation job working
- ✅ Performance comparison report

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Streaming Optimization**
- [ ] Optimize streaming performance
  - [ ] Tune Kafka consumer settings
    ```python
    .option("kafka.max.poll.records", "1000")
    .option("kafka.fetch.min.bytes", "1048576")  # 1MB
    ```
  - [ ] Optimize trigger interval
  - [ ] Minimize shuffle operations
  - [ ] Coalesce/Repartition optimization
  
- [ ] Implement streaming analytics
  - [ ] Real-time fraud detection (simple rules)
  - [ ] Anomaly detection (statistical)
  - [ ] Trending products detection
  
- [ ] Add stream monitoring
  - [ ] Processing rate metrics
  - [ ] Batch processing time
  - [ ] Watermark delay metrics
  - [ ] State size monitoring
  
- [ ] Failure recovery testing
  - [ ] Kill streaming job
  - [ ] Verify checkpoint recovery
  - [ ] Measure recovery time
  - [ ] Document recovery procedure

**Deliverables:**
- ✅ Streaming performance optimized
- ✅ Real-time analytics implemented
- ✅ Monitoring metrics added
- ✅ Failure recovery tested and documented

---

#### **👨‍💻 Huy (Data Scientist) - Prepare for ML**
- [ ] Finalize ML datasets
  - [ ] Feature selection
  - [ ] Train/validation/test split
  - [ ] Data normalization/scaling
- [ ] Setup ML pipeline structure
  - [ ] `services/ml/` folder structure
  - [ ] Model training scripts
  - [ ] Model evaluation framework
- [ ] Create feature store in MongoDB
  - [ ] Collection: `feature_store`
  - [ ] Versioning mechanism
  - [ ] Feature metadata
- [ ] Grafana Dashboard 4: System Monitoring
  - [ ] Kafka metrics (lag, throughput)
  - [ ] Spark metrics (job duration, stages)
  - [ ] MongoDB metrics (connections, operations)
  - [ ] JVM metrics (from Java services)
  - [ ] System metrics (CPU, memory)

**Deliverables:**
- ✅ ML datasets finalized
- ✅ ML pipeline structure ready
- ✅ Feature store in MongoDB
- ✅ Dashboard 4: System Monitoring completed

---

### 📅 TUẦN 8: Advanced Analytics (ML & Graph)

#### **🎯 Mục tiêu tuần:**
- 3 ML models trained and evaluated
- GraphFrames analysis completed
- Time series analysis

#### **👨‍💼 Nam - MLflow Setup & Code Review**
- [ ] Setup MLflow (optional but recommended)
  - [ ] Install MLflow
  - [ ] Configure tracking server
  - [ ] Model registry
- [ ] Code review for ML code
  - [ ] Review model training code
  - [ ] Verify evaluation metrics
  - [ ] Check for overfitting
- [ ] Create model deployment guide
  - [ ] How to load models
  - [ ] How to make predictions
  - [ ] Model versioning strategy
- [ ] Integration testing with ML models
  - [ ] Test batch prediction
  - [ ] Test real-time prediction (if applicable)

**Deliverables:**
- ✅ MLflow setup (optional)
- ✅ ML code review completed
- ✅ Model deployment guide
- ✅ ML integration tests

---

#### **👨‍💻 Thế (Java Developer) - ML Model Serving (Optional)**
- [ ] Create model serving API (Optional)
  - [ ] REST API to serve predictions
  - [ ] Load ML model (using PMML or ONNX)
  - [ ] Prediction endpoint
- [ ] Assist Huy with ML infrastructure
  - [ ] Help with data pipeline for ML
  - [ ] Review ML code
- [ ] Finalize Java services documentation
  - [ ] API documentation
  - [ ] Deployment guide
  - [ ] Configuration guide
- [ ] Performance testing Java services
  - [ ] Load testing
  - [ ] Stress testing
  - [ ] Benchmark results

**Deliverables:**
- ✅ ML serving API (optional)
- ✅ ML infrastructure support provided
- ✅ Java documentation completed
- ✅ Performance testing done

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Support ML Data Prep**
- [ ] Assist Huy with data preparation
  - [ ] Feature engineering pipeline
  - [ ] Data sampling for training
  - [ ] Data validation
- [ ] Optimize batch jobs for ML
  - [ ] Efficient feature extraction
  - [ ] Caching intermediate results
- [ ] Create data export utilities
  - [ ] Export data for ML (CSV, Parquet)
  - [ ] Sampling utilities
  - [ ] Data versioning
- [ ] Code cleanup and refactoring
  - [ ] Remove dead code
  - [ ] Improve modularity
  - [ ] Add more unit tests

**Deliverables:**
- ✅ ML data prep support completed
- ✅ Batch jobs optimized for ML
- ✅ Data export utilities created
- ✅ Code cleaned up

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Real-time Feature Engineering**
- [ ] Implement real-time feature computation
  - [ ] Streaming aggregations as features
  - [ ] Rolling window features
  - [ ] Stateful features
- [ ] Write features to feature store (MongoDB)
  - [ ] Real-time feature updates
  - [ ] Feature versioning
- [ ] Create feature serving API
  - [ ] FastAPI to query features
  - [ ] Low-latency feature retrieval
  - [ ] Caching layer
- [ ] Assist Huy with ML
  - [ ] Help with streaming ML inference (if needed)
  - [ ] Review ML code

**Deliverables:**
- ✅ Real-time feature engineering
- ✅ Features in feature store
- ✅ Feature serving API
- ✅ ML support provided

---

#### **👨‍💻 Huy (Data Scientist) - ML & Advanced Analytics** ⭐

###### **Machine Learning với Spark MLlib:**

**Model 1: Product Recommendation (ALS)**
```python
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

# Prepare data
ratings = spark.sql("""
    SELECT customer_id as user, 
           product_id as item, 
           1.0 as rating  -- implicit feedback
    FROM order_items
""")

# Split data
train, test = ratings.randomSplit([0.8, 0.2])

# Train ALS model
als = ALS(
    maxIter=10, 
    regParam=0.1, 
    userCol="user", 
    itemCol="item", 
    ratingCol="rating",
    coldStartStrategy="drop"
)

model = als.fit(train)

# Evaluate
predictions = model.transform(test)
evaluator = RegressionEvaluator(metricName="rmse", 
                                labelCol="rating", 
                                predictionCol="prediction")
rmse = evaluator.evaluate(predictions)

# Generate recommendations
user_recs = model.recommendForAllUsers(10)
```

**Model 2: Customer Churn Prediction (Random Forest)**
```python
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.evaluation import BinaryClassificationEvaluator

# Feature engineering
features = ["recency", "frequency", "monetary", "avg_order_value", 
            "days_since_last_order", "avg_review_score"]

assembler = VectorAssembler(inputCols=features, outputCol="features")
data = assembler.transform(customer_features)

# Label: churned = 1 if no order in last 90 days
data = data.withColumn("label", 
    when(col("days_since_last_order") > 90, 1).otherwise(0))

train, test = data.randomSplit([0.8, 0.2])

# Train Random Forest
rf = RandomForestClassifier(featuresCol="features", 
                            labelCol="label", 
                            numTrees=100)
model = rf.fit(train)

# Evaluate
predictions = model.transform(test)
evaluator = BinaryClassificationEvaluator()
auc = evaluator.evaluate(predictions)

# Feature importance
importances = model.featureImportances
```

**Model 3: Revenue Forecasting (Linear Regression)**
```python
from pyspark.ml.regression import LinearRegression
from pyspark.sql.functions import dayofweek, month, year

# Time series features
revenue_df = revenue_df.withColumn("day_of_week", dayofweek("date"))
revenue_df = revenue_df.withColumn("month", month("date"))
revenue_df = revenue_df.withColumn("year", year("date"))

# Lagged features
from pyspark.sql.window import Window
window_spec = Window.orderBy("date")
revenue_df = revenue_df.withColumn("lag_1", lag("revenue", 1).over(window_spec))
revenue_df = revenue_df.withColumn("lag_7", lag("revenue", 7).over(window_spec))

features = ["day_of_week", "month", "lag_1", "lag_7"]
assembler = VectorAssembler(inputCols=features, outputCol="features")
data = assembler.transform(revenue_df)

train, test = data.randomSplit([0.8, 0.2])

lr = LinearRegression(featuresCol="features", labelCol="revenue")
model = lr.fit(train)

predictions = model.transform(test)
```

###### **Graph Analytics với GraphFrames:**

```python
from graphframes import GraphFrame

# Construct graph
# Nodes: customers, products, sellers
customers = spark.table("customers").select(
    col("customer_id").alias("id"), 
    lit("customer").alias("type")
)
products = spark.table("products").select(
    col("product_id").alias("id"), 
    lit("product").alias("type")
)
sellers = spark.table("sellers").select(
    col("seller_id").alias("id"), 
    lit("seller").alias("type")
)

vertices = customers.union(products).union(sellers)

# Edges: purchases, sells
purchases = spark.table("orders").select(
    col("customer_id").alias("src"),
    col("product_id").alias("dst"),
    lit("purchases").alias("relationship")
)
sells = spark.table("order_items").select(
    col("seller_id").alias("src"),
    col("product_id").alias("dst"),
    lit("sells").alias("relationship")
)

edges = purchases.union(sells)

# Create GraphFrame
graph = GraphFrame(vertices, edges)

# PageRank: Identify influential sellers
pagerank = graph.pageRank(resetProbability=0.15, maxIter=10)
top_sellers = pagerank.vertices \
    .filter(col("type") == "seller") \
    .orderBy(col("pagerank").desc()) \
    .limit(10)

# Connected Components: Find communities
components = graph.connectedComponents()

# Triangle Count: Detect patterns
triangle_count = graph.triangleCount()

# Motif finding
motifs = graph.find("(customer)-[purchases]->(product); (seller)-[sells]->(product)")
```

###### **Time Series Analysis:**

```python
# Seasonality decomposition
from pyspark.sql.functions import month, year, avg

monthly_revenue = revenue_df.groupBy("year", "month") \
    .agg(sum("revenue").alias("monthly_revenue"))

# Trend analysis
window_spec = Window.orderBy("year", "month")
monthly_revenue = monthly_revenue.withColumn(
    "moving_avg_3m", 
    avg("monthly_revenue").over(window_spec.rowsBetween(-2, 0))
)

# Anomaly detection (IQR method)
from pyspark.sql.functions import expr

# Calculate Q1, Q3
quantiles = revenue_df.approxQuantile("revenue", [0.25, 0.75], 0.01)
q1, q3 = quantiles[0], quantiles[1]
iqr = q3 - q1

# Detect outliers
anomalies = revenue_df.filter(
    (col("revenue") < q1 - 1.5 * iqr) | 
    (col("revenue") > q3 + 1.5 * iqr)
)
```

**Deliverables:**
- ✅ 3 ML models trained and evaluated
- ✅ Model performance report (RMSE, AUC, R², etc.)
- ✅ GraphFrames analysis (PageRank, Components, Triangles)
- ✅ Time series analysis (seasonality, trends, anomalies)
- ✅ Models saved to MinIO/MongoDB
- ✅ Jupyter notebooks with analysis

---

### 📅 TUẦN 9: Integration, Testing & Monitoring

#### **🎯 Mục tiêu tuần:**
- Full pipeline working end-to-end
- All tests passing
- Monitoring dashboards operational
- Performance acceptable

#### **👨‍💼 Nam - Integration & Performance Testing** ⭐
- [ ] End-to-end integration testing
  - [ ] Data flow validation (Postgres → Kafka → Spark → MongoDB → Grafana)
  - [ ] Data consistency checks
  - [ ] Latency measurements
  - [ ] Throughput testing
- [ ] Performance tuning
  - [ ] Identify bottlenecks
  - [ ] Optimize slow queries
  - [ ] Tune Spark configurations
  - [ ] Optimize Kafka settings
- [ ] Load testing
  - [ ] Generate high data volume
  - [ ] Stress test all components
  - [ ] Measure breaking points
  - [ ] Document results
- [ ] Create deployment runbook
  - [ ] Step-by-step deployment guide
  - [ ] Configuration checklist
  - [ ] Troubleshooting guide
  - [ ] Rollback procedures

**Deliverables:**
- ✅ E2E integration tests passing
- ✅ Performance tuning completed
- ✅ Load testing report
- ✅ Deployment runbook

---

#### **👨‍💻 Thế (Java Developer) - Monitoring & Logging**
- [ ] Centralized logging setup
  - [ ] Configure structured logging
  - [ ] Log aggregation (ELK stack optional, or file-based)
  - [ ] Log correlation IDs
- [ ] Metrics collection
  - [ ] Expose Prometheus metrics from Java services
  - [ ] JVM metrics (heap, GC, threads)
  - [ ] Application metrics (requests, errors)
- [ ] Health checks
  - [ ] Kubernetes liveness probes
  - [ ] Readiness probes
  - [ ] Dependency health checks
- [ ] Testing
  - [ ] Integration tests for Java services
  - [ ] Error scenario testing
  - [ ] Performance regression tests

**Deliverables:**
- ✅ Centralized logging working
- ✅ Metrics collection operational
- ✅ Health checks configured
- ✅ Testing completed

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Testing & Documentation**
- [ ] Comprehensive testing
  - [ ] Unit tests for all functions
  - [ ] Integration tests for pipelines
  - [ ] Data quality tests
  - [ ] Performance regression tests
- [ ] Test coverage report
  - [ ] Measure code coverage (>80% target)
  - [ ] Identify untested code
  - [ ] Add missing tests
- [ ] Documentation
  - [ ] Batch processing user guide
  - [ ] Code documentation (docstrings)
  - [ ] Performance tuning guide
  - [ ] Troubleshooting guide
- [ ] Create demo scenarios
  - [ ] Demo 1: Batch processing pipeline
  - [ ] Demo 2: Performance optimization
  - [ ] Demo 3: Data quality checks

**Deliverables:**
- ✅ Test coverage >80%
- ✅ All tests passing
- ✅ Documentation completed
- ✅ Demo scenarios prepared

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Streaming Testing**
- [ ] Streaming integration tests
  - [ ] Test window aggregations
  - [ ] Test watermarking with late data
  - [ ] Test stateful processing
  - [ ] Test exactly-once semantics
- [ ] Failure recovery testing
  - [ ] Test checkpoint recovery
  - [ ] Test after Kafka restart
  - [ ] Test after Spark restart
  - [ ] Measure recovery time
- [ ] Performance testing
  - [ ] Measure processing latency
  - [ ] Measure throughput
  - [ ] Test with different data rates
  - [ ] Document results
- [ ] Documentation
  - [ ] Streaming user guide
  - [ ] Troubleshooting guide
  - [ ] Demo scenarios

**Deliverables:**
- ✅ Streaming tests passing
- ✅ Failure recovery verified
- ✅ Performance testing completed
- ✅ Documentation done

---

#### **👨‍💻 Huy (Data Scientist) - Finalize Dashboards & Visualization**
- [ ] Finalize all Grafana dashboards
  - [ ] Dashboard 1: Business Metrics (polish)
  - [ ] Dashboard 2: Customer Analytics (polish)
  - [ ] Dashboard 3: Product Performance (polish)
  - [ ] Dashboard 4: System Monitoring (polish)
  - [ ] Dashboard 5: ML Model Performance (new)
- [ ] Add interactive features
  - [ ] Drill-down capabilities
  - [ ] Date range selectors
  - [ ] Variable templates
- [ ] Configure alerts
  - [ ] Revenue anomaly alerts
  - [ ] System health alerts
  - [ ] Data quality alerts
  - [ ] Email/Slack notifications (optional)
- [ ] Create dashboard user guide
  - [ ] How to navigate dashboards
  - [ ] What each metric means
  - [ ] How to interpret alerts
- [ ] ML model monitoring dashboard
  - [ ] Model performance over time
  - [ ] Prediction accuracy
  - [ ] Feature drift detection

**Deliverables:**
- ✅ 5 Grafana dashboards finalized
- ✅ Interactive features added
- ✅ Alerts configured
- ✅ Dashboard user guide
- ✅ ML monitoring dashboard

---

### 📅 TUẦN 10: Documentation, Presentation & Finalization

#### **🎯 Mục tiêu tuần:**
- Final report completed
- Presentation slides ready
- Demo video recorded
- All documentation finalized

#### **👨‍💼 Nam - Final Report & Presentation** ⭐
- [ ] Write final report (30-40 pages)
  - [ ] **Section 1:** Introduction & Business Context
  - [ ] **Section 2:** Architecture & Design
    - Lambda Architecture explanation
    - Component diagram
    - Data flow diagram
  - [ ] **Section 3:** Technology Stack
    - Justification for each technology
    - Alternatives considered
  - [ ] **Section 4:** Implementation Details
    - Batch processing
    - Streaming processing
    - Java services
    - ML & Analytics
  - [ ] **Section 5:** Spark Advanced Features (CRITICAL)
    - Detailed explanation of 6 requirements
    - Code snippets
    - Execution plans
    - Performance metrics
  - [ ] **Section 6:** Testing & Quality Assurance
  - [ ] **Section 7:** Monitoring & Operations
  - [ ] **Section 8:** Challenges & Lessons Learned
  - [ ] **Section 9:** Future Improvements
  - [ ] **Appendices:** Code samples, configurations

- [ ] Create presentation slides (20-25 slides)
  - [ ] Slide 1: Title & Team
  - [ ] Slides 2-3: Problem Statement & Business Context
  - [ ] Slides 4-5: Architecture Overview
  - [ ] Slides 6-10: Spark Advanced Features (DEMO)
  - [ ] Slides 11-12: Streaming Processing
  - [ ] Slides 13-14: ML & Analytics
  - [ ] Slides 15-17: Results & Metrics
  - [ ] Slides 18-19: Challenges & Lessons
  - [ ] Slide 20: Demo
  - [ ] Slide 21: Future Work
  - [ ] Slide 22: Q&A

- [ ] Record demo video (10-15 minutes)
  - [ ] Introduction
  - [ ] Architecture walkthrough
  - [ ] Live demo: Data flowing through pipeline
  - [ ] Grafana dashboards
  - [ ] Code walkthrough (key parts)
  - [ ] Q&A preparation

- [ ] Prepare Q&A document
  - [ ] Anticipate questions
  - [ ] Prepare answers
  - [ ] Technical deep dives ready

**Deliverables:**
- ✅ Final report (30-40 pages)
- ✅ Presentation slides (20-25 slides)
- ✅ Demo video (10-15 min)
- ✅ Q&A document

---

#### **👨‍💻 Thế (Java Developer) - Java Services Documentation**
- [ ] Write Java services documentation
  - [ ] Architecture of Java services
  - [ ] API documentation (OpenAPI/Swagger)
  - [ ] Configuration guide
  - [ ] Deployment guide
- [ ] Code documentation
  - [ ] Javadoc for all classes
  - [ ] README for each service
  - [ ] Example usage
- [ ] Create deployment guide
  - [ ] Docker deployment
  - [ ] Kubernetes deployment
  - [ ] Configuration management
- [ ] Prepare demo scenarios
  - [ ] Demo: Java Kafka consumer in action
  - [ ] Demo: MongoDB writer performance
  - [ ] Demo: Circuit breaker in action

**Deliverables:**
- ✅ Java documentation completed
- ✅ API documentation
- ✅ Deployment guide
- ✅ Demo scenarios prepared

---

#### **👨‍💻 Quang (Spark Batch Engineer) - Batch Processing Documentation**
- [ ] Write batch processing documentation
  - [ ] Architecture of batch pipeline
  - [ ] Data flow explanation
  - [ ] Performance optimization guide
  - [ ] Troubleshooting guide
- [ ] Create code documentation
  - [ ] Docstrings for all functions
  - [ ] README for each module
  - [ ] Example usage
- [ ] Create demo notebook
  - [ ] Jupyter notebook demonstrating:
    - Broadcast join
    - Window functions
    - Pivot operations
    - Performance optimization
- [ ] Contribute to final report
  - [ ] Batch processing section
  - [ ] Performance metrics section

**Deliverables:**
- ✅ Batch documentation completed
- ✅ Code documentation
- ✅ Demo notebook
- ✅ Report contribution

---

#### **👨‍💻 Hoàng (Spark Streaming Engineer) - Streaming Documentation**
- [ ] Write streaming documentation
  - [ ] Architecture of streaming pipeline
  - [ ] Watermarking strategy explained
  - [ ] Stateful processing guide
  - [ ] Troubleshooting guide
- [ ] Create code documentation
  - [ ] Docstrings for all functions
  - [ ] README for streaming module
  - [ ] Example usage
- [ ] Create demo notebook
  - [ ] Jupyter notebook demonstrating:
    - Window aggregations
    - Watermarking
    - Stateful processing
    - Exactly-once semantics
- [ ] Contribute to final report
  - [ ] Streaming processing section
  - [ ] Real-time metrics section

**Deliverables:**
- ✅ Streaming documentation completed
- ✅ Code documentation
- ✅ Demo notebook
- ✅ Report contribution

---

#### **👨‍💻 Huy (Data Scientist) - ML & Visualization Documentation**
- [ ] Write ML documentation
  - [ ] Model architecture & algorithms
  - [ ] Feature engineering explained
  - [ ] Model evaluation & results
  - [ ] GraphFrames analysis explained
  - [ ] Time series analysis explained
- [ ] Create ML notebooks
  - [ ] Notebook 1: ALS Recommendation
  - [ ] Notebook 2: Churn Prediction
  - [ ] Notebook 3: Revenue Forecasting
  - [ ] Notebook 4: Graph Analytics
  - [ ] Notebook 5: Time Series Analysis
- [ ] Write dashboard documentation
  - [ ] Dashboard user guide
  - [ ] Metrics explanation
  - [ ] How to create alerts
- [ ] Contribute to final report
  - [ ] ML & Analytics section
  - [ ] Visualization section
  - [ ] Results & insights section

**Deliverables:**
- ✅ ML documentation completed
- ✅ 5 ML notebooks
- ✅ Dashboard documentation
- ✅ Report contribution

---

#### **ALL MEMBERS - Final Week Activities:**
- [ ] Practice presentation (2-3 times)
- [ ] Review final report
- [ ] Test demo scenarios
- [ ] Prepare for Q&A
- [ ] Final code cleanup
- [ ] Final testing
- [ ] GitHub repo cleanup (remove sensitive data)
- [ ] Create release tag (v1.0.0)

---

#### 3.4. Technology Stack Summary

| Component | Technology | Owner |
|-----------|-----------|-------|
| **Data Source** | PostgreSQL | Thế |
| **CDC** | Debezium | Member 1, 2 |
| **Message Queue** | Apache Kafka | Member 1, 2, 4 |
| **Stream Processing** | PySpark Structured Streaming | Hoàng |
| **Batch Processing** | PySpark | Quang |
| **Distributed Storage** | MinIO (S3-compatible) | Member 1 |
| **NoSQL Database** | MongoDB Atlas | Member 1, 5 |
| **Java Services** | Spring Boot + Kafka + MongoDB | Member 1, 2 |
| **ML & Analytics** | Spark MLlib, GraphFrames | Huy |
| **Orchestration** | Apache Airflow | Member 1 |
| **Containerization** | Docker | All |
| **Orchestration** | Kubernetes (Minikube) | Member 1 |
| **Visualization** | Grafana | Huy |
| **Monitoring** | Prometheus (optional) | Member 1, 2 |
| **Version Control** | Git/GitHub | All |

#### 3.5. Code Structure

```
Big-Data/
├── config/
│   ├── kafka.conf
│   ├── mongodb.env
│   ├── spark_config.py
│   └── postgres.conf
├── data/
│   ├── external/          # Raw CSV files
│   ├── bronze/            # Parquet (from Kafka/CDC)
│   ├── silver/            # Cleaned & joined data
│   └── gold/              # Aggregated data
├── services/
│   ├── spark-batch/
│   │   ├── data_ingestion.py
│   │   ├── bronze_to_silver.py
│   │   ├── silver_to_gold.py
│   │   └── utils.py
│   ├── spark-streaming/
│   │   ├── kafka_consumer.py
│   │   ├── streaming_aggregations.py
│   │   ├── stateful_streaming.py
│   │   └── utils.py
│   ├── java-consumer/
│   │   └── src/main/java/...
│   ├── java-mongodb-writer/
│   │   └── src/main/java/...
│   ├── ml/
│   │   ├── recommendation.py
│   │   ├── churn_prediction.py
│   │   ├── revenue_forecasting.py
│   │   ├── graph_analysis.py
│   │   └── time_series.py
│   └── warehouse-nosql/
│       └── mongo_connector.py
├── deployment/
│   ├── k8s/
│   │   ├── namespace.yaml
│   │   ├── debezium-deployment.yaml
│   │   ├── kafka-deployment.yaml
│   │   └── spark-deployment.yaml
│   ├── docker/
│   │   └── docker-compose.yml
│   └── scripts/
│       └── deploy.sh
├── orchestration/
│   └── dags/
│       ├── batch_ingestion_dag.py
│       ├── ml_training_dag.py
│       └── monitoring_dag.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── performance/
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── user_guide.md
│   └── api_docs.md
├── notebooks/
│   ├── eda.ipynb
│   ├── ml_recommendation.ipynb
│   ├── ml_churn.ipynb
│   ├── ml_forecasting.ipynb
│   └── graph_analysis.ipynb
├── scripts/
│   ├── setup_env.sh
│   ├── data_generator.py
│   ├── data_quality.py
│   └── verify_pipeline.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

#### 3.6. Communication & Collaboration

**Daily Standup (15 minutes):**
- What did you do yesterday?
- What will you do today?
- Any blockers?
- Time: 9:00 AM (Slack/Zalo call)

**Weekly Review (1 hour):**
- Review deliverables
- Demo progress
- Adjust plan if needed
- Time: Friday 3:00 PM

**Code Review:**
- All code must be reviewed before merge
- Use GitHub Pull Requests
- At least 1 approval required
- Team Leader reviews critical code

**Tools:**
- **Communication:** Slack/Zalo/Discord
- **Project Management:** Trello/Jira/GitHub Projects
- **Version Control:** GitHub
- **Documentation:** Google Docs, Notion
- **File Sharing:** Google Drive

---

#### 3.7. Definition of Done

**For each task:**
- [ ] Code written and tested
- [ ] Unit tests passing (if applicable)
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Merged to main branch

**For each week:**
- [ ] All checklist items completed
- [ ] Deliverables ready
- [ ] Demo prepared
- [ ] No blocking issues

**For final project:**
- [ ] All 6 Spark requirements implemented ✅
- [ ] All 11 knowledge areas covered ✅
- [ ] Pipeline working end-to-end ✅
- [ ] Tests passing ✅
- [ ] Documentation complete ✅
- [ ] Dashboards operational ✅
- [ ] Presentation ready ✅
- [ ] Demo video recorded ✅

---

### CRITICAL SUCCESS FACTORS

#### ⭐ Top Priorities (MUST HAVE):
1. **Spark Advanced Features (60%):** All 6 requirements fully implemented
2. **Working Pipeline (20%):** End-to-end data flow operational
3. **Documentation (10%):** Clear, comprehensive report
4. **Visualization (10%):** Grafana dashboards showing results

#### ⚠️ Medium Priority (NICE TO HAVE):
- Advanced ML models with high accuracy
- Complex graph analysis
- Perfect performance optimization
- Comprehensive testing (>90% coverage)

#### 💡 Low Priority (BONUS):
- Security features
- Advanced auto-scaling
- CI/CD pipeline
- Production-ready deployment

---

**Good luck team! Chúc mừng thành công! 🚀**

###### **MEMBER 1 - TEAM LEADER (Bạn)**

**Vai trò:** Project Manager + Infrastructure Lead + Integration Engineer

**Nhiệm vụ chính:**
1. **Quản lý dự án (Throughout):**
   - Tổ chức họp nhóm hàng tuần
   - Review code của các thành viên
   - Đảm bảo timeline
   - Phân giải blocking issues

2. **Infrastructure Setup (Tuần 1-2):**
   - Setup Kafka (Confluent Cloud hoặc Local)
   - Setup MinIO (S3-compatible storage)
   - Setup MongoDB Atlas
   - Setup Kubernetes (Minikube)
   - Viết docker-compose/k8s manifests
   - Setup Debezium CDC

3. **Integration & Orchestration (Tuần 6-9):**
   - Tích hợp tất cả components
   - Setup Apache Airflow DAGs
   - End-to-end testing
   - Performance tuning

4. **Documentation (Tuần 10):**
   - Viết báo cáo tổng hợp
   - Tạo presentation slides
   - Tạo demo video

**Deliverables:**
- Tuần 2: Infrastructure ready (Kafka, MinIO, MongoDB, K8s)
- Tuần 7: Airflow DAGs hoạt động
- Tuần 9: Pipeline end-to-end test passed
- Tuần 10: Báo cáo + Slides + Demo video

---

###### **Thế - SPARK BATCH ENGINEER**

**Vai trò:** Chuyên gia Spark Batch Processing

**Nhiệm vụ chính:**

1. **Data Ingestion (Tuần 3):**
   - Tải full dataset Olist (9 files CSV)
   - Ingest vào Bronze layer (Parquet format)
   - Data quality checks

2. **Batch Processing - Core (Tuần 3-4):**
   
   **File: `batch_transformations.py`**
   - Implement complex joins:
     - Broadcast join: orders ⋈ product_categories
     - Sort-merge join: orders ⋈ order_items ⋈ products
     - Multiple join optimization (4-5 tables)
   
   - Implement aggregations:
     - Revenue by seller/category/month
     - Customer RFM segmentation
     - Product performance metrics
   
   - Implement UDFs:
     - Custom discount calculator
     - Delivery status classifier
     - Review sentiment scorer (simple rule-based)

3. **Advanced Transformations (Tuần 4-5):**
   
   **File: `advanced_batch.py`**
   - Window functions:
     - Ranking top products per category
     - Running totals and moving averages
     - Lead/Lag for trend analysis
   
   - Pivot/Unpivot operations:
     - Payment methods distribution pivot
     - Category sales matrix
   
   - Custom aggregation functions:
     - Weighted average ratings
     - Geometric mean for growth rates

4. **Performance Optimization (Tuần 5):**
   - Implement partitioning strategies
   - Bucketing for join optimization
   - Caching strategies
   - Analyze execution plans (`.explain()`)
   - Document performance improvements

**Deliverables:**
- Tuần 3: Bronze → Silver data pipeline
- Tuần 4: Complex transformations với joins + UDFs
- Tuần 5: Silver → Gold aggregations + optimization
- Tuần 5: Performance report (before/after optimization)

**Kỹ thuật cần thực hiện:**
- ✅ Broadcast join
- ✅ Sort-merge join
- ✅ Window functions (rank, dense_rank, row_number, lead, lag)
- ✅ Pivot/Unpivot
- ✅ Custom UDFs
- ✅ Partitioning & Bucketing
- ✅ Cache & Persist

---

###### **Quang - SPARK STREAMING ENGINEER**

**Vai trò:** Chuyên gia Spark Structured Streaming

**Nhiệm vụ chính:**

1. **Streaming Pipeline Setup (Tuần 6):**
   
   **File: `streaming_consumer.py`**
   - Consume từ Kafka topics
   - Parse JSON messages
   - Schema validation

2. **Real-time Aggregations (Tuần 6):**
   
   **File: `streaming_aggregations.py`**
   - Window aggregations:
     - Tumbling window (5 minutes): Revenue per 5 min
     - Sliding window (1 hour, slide 10 min): Moving hourly revenue
     - Session window: Customer session analysis
   
   - Watermarking:
     - Handle late data (10 minutes watermark)
     - Drop late events strategy
     - Update mode vs Append mode vs Complete mode

3. **Stateful Streaming (Tuần 7):**
   
   **File: `stateful_streaming.py`**
   - MapGroupsWithState:
     - Track customer session state
     - Detect fraudulent patterns
   
   - FlatMapGroupsWithState:
     - Complex event processing
     - Shopping cart abandonment detection
   
   - Checkpointing:
     - Configure checkpoint location
     - Recovery testing

4. **Stream-Batch Integration (Tuần 7):**
   - Write streaming results to MongoDB
   - Write to Delta Lake (Bronze/Silver)
   - Trigger modes (ProcessingTime, Once, Continuous)
   - Exactly-once semantics

**Deliverables:**
- Tuần 6: Kafka → Spark Streaming → MinIO pipeline
- Tuần 6: Window aggregations + watermarking working
- Tuần 7: Stateful processing implementation
- Tuần 7: Streaming → MongoDB integration

**Kỹ thuật cần thực hiện:**
- ✅ Structured Streaming
- ✅ Window functions (tumbling, sliding, session)
- ✅ Watermarking
- ✅ Stateful processing (mapGroupsWithState)
- ✅ Multiple output modes
- ✅ Checkpointing
- ✅ Exactly-once delivery

---

###### **Hoàng - ML & ADVANCED ANALYTICS ENGINEER**

**Vai trò:** Data Scientist - Machine Learning & Graph Analytics

**Nhiệm vụ chính:**

1. **Machine Learning với Spark MLlib (Tuần 8):**
   
   **File: `ml_models.py`**
   
   **Model 1: Product Recommendation (Collaborative Filtering)**
   - Load order_items data
   - Create user-item matrix
   - Train ALS (Alternating Least Squares) model
   - Evaluate with RMSE
   - Generate top-N recommendations
   
   **Model 2: Customer Churn Prediction (Classification)**
   - Feature engineering:
     - Days since last purchase
     - Number of orders
     - Average order value
     - Review scores
   - Train Random Forest Classifier
   - Evaluate with AUC, Precision, Recall
   - Feature importance analysis
   
   **Model 3: Revenue Forecasting (Regression)**
   - Time series features
   - Linear Regression or Gradient Boosted Trees
   - Predict next month revenue

2. **Graph Analytics với GraphFrames (Tuần 8):**
   
   **File: `graph_analysis.py`**
   
   - Construct seller-product-customer graph:
     - Nodes: Sellers, Products, Customers
     - Edges: sells, purchases, reviews
   
   - Graph algorithms:
     - PageRank: Identify influential sellers
     - Connected Components: Find seller communities
     - Triangle Count: Detect fraud patterns
     - Shortest Paths: Supply chain analysis
   
   - Motif finding:
     - Find patterns like "customer → product → seller"

3. **Time Series Analysis (Tuần 8):**
   
   **File: `time_series_analysis.py`**
   
   - Seasonality decomposition (revenue by month/quarter)
   - Trend analysis
   - Anomaly detection (IQR method)
   - Moving averages (7-day, 30-day)
   - Growth rate calculations

**Deliverables:**
- Tuần 8: 3 ML models trained and evaluated
- Tuần 8: GraphFrames analysis với 3+ algorithms
- Tuần 8: Time series analysis notebook
- Tuần 8: Model performance report + visualizations

**Kỹ thuật cần thực hiện:**
- ✅ Spark MLlib (ALS, RandomForest, LinearRegression)
- ✅ GraphFrames (PageRank, ConnectedComponents, TriangleCount)
- ✅ Time series analysis
- ✅ Feature engineering
- ✅ Model evaluation metrics

---

###### **Huy - DATA ENGINEERING & VISUALIZATION**

**Vai trò:** Data Engineer + Visualization Engineer

**Nhiệm vụ chính:**

1. **Data Quality & Validation (Tuần 3):**
   
   **File: `data_quality.py`**
   - Data profiling
   - Null value analysis
   - Duplicate detection
   - Schema validation
   - Data quality report

2. **NoSQL Database Integration (Tuần 4-5):**
   
   **File: `mongo_connector.py`**
   - Design MongoDB schema (collections):
     - `revenue_metrics` (pre-aggregated)
     - `customer_segments` (RFM)
     - `product_performance`
     - `seller_analytics`
   
   - Write Spark → MongoDB connector
   - Implement upsert logic
   - Indexing strategy
   - Query optimization

3. **Postgres CDC Setup (Tuần 6):**
   
   **File: `cdc_setup.md` + configs**
   - Configure PostgreSQL for CDC (WAL)
   - Setup Debezium connector
   - Kafka topic mapping
   - Schema registry integration

4. **Grafana Dashboards (Tuần 9-10):**
   
   **Dashboards:**
   
   **Dashboard 1: Real-time Business Metrics**
   - Revenue per 5 minutes (line chart)
   - Top 10 products (bar chart)
   - Orders by state (map visualization)
   - Alert rules for anomalies
   
   **Dashboard 2: Customer Analytics**
   - Customer segments distribution (pie chart)
   - RFM heatmap
   - Churn prediction summary
   
   **Dashboard 3: Seller Performance**
   - Seller ranking table
   - Delivery performance metrics
   - Review sentiment trends
   
   **Dashboard 4: System Monitoring**
   - Kafka lag
   - Spark job duration
   - Data pipeline health

5. **Testing & Documentation (Tuần 9):**
   - Integration tests
   - Performance benchmarks
   - User guide for dashboards
   - Troubleshooting guide

**Deliverables:**
- Tuần 3: Data quality report
- Tuần 5: MongoDB schema + connector
- Tuần 6: Debezium CDC working
- Tuần 10: 4 Grafana dashboards deployed
- Tuần 10: Testing report + documentation

**Kỹ thuật cần thực hiện:**
- ✅ MongoDB integration
- ✅ Debezium CDC
- ✅ Grafana dashboards
- ✅ Data quality framework

---

#### 3.3. Weekly Sprint Plan

###### **TUẦN 1-2: Infrastructure Setup Sprint**

**Mục tiêu:** Tất cả infrastructure services sẵn sàng

**Công việc:**

**Nam:**
- [ ] Setup Kafka cluster (Confluent Cloud hoặc local)
- [ ] Setup MinIO (docker hoặc k8s)
- [ ] Setup MongoDB Atlas account
- [ ] Setup Minikube + kubectl
- [ ] Create base docker-compose.yml
- [ ] Document connection strings

**Thế-5:**
- [ ] Install Java 17, Python 3.12, Spark 3.5.8
- [ ] Setup development environment
- [ ] Clone & explore Olist dataset
- [ ] Study Lambda Architecture pattern
- [ ] Setup Git workflow (branches, PR process)

**Definition of Done:**
- [ ] Kafka topic created and accessible
- [ ] MinIO bucket created, upload/download tested
- [ ] MongoDB connection successful
- [ ] Minikube running, can deploy test pod
- [ ] All members can run Spark locally

---

###### **TUẦN 3-4: Batch Processing Core Sprint**

**Mục tiêu:** Spark Batch pipeline hoàn chỉnh với joins + aggregations

**Member 1:**
- [ ] Setup Airflow (docker)
- [ ] Create DAG for batch ingestion
- [ ] Monitor Thế's progress
- [ ] Code review

**Thế:**
- [ ] Download all 9 Olist CSV files
- [ ] Create `data_ingestion.py` (CSV → Parquet)
- [ ] Create `bronze_to_silver.py`:
  - [ ] Broadcast join implementation
  - [ ] Sort-merge join implementation
  - [ ] 3+ UDFs for business logic
- [ ] Create `silver_to_gold.py`:
  - [ ] Revenue aggregations
  - [ ] RFM segmentation
  - [ ] Product performance metrics

**Quang:**
- [ ] Study Structured Streaming documentation
- [ ] Prepare streaming test data
- [ ] Assist Thế with joins

**Hoàng:**
- [ ] Data exploration & EDA
- [ ] Feature engineering for ML
- [ ] Prepare ML dataset

**Huy:**
- [ ] Run data quality checks
- [ ] Create data profiling report
- [ ] Design MongoDB schema
- [ ] Start MongoDB connector

**Definition of Done:**
- [ ] Bronze layer: 9 tables in Parquet format
- [ ] Silver layer: Joined tables with clean data
- [ ] Gold layer: Aggregated metrics ready
- [ ] At least 2 types of joins working
- [ ] At least 3 UDFs implemented

---

###### **TUẦN 5: Optimization & Advanced Batch Sprint**

**Member 1:**
- [ ] Performance monitoring setup
- [ ] Resource allocation tuning

**Thế:**
- [ ] Implement window functions (rank, lead, lag)
- [ ] Implement pivot/unpivot operations
- [ ] Partitioning strategy (by year, month)
- [ ] Bucketing for frequently joined tables
- [ ] Caching strategy
- [ ] Analyze `.explain()` output
- [ ] Document performance improvements

**Huy:**
- [ ] Complete MongoDB connector
- [ ] Write batch data to MongoDB
- [ ] Create indexes
- [ ] Test query performance

**Definition of Done:**
- [ ] Window functions working (3+ examples)
- [ ] Pivot table created
- [ ] Partitioned data in MinIO
- [ ] Bucketed tables created
- [ ] Performance report showing improvement
- [ ] MongoDB contains aggregated data

---

###### **TUẦN 6-7: Streaming Processing Sprint**

**Mục tiêu:** Real-time pipeline end-to-end

**Member 1:**
- [ ] Setup Debezium
- [ ] Configure Postgres → Kafka CDC
- [ ] Monitor streaming pipeline
- [ ] Assist integration

**Thế:**
- [ ] Support streaming integration
- [ ] Code review for Quang

**Quang:**
- [ ] Create `streaming_consumer.py`
- [ ] Implement window aggregations:
  - [ ] Tumbling window (5 min)
  - [ ] Sliding window (1 hour)
  - [ ] Session window
- [ ] Implement watermarking (10 min)
- [ ] Test all output modes (append/update/complete)
- [ ] Create `stateful_streaming.py`:
  - [ ] MapGroupsWithState for session tracking
  - [ ] Checkpoint configuration
- [ ] Write streaming results to MongoDB
- [ ] Write streaming results to MinIO (Delta Lake)

**Huy:**
- [ ] Configure Debezium connector
- [ ] Test CDC pipeline
- [ ] Create Postgres test data generator script

**Definition of Done:**
- [ ] Debezium capturing Postgres changes
- [ ] Kafka topics receiving events
- [ ] Spark Streaming consuming from Kafka
- [ ] Window aggregations working
- [ ] Watermarking handling late data
- [ ] Stateful processing working
- [ ] Results appearing in MongoDB real-time

---

###### **TUẦN 8: Advanced Analytics Sprint**

**Mục tiêu:** ML models + Graph analysis hoàn chỉnh

**Member 1:**
- [ ] Review ML code
- [ ] Setup MLflow (optional but good)

**Hoàng:**
- [ ] Implement ALS Recommendation:
  - [ ] Train model
  - [ ] Evaluate RMSE
  - [ ] Generate recommendations
- [ ] Implement Churn Prediction:
  - [ ] Feature engineering
  - [ ] Train Random Forest
  - [ ] Evaluate metrics (AUC, F1)
- [ ] Implement Revenue Forecasting:
  - [ ] Train regression model
  - [ ] Evaluate RMSE, R²
- [ ] GraphFrames analysis:
  - [ ] Build graph
  - [ ] Run PageRank
  - [ ] Run Connected Components
  - [ ] Motif finding
- [ ] Time series analysis:
  - [ ] Seasonality detection
  - [ ] Trend analysis
  - [ ] Anomaly detection

**Thế, 3:**
- [ ] Assist with data preparation for ML
- [ ] Review ML code

**Huy:**
- [ ] Prepare datasets for ML from MongoDB
- [ ] Validate ML results

**Definition of Done:**
- [ ] 3 ML models trained and evaluated
- [ ] Model performance report
- [ ] GraphFrames analysis completed
- [ ] Time series analysis completed
- [ ] Results saved to MongoDB

---

###### **TUẦN 9: Integration & Testing Sprint**

**Mục tiêu:** End-to-end pipeline hoạt động ổn định

**Member 1:**
- [ ] End-to-end integration testing
- [ ] Airflow DAGs for full pipeline
- [ ] Performance tuning
- [ ] Load testing
- [ ] Fix integration bugs

**Thế, 3, 4:**
- [ ] Bug fixes
- [ ] Code refactoring
- [ ] Add error handling
- [ ] Add logging
- [ ] Optimize slow jobs

**Huy:**
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] System monitoring setup
- [ ] Start Grafana dashboards

**Definition of Done:**
- [ ] Full pipeline runs end-to-end without errors
- [ ] All Airflow DAGs successful
- [ ] Performance acceptable (jobs complete in reasonable time)
- [ ] Error handling in place
- [ ] Logs available for debugging

---

###### **TUẦN 10: Visualization & Documentation Sprint**

**Mục tiêu:** Hoàn thiện dashboard, báo cáo, và presentation

**Member 1:**
- [ ] Write final report (architecture, design decisions)
- [ ] Create presentation slides
- [ ] Record demo video
- [ ] Prepare Q&A document

**Thế, 3, 4:**
- [ ] Write technical documentation for their components
- [ ] Create code documentation (docstrings)
- [ ] Write README for each module
- [ ] Prepare demo scenarios

**Huy:**
- [ ] Complete 4 Grafana dashboards
- [ ] Create dashboard user guide
- [ ] Write troubleshooting guide
- [ ] Prepare demo data

**All Members:**
- [ ] Practice presentation
- [ ] Review báo cáo
- [ ] Test demo scenarios
- [ ] Finalize documentation

**Definition of Done:**
- [ ] 4 Grafana dashboards working
- [ ] Final report completed (30-40 pages)
- [ ] Presentation slides ready (20-25 slides)
- [ ] Demo video recorded (10-15 minutes)
- [ ] All code documented
- [ ] README updated

---

#### 3.4. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Member không đủ skill Spark | High | Medium | Học tập intensive tuần đầu, pair programming, code review |
| Infrastructure setup lâu | Medium | High | Member 1 làm trước 2 tuần, có plan B (dùng cloud services) |
| Data không đủ lớn để demo | Medium | Low | Script duplicate data, tạo synthetic data |
| Kubernetes phức tạp | Low | Medium | Dùng Minikube đơn giản hóa, không cần multi-node |
| Integration issues | High | High | Reserve tuần 9 cho integration, daily standup |
| Member bỏ cuộc giữa chừng | High | Low | Phân công rõ ràng, milestone tracking, peer pressure |

#### 3.5. Tools & Communication

**Communication:**
- Daily standup (15 min): Slack/Zalo call
- Weekly review (1 hour): In-person or Zoom
- Code review: GitHub Pull Requests

**Project Management:**
- Trello/Jira: Task tracking
- GitHub Projects: Kanban board
- Google Sheets: Timeline tracking

**Technical:**
- Git/GitHub: Version control
- Slack/Discord: Team communication
- Google Drive: Document sharing
- Notion: Knowledge base

---

### PHẦN 4: CÁC ĐIỂM LƯU Ý KỸ THUẬT

#### 4.1. Spark Configuration for Learning

```python
# spark_config.py
spark = SparkSession.builder \
    .appName("BigDataProject") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.sql.autoBroadcastJoinThreshold", "10485760")  # 10MB \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.streaming.kafka.consumer.cache.enabled", "false") \
    .getOrCreate()
```

#### 4.2. Dataset Augmentation Strategy

```python
# Tạo data lớn hơn từ Olist
def augment_data(df, multiplier=10):
    """Nhân data lên 10 lần với variation"""
    from pyspark.sql.functions import concat, lit, rand, date_add
    
    augmented = df
    for i in range(multiplier):
        temp = df.withColumn("order_id", 
            concat(col("order_id"), lit(f"_gen{i}")))
        temp = temp.withColumn("order_purchase_timestamp",
            date_add(col("order_purchase_timestamp"), 
                     (rand() * 365).cast("int")))
        augmented = augmented.union(temp)
    
    return augmented
```

#### 4.3. Kafka Topic Design

```
orders_raw          - Raw order events from CDC
orders_enriched     - Enriched with customer/product info
revenue_metrics     - Real-time revenue aggregations
fraud_alerts        - Fraud detection alerts
```

#### 4.4. MongoDB Collections Design

```javascript
// revenue_metrics collection
{
  "_id": "2024-01-15T10:00:00_electronics",
  "window_start": ISODate("2024-01-15T10:00:00Z"),
  "window_end": ISODate("2024-01-15T10:05:00Z"),
  "category": "electronics",
  "revenue": 15420.50,
  "order_count": 127,
  "avg_order_value": 121.42
}

// customer_segments collection
{
  "_id": "customer_123",
  "recency_days": 15,
  "frequency": 8,
  "monetary": 1250.00,
  "rfm_segment": "Champion",
  "churn_probability": 0.05,
  "recommended_products": ["prod_1", "prod_5", "prod_12"]
}
```

#### 4.5. Key Spark Operations to Demonstrate

**1. Broadcast Join Example:**
```python
# Small dimension table
product_categories = spark.read.parquet("gold/product_categories")
broadcast_df = broadcast(product_categories)

# Large fact table
orders = spark.read.parquet("silver/orders")

# Broadcast join (efficient)
result = orders.join(broadcast_df, "product_id")
```

**2. Window Functions Example:**
```python
from pyspark.sql.window import Window
from pyspark.sql.functions import rank, dense_rank, row_number

window_spec = Window.partitionBy("category").orderBy(col("revenue").desc())

top_products = df.withColumn("rank", rank().over(window_spec)) \
                 .filter(col("rank") <= 10)
```

**3. Watermarking Example:**
```python
# Streaming with watermark
streaming_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "orders") \
    .load()

parsed = streaming_df.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json("json", schema).alias("data")) \
    .select("data.*")

# Watermark: allow 10 minutes late data
windowed = parsed \
    .withWatermark("event_time", "10 minutes") \
    .groupBy(
        window("event_time", "5 minutes"),
        "category"
    ) \
    .agg(sum("price").alias("revenue"))
```

---

### PHẦN 5: KẾT LUẬN & KHUYẾN NGHỊ

#### 5.1. Tóm tắt

Dự án hiện tại chỉ mới có **5% tiến độ**. Để hoàn thành đúng yêu cầu giảng viên trong 2.5 tháng, nhóm cần:

1. **Focus vào Spark Processing (60% effort)** - Đây là phần quan trọng nhất
2. **Setup Infrastructure đúng cách (20% effort)** - Foundation cho mọi thứ
3. **Integration & Visualization (20% effort)** - Chứng minh hệ thống hoạt động

#### 5.2. Critical Success Factors

✅ **Phải có:**
- Tất cả 6 yêu cầu Spark được implement
- Pipeline hoạt động end-to-end
- Dashboard trực quan hóa
- Kubernetes deployment
- Báo cáo kỹ thuật chi tiết

⚠️ **Nice to have:**
- Advanced ML models
- Complex graph analysis
- Perfect performance optimization

#### 5.3. Next Steps (Immediate Actions)

**Tuần này (Tuần 1):**

1. **Team Leader (Member 1):**
   - [ ] Họp nhóm kick-off (2 hours)
   - [ ] Chia sẻ document này với team
   - [ ] Setup GitHub repository
   - [ ] Create Trello board với tasks
   - [ ] Assign members chính thức
   - [ ] Setup Kafka cluster

2. **All Members:**
   - [ ] Đọc kỹ document này
   - [ ] Confirm vai trò và nhiệm vụ
   - [ ] Install: Java 17, Python 3.12, Spark 3.5.8
   - [ ] Clone Olist dataset
   - [ ] Đọc Spark documentation (Structured APIs, Streaming)
   - [ ] Setup development environment

3. **Specific:**
   - Thế: Đọc sâu về Spark SQL, Joins, Window Functions
   - Quang: Đọc sâu về Structured Streaming, Watermarking
   - Hoàng: Đọc sâu về MLlib, GraphFrames
   - Huy: Đọc về MongoDB, Grafana, Debezium

**Deliverable tuần 1:**
- [ ] GitHub repo với structure folders
- [ ] Trello board với tất cả tasks
- [ ] Infrastructure plan document
- [ ] All members có môi trường dev hoạt động

---

### PHẦN 6: APPENDIX

#### 6.1. Learning Resources

**Spark:**
- [Spark Official Documentation](https://spark.apache.org/docs/latest/)
- [Spark: The Definitive Guide (O'Reilly)](https://pages.databricks.com/rs/094-YMS-629/images/LearningSpark2.0.pdf)

**Streaming:**
- [Structured Streaming Programming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)

**MLlib:**
- [MLlib Guide](https://spark.apache.org/docs/latest/ml-guide.html)

**GraphFrames:**
- [GraphFrames User Guide](https://graphframes.github.io/graphframes/docs/_site/user-guide.html)

**Kafka:**
- [Kafka Quickstart](https://kafka.apache.org/quickstart)

**Kubernetes:**
- [Minikube Start](https://minikube.sigs.k8s.io/docs/start/)

#### 6.2. Code Templates Location

```
project/
├── templates/
│   ├── spark_batch_template.py
│   ├── spark_streaming_template.py
│   ├── ml_pipeline_template.py
│   ├── airflow_dag_template.py
│   └── k8s_deployment_template.yaml
```

#### 6.3. Grading Rubric (Estimate)

| Criteria | Weight | Notes |
|----------|--------|-------|
| Spark Advanced Operations | 30% | Window, Join, UDF, Optimization |
| Streaming Processing | 20% | Watermark, State, Exactly-once |
| Infrastructure | 15% | K8s, Kafka, NoSQL, HDFS equivalent |
| ML & Analytics | 15% | MLlib, GraphFrames, Time series |
| Visualization | 10% | Grafana dashboards |
| Documentation & Presentation | 10% | Report, slides, demo |

---

**Good luck! Chúc nhóm thành công! 🚀**

**Lưu ý cuối cùng:** Đây là bài tập lớn, không phải dự án thực tế. Focus vào việc **demonstrate technical skills** hơn là tạo ra sản phẩm hoàn hảo. Giảng viên sẽ đánh giá cao việc bạn hiểu và vận dụng đúng các kỹ thuật Big Data hơn là có hệ thống production-ready.

**Contact Team Leader nếu có thắc mắc!**

---
*Document created: April 2026*
*Version: 1.0*
*Team: Big Data Project - 5 Members*
