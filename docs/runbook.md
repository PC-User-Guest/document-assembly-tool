# Troubleshooting Runbook

This guide contains common issues, their causes, and solutions for the Document Assembly Tool.

## Redis Cache Issues

### 1. Connection Refused
- **Cause**: Redis server is down or the provided host/port is incorrect.
- **Solution**: Check if Redis is running and verify the `--redis-host` and `--redis-port` arguments.

### 2. Cache Memory Limit Exceeded
- **Cause**: Redis has reached its memory limit and can no longer store new templates.
- **Solution**: Increase the Redis memory limit or configure an eviction policy (e.g., `allkeys-lru`).

## gRPC API Issues

### 1. UNAVAILABLE (503)
- **Cause**: The gRPC server is not running or the client is using the wrong port.
- **Solution**: Ensure the server is started with `--grpc-port` and check for port conflicts.

### 2. UNKNOWN: Pickling Errors
- **Cause**: Top-level function requirement for `ProcessPoolExecutor`.
- **Solution**: Ensure that all functions passed to the worker pool are defined at the module level.

## Kafka Consumer Issues

### 1. Consumer Lag
- **Cause**: Processing rate is lower than the message production rate.
- **Solution**: Increase the number of consumer instances (horizontal scaling) or the number of worker threads.

### 2. Dead-Letter Topic Messages
- **Cause**: Jobs with invalid schemas or missing files are being sent to the input topic.
- **Solution**: Inspect the DLQ messages for error details and validate the input job schema.

## Kubernetes Operator Issues

### 1. Operator Not Scaling
- **Cause**: The operator doesn't have the necessary RBAC permissions or can't connect to the Kubernetes API.
- **Solution**: Check the operator logs with `kubectl logs` and verify the service account permissions.

### 2. Custom Resource Not Reconciled
- **Cause**: Kopf is not correctly watching the `DocumentAssemblyJob` resource.
- **Solution**: Restart the operator pod and verify the CRD definition is applied.

## Multi-Region Failover Issues

### 1. Replication Lag
- **Cause**: Network latency or slow replica database performance.
- **Solution**: Switch to `async` replication mode and monitor the replica database performance.

### 2. Failover Not Triggering
- **Cause**: Manual failover command was not executed or failed.
- **Solution**: Run the manual failover command and check the logs for errors:
  ```bash
  python -m src.cli audit failover --new-primary 0
  ```

## OpenTelemetry Tracing Issues

### 1. Missing Traces
- **Cause**: The OTLP collector is unreachable or tracing is disabled.
- **Solution**: Check the `--trace-enabled` and `--trace-endpoint` flags. Verify the collector logs.

### 2. High Tracing Overhead
- **Cause**: Sampling ratio is set to 1.0 (100%), causing high CPU/memory usage.
- **Solution**: Reduce the sampling ratio using `--trace-sampling-ratio 0.1`.
