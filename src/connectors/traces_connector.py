"""
Traces Connector - Ingest APM traces and detect performance issues

Features:
- Fetch traces from APM systems (Jaeger, Datadog, New Relic)
- Detect slow traces (threshold-based)
- Extract span errors
- Identify critical paths
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from src.models.event import Event, EventSource, EventSeverity
from src.connectors.base_connector import (
    BaseConnector,
    RetryPolicy,
    CircuitBreakerConfig,
)


class TracesConnector(BaseConnector):
    """Collect and analyze APM traces to detect performance issues."""

    # Latency thresholds (milliseconds)
    LATENCY_THRESHOLDS = {
        "critical": 5000,  # > 5 seconds = critical
        "high": 1000,  # > 1 second = high
        "medium": 500,  # > 500ms = medium
    }

    def __init__(
        self,
        apm_source: str = "jaeger",  # jaeger, datadog, new_relic, etc.
        service_name: str = None,  # Filter by service
        lookback_period: int = 300,  # Seconds
        retry_policy: RetryPolicy = None,
        circuit_breaker_config: CircuitBreakerConfig = None,
    ):
        """
        Initialize traces connector.

        Args:
            apm_source: APM system (jaeger, datadog, new_relic)
            service_name: Service name to filter traces
            lookback_period: Period (seconds) to look back for traces
            retry_policy: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__(
            source=EventSource.TRACES,
            retry_policy=retry_policy,
            circuit_breaker_config=circuit_breaker_config,
        )
        self.apm_source = apm_source
        self.service_name = service_name
        self.lookback_period = lookback_period

    def _collect_with_timeout(self) -> List[Event]:
        """
        Collect traces and detect performance issues.

        Returns:
            List of Event objects for detected issues
        """
        traces = self._fetch_traces()
        events = []

        for trace in traces:
            try:
                # Check for slow spans
                slow_event = self._detect_slow_trace(trace)
                if slow_event:
                    events.append(slow_event)

                # Check for errors in spans
                error_events = self._detect_span_errors(trace)
                events.extend(error_events)
            except Exception as e:
                self.logger.warning(f"Failed to analyze trace: {e}")
                continue

        self.logger.info(f"Detected {len(events)} issues from {len(traces)} traces")
        return events

    def _fetch_traces(self) -> List[Dict[str, Any]]:
        """
        Fetch traces from APM source.

        Currently supports:
        - In-memory traces (for testing)
        - Jaeger API

        Returns:
            List of trace objects
        """
        if isinstance(self.apm_source, list):
            # For testing: accept pre-populated traces
            return self.apm_source

        try:
            if self.apm_source == "jaeger":
                return self._fetch_from_jaeger()
            elif self.apm_source == "datadog":
                return self._fetch_from_datadog()
            elif self.apm_source == "new_relic":
                return self._fetch_from_new_relic()
            else:
                self.logger.warning(f"Unknown APM source: {self.apm_source}")
                return []
        except Exception as e:
            self.logger.error(f"Failed to fetch traces: {e}")
            raise

    def _fetch_from_jaeger(self) -> List[Dict[str, Any]]:
        """Fetch traces from Jaeger."""
        # TODO: Implement Jaeger query API
        # Would query /api/traces?service=<service>&limit=100
        return []

    def _fetch_from_datadog(self) -> List[Dict[str, Any]]:
        """Fetch traces from Datadog."""
        # TODO: Implement Datadog APM API
        return []

    def _fetch_from_new_relic(self) -> List[Dict[str, Any]]:
        """Fetch traces from New Relic."""
        # TODO: Implement New Relic API
        return []

    def _detect_slow_trace(self, trace: Dict[str, Any]) -> Optional[Event]:
        """
        Detect slow trace.

        Args:
            trace: Trace object with spans

        Returns:
            Event if slow trace detected, None otherwise
        """
        trace_id = trace.get("traceID")
        spans = trace.get("spans", [])

        if not spans:
            return None

        # Calculate total duration (max span end - min span start)
        start_times = [s.get("startTime", 0) for s in spans]
        end_times = [s.get("startTime", 0) + s.get("duration", 0) for s in spans]

        if not start_times or not end_times:
            return None

        total_duration = (max(end_times) - min(start_times)) / 1000  # Convert to ms

        # Determine severity based on thresholds
        severity = None
        threshold = None

        for sev, thresh in self.LATENCY_THRESHOLDS.items():
            if total_duration > thresh:
                severity = sev
                threshold = thresh
                break

        if not severity:
            return None  # Within acceptable latency

        # Find slowest span
        slowest_span = max(spans, key=lambda s: s.get("duration", 0))

        # Create event
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.TRACES,
            event_type="slow_trace",
            severity=EventSeverity[severity.upper()],
            data={
                "trace_id": trace_id,
                "service": trace.get("processes", {}).get("p1", {}).get("serviceName"),
                "total_duration_ms": total_duration,
                "threshold_ms": threshold,
                "slowest_span": slowest_span.get("operationName"),
                "slowest_span_duration_ms": slowest_span.get("duration", 0) / 1000,
                "span_count": len(spans),
            },
            source_id=f"trace:{trace_id}",
            tags=["slow_trace", "performance"],
            metadata={
                "apm_source": self.apm_source,
                "service": trace.get("processes", {}).get("p1", {}).get("serviceName"),
            },
        )

        return event

    def _detect_span_errors(self, trace: Dict[str, Any]) -> List[Event]:
        """
        Detect errors in spans.

        Args:
            trace: Trace object with spans

        Returns:
            List of Event objects for detected errors
        """
        events = []
        trace_id = trace.get("traceID")
        spans = trace.get("spans", [])

        for span in spans:
            # Check for error tags
            tags = span.get("tags", [])
            error_found = False
            error_msg = None

            for tag in tags:
                if tag.get("key") == "error":
                    error_found = tag.get("value", True)
                    break

            if not error_found:
                continue

            # Extract error message from logs
            logs = span.get("logs", [])
            for log in logs:
                for field in log.get("fields", []):
                    if field.get("key") in ["message", "error.msg"]:
                        error_msg = field.get("value")
                        break

            # Create event
            event = Event(
                timestamp=datetime.utcnow().isoformat(),
                source=EventSource.TRACES,
                event_type="span_error",
                severity=EventSeverity.HIGH,
                data={
                    "trace_id": trace_id,
                    "span_id": span.get("spanID"),
                    "operation": span.get("operationName"),
                    "error_message": error_msg,
                    "service": trace.get("processes", {})
                    .get("p1", {})
                    .get("serviceName"),
                },
                source_id=f"span:{span.get('spanID')}",
                tags=["span_error", "error"],
                metadata={
                    "apm_source": self.apm_source,
                },
            )

            events.append(event)

        return events
