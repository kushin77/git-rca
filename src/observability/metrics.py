"""
Prometheus Metrics Collection
==============================

Provides production-grade metrics collection for monitoring and observability.

Key Responsibilities:
- Collect operation metrics (counts, latencies)
- Track error rates
- Export metrics in Prometheus format
- Provide custom business metrics
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
from collections import defaultdict
import time


class MetricPoint:
    """A single metric data point."""
    
    def __init__(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.name = name
        self.value = value
        self.labels = labels or {}
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus exposition format."""
        if self.labels:
            labels_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
            return f'{self.name}{{{labels_str}}} {self.value}'
        return f'{self.name} {self.value}'


class Counter:
    """Prometheus Counter - monotonically increasing metric."""
    
    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.values: Dict[tuple, float] = defaultdict(float)
    
    def inc(self, amount: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the counter."""
        key = self._make_key(labels)
        self.values[key] += amount
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value."""
        key = self._make_key(labels)
        return self.values[key]
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> tuple:
        """Create a hashable key from labels."""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[MetricPoint]:
        """Collect all counter values."""
        points = []
        for label_key, value in self.values.items():
            labels = dict(label_key) if label_key else {}
            points.append(MetricPoint(self.name, value, labels))
        return points


class Histogram:
    """Prometheus Histogram - distribution of values."""
    
    def __init__(
        self,
        name: str,
        description: str,
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.values: Dict[tuple, List[float]] = defaultdict(list)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation."""
        key = self._make_key(labels)
        self.values[key].append(value)
    
    def get_values(self, labels: Optional[Dict[str, str]] = None) -> List[float]:
        """Get all observations."""
        key = self._make_key(labels)
        return self.values[key].copy()
    
    def get_percentile(self, percentile: float, labels: Optional[Dict[str, str]] = None) -> float:
        """Get percentile value."""
        values = self.get_values(labels)
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_count(self, labels: Optional[Dict[str, str]] = None) -> int:
        """Get count of observations."""
        return len(self.get_values(labels))
    
    def get_sum(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get sum of observations."""
        return sum(self.get_values(labels))
    
    def get_average(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get average of observations."""
        values = self.get_values(labels)
        if not values:
            return 0.0
        return self.get_sum(labels) / len(values)
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> tuple:
        """Create a hashable key from labels."""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[MetricPoint]:
        """Collect histogram metrics."""
        points = []
        for label_key, values in self.values.items():
            labels = dict(label_key) if label_key else {}
            if values:
                points.append(MetricPoint(f'{self.name}_count', float(len(values)), labels))
                points.append(MetricPoint(f'{self.name}_sum', sum(values), labels))
                points.append(MetricPoint(f'{self.name}_average', self.get_average(dict(label_key) if label_key else None), labels))
        return points


class Gauge:
    """Prometheus Gauge - value that can go up or down."""
    
    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.values: Dict[tuple, float] = defaultdict(float)
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set the gauge value."""
        key = self._make_key(labels)
        self.values[key] = value
    
    def inc(self, amount: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the gauge."""
        key = self._make_key(labels)
        self.values[key] += amount
    
    def dec(self, amount: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement the gauge."""
        key = self._make_key(labels)
        self.values[key] -= amount
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        key = self._make_key(labels)
        return self.values[key]
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> tuple:
        """Create a hashable key from labels."""
        if not labels:
            return ()
        return tuple(sorted(labels.items()))
    
    def collect(self) -> List[MetricPoint]:
        """Collect all gauge values."""
        points = []
        for label_key, value in self.values.items():
            labels = dict(label_key) if label_key else {}
            points.append(MetricPoint(self.name, value, labels))
        return points


class MetricsCollector:
    """
    Collects and manages Prometheus metrics.
    
    Provides:
    - Operation counters and latencies
    - Error tracking
    - Custom business metrics
    - Metrics export
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {}
        self._init_default_metrics()
    
    def _init_default_metrics(self) -> None:
        """Initialize default metrics."""
        # Operation metrics
        self.canvas_operations_total = Counter(
            'canvas_operations_total',
            'Total canvas operations',
            ['operation', 'status'],
        )
        self.canvas_errors_total = Counter(
            'canvas_errors_total',
            'Total canvas errors',
            ['operation', 'error_type'],
        )
        
        # Latency metrics
        self.operation_latency_seconds = Histogram(
            'operation_latency_seconds',
            'Operation latency in seconds',
            labels=['operation'],
        )
        
        # Canvas metrics
        self.canvas_nodes_count = Histogram(
            'canvas_nodes_count',
            'Number of nodes in canvas',
        )
        self.canvas_edges_count = Histogram(
            'canvas_edges_count',
            'Number of edges in canvas',
        )
        
        # Access control metrics
        self.permission_checks_total = Counter(
            'permission_checks_total',
            'Total permission checks',
            ['result'],
        )
        
        # Audit metrics
        self.audit_entries_total = Counter(
            'audit_entries_total',
            'Total audit entries',
            ['operation', 'status'],
        )
    
    def record_operation(
        self,
        operation: str,
        status: str,
        duration: float,
    ) -> None:
        """
        Record an operation execution.
        
        Args:
            operation: Operation name
            status: Operation status (success, failure, etc.)
            duration: Duration in seconds
        """
        self.canvas_operations_total.inc(
            labels={'operation': operation, 'status': status}
        )
        self.operation_latency_seconds.observe(duration, {'operation': operation})
    
    def record_error(
        self,
        operation: str,
        error_type: str,
    ) -> None:
        """Record an error."""
        self.canvas_errors_total.inc(
            labels={'operation': operation, 'error_type': error_type}
        )
    
    def record_canvas_size(self, node_count: int, edge_count: int) -> None:
        """Record canvas node and edge counts."""
        self.canvas_nodes_count.observe(float(node_count))
        self.canvas_edges_count.observe(float(edge_count))
    
    def record_permission_check(self, allowed: bool) -> None:
        """Record a permission check."""
        result = 'allowed' if allowed else 'denied'
        self.permission_checks_total.inc(labels={'result': result})
    
    def record_audit_entry(self, operation: str, status: str) -> None:
        """Record an audit entry."""
        self.audit_entries_total.inc(
            labels={'operation': operation, 'status': status}
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dictionary."""
        return {
            'canvas_operations': self.canvas_operations_total.values.copy(),
            'canvas_errors': self.canvas_errors_total.values.copy(),
            'operation_latencies': self.operation_latency_seconds.values.copy(),
            'canvas_nodes': self.canvas_nodes_count.values.copy(),
            'canvas_edges': self.canvas_edges_count.values.copy(),
            'permission_checks': self.permission_checks_total.values.copy(),
            'audit_entries': self.audit_entries_total.values.copy(),
        }
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus exposition format."""
        lines = []
        
        # Add type and help comments
        lines.append('# HELP canvas_operations_total Total canvas operations')
        lines.append('# TYPE canvas_operations_total counter')
        for point in self.canvas_operations_total.collect():
            lines.append(point.to_prometheus_format())
        
        lines.append('# HELP operation_latency_seconds Operation latency in seconds')
        lines.append('# TYPE operation_latency_seconds histogram')
        for point in self.operation_latency_seconds.collect():
            lines.append(point.to_prometheus_format())
        
        lines.append('# HELP canvas_nodes_count Number of nodes in canvas')
        lines.append('# TYPE canvas_nodes_count histogram')
        for point in self.canvas_nodes_count.collect():
            lines.append(point.to_prometheus_format())
        
        return '\n'.join(lines)
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._init_default_metrics()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def initialize_metrics() -> MetricsCollector:
    """Initialize global metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector."""
    return _metrics_collector


def record_operation_metric(
    operation: str,
    status: str,
    duration: float,
) -> None:
    """Record operation metric."""
    collector = get_metrics_collector()
    if collector:
        collector.record_operation(operation, status, duration)


def record_error_metric(operation: str, error_type: str) -> None:
    """Record error metric."""
    collector = get_metrics_collector()
    if collector:
        collector.record_error(operation, error_type)
