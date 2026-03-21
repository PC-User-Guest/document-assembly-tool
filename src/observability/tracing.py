import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

logger = logging.getLogger(__name__)

def setup_tracing(service_name="document-assembler", endpoint="http://localhost:4317", sampling_ratio=1.0):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource, sampler=TraceIdRatioBased(sampling_ratio))

    try:
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)
    except Exception as e:
        logger.warning(f"Failed to setup OTLP exporter: {e}")

    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)

# Global tracer
tracer = trace.get_tracer("document-assembler")

def instrument_document_assembler():
    # In a real system, we'd use auto-instrumentation or manual spans
    pass
