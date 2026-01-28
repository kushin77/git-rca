"""
Tests for Phase 3b - Advanced Event Connectors & Resilience Patterns

Test cases for:
- Base connector with retry and circuit breaker
- Logs connector (JSON parsing, severity classification)
- Metrics connector (anomaly detection)
- Traces connector (slow trace detection, span errors)
- Resilience patterns (retry policy, circuit breaker, DLQ)
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from src.models.event import EventSource, EventSeverity
from src.connectors.base_connector import (
    BaseConnector,
    RetryPolicy,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreaker,
    DeadLetterQueue,
)
from src.connectors.logs_connector import LogsConnector
from src.connectors.metrics_connector import MetricsConnector
from src.connectors.traces_connector import TracesConnector


class TestRetryPolicy:
    """Test retry policy with exponential backoff."""

    def test_default_retry_policy(self):
        """Test default retry policy."""
        policy = RetryPolicy()

        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0
        assert policy.max_delay == 30.0

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Delays should double: 1, 2, 4, 8, ...
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0

    def test_max_delay_cap(self):
        """Test that max delay is capped."""
        policy = RetryPolicy(
            initial_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False,
        )

        # Should cap at max_delay
        assert policy.get_delay(4) == 10.0  # Would be 16, capped at 10


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_breaker_closed(self):
        """Test circuit breaker in CLOSED state."""
        cb = CircuitBreaker()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_execute()

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)

        # Record failures
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        cb.record_failure()  # Third failure triggers open
        assert cb.state == CircuitBreakerState.OPEN
        assert not cb.can_execute()

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=1,  # 1 second
        )
        cb = CircuitBreaker(config)

        # Trip the circuit
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Immediately, can't execute
        assert not cb.can_execute()

        # Wait for timeout
        time.sleep(1.1)

        # Now can execute (transitions to HALF_OPEN)
        assert cb.can_execute()
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_breaker_closes_on_success_in_half_open(self):
        """Test circuit closes from HALF_OPEN on success."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=1,
            success_threshold=1,
        )
        cb = CircuitBreaker(config)

        # Trip circuit
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait and transition to HALF_OPEN
        time.sleep(1.1)
        cb.can_execute()  # Triggers transition

        # Record success (should close)
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED


class TestDeadLetterQueue:
    """Test dead letter queue."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up test database before each test."""
        import os

        db_path = "data/test_dlq.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        yield
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_put_and_get_events(self):
        """Test storing and retrieving events from DLQ."""
        from src.models.event import Event

        dlq = DeadLetterQueue("data/test_dlq.db")

        # Create and store event
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.LOGS,
            event_type="test",
        )

        result = dlq.put(event, "Test error", 3)
        assert result is True

        # Retrieve
        events = dlq.get_all()
        assert len(events) == 1
        assert events[0]["id"] == event.id
        assert events[0]["error_message"] == "Test error"

    def test_remove_from_dlq(self):
        """Test removing event from DLQ."""
        from src.models.event import Event

        dlq = DeadLetterQueue("data/test_dlq.db")

        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.LOGS,
            event_type="test",
        )

        dlq.put(event, "Error", 1)
        assert len(dlq.get_all()) == 1

        # Remove
        result = dlq.remove(event.id)
        assert result is True
        assert len(dlq.get_all()) == 0


