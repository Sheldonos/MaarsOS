"""
OpenTelemetry integration for distributed tracing and metrics.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

from .config import settings
from .models import TraceData, SpanData

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages OpenTelemetry tracing and metrics."""
    
    def __init__(self):
        """Initialize telemetry manager."""
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.meter: Optional[metrics.Meter] = None
        
        # Metrics
        self.request_counter: Optional[metrics.Counter] = None
        self.request_duration: Optional[metrics.Histogram] = None
        self.error_counter: Optional[metrics.Counter] = None
        self.policy_evaluation_duration: Optional[metrics.Histogram] = None
        self.anomaly_detection_duration: Optional[metrics.Histogram] = None
        self.violation_counter: Optional[metrics.Counter] = None
        self.anomaly_counter: Optional[metrics.Counter] = None
    
    def initialize(self):
        """Initialize OpenTelemetry providers and instruments."""
        if not settings.otel_enabled:
            logger.info("OpenTelemetry is disabled")
            return
        
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: settings.otel_service_name,
                ResourceAttributes.SERVICE_VERSION: settings.service_version,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.environment,
            })
            
            # Initialize tracing
            self._initialize_tracing(resource)
            
            # Initialize metrics
            self._initialize_metrics(resource)
            
            logger.info("OpenTelemetry initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
    
    def _initialize_tracing(self, resource: Resource):
        """Initialize distributed tracing."""
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Create OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_endpoint,
            insecure=True  # Use TLS in production
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
        
        logger.info("Tracing initialized")
    
    def _initialize_metrics(self, resource: Resource):
        """Initialize metrics collection."""
        # Create OTLP metric exporter
        otlp_exporter = OTLPMetricExporter(
            endpoint=settings.otel_exporter_endpoint,
            insecure=True  # Use TLS in production
        )
        
        # Create metric reader
        metric_reader = PeriodicExportingMetricReader(
            otlp_exporter,
            export_interval_millis=60000  # Export every 60 seconds
        )
        
        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(__name__)
        
        # Create metrics
        self._create_metrics()
        
        logger.info("Metrics initialized")
    
    def _create_metrics(self):
        """Create metric instruments."""
        if not self.meter:
            return
        
        # Request metrics
        self.request_counter = self.meter.create_counter(
            name="observability.requests.total",
            description="Total number of requests",
            unit="1"
        )
        
        self.request_duration = self.meter.create_histogram(
            name="observability.request.duration",
            description="Request duration in milliseconds",
            unit="ms"
        )
        
        self.error_counter = self.meter.create_counter(
            name="observability.errors.total",
            description="Total number of errors",
            unit="1"
        )
        
        # Policy evaluation metrics
        self.policy_evaluation_duration = self.meter.create_histogram(
            name="observability.policy.evaluation.duration",
            description="Policy evaluation duration in milliseconds",
            unit="ms"
        )
        
        self.violation_counter = self.meter.create_counter(
            name="observability.policy.violations.total",
            description="Total number of policy violations",
            unit="1"
        )
        
        # Anomaly detection metrics
        self.anomaly_detection_duration = self.meter.create_histogram(
            name="observability.anomaly.detection.duration",
            description="Anomaly detection duration in milliseconds",
            unit="ms"
        )
        
        self.anomaly_counter = self.meter.create_counter(
            name="observability.anomalies.total",
            description="Total number of anomalies detected",
            unit="1"
        )
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracing an operation.
        
        Args:
            operation_name: Name of the operation
            attributes: Additional attributes to add to the span
            
        Yields:
            Span object
        """
        if not self.tracer:
            yield None
            return
        
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise
    
    def record_request(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """
        Record a request metric.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            duration_ms: Request duration in milliseconds
        """
        if not self.request_counter or not self.request_duration:
            return
        
        attributes = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }
        
        self.request_counter.add(1, attributes)
        self.request_duration.record(duration_ms, attributes)
        
        if status_code >= 400 and self.error_counter:
            self.error_counter.add(1, attributes)
    
    def record_policy_evaluation(self, tenant_id: str, duration_ms: float, violations: int):
        """
        Record policy evaluation metrics.
        
        Args:
            tenant_id: Tenant identifier
            duration_ms: Evaluation duration in milliseconds
            violations: Number of violations found
        """
        if not self.policy_evaluation_duration:
            return
        
        attributes = {"tenant_id": tenant_id}
        
        self.policy_evaluation_duration.record(duration_ms, attributes)
        
        if violations > 0 and self.violation_counter:
            self.violation_counter.add(violations, attributes)
    
    def record_anomaly_detection(self, tenant_id: str, duration_ms: float, is_anomaly: bool):
        """
        Record anomaly detection metrics.
        
        Args:
            tenant_id: Tenant identifier
            duration_ms: Detection duration in milliseconds
            is_anomaly: Whether an anomaly was detected
        """
        if not self.anomaly_detection_duration:
            return
        
        attributes = {"tenant_id": tenant_id}
        
        self.anomaly_detection_duration.record(duration_ms, attributes)
        
        if is_anomaly and self.anomaly_counter:
            self.anomaly_counter.add(1, attributes)
    
    async def process_trace(self, trace_data: TraceData) -> Dict[str, Any]:
        """
        Process and analyze trace data.
        
        Args:
            trace_data: Trace data to process
            
        Returns:
            Analysis results
        """
        try:
            # Calculate trace statistics
            total_spans = len(trace_data.spans)
            error_spans = sum(1 for span in trace_data.spans if span.status == "error")
            
            # Find critical path (longest span chain)
            critical_path_duration = self._calculate_critical_path(trace_data.spans)
            
            # Identify slow spans
            slow_spans = [
                span for span in trace_data.spans
                if span.duration_ms > 1000  # Spans over 1 second
            ]
            
            # Calculate span statistics
            span_durations = [span.duration_ms for span in trace_data.spans]
            avg_span_duration = sum(span_durations) / len(span_durations) if span_durations else 0
            
            return {
                "trace_id": trace_data.trace_id,
                "service_name": trace_data.service_name,
                "total_duration_ms": trace_data.duration_ms,
                "total_spans": total_spans,
                "error_spans": error_spans,
                "error_rate": error_spans / total_spans if total_spans > 0 else 0,
                "critical_path_duration_ms": critical_path_duration,
                "avg_span_duration_ms": avg_span_duration,
                "slow_spans": len(slow_spans),
                "slow_span_details": [
                    {
                        "operation": span.operation_name,
                        "duration_ms": span.duration_ms
                    }
                    for span in slow_spans[:5]  # Top 5 slow spans
                ]
            }
            
        except Exception as e:
            logger.error(f"Error processing trace: {e}")
            return {
                "error": str(e),
                "trace_id": trace_data.trace_id
            }
    
    def _calculate_critical_path(self, spans: List[SpanData]) -> float:
        """
        Calculate the critical path duration (longest chain of dependent spans).
        
        Args:
            spans: List of spans
            
        Returns:
            Critical path duration in milliseconds
        """
        if not spans:
            return 0.0
        
        # Build span hierarchy
        span_map = {span.span_id: span for span in spans}
        children = {}
        
        for span in spans:
            if span.parent_span_id:
                if span.parent_span_id not in children:
                    children[span.parent_span_id] = []
                children[span.parent_span_id].append(span.span_id)
        
        # Find root spans (no parent)
        root_spans = [span for span in spans if not span.parent_span_id]
        
        if not root_spans:
            return max(span.duration_ms for span in spans)
        
        # Calculate longest path from each root
        def calculate_path_duration(span_id: str) -> float:
            span = span_map.get(span_id)
            if not span:
                return 0.0
            
            child_ids = children.get(span_id, [])
            if not child_ids:
                return span.duration_ms
            
            max_child_duration = max(
                calculate_path_duration(child_id)
                for child_id in child_ids
            )
            
            return span.duration_ms + max_child_duration
        
        return max(
            calculate_path_duration(root.span_id)
            for root in root_spans
        )
    
    def shutdown(self):
        """Shutdown telemetry providers."""
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            logger.info("Telemetry shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down telemetry: {e}")


# Global telemetry manager instance
telemetry_manager = TelemetryManager()

# Made with Bob
