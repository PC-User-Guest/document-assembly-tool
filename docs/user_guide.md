# Document Assembly Tool - User Guide

## Overview

The Document Assembly Tool automates the merging of structured data into a Word template, replacing placeholders with formatted content. It supports multiple data sources (Word tables, CSV, JSON) and preserves formatting such as bold, italic, underline, and lists.

### Typical Use Cases

* **Contract Generation** - Populate contract templates with client data.
* **Personalized Marketing Materials** - Create proposals, letters, and brochures.
* **Report Automation** - Generate recurring reports by merging data from databases or spreadsheets.
* **Document Personalization** - Insert names, dates, and other variable content into standard documents.

---

## System Requirements

* Python 3.10 or higher
* `python-docx` (install via `pip install -r requirements.txt`)

---

## Installation

1. Clone or download the project repository:
```bash
git clone https://github.com/PC-User-Guest/document-assembly-tool.git
```
2. Open a terminal in the project root directory:
```bash
cd <repository-directory>
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Data Source Formats

### Word Table (`--data-type word`)

- The first table in the document is used.
- First row is treated as header and skipped.
- Each subsequent row must contain:

  * Column 1: Field Name
  * Column 2: Value
- The Value column can contain formatted text (bold, italic, lists).

### CSV (`--data-type csv`)

- First row must be header (field names).
- Only the first data row is used (multiple rows are ignored with a warning).
- Values are plain text; formatting is not preserved.
  
### JSON (`--data-type json`)

- File must contain a JSON object (key-value pairs) or an array of objects (first object used).
- Values can be strings, numbers, or booleans; they are converted to plain text.

---

## Template Placeholders

Placeholders in the template document follow a configurable pattern. The default pattern is `{{ field_name }}` (curly braces with optional spaces). You can change the pattern using the `--placeholder-pattern` option (must include a named group `field_name`).

Default placeholder format:

```text
{{ field_name }}
```

Custom placeholder example:

```text
<<client_name>>
```

Recommended custom regex:

```regex
<<\s*(?P<field_name>[A-Za-z_][A-Za-z0-9_-]*)\s*>>
```

This pattern matches placeholder names such as:

* `client_name`
* `project_title`
* `line-item_01`
* `account-id`

### Notes

* The pattern must include a named group called `field_name`.
* Use single quotes around the regex in shell examples to avoid escaping issues.
* Placeholder names in the template must match the data keys exactly and are case-sensitive.
* Placeholders can be inline or standalone, but best results are achieved using standalone paragraphs.

---

## Usage

```bash
python -m src.cli -d data.docx -t template.docx -o output.docx
```

---

## Command-Line Arguments

| Argument                | Description                   | Default                             |
| ----------------------- | ----------------------------- | ----------------------------------- |
| `-d, --data`            | Path to data source           | Required                            |
| `-t, --template`        | Path to template file         | Required                            |
| `-o, --output`          | Output file path              | `assembled_document.docx`           |
| `--data-type`           | `word`, `csv`, or `json`      | `word`                              |
| `--placeholder-pattern` | Regex with `field_name` group | `\{\{\s*(?P<field_name>\w+)\s*\}\}` |
| `--log-level`           | Logging level                 | `INFO`                              |

---

## Examples

### Word Data Source

```bash
python -m src.cli -d data.docx -t template.docx -o contract.docx
```

### CSV Data Source

```bash
python -m src.cli -d clients.csv -t proposal.docx -o output.docx --data-type csv
```

### JSON with Custom Placeholders

```bash
python -m src.cli \
  -d data.json \
  -t template.docx \
  -o output.docx \
  --data-type json \
  --placeholder-pattern '<<\s*(?P<field_name>[A-Za-z_][A-Za-z0-9_-]*)\s*>>'
