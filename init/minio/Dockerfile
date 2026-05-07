FROM alpine:3.19 AS base
RUN apk add --no-cache \
    iproute2 \
    curl \
    bash \
    ca-certificates

RUN curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio \
    -o /usr/local/bin/minio && \
    chmod +x /usr/local/bin/minio

RUN addgroup -S minio && adduser -S minio -G minio

RUN mkdir -p /data && chown -R minio:minio /data

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV THROTTLE_ENABLED=true \
    BANDWIDTH_LIMIT=10mbit \
    LATENCY_MS=50 \
    LATENCY_JITTER_MS=10 \
    PACKET_LOSS_PERCENT=0 \
    NETWORK_INTERFACE=eth0

ENV MINIO_ROOT_USER=minioadmin \
    MINIO_ROOT_PASSWORD=minioadmin

# Expose ports
EXPOSE 9000 9001

# Volume cho data
VOLUME ["/data"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["server", "/data", "--console-address", ":9001"]