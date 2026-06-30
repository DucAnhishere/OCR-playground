"""
shared/telemetry.py
Bootstrap module for OpenTelemetry tracing.
Call `init_telemetry(app, service_name)` once in each FastAPI service's startup
to enable distributed tracing with Jaeger.
"""
import os
import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

logger = logging.getLogger(__name__)


def init_telemetry(app, service_name: str = None) -> None:
    """
    Initialize OpenTelemetry tracing for a FastAPI service.

    Args:
        app: The FastAPI application instance to instrument.
        service_name: The service name shown in Jaeger UI. Falls back to the
                      OTEL_SERVICE_NAME environment variable, then 'unknown'.
    """
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "unknown")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("[Telemetry] Sending traces to %s as service '%s'", endpoint, service_name)
    except Exception as e:
        # If Jaeger is unreachable or the library is not installed, tracing is a no-op.
        logger.warning("[Telemetry] Could not configure OTLP exporter: %s. Tracing disabled.", e)

    trace.set_tracer_provider(provider)

    # Auto-instrument all FastAPI routes (adds HTTP-level spans automatically)
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("[Telemetry] FastAPI auto-instrumentation enabled for '%s'", service_name)
    except Exception as e:
        logger.warning("[Telemetry] FastAPI instrumentation failed: %s", e)

    # Auto-instrument httpx (only the Orchestrator uses httpx; others skip silently)
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
        logger.info("[Telemetry] httpx auto-instrumentation enabled for '%s'", service_name)
    except ImportError:
        pass  # Not installed in microservices that don't need it


def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Returns a tracer for creating custom spans.

    Usage:
        tracer = get_tracer("my_module")
        with tracer.start_as_current_span("my_operation") as span:
            span.set_attribute("key", "value")
            do_work()
    """
    return trace.get_tracer(name)