```

### Debug Logging

```bash
python -m src.cli -d data.docx -t template.docx --log-level DEBUG
```

---

## Output

Generates a new `.docx` file with all placeholders replaced.

### Preserved Formatting

* Paragraph styles
* Bullet and numbered lists
* Inline formatting (bold, italic, underline)
* Multi-paragraph content (Word source only)

---

## Error Handling and Logging

Logs are written to stderr with timestamps.

### Common Warnings

| Warning                                           | Description            |
| ------------------------------------------------- | ---------------------- |
| `Skipping row with fewer than 2 cells`            | Invalid Word table row |
| `Field '{name}' not found in data`                | Placeholder mismatch   |
| `Style '{name}' not found`                        | Style fallback applied |
| `CSV has multiple rows; using only the first row` | CSV limitation         |
| `JSON is an array; using first object`            | Array handling         |

### Exit Codes

* Returns a non-zero exit code on critical failures (for example, missing files)

---

## Troubleshooting

### Placeholders Not Replaced

* Confirm the placeholder pattern matches the template syntax.
* Ensure field names match exactly and are case-sensitive.
* Prefer standalone paragraph placeholders.
* Use single quotes around custom regex patterns in shell commands.

### Formatting Lost (CSV/JSON)

* CSV and JSON do not support rich formatting.
* Use a Word data source for formatted content.

### Word Table Not Parsed Correctly

* Ensure:

  * The first row is a header.
  * Each row has exactly two columns.
  * Field names are strings.

### Custom Placeholder Pattern Issues

* The regex must include a named group called `field_name`.
* For placeholders like `<<client_name>>`, use:

```regex
<<\s*(?P<field_name>[A-Za-z_][A-Za-z0-9_-]*)\s*>>
```

* This recommended pattern supports letters, numbers, underscores, and hyphens in field names.
* Validate the pattern with a regex tester if needed.

---

## Customization

### Adding New Data Sources

Extend the `DocumentAssembler` class:

```python
_load_data_from_<source>()
```

Then update the dispatcher in `load_data`.

### Supporting Inline Placeholders

Requires modifying the `insert_data` method to:

* Split runs within paragraphs
* Preserve surrounding text

---

## Enterprise Use Cases

* **Legal and Compliance** - Contracts, NDAs, policies
* **Sales and Marketing** - Proposals, quotes, brochures
* **Human Resources** - Offer letters, reviews
* **Finance** - Reports and summaries
* **Education** - Certificates, transcripts

---

## Version History

| Version | Date       | Description                                                       |
| ------- | ---------- | ----------------------------------------------------------------- |
| 2.0.1   | 2025-03-19 | README fixes for custom placeholder regex and shell-safe examples |
| 2.0.0   | 2025-03-19 | Multi-source support and customizable placeholders                |
| 1.0.0   | 2025-03-19 | Initial release                                                   |

---

## Redis Cache Setup

The Document Assembly Tool supports a Redis-backed cache for parsed template documents, which is ideal for distributed deployments.

### Configuration

You can configure the Redis cache using command-line arguments or environment variables:

| Argument | Environment Variable | Default |
|----------|----------------------|---------|
| `--cache-backend` | - | `sqlite` |
| `--redis-host` | `REDIS_HOST` | `localhost` |
| `--redis-port` | `REDIS_PORT` | `6379` |
| `--redis-password` | `REDIS_PASSWORD` | - |
| `--redis-db` | `REDIS_DB` | `0` |

### Example Usage

To use Redis as the cache backend:

```bash
python -m src.cli -d data.docx -t template.docx --cache-backend redis --redis-host 10.0.0.5
```

### Performance Considerations

* **Template Hashing**: Templates are keyed by a SHA256 hash of their content. If a template changes, the cache will be automatically updated.
* **Network Latency**: While Redis is fast, consider the network latency between your application and the Redis server.
* **Memory Usage**: Parsed template documents are stored as serialized blobs. Ensure your Redis instance has enough memory to accommodate your template library.

---

## gRPC API Reference

The Document Assembly Tool provides a high-performance gRPC API as an alternative to the CLI.

### Service Definition

The service is defined in `src/proto/assembler.proto` and includes the following RPCs:

* `AssembleDocument`: Merge data into a single template.
* `BatchAssemble`: Process multiple assembly requests concurrently.
* `HealthCheck`: Get the server status.
* `GetMetrics`: Retrieve performance metrics.

### Starting the Server

To start the gRPC server:

```bash
python -m src.cli --grpc-port 50051
```

### Usage Example (Python)

See `examples/grpc_client.py` for a complete client example.

```python
import grpc
from src.proto import assembler_pb2, assembler_pb2_grpc

