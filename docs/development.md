# Development Guide

This guide describes how to work with the Document Assembly Tool and its new modules.

## 1. Development Environment Setup

Clone the repository and install all dependencies:

```bash
pip install -r requirements.txt
```

## 2. Testing

Run all unit and integration tests with pytest:

```bash
python -m pytest tests/
```

To test specific modules:

```bash
python -m pytest tests/test_cache.py
```

To run coverage:

```bash
python -m pytest --cov=src tests/
```

## 3. Local Development with gRPC

After modifying the service definition in `src/proto/assembler.proto`, regenerate the Python code:

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. src/proto/assembler.proto
```

Then start the server for testing:

```bash
python -m src.cli --grpc-port 50051
```

## 4. Local Development with Kafka

You can run a local Kafka instance with Docker:

```bash
docker-compose -f deploy/kafka-docker-compose.yaml up
```

Then start the consumer:

```bash
python -m src.cli --kafka-bootstrap-servers localhost:9092
```

## 5. Local Kubernetes Testing with Kind

1. Create a Kind cluster:
   ```bash
   kind create cluster
   ```

2. Apply the CRD:
   ```bash
   kubectl apply -f deploy/crd.yaml
   ```

3. Run the operator:
   ```bash
   kopf run src/operator/operator.py
   ```

## 6. Code Quality

The project uses `flake8` for code quality. Ensure your changes pass before submitting:

```bash
flake8 src tests
```

## Open-Source Dependencies

All new dependencies added in version 2.1.0 are open-source and compatible with the MIT license:

* `redis`, `hiredis`: MIT
* `grpcio`, `grpcio-tools`: Apache 2.0
* `kafka-python`: Apache 2.0
* `kopf`: Apache 2.0
* `kubernetes`: Apache 2.0
* `psycopg2-binary`: LGPL with exceptions (standard for Postgres in Python)
* `opentelemetry-*`: Apache 2.0
