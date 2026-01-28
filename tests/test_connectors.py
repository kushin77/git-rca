"""
Tests for advanced event connectors with resilience patterns

Tests retry logic, circuit breaker, and DLQ functionality
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from src.connectors.base_connector import BaseConnector, RetryPolicy, CircuitBreakerConfig, CircuitBreaker, CircuitBreakerState
from src.connectors.logs_connector import LogsConnector
from src.connectors.metrics_connector import MetricsConnector
from src.connectors.traces_connector import TracesConnector
from src.connectors.git_connector import GitConnector
from src.connectors.ci_connector import CIConnector
from src.models.event import EventSource, EventSeverity


class TestBaseConnector:
    """Test base connector resilience patterns."""

    def test_retry_policy(self):
        """Test retry policy exponential backoff."""
        policy = RetryPolicy(max_retries=3, initial_delay=1.0, exponential_base=2.0, jitter=False)

        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        cb = CircuitBreaker(config)

        assert cb.state == CircuitBreakerState.CLOSED

        # Record failures
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Test recovery timeout (mock time)
        with patch('src.connectors.base_connector.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(seconds=config.recovery_timeout * 2)
            mock_datetime.timedelta = timedelta

            assert cb.can_execute() == True
            assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_dlq_storage(self):
        """Test dead letter queue storage."""
        from src.connectors.base_connector import DeadLetterQueue
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False) as f:
            db_path = f.name

        try:
            dlq = DeadLetterQueue(db_path)

            # Create test event
            event = MagicMock()
            event.id = "test-event-1"
            event.to_dict.return_value = {"id": "test-event-1", "data": "test"}

            # Store failed event
            success = dlq.put(event, "Test error", 3)
            assert success == True

            # Retrieve events
            events = dlq.get_all()
            assert len(events) == 1
            assert events[0]["id"] == "test-event-1"
            assert events[0]["error_message"] == "Test error"
            assert events[0]["retry_count"] == 3

        finally:
            os.unlink(db_path)


class TestLogsConnector:
    """Test logs connector functionality."""

    def test_logs_connector_creation(self):
        """Test logs connector initialization."""
        connector = LogsConnector()
        assert connector.source == EventSource.LOGS
        assert connector.retry_policy.max_retries == 3

    def test_error_pattern_detection(self):
        """Test error pattern detection in logs."""
        connector = LogsConnector()

        error_log = "2023-01-01 10:00:00 ERROR Database connection failed"
        warning_log = "2023-01-01 10:00:01 WARN High memory usage detected"
        info_log = "2023-01-01 10:00:02 INFO Application started successfully"

        # Test error detection
        assert "ERROR" in error_log
        assert any(pattern in error_log.lower() for pattern in connector.ERROR_PATTERNS)

        # Test severity classification would work in _classify_severity
        # (This is tested indirectly through collect method)


class TestMetricsConnector:
    """Test metrics connector functionality."""

    def test_metrics_connector_creation(self):
        """Test metrics connector initialization."""
        connector = MetricsConnector()
        assert connector.source == EventSource.METRICS
        assert connector.baseline_period == 3600

    def test_anomaly_detection(self):
        """Test basic anomaly detection logic."""
        connector = MetricsConnector()

        # Test threshold lookup
        assert connector.ANOMALY_THRESHOLDS['cpu'] == 2.0
        assert connector.ANOMALY_THRESHOLDS['latency'] == 2.5


class TestTracesConnector:
    """Test traces connector functionality."""

    def test_traces_connector_creation(self):
        """Test traces connector initialization."""
        connector = TracesConnector()
        assert connector.source == EventSource.TRACES
        assert connector.lookback_period == 300

    def test_latency_thresholds(self):
        """Test latency threshold configuration."""
        connector = TracesConnector()

        assert connector.LATENCY_THRESHOLDS['critical'] == 5000
        assert connector.LATENCY_THRESHOLDS['high'] == 1000


class TestGitConnector:
    """Test Git connector functionality."""

    def test_git_connector_creation(self):
        """Test Git connector initialization."""
        connector = GitConnector()
        assert connector.source == EventSource.GIT
        assert connector.lookback_commits == 10

    @patch('subprocess.run')
    def test_git_log_parsing(self, mock_subprocess):
        """Test Git log output parsing."""
        # Mock git log output
        mock_output = """COMMIT_START
Hash: abc123def456
Author: Test User <test@example.com>
Date: 2023-01-01 10:00:00 +0000
Subject: Fix critical bug
Body: This fixes a critical issue
Files: 5
Insertions: 100
 5 files changed, 100 insertions(+), 50 deletions(-)
"""

        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )

        connector = GitConnector()
        commits = connector._get_recent_commits()

        assert len(commits) == 1
        commit = commits[0]
        assert commit["hash"] == "abc123def456"
        assert commit["author"] == "Test User <test@example.com>"
        assert commit["subject"] == "Fix critical bug"
        assert commit["files_changed"] == 5
        assert commit["insertions"] == 100


class TestCIConnector:
    """Test CI connector functionality."""

    def test_ci_connector_creation(self):
        """Test CI connector initialization."""
        connector = CIConnector()
        assert connector.source == EventSource.CI
        assert connector.ci_source == "github_actions"

    def test_status_pattern_detection(self):
        """Test CI status pattern detection."""
        connector = CIConnector()

        assert "failed" in connector.FAILURE_PATTERNS
        assert "success" in connector.SUCCESS_PATTERNS

    def test_ci_event_creation(self):
        """Test CI event creation from data."""
        connector = CIConnector()

        event_data = {
            "id": "ci-run-1",
            "status": "failed",
            "workflow": "Test Pipeline",
            "branch": "main",
            "commit": "abc123",
            "run_time": "2023-01-01T10:00:00",
            "duration_seconds": 300,
            "jobs": 5,
            "artifacts": 2,
        }

        event = connector._create_ci_event(event_data)
        assert event is not None
        assert event.id is not None
        assert len(event.id) > 0  # UUID format
        assert event.source == EventSource.CI
        assert event.event_type == "ci_run"
        assert event.metadata["status"] == "failed"


class TestConnectorIntegration:
    """Test connector integration with resilience patterns."""

    def test_connector_with_retry_on_failure(self):
        """Test that connectors properly retry on failure."""
        connector = LogsConnector()

        # Mock _collect_with_timeout to always fail
        original_method = connector._collect_with_timeout
        connector._collect_with_timeout = MagicMock(side_effect=Exception("Test failure"))

        # Collect should trigger retries
        events = connector.collect()

        # Should return empty list after retries
        assert events == []

        # Circuit breaker should record failure
        assert connector.circuit_breaker.failure_count > 0

    def test_connector_success_resets_circuit_breaker(self):
        """Test that successful collection resets circuit breaker."""
        connector = LogsConnector()

        # First fail to open circuit (default threshold is 5)
        for _ in range(5):
            connector.circuit_breaker.record_failure()
        assert connector.circuit_breaker.state == CircuitBreakerState.OPEN

        # Manually set to HALF_OPEN to allow execution
        connector.circuit_breaker._set_half_open()
        assert connector.circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Mock successful collection
        with patch.object(connector, '_collect_with_timeout', return_value=[]):
            # Need 2 successes to close from HALF_OPEN (default success_threshold=2)
            events = connector.collect()
            assert connector.circuit_breaker.state == CircuitBreakerState.HALF_OPEN
            events = connector.collect()
            assert connector.circuit_breaker.state == CircuitBreakerState.CLOSED
            assert connector.circuit_breaker.failure_count == 0