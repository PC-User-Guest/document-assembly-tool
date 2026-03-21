# Architecture Blueprint

## System Architecture

```mermaid
graph TB
    CLI["CLI Interface"]
    GRPC["gRPC API Server"]
    KAFKA_C["Kafka Consumer"]
    OPERATOR["Kubernetes Operator"]
    
    DA["DocumentAssembler<br/>(Core Engine)"]
    AF["Advanced Features"]
    
    subgraph "Data Sources"
        WORD["Word Tables"]
        CSV["CSV"]
        JSON["JSON"]
    end
    
    subgraph "Persistence & Cache"
        SQLITE_DB["SQLite DB<br/>(Audit Trail)"]
        POSTGRES_DB["PostgreSQL DB<br/>(Replica)"]
        REDIS_CACHE["Redis Cache<br/>(Distributed)"]
    end
    
    subgraph "Observability"
        PROM["Prometheus Metrics"]
        OTEL["OpenTelemetry<br/>(OTLP Tracing)"]
    end
    
    CLI & GRPC & KAFKA_C --> DA
    DA --> AF
    AF --> WORD & CSV & JSON
    AF --> SQLITE_DB & POSTGRES_DB & REDIS_CACHE
    AF --> PROM & OTEL
    OPERATOR -.-> GRPC
```

## Core Components

### 1. DocumentAssembler
The core engine responsible for loading data, parsing templates, and performing placeholder replacement. Now instrumented with OpenTelemetry spans for performance profiling.

### 2. Cache Layer
Supports both local SQLite and distributed Redis backends. Templates are cached as serialized blobs keyed by SHA256 hashes of the file content.

### 3. API & Integration
- **gRPC API**: Low-latency interface for inter-process communication, supporting single and batch assembly.
- **Kafka Consumer**: Stream-based processing for high-throughput asynchronous workloads.
- **CLI**: Feature-rich command-line tool for manual and scripted operations.

### 4. Persistence & Failover
Audit logs are written to a primary backend (SQLite or PostgreSQL) and can be asynchronously replicated to standby sites for disaster recovery.

### 5. Kubernetes Operator
Managed via Kopf, the operator watches for `DocumentAssemblyJob` custom resources and auto-scales worker deployments based on backlog metrics from Prometheus.

## Data Flow

```mermaid
sequenceDiagram
    participant C as Client (CLI/gRPC/Kafka)
    participant DA as DocumentAssembler
    participant CA as Cache (Redis/SQLite)
    participant DS as Data Source
    participant OT as OpenTelemetry
    
    C->>DA: Assemble Request
    activate DA
    DA->>OT: Start Span
    DA->>CA: Get Cached Template
    alt Cache Miss
        CA-->>DA: Miss
        DA->>DS: Load Template from Disk
        DA->>CA: Set Cache
    else Cache Hit
        CA-->>DA: Return Template
    end
    DA->>DA: Process Placeholders
    DA->>OT: End Span
    DA-->>C: Return Result
    deactivate DA
```

## Deployment Topology (Distributed)

```mermaid
graph TB
    subgraph "Region A (Primary)"
        LB[Load Balancer]
        W1[Worker Pod 1]
        W2[Worker Pod 2]
        REDIS[(Redis Cache)]
        PG1[(PostgreSQL Primary)]
    end
    
    subgraph "Region B (Standby)"
        PG2[(PostgreSQL Replica)]
    end
    
    subgraph "Monitoring"
        JAEGER[Jaeger/Tracing]
        PROM2[Prometheus]
    end
    
    LB --> W1 & W2
    W1 & W2 --> REDIS
    W1 & W2 --> PG1
    PG1 -.->|Replication| PG2
    W1 & W2 --> JAEGER & PROM2
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Core** | Python 3.10+, python-docx |
| **API** | gRPC, Protobuf |
| **Streaming** | Apache Kafka |
| **Cache** | Redis, SQLite |
| **Persistence** | PostgreSQL, SQLite |
| **Observability** | Prometheus, OpenTelemetry |
| **Orchestration** | Kubernetes, Kopf, Helm |
