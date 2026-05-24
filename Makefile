# Configuration for running commands

# hướng dẫn chạy tại terminal:
# tại thư mục dự án `/BigData`, chạy các lệnh bắt đầu bằng `make`
# ví dự muốn cài đặt các env, chạy lệnh `make install-deps`

.PHONY: help install-deps run-ingest-bronze docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install-deps          - Install Python dependencies"
	@echo "  make run-ingest-bronze     - Run Spark batch ingest_bronze job"
	@echo "  make docker-up             - Start Docker containers"
	@echo "  make docker-down           - Stop Docker containers"

# cai dat env de chay code spark local
install-deps:
	pip install -r spark-streaming/requirements.txt

# local run spark batch
batch-bronze:
	spark-submit \
		--packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
		spark-batch/ingest_bronze.py


# docker
docker-up:
	cd init && docker compose up -d

docker-down:
	cd init && docker compose down