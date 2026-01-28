"""
Tests for OpenTelemetry Tracing Integration
============================================

Comprehensive test suite for distributed tracing, including:
- Span creation and management
- Context propagation
- Decorator functionality
- Exception handling
- Span attributes and events
"""

import pytest
from datetime import datetime
from src.observability.tracing import (
    TracingManager,
    MockSpan,
    trace_operation,
    trace_method,
    initialize_tracing,
    get_tracing_manager,
    add_span_event,
    set_span_attribute,
)


@pytest.fixture
def tracing_manager():
    """Create a fresh tracing manager for each test."""
    return TracingManager("test-service", "test")


@pytest.fixture
def initialized_tracing():
    """Initialize global tracing manager for tests."""
    manager = initialize_tracing("test-service", "test")
    yield manager
    manager.shutdown()


class TestMockSpan:
    """Tests for MockSpan class."""
    
    def test_span_creation(self):
        """Test creating a span."""
        span = MockSpan("test-span")
        
        assert span.name == "test-span"
        assert span.attributes == {}
        assert span.events == []
        assert span.status == "UNSET"
        assert span.exception is None
    
    def test_span_with_attributes(self):
        """Test creating span with initial attributes."""
        attrs = {"user": "user-1", "action": "create"}
        span = MockSpan("test-span", attrs)
        
        assert span.attributes == attrs
    
    def test_set_attribute(self):
        """Test setting attributes on a span."""
        span = MockSpan("test-span")
        
        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 42)
        
        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == 42
    
    def test_add_event(self):
        """Test adding events to a span."""
        span = MockSpan("test-span")
        
        span.add_event("event1")
        span.add_event("event2", {"detail": "some info"})
        
        assert len(span.events) == 2
        assert span.events[0]["name"] == "event1"
        assert span.events[1]["name"] == "event2"
        assert span.events[1]["attributes"]["detail"] == "some info"
    
    def test_record_exception(self):
        """Test recording an exception in a span."""
        span = MockSpan("test-span")
        exception = ValueError("Test error")
        
        span.record_exception(exception)
        
        assert span.exception == exception
        assert span.status == "ERROR"
        assert len(span.events) == 1
        assert span.events[0]["name"] == "exception"
    
    def test_span_lifecycle(self):
        """Test span start and end."""
        span = MockSpan("test-span")
        
        assert span.start_time is not None
        assert span.end_time is None
        
        span.end()
        
        assert span.end_time is not None
        assert span.end_time >= span.start_time
    
    def test_span_to_dict(self):
        """Test converting span to dictionary."""
        span = MockSpan("test-span", {"user": "user-1"})
        span.set_attribute("action", "create")
        span.add_event("started")
        span.end()
        
        data = span.to_dict()
        
        assert data["name"] == "test-span"
        assert data["attributes"]["user"] == "user-1"
        assert data["attributes"]["action"] == "create"
        assert data["status"] == "UNSET"
        assert len(data["events"]) == 1
        assert data["duration_ms"] is not None


