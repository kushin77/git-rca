"""
OpenTelemetry Tracing Integration
==================================

Provides distributed tracing capabilities for observability and debugging.
Enables full context propagation across async boundaries and microservices.

Key Responsibilities:
- Configure OpenTelemetry SDK
- Initialize OTLP exporters
- Manage span creation and context
- Propagate trace context
- Handle errors and exceptions in spans
"""

from typing import Optional, Dict, Any, Callable, TypeVar
from functools import wraps
from datetime import datetime
import logging
from contextlib import contextmanager

# Mock OpenTelemetry imports (full implementation would use real OTEL library)
# In production, replace with: from opentelemetry import trace, metrics
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import SimpleSpanProcessor


logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class SpanAttribute:
    """Represents an attribute to be added to a span."""
    
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value


class MockSpan:
    """Mock implementation of OpenTelemetry Span for testing/demo."""
    
    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes or {}
        self.events = []
        self.start_time = datetime.utcnow()
        self.end_time = None
        self.status = "UNSET"
        self.exception = None
    
    def set_attribute(self, key: str, value: Any) -> 'MockSpan':
        """Set an attribute on the span."""
        self.attributes[key] = value
        return self
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> 'MockSpan':
        """Add an event to the span."""
        self.events.append({
            'name': name,
            'attributes': attributes or {},
            'timestamp': datetime.utcnow(),
        })
        return self
    
    def record_exception(self, exception: Exception) -> 'MockSpan':
        """Record an exception in the span."""
        self.exception = exception
        self.status = "ERROR"
        self.add_event(
            "exception",
            {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            }
        )
        return self
    
    def set_status(self, status: str) -> 'MockSpan':
        """Set the span status."""
        self.status = status
        return self
    
    def end(self) -> None:
        """End the span."""
        self.end_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for inspection."""
        duration_ms = None
        if self.end_time and self.start_time:
            duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        return {
            'name': self.name,
            'attributes': self.attributes,
            'events': self.events,
            'status': self.status,
            'duration_ms': duration_ms,
            'has_exception': self.exception is not None,
        }


class TracingManager:
    """
    Manages OpenTelemetry tracing configuration and span lifecycle.
    
    Provides:
    - Tracer initialization
    - Span creation and management
    - Context propagation
    - Error handling
    """
    
    def __init__(self, service_name: str, environment: str = "development"):
        """
        Initialize tracing manager.
        
        Args:
            service_name: Name of the service/application
            environment: Environment name (development, staging, production)
        """
        self.service_name = service_name
        self.environment = environment
        self.tracer = MockTracer(service_name)
        self.spans_stack = []
        self.shutdown_called = False
        
        logger.info(
            f"Tracing initialized for {service_name} in {environment} environment"
        )
    
    def create_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> MockSpan:
        """
        Create a new span.
        
        Args:
            name: Name of the span
            attributes: Initial attributes for the span
        
        Returns:
            MockSpan: The created span
        """
        span = self.tracer.start_span(name, attributes)
        self.spans_stack.append(span)
        return span
    
    def end_span(self, span: MockSpan) -> None:
        """
        End a span.
        
        Args:
            span: The span to end
        """
        if span in self.spans_stack:
            self.spans_stack.remove(span)
        span.end()
    
    def get_current_span(self) -> Optional[MockSpan]:
        """Get the currently active span."""
        return self.spans_stack[-1] if self.spans_stack else None
    
    def record_exception(self, exception: Exception) -> None:
        """
        Record an exception in the current span.
        
        Args:
            exception: The exception to record
        """
        span = self.get_current_span()
        if span:
            span.record_exception(exception)
        logger.exception(f"Exception recorded in span: {exception}")
    
    @contextmanager
    def span_context(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for span lifecycle.
        
        Usage:
            with tracing_manager.span_context("operation", {"user": "user-1"}):
                # code here
        
        Args:
            name: Span name
            attributes: Initial attributes
        
        Yields:
            MockSpan: The created span
        """
        span = self.create_span(name, attributes)
        try:
            yield span
            span.set_status("OK")
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            self.end_span(span)
    
    def shutdown(self) -> None:
        """Shutdown the tracer and flush spans."""
        if self.shutdown_called:
            return
        
        self.shutdown_called = True
        logger.info(f"Shutting down tracing for {self.service_name}")
    
    def get_active_spans(self) -> list:
        """Get all currently active spans."""
        return self.spans_stack.copy()