class TestLogsConnector:
    """Test logs connector."""

    def test_parse_error_log(self):
        """Test parsing error log entry."""
        logs = [
            {
                "level": "error",
                "message": "Database connection failed",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "api-service",
                "request_id": "req-123",
            }
        ]

        connector = LogsConnector(log_source=logs)
        events = connector.collect()

        assert len(events) == 1
        assert events[0].source == EventSource.LOGS
        assert events[0].severity == EventSeverity.HIGH  # error level
        assert "request_id" in events[0].data

    def test_parse_warning_log(self):
        """Test parsing warning log entry."""
        logs = [
            {
                "level": "warning",
                "message": "Slow query detected",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]

        connector = LogsConnector(log_source=logs)
        events = connector.collect()

        assert len(events) == 1
        assert events[0].severity == EventSeverity.MEDIUM

    def test_skip_info_logs(self):
        """Test that info logs are skipped."""
        logs = [
            {
                "level": "info",
                "message": "Request processed",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]

        connector = LogsConnector(log_source=logs)
        events = connector.collect()

        assert len(events) == 0

    def test_extract_tags(self):
        """Test tag extraction from logs."""
        logs = [
            {
                "level": "error",
                "message": "Connection timeout",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "database",
            }
        ]

        connector = LogsConnector(log_source=logs)
        events = connector.collect()

        assert len(events) == 1
        tags = events[0].tags
        assert "error" in tags
        assert "timeout" in tags
        assert "connection_error" in tags


class TestMetricsConnector:
    """Test metrics connector."""

    def test_detect_cpu_anomaly(self):
        """Test detecting CPU anomaly."""
        metrics = {
            "cpu_usage": {
                "value": 95.0,  # High value
                "history": [10.0, 12.0, 11.0, 13.0, 12.0],  # Normal baseline
            }
        }

        connector = MetricsConnector(metrics_source=metrics)
        events = connector.collect()

        assert len(events) == 1
        assert events[0].event_type == "metric_anomaly"
        assert events[0].severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]

    def test_no_anomaly_in_normal_metrics(self):
        """Test that normal metrics don't generate anomalies."""
        metrics = {
            "cpu_usage": {
                "value": 12.0,  # Normal value
                "history": [10.0, 12.0, 11.0, 13.0, 12.0],
            }
        }

        connector = MetricsConnector(metrics_source=metrics)
        events = connector.collect()

        assert len(events) == 0

    def test_classify_metric_type(self):
        """Test metric type classification."""
        connector = MetricsConnector()

        assert connector._classify_metric("cpu_usage") == "cpu"
        assert connector._classify_metric("memory_mb") == "memory"
        assert connector._classify_metric("disk_io") == "disk"
        assert connector._classify_metric("response_time_ms") == "latency"
        assert connector._classify_metric("error_rate") == "error_rate"


class TestTracesConnector:
    """Test traces connector."""

    def test_detect_slow_trace(self):
        """Test detecting slow trace."""
        traces = [
            {
                "traceID": "trace-123",
                "processes": {"p1": {"serviceName": "api-service"}},
                "spans": [
                    {
                        "spanID": "span-1",
                        "operationName": "request_handler",
                        "startTime": 0,
                        "duration": 6000000,  # 6 seconds in microseconds
                        "tags": [],
                        "logs": [],
                    }
                ],
            }
        ]

        connector = TracesConnector(apm_source=traces)
        events = connector.collect()

        assert len(events) == 1
        assert events[0].event_type == "slow_trace"
        assert events[0].severity == EventSeverity.CRITICAL  # > 5 seconds

    def test_detect_span_error(self):
        """Test detecting span error."""
        traces = [
            {
                "traceID": "trace-456",
                "processes": {"p1": {"serviceName": "database-service"}},
                "spans": [
                    {
                        "spanID": "span-2",
                        "operationName": "query",
                        "startTime": 0,
                        "duration": 100000,
                        "tags": [{"key": "error", "value": True}],
                        "logs": [
                            {
                                "fields": [
                                    {"key": "message", "value": "Connection refused"}
                                ]
                            }
                        ],
                    }
                ],
            }
        ]

        connector = TracesConnector(apm_source=traces)
        events = connector.collect()

        assert len(events) == 1
        assert events[0].event_type == "span_error"
        assert events[0].severity == EventSeverity.HIGH

    def test_normal_fast_trace(self):
        """Test that fast, error-free traces generate no events."""
        traces = [
            {
                "traceID": "trace-789",
                "processes": {"p1": {"serviceName": "cache-service"}},
                "spans": [
                    {
                        "spanID": "span-3",
                        "operationName": "cache_get",
                        "startTime": 0,
                        "duration": 10000,  # 10ms
                        "tags": [],
                        "logs": [],
                    }
                ],
            }
        ]

        connector = TracesConnector(apm_source=traces)
        events = connector.collect()

        assert len(events) == 0


class TestConnectorIntegration:
    """Integration tests for connectors."""

    def test_all_connectors_extend_base(self):
        """Test that all connectors properly extend BaseConnector."""
        assert issubclass(LogsConnector, BaseConnector)
        assert issubclass(MetricsConnector, BaseConnector)
        assert issubclass(TracesConnector, BaseConnector)

    def test_connector_sources(self):
        """Test that connectors have correct source."""
        logs = LogsConnector(log_source=[])
        assert logs.source == EventSource.LOGS

        metrics = MetricsConnector(metrics_source={})
        assert metrics.source == EventSource.METRICS

        traces = TracesConnector(apm_source=[])
        assert traces.source == EventSource.TRACES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