with grpc.insecure_channel('localhost:50051') as channel:
    stub = assembler_pb2_grpc.DocumentAssemblerStub(channel)
    request = assembler_pb2.AssembleRequest(
        data_source="data.docx",
        template_path="template.docx",
        output_path="output.docx",
        data_type="word"
    )
    response = stub.AssembleDocument(request)
    print(f"Success: {response.success}")
```

---

## Kafka Pipeline

The Document Assembly Tool can consume assembly jobs from an Apache Kafka topic for high-throughput stream processing.

### Configuration

Use the following command-line arguments to enable Kafka integration:

| Argument | Description | Default |
|----------|-------------|---------|
| `--kafka-bootstrap-servers` | Comma-separated list of Kafka brokers | Required to enable Kafka |
| `--input-topic` | Topic to consume jobs from | `assembly-jobs` |
| `--output-topic` | Topic to produce results to | `assembly-results` |
| `--dlq-topic` | Dead-letter topic for failed jobs | `assembly-dlq` |
| `--consumer-group` | Kafka consumer group ID | `assembler-group` |

### Message Schema

Jobs must be published as JSON messages to the input topic:

```json
{
  "data_source": "s3://bucket/data.docx",
  "template_path": "s3://bucket/template.docx",
  "output_path": "s3://bucket/output.docx",
  "data_type": "word"
}
```

### Running the Consumer

```bash
python -m src.cli --kafka-bootstrap-servers localhost:9092 --input-topic document-jobs
```

The consumer will process each job and produce a success message to the output topic or an error message to the DLQ topic.

---

## Kubernetes Operator

The Document Assembly Operator auto-scales worker pools based on queue length and manages document assembly jobs.

### Custom Resource Definition (CRD)

Define a `DocumentAssemblyJob` with your template and data sources:

```yaml
apiVersion: assembler.io/v1
kind: DocumentAssemblyJob
metadata:
  name: job-01
spec:
  templatePath: s3://bucket/template.docx
  dataSource: s3://bucket/data.docx
  outputLocation: s3://bucket/output.docx
  dataType: word
```

### Installation via Helm

Install the operator and worker components:

```bash
helm install operator ./deploy/helm/operator
helm install worker ./deploy/helm/worker
```

### Auto-Scaling

The operator monitors queue metrics from Prometheus and adjusts the number of worker replicas accordingly. This ensures high availability during peak periods and cost optimization during idle time.

### Local Testing

To test the operator locally with Kind:

1. Create a Kind cluster: `kind create cluster`
2. Apply the CRD: `kubectl apply -f deploy/crd.yaml`
3. Run the operator: `kopf run src/operator/operator.py`
4. Submit a job: `kubectl apply -f examples/job.yaml`

---

## Multi-Region Failover

To ensure high availability and disaster recovery, the Document Assembly Tool can replicate its audit logs to multiple standby sites.

### Backend Support

* **SQLite**: Local file-based storage.
* **PostgreSQL**: Distributed SQL database for enterprise deployments.

### Replication Configuration

| Argument | Description | Default |
|----------|-------------|---------|
| `--primary-db-url` | Primary database URL (SQLite path or Postgres DSN) | Required for replication |
| `--replica-db-urls` | List of replica database URLs | - |
| `--replication-mode` | `sync` or `async` replication | `async` |

### Manual Failover

If the primary database becomes unavailable, you can manually promote a replica:

```bash
python -m src.cli audit failover --new-primary 0
```

### Example: PostgreSQL Replication

```bash
python -m src.cli -d data.docx -t template.docx \
  --primary-db-url "postgresql://user:pass@primary-db:5432/audit" \
  --replica-db-urls "postgresql://user:pass@standby-db:5432/audit" \
  --replication-mode async
```

---

## OpenTelemetry Tracing

Add full distributed tracing and context propagation using OpenTelemetry.

### Configuration

Enable tracing using the following arguments:

| Argument | Description | Default |
|----------|-------------|---------|
| `--trace-enabled` | Enable tracing | `false` |
| `--trace-endpoint` | OTLP collector endpoint | `http://localhost:4317` |
| `--trace-sampling-ratio` | Sampling ratio (0.0 to 1.0) | `1.0` |

### Running with Tracing

To enable tracing and export to a Jaeger collector:

```bash
python -m src.cli -d data.docx -t template.docx --trace-enabled --trace-endpoint http://jaeger-collector:4317
```

You can then view the traces in the Jaeger UI to analyze performance bottlenecks and service dependencies.
