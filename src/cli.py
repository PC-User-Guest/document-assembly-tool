import argparse
import sys
import os
import logging
from .document_assembler import DocumentAssembler
from .cache.sqlite_cache import SQLiteCache

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Assemble a document by merging data from a structured source into a template."
    )
    parser.add_argument(
        '-d', '--data',
        help='Path to the data source (Word, CSV, JSON)'
    )
    parser.add_argument(
        '-t', '--template',
        help='Path to the template Word document'
    )
    parser.add_argument(
        '-o', '--output',
        default='assembled_document.docx',
        help='Path for the output document (default: assembled_document.docx)'
    )
    parser.add_argument(
        '--data-type',
        default='word',
        choices=['word', 'csv', 'json'],
        help='Type of data source (default: word)'
    )
    parser.add_argument(
        '--placeholder-pattern',
        help='Regex pattern with named group field_name to match placeholders'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set logging verbosity (default: INFO)'
    )

    # Cache configuration
    parser.add_argument(
        '--cache-backend',
        default='sqlite',
        choices=['sqlite', 'redis'],
        help='Cache backend for template documents (default: sqlite)'
    )
    parser.add_argument('--redis-host', default=os.getenv('REDIS_HOST', 'localhost'))
    parser.add_argument('--redis-port', type=int, default=int(os.getenv('REDIS_PORT', 6379)))
    parser.add_argument('--redis-password', default=os.getenv('REDIS_PASSWORD'))
    parser.add_argument('--redis-db', type=int, default=int(os.getenv('REDIS_DB', 0)))

    # gRPC configuration
    parser.add_argument('--grpc-port', type=int, help='Start gRPC server on this port')
    parser.add_argument('--grpc-address', default='[::]', help='Address for gRPC server')

    # Kafka configuration
    parser.add_argument('--kafka-bootstrap-servers', help='Comma-separated Kafka bootstrap servers')
    parser.add_argument('--input-topic', default='assembly-jobs')
    parser.add_argument('--output-topic', default='assembly-results')
    parser.add_argument('--dlq-topic', default='assembly-dlq')
    parser.add_argument('--consumer-group', default='assembler-group')

    # Failover configuration
    parser.add_argument('--primary-db-url', help='Primary audit database URL')
    parser.add_argument('--replica-db-urls', nargs='+', help='List of replica audit database URLs')
    parser.add_argument('--replication-mode', default='async', choices=['sync', 'async'])

    # Tracing configuration
    parser.add_argument('--trace-enabled', action='store_true', help='Enable OpenTelemetry tracing')
    parser.add_argument('--trace-endpoint', default='http://localhost:4317', help='OTLP collector endpoint')
    parser.add_argument('--trace-sampling-ratio', type=float, default=1.0, help='Tracing sampling ratio (0.0 to 1.0)')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command')
    audit_parser = subparsers.add_parser('audit', help='Audit trail management')
    audit_parser.add_argument('subcommand', choices=['failover'])
    audit_parser.add_argument('--new-primary', type=int, default=0)

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.trace_enabled:
        from .observability.tracing import setup_tracing
        setup_tracing(endpoint=args.trace_endpoint, sampling_ratio=args.trace_sampling_ratio)

    if args.command == 'audit' and args.subcommand == 'failover':
        print(f"Triggering manual failover to replica index {args.new_primary}...")
        return

    if args.grpc_port:
        from .grpc_server import serve
        serve(port=args.grpc_port)
        return

    if args.kafka_bootstrap_servers:
        from .kafka_consumer import start_kafka_consumer
        start_kafka_consumer(
            args.kafka_bootstrap_servers,
            args.input_topic,
            args.output_topic,
            args.dlq_topic,
            args.consumer_group
        )
        return

    # Normal CLI execution
    if not args.data or not args.template:
        parser.error("-d/--data and -t/--template are required when not running as a server.")

    cache = None
    if args.cache_backend == 'redis':
        try:
            from .cache.redis_cache import RedisCache
            cache = RedisCache(
                host=args.redis_host,
                port=args.redis_port,
                password=args.redis_password,
                db=args.redis_db
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}. Falling back to SQLite.")
            cache = SQLiteCache()
    else:
        cache = SQLiteCache()

    assembler = DocumentAssembler(
        data_source=args.data,
        template_path=args.template,
        output_path=args.output,
        data_type=args.data_type,
        placeholder_pattern=args.placeholder_pattern,
        log_level=args.log_level,
        cache=cache
    )
    assembler.run()

if __name__ == "__main__":
    main()
