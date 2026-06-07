FROM quay.io/debezium/connect:2.4

USER root

# Cài đặt công cụ unzip (Image của Debezium dùng microdnf)
RUN microdnf -y install unzip

# Tải và giải nén S3 Sink Connector (bản 10.5.7)
RUN curl -L -o s3.zip https://d2p6pa21dvn84.cloudfront.net/api/plugins/confluentinc/kafka-connect-s3/versions/10.5.7/confluentinc-kafka-connect-s3-10.5.7.zip && \
    unzip s3.zip -d /kafka/connect/ && \
    rm s3.zip

# Tải và giải nén Avro Converter (bản 7.5.0)
RUN curl -L -o avro.zip https://d2p6pa21dvn84.cloudfront.net/api/plugins/confluentinc/kafka-connect-avro-converter/versions/7.5.0/confluentinc-kafka-connect-avro-converter-7.5.0.zip && \
    unzip avro.zip -d /kafka/connect/ && \
    rm avro.zip

USER 1001