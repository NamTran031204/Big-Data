# =====================================================================
# Airflow image custom: có sẵn JDK + Spark 3.5.1 + provider apache-spark
# để SparkSubmitOperator submit job tới spark://spark-master:7077.
# =====================================================================
FROM apache/airflow:2.11.2

USER root

# Java cho spark-submit + vài tiện ích
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless curl procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# JAVA_HOME độc lập kiến trúc (amd64/arm64)
RUN ln -s "$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")" /opt/java-home
ENV JAVA_HOME=/opt/java-home

# Spark 3.5.1 (khớp cluster apache/spark:3.5.1) — dùng file local thay vì curl
ENV SPARK_VERSION=3.5.1
COPY downloads/spark-${SPARK_VERSION}-bin-hadoop3.tgz /tmp/spark.tgz
RUN tar -xzf /tmp/spark.tgz -C /opt \
    && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop3" /opt/spark \
    && rm /tmp/spark.tgz
ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:${PATH}"

USER airflow

# Provider Spark (SparkSubmitOperator) + PyMongo (job gold ghi Mongo).
# Không pin để pip tự khớp ràng buộc với apache-airflow 2.11.2 đã cài.
RUN pip install --no-cache-dir \
        "apache-airflow-providers-apache-spark" \
        "pymongo>=4,<5"
