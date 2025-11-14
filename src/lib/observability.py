"""OpenTelemetry SDK setup for distributed tracing and metrics."""

from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import start_http_server

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)


def setup_tracing() -> None:
    """
    Configure OpenTelemetry distributed tracing with Jaeger.

    Sets up:
    - TracerProvider with service name
    - Jaeger exporter for trace data
    - BatchSpanProcessor for efficient batching
    """
    if not settings.enable_tracing:
        logger.info("Tracing is disabled")
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": "ragflow",
                "service.version": "0.1.0",
                "deployment.environment": settings.environment,
            }
        )

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.jaeger_agent_host,
            agent_port=settings.jaeger_agent_port,
        )

        # Add span processor for batching
        span_processor = BatchSpanProcessor(jaeger_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        logger.info(
            f"Tracing configured with Jaeger at "
            f"{settings.jaeger_agent_host}:{settings.jaeger_agent_port}"
        )

    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}")
        # Don't fail application if tracing setup fails
        logger.warning("Application will continue without tracing")


def setup_metrics() -> None:
    """
    Configure OpenTelemetry metrics with Prometheus.

    Sets up:
    - MeterProvider with service name
    - PrometheusMetricReader for Prometheus scraping
    - HTTP server for metrics endpoint
    """
    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": "ragflow",
                "service.version": "0.1.0",
                "deployment.environment": settings.environment,
            }
        )

        # Create Prometheus metrics reader
        prometheus_reader = PrometheusMetricReader()

        # Create meter provider
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader],
        )

        # Set global meter provider
        metrics.set_meter_provider(meter_provider)

        # Start Prometheus HTTP server for scraping
        if settings.environment == "development":
            # In development, start HTTP server directly
            start_http_server(port=settings.prometheus_port, addr="0.0.0.0")
            logger.info(f"Prometheus metrics available at http://0.0.0.0:{settings.prometheus_port}/metrics")
        else:
            # In production, metrics are scraped from the main API port
            logger.info("Prometheus metrics configured (available via /metrics endpoint)")

    except Exception as e:
        logger.error(f"Failed to setup metrics: {e}")
        # Don't fail application if metrics setup fails
        logger.warning("Application will continue without metrics")


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for the given name.

    Args:
        name: Name of the tracer (typically module name)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """
    Get a meter instance for the given name.

    Args:
        name: Name of the meter (typically module name)

    Returns:
        Meter instance
    """
    return metrics.get_meter(name)


class TracingContext:
    """Context manager for creating tracing spans."""

    def __init__(
        self,
        tracer: trace.Tracer,
        span_name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize tracing context.

        Args:
            tracer: Tracer instance
            span_name: Name of the span
            attributes: Optional span attributes
        """
        self.tracer = tracer
        self.span_name = span_name
        self.attributes = attributes or {}
        self.span: trace.Span | None = None

    def __enter__(self) -> trace.Span:
        """Start span."""
        self.span = self.tracer.start_span(self.span_name)

        # Add attributes
        if self.attributes:
            for key, value in self.attributes.items():
                self.span.set_attribute(key, value)

        return self.span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """End span."""
        if self.span:
            # Record exception if occurred
            if exc_type is not None:
                self.span.record_exception(exc_val)
                self.span.set_status(
                    trace.Status(
                        status_code=trace.StatusCode.ERROR,
                        description=str(exc_val),
                    )
                )
            else:
                self.span.set_status(trace.Status(status_code=trace.StatusCode.OK))

            self.span.end()


def create_span(
    tracer: trace.Tracer,
    span_name: str,
    attributes: dict[str, Any] | None = None,
) -> TracingContext:
    """
    Create a tracing span context manager.

    Args:
        tracer: Tracer instance
        span_name: Name of the span
        attributes: Optional span attributes

    Returns:
        TracingContext instance

    Example:
        tracer = get_tracer(__name__)
        with create_span(tracer, "process_query", {"query_id": "123"}):
            # Your code here
            pass
    """
    return TracingContext(tracer, span_name, attributes)


# Metric instruments for common operations
_query_counter: metrics.Counter | None = None
_query_latency: metrics.Histogram | None = None
_cache_hit_counter: metrics.Counter | None = None
_embedding_counter: metrics.Counter | None = None


def setup_common_metrics() -> None:
    """Setup common metric instruments used across the application."""
    global _query_counter, _query_latency, _cache_hit_counter, _embedding_counter

    meter = get_meter("ragflow")

    # Query metrics
    _query_counter = meter.create_counter(
        name="ragflow.queries.total",
        description="Total number of queries processed",
        unit="1",
    )

    _query_latency = meter.create_histogram(
        name="ragflow.query.latency",
        description="Query processing latency",
        unit="ms",
    )

    # Cache metrics
    _cache_hit_counter = meter.create_counter(
        name="ragflow.cache.hits",
        description="Cache hit/miss counter",
        unit="1",
    )

    # Embedding metrics
    _embedding_counter = meter.create_counter(
        name="ragflow.embeddings.generated",
        description="Total number of embeddings generated",
        unit="1",
    )

    logger.info("Common metrics instruments created")


def record_query_metric(latency_ms: float, status: str, collection: str) -> None:
    """Record query processing metrics."""
    if _query_counter:
        _query_counter.add(1, {"status": status, "collection": collection})

    if _query_latency:
        _query_latency.record(latency_ms, {"status": status, "collection": collection})


def record_cache_metric(hit: bool) -> None:
    """Record cache hit/miss metrics."""
    if _cache_hit_counter:
        _cache_hit_counter.add(1, {"result": "hit" if hit else "miss"})


def record_embedding_metric(count: int, model: str) -> None:
    """Record embedding generation metrics."""
    if _embedding_counter:
        _embedding_counter.add(count, {"model": model})


def initialize_observability() -> None:
    """
    Initialize complete observability stack.

    Should be called once at application startup.
    """
    logger.info("Initializing observability...")

    # Setup tracing
    setup_tracing()

    # Setup metrics
    setup_metrics()

    # Setup common metric instruments
    setup_common_metrics()

    logger.info("Observability initialized successfully")