class MockTracer:
    """Mock implementation of OpenTelemetry Tracer."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.spans = []
    
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> MockSpan:
        """Start a new span."""
        span = MockSpan(name, attributes)
        self.spans.append(span)
        return span
    
    def get_spans(self) -> list:
        """Get all recorded spans."""
        return self.spans.copy()


# Global tracing manager instance
_tracing_manager: Optional[TracingManager] = None


def initialize_tracing(
    service_name: str,
    environment: str = "development",
) -> TracingManager:
    """
    Initialize global tracing manager.
    
    Args:
        service_name: Name of the service
        environment: Environment name
    
    Returns:
        TracingManager: The initialized manager
    """
    global _tracing_manager
    _tracing_manager = TracingManager(service_name, environment)
    return _tracing_manager


def get_tracing_manager() -> Optional[TracingManager]:
    """Get the global tracing manager."""
    return _tracing_manager


def trace_operation(func: F) -> F:
    """
    Decorator to trace an operation (e.g., API endpoint).
    
    Automatically:
    - Creates a span with the function name
    - Captures function arguments
    - Records execution duration
    - Handles exceptions
    
    Usage:
        @trace_operation
        def create_canvas(self, canvas_data):
            # implementation
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        manager = get_tracing_manager()
        if not manager:
            return func(*args, **kwargs)
        
        span_name = f"{func.__module__}.{func.__qualname__}"
        attributes = {
            'function': func.__name__,
            'type': 'operation',
        }
        
        # Add argument info (avoid sensitive data)
        if args:
            attributes['args_count'] = len(args)
        if kwargs:
            attributes['kwargs_keys'] = list(kwargs.keys())
        
        with manager.span_context(span_name, attributes) as span:
            try:
                result = func(*args, **kwargs)
                span.set_attribute('result_type', type(result).__name__)
                return result
            except Exception as e:
                span.record_exception(e)
                raise
    
    return wrapper  # type: ignore


def trace_method(
    name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to trace a method with customizable options.
    
    Args:
        name: Custom span name (default: method name)
        include_args: Include argument values in span attributes
        include_result: Include result value in span attributes
    
    Usage:
        @trace_method(name="process_canvas", include_result=True)
        def process(self, canvas):
            # implementation
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            if not manager:
                return func(*args, **kwargs)
            
            span_name = name or func.__name__
            attributes = {
                'method': func.__name__,
                'type': 'method',
            }
            
            # Add arguments if requested
            if include_args:
                attributes['args_count'] = len(args)
                if kwargs:
                    attributes['kwargs'] = str(kwargs)
            
            with manager.span_context(span_name, attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    if include_result:
                        span.set_attribute('result', str(result))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise
        
        return wrapper  # type: ignore
    
    return decorator


def add_span_event(event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.
    
    Args:
        event_name: Name of the event
        attributes: Event attributes
    """
    manager = get_tracing_manager()
    if not manager:
        return
    
    span = manager.get_current_span()
    if span:
        span.add_event(event_name, attributes)


def set_span_attribute(key: str, value: Any) -> None:
    """
    Set an attribute on the current span.
    
    Args:
        key: Attribute key
        value: Attribute value
    """
    manager = get_tracing_manager()
    if not manager:
        return
    
    span = manager.get_current_span()
    if span:
        span.set_attribute(key, value)
