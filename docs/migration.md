# Migration Guide

This guide describes how to migrate to the new distributed features of the Document Assembly Tool.

## 1. Switching to Redis Cache

To replace the local SQLite cache with a distributed Redis cache:

1. Deploy a Redis instance (e.g., `docker run -p 6379:6379 redis`).
2. Update your command to use `--cache-backend redis`:
   ```bash
   python -m src.cli -d data.docx -t template.docx --cache-backend redis --redis-host localhost
   ```

## 2. Deploying the gRPC Server

To switch from CLI to gRPC for inter-process communication:

1. Start the gRPC server:
   ```bash
   python -m src.cli --grpc-port 50051
   ```
2. Update your clients to use the gRPC stub defined in `src/proto/assembler.proto`.

## 3. Integrating with Kafka

To enable stream-based processing:

1. Deploy a Kafka cluster.
2. Run the assembler as a Kafka consumer:
   ```bash
   python -m src.cli --kafka-bootstrap-servers localhost:9092 --input-topic document-jobs
   ```

## 4. Multi-Region Failover

To migrate to a distributed audit log:

1. Deploy a PostgreSQL database in multiple regions.
2. Configure the primary and replica URLs:
   ```bash
   python -m src.cli -d data.docx -t template.docx \
     --primary-db-url "postgresql://user:pass@region1-db:5432/audit" \
     --replica-db-urls "postgresql://user:pass@region2-db:5432/audit"
   ```

## 5. Enabling Tracing

To monitor your deployment with OpenTelemetry:

1. Deploy an OTLP collector (e.g., Jaeger).
2. Start the tool with `--trace-enabled`:
   ```bash
   python -m src.cli -d data.docx -t template.docx --trace-enabled --trace-endpoint http://jaeger:4317
   ```