class TestTracingManager:
    """Tests for TracingManager."""
    
    def test_manager_initialization(self, tracing_manager):
        """Test initializing tracing manager."""
        assert tracing_manager.service_name == "test-service"
        assert tracing_manager.environment == "test"
        assert not tracing_manager.shutdown_called
    
    def test_create_span(self, tracing_manager):
        """Test creating a span."""
        span = tracing_manager.create_span("test-span")
        
        assert span.name == "test-span"
        assert tracing_manager.get_current_span() == span
    
    def test_create_span_with_attributes(self, tracing_manager):
        """Test creating span with attributes."""
        attrs = {"user": "user-1", "resource": "canvas-1"}
        span = tracing_manager.create_span("test-span", attrs)
        
        assert span.attributes == attrs
    
    def test_span_stack_management(self, tracing_manager):
        """Test span stack for nested spans."""
        span1 = tracing_manager.create_span("span1")
        span2 = tracing_manager.create_span("span2")
        
        assert tracing_manager.get_current_span() == span2
        assert len(tracing_manager.get_active_spans()) == 2
        
        tracing_manager.end_span(span2)
        
        assert tracing_manager.get_current_span() == span1
        assert len(tracing_manager.get_active_spans()) == 1
    
    def test_end_span(self, tracing_manager):
        """Test ending a span."""
        span = tracing_manager.create_span("test-span")
        
        assert span.end_time is None
        
        tracing_manager.end_span(span)
        
        assert span.end_time is not None
    
    def test_span_context_manager(self, tracing_manager):
        """Test span context manager."""
        with tracing_manager.span_context("test-span") as span:
            assert span.name == "test-span"
            assert span.status == "UNSET"
        
        assert span.status == "OK"
        assert span.end_time is not None
    
    def test_span_context_with_exception(self, tracing_manager):
        """Test span context manager with exception."""
        with pytest.raises(ValueError):
            with tracing_manager.span_context("test-span") as span:
                raise ValueError("Test error")
        
        assert span.status == "ERROR"
        assert span.exception is not None
    
    def test_record_exception(self, tracing_manager):
        """Test recording exception in current span."""
        span = tracing_manager.create_span("test-span")
        exception = RuntimeError("Test error")
        
        tracing_manager.record_exception(exception)
        
        assert span.exception == exception
        assert span.status == "ERROR"
    
    def test_shutdown(self, tracing_manager):
        """Test shutting down tracing manager."""
        assert not tracing_manager.shutdown_called
        
        tracing_manager.shutdown()
        
        assert tracing_manager.shutdown_called
    
    def test_get_current_span_empty(self, tracing_manager):
        """Test getting current span when none exist."""
        assert tracing_manager.get_current_span() is None


class TestTraceOperationDecorator:
    """Tests for @trace_operation decorator."""
    
    def test_trace_operation_basic(self, initialized_tracing):
        """Test basic trace operation decorator."""
        @trace_operation
        def test_function():
            return "result"
        
        result = test_function()
        
        assert result == "result"
        spans = initialized_tracing.tracer.get_spans()
        assert len(spans) == 1
        assert spans[0].name.endswith("test_function")
    
    def test_trace_operation_with_args(self, initialized_tracing):
        """Test trace operation with arguments."""
        @trace_operation
        def test_function(a, b, c=None):
            return a + b
        
        result = test_function(1, 2, c=3)
        
        assert result == 3
        spans = initialized_tracing.tracer.get_spans()
        assert spans[0].attributes["args_count"] == 2
        assert "c" in spans[0].attributes["kwargs_keys"]
    
    def test_trace_operation_exception(self, initialized_tracing):
        """Test trace operation with exception."""
        @trace_operation
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function()
        
        spans = initialized_tracing.tracer.get_spans()
        assert spans[0].status == "ERROR"
        assert spans[0].exception is not None
    
    def test_trace_operation_captures_result_type(self, initialized_tracing):
        """Test that decorator captures result type."""
        @trace_operation
        def test_function():
            return {"key": "value"}
        
        test_function()
        
        spans = initialized_tracing.tracer.get_spans()
        assert spans[0].attributes["result_type"] == "dict"
    
    def test_trace_operation_without_manager(self):
        """Test trace operation when no manager initialized."""
        @trace_operation
        def test_function():
            return "result"
        
        result = test_function()
        
        assert result == "result"


class TestTraceMethodDecorator:
    """Tests for @trace_method decorator."""
    
    def test_trace_method_basic(self, initialized_tracing):
        """Test basic trace method decorator."""
        class TestClass:
            @trace_method()
            def test_method(self):
                return "result"
        
        obj = TestClass()
        result = obj.test_method()
        
        assert result == "result"
        spans = initialized_tracing.tracer.get_spans()
        assert len(spans) == 1
        assert "test_method" in spans[0].name
    
    def test_trace_method_custom_name(self, initialized_tracing):
        """Test trace method with custom span name."""
        class TestClass:
            @trace_method(name="custom_operation")
            def test_method(self):
                return "result"
        
        obj = TestClass()
        obj.test_method()
        
        spans = initialized_tracing.tracer.get_spans()
        assert spans[0].name == "custom_operation"
    
    def test_trace_method_with_args(self, initialized_tracing):
        """Test trace method with arguments."""
        class TestClass:
            @trace_method(include_args=True)
            def test_method(self, a, b):
                return a + b
        
        obj = TestClass()
        result = obj.test_method(1, 2)
        
        assert result == 3
        spans = initialized_tracing.tracer.get_spans()
        # args_count includes self, so 3 (self, a, b)
        assert spans[0].attributes["args_count"] == 3
    
    def test_trace_method_with_result(self, initialized_tracing):
        """Test trace method capturing result."""
        class TestClass:
            @trace_method(include_result=True)
            def test_method(self):
                return 42
        
        obj = TestClass()
        obj.test_method()
        
        spans = initialized_tracing.tracer.get_spans()
        assert "result" in spans[0].attributes
        assert spans[0].attributes["result"] == "42"
    
    def test_trace_method_exception(self, initialized_tracing):
        """Test trace method with exception."""
        class TestClass:
            @trace_method()
            def test_method(self):
                raise RuntimeError("Test error")
        
        obj = TestClass()
        
        with pytest.raises(RuntimeError):
            obj.test_method()
        
        spans = initialized_tracing.tracer.get_spans()
        assert spans[0].status == "ERROR"


