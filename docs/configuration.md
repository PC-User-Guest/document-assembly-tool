# Configuration Reference

This guide provides a comprehensive list of all command-line arguments and environment variables for the Document Assembly Tool.

## Global Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-d, --data` | Path to the data source (Word, CSV, JSON) | Required |
| `-t, --template` | Path to the template Word document | Required |
| `-o, --output` | Path for the output document | `assembled_document.docx` |
| `--data-type` | Type of data source (`word`, `csv`, `json`) | `word` |
| `--placeholder-pattern` | Regex with `field_name` group | `\{\{\s*(?P<field_name>\w+)\s*\}\}` |
| `--log-level` | Logging verbosity (`DEBUG`, `INFO`, etc.) | `INFO` |

## Cache Configuration

| Argument | Environment Variable | Default |
|----------|----------------------|---------|
| `--cache-backend` | - | `sqlite` |
| `--redis-host` | `REDIS_HOST` | `localhost` |
| `--redis-port` | `REDIS_PORT` | `6379` |
| `--redis-password` | `REDIS_PASSWORD` | - |
| `--redis-db` | `REDIS_DB` | `0` |

## gRPC Server Configuration

| Argument | Description | Default |
|----------|-------------|---------|
| `--grpc-port` | Start gRPC server on this port | - |
| `--grpc-address` | Address for gRPC server | `[::]` |

## Kafka Configuration

| Argument | Description | Default |
|----------|-------------|---------|
| `--kafka-bootstrap-servers` | Comma-separated Kafka brokers | - |
| `--input-topic` | Topic to consume jobs from | `assembly-jobs` |
| `--output-topic` | Topic to produce results to | `assembly-results` |
| `--dlq-topic` | Dead-letter topic for failed jobs | `assembly-dlq` |
| `--consumer-group` | Kafka consumer group ID | `assembler-group` |

## Multi-Region Failover Configuration

| Argument | Description | Default |
|----------|-------------|---------|
| `--primary-db-url` | Primary database URL | - |
| `--replica-db-urls` | List of replica database URLs | - |
| `--replication-mode` | `sync` or `async` replication | `async` |

## OpenTelemetry Tracing Configuration

| Argument | Description | Default |
|----------|-------------|---------|
| `--trace-enabled` | Enable tracing | `false` |
| `--trace-endpoint` | OTLP collector endpoint | `http://localhost:4317` |
| `--trace-sampling-ratio` | Sampling ratio (0.0 to 1.0) | `1.0` |
