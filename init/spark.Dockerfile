# =====================================================================
# Spark image custom: apache/spark 3.5.1 + pymongo (job gold ghi Mongo
# qua MongoConnector chạy ở driver). Dùng cho cả master & worker.
# =====================================================================
FROM apache/spark:3.5.1

USER root
RUN pip3 install --no-cache-dir "pymongo>=4,<5" \
    && mkdir -p /home/spark/.ivy2/cache /home/spark/.ivy2/jars \
    && chown -R spark:spark /home/spark/.ivy2
USER spark