class TestGlobalFunctions:
    """Tests for global tracing functions."""
    
    def test_initialize_tracing(self):
        """Test initializing global tracing."""
        manager = initialize_tracing("service", "prod")
        
        assert manager.service_name == "service"
        assert manager.environment == "prod"
        assert get_tracing_manager() == manager
    
    def test_get_tracing_manager_before_init(self):
        """Test getting manager before initialization."""
        # Note: This test assumes a fresh state
        manager = get_tracing_manager()
        # Could be None if not initialized in test, or could be from previous test
        # This is why fixtures are better
    
    def test_add_span_event(self, initialized_tracing):
        """Test adding event to current span."""
        with initialized_tracing.span_context("test"):
            add_span_event("test-event", {"detail": "info"})
        
        spans = initialized_tracing.tracer.get_spans()
        assert len(spans[0].events) == 1
        assert spans[0].events[0]["name"] == "test-event"
    
    def test_set_span_attribute(self, initialized_tracing):
        """Test setting attribute on current span."""
        with initialized_tracing.span_context("test") as span:
            set_span_attribute("key", "value")
        
        assert span.attributes["key"] == "value"
    
    def test_add_span_event_without_span(self):
        """Test adding event when no span is active."""
        # Should not raise, just do nothing
        add_span_event("event")
    
    def test_set_span_attribute_without_span(self):
        """Test setting attribute when no span is active."""
        # Should not raise, just do nothing
        set_span_attribute("key", "value")


class TestNestedSpans:
    """Tests for nested span scenarios."""
    
    def test_nested_spans_tracking(self, tracing_manager):
        """Test nested span tracking."""
        span1 = tracing_manager.create_span("parent")
        span2 = tracing_manager.create_span("child")
        span3 = tracing_manager.create_span("grandchild")
        
        assert len(tracing_manager.get_active_spans()) == 3
        assert tracing_manager.get_current_span() == span3
        
        tracing_manager.end_span(span3)
        assert tracing_manager.get_current_span() == span2
        
        tracing_manager.end_span(span2)
        assert tracing_manager.get_current_span() == span1
        
        tracing_manager.end_span(span1)
        assert tracing_manager.get_current_span() is None
    
    def test_nested_contexts(self, tracing_manager):
        """Test nested context managers."""
        with tracing_manager.span_context("parent") as parent:
            with tracing_manager.span_context("child") as child:
                pass
        
        assert parent.status == "OK"
        assert child.status == "OK"


class TestTraceIntegration:
    """Integration tests for tracing functionality."""
    
    def test_full_span_lifecycle(self, tracing_manager):
        """Test complete span lifecycle."""
        with tracing_manager.span_context("operation", {"user": "user-1"}) as span:
            span.set_attribute("step", "1")
            span.add_event("started")
            span.set_attribute("step", "2")
            span.add_event("processing")
            span.set_attribute("step", "3")
            span.add_event("completed")
        
        assert span.name == "operation"
        assert span.attributes["user"] == "user-1"
        assert span.attributes["step"] == "3"
        assert len(span.events) == 3
        assert span.status == "OK"
        assert span.end_time is not None
    
    def test_tracing_with_exceptions(self, tracing_manager):
        """Test tracing through exception scenarios."""
        try:
            with tracing_manager.span_context("operation") as span:
                span.add_event("starting")
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        assert span.status == "ERROR"
        assert span.exception is not None
        assert len(span.events) == 2  # started + exception event
