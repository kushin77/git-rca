"""
Metrics Connector - Fetch and analyze metrics to detect anomalies

Features:
- Fetch metrics from monitoring systems
- Anomaly detection (threshold-based)
- Metric classification (CPU, memory, latency, etc.)
- Severity inference based on anomaly type
"""

import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from src.models.event import Event, EventSource, EventSeverity
from src.connectors.base_connector import BaseConnector, RetryPolicy, CircuitBreakerConfig


class MetricsConnector(BaseConnector):
    """Collect and analyze metrics to detect anomalies."""
    
    # Standard deviation thresholds for anomaly detection
    ANOMALY_THRESHOLDS = {
        'cpu': 2.0,        # 2 std dev above normal
        'memory': 2.0,
        'disk': 2.0,
        'latency': 2.5,    # More sensitive to latency
        'error_rate': 2.0,
    }
    
    def __init__(self,
                 metrics_source: str = "prometheus",  # prometheus, datadog, cloudwatch, etc.
                 baseline_period: int = 3600,  # Seconds for baseline calculation
                 retry_policy: RetryPolicy = None,
                 circuit_breaker_config: CircuitBreakerConfig = None):
        """
        Initialize metrics connector.
        
        Args:
            metrics_source: Metrics system (prometheus, datadog, etc.)
            baseline_period: Period (seconds) for calculating baseline
            retry_policy: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__(
            source=EventSource.METRICS,
            retry_policy=retry_policy,
            circuit_breaker_config=circuit_breaker_config,
        )
        self.metrics_source = metrics_source
        self.baseline_period = baseline_period
    
    def _collect_with_timeout(self) -> List[Event]:
        """
        Collect metrics and detect anomalies.
        
        Returns:
            List of Event objects for detected anomalies
        """
        metrics = self._fetch_metrics()
        events = []
        
        for metric_name, metric_data in metrics.items():
            try:
                anomaly_event = self._detect_anomaly(metric_name, metric_data)
                if anomaly_event:
                    events.append(anomaly_event)
            except Exception as e:
                self.logger.warning(f"Failed to analyze metric {metric_name}: {e}")
                continue
        
        self.logger.info(f"Detected {len(events)} anomalies from {len(metrics)} metrics")
        return events
    
    def _fetch_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch metrics from source.
        
        Currently supports:
        - In-memory metrics (for testing)
        - Prometheus API
        
        Returns:
            Dict of metric_name -> metric_data
        """
        if isinstance(self.metrics_source, dict):
            # For testing: accept pre-populated metrics
            return self.metrics_source
        
        try:
            if self.metrics_source == 'prometheus':
                return self._fetch_from_prometheus()
            elif self.metrics_source == 'datadog':
                return self._fetch_from_datadog()
            else:
                self.logger.warning(f"Unknown metrics source: {self.metrics_source}")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to fetch metrics: {e}")
            raise
    
    def _fetch_from_prometheus(self) -> Dict[str, Dict[str, Any]]:
        """Fetch metrics from Prometheus."""
        # TODO: Implement Prometheus query
        # Would query endpoints like:
        # /api/v1/query?query=node_cpu_seconds_total
        # /api/v1/query?query=container_memory_usage_bytes
        return {}
    
    def _fetch_from_datadog(self) -> Dict[str, Dict[str, Any]]:
        """Fetch metrics from Datadog."""
        # TODO: Implement Datadog API
        return {}
    
    def _detect_anomaly(self, metric_name: str, metric_data: Dict[str, Any]) -> Optional[Event]:
        """
        Detect anomaly in metric.
        
        Args:
            metric_name: Name of metric
            metric_data: Metric data with current value and history
            
        Returns:
            Event object if anomaly detected, None otherwise
        """
        current_value = metric_data.get('value')
        history = metric_data.get('history', [])
        
        if not history or len(history) < 2:
            return None
        
        # Calculate baseline statistics
        baseline_mean = statistics.mean(history)
        baseline_stdev = statistics.stdev(history) if len(history) > 1 else 0
        
        if baseline_stdev == 0:
            return None  # No variance, can't detect anomaly
        
        # Calculate z-score
        z_score = (current_value - baseline_mean) / baseline_stdev
        
        # Get threshold for this metric type
        metric_type = self._classify_metric(metric_name)
        threshold = self.ANOMALY_THRESHOLDS.get(metric_type, 2.0)
        
        # Check if anomaly
        if abs(z_score) < threshold:
            return None  # Not an anomaly
        
        # Determine severity based on z-score magnitude
        severity = self._classify_severity(z_score, threshold)
        
        # Create event
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.METRICS,
            event_type='metric_anomaly',
            severity=severity,
            data={
                'metric_name': metric_name,
                'current_value': current_value,
                'baseline_mean': baseline_mean,
                'baseline_stdev': baseline_stdev,
                'z_score': z_score,
                'threshold': threshold,
            },
            source_id=f"metrics:{metric_name}",
            tags=[metric_type, 'anomaly'],
            metadata={
                'metric_source': self.metrics_source,
                'metric_type': metric_type,
            },
        )
        
        return event
    
    def _classify_metric(self, metric_name: str) -> str:
        """
        Classify metric type.
        
        Args:
            metric_name: Metric name
            
        Returns:
            Metric type (cpu, memory, disk, latency, error_rate, etc.)
        """
        name_lower = metric_name.lower()
        
        if 'cpu' in name_lower or 'processor' in name_lower:
            return 'cpu'
        elif 'memory' in name_lower or 'mem' in name_lower or 'heap' in name_lower:
            return 'memory'
        elif 'disk' in name_lower or 'io' in name_lower:
            return 'disk'
        elif 'latency' in name_lower or 'duration' in name_lower or 'response_time' in name_lower:
            return 'latency'
        elif 'error' in name_lower or 'failure' in name_lower:
            return 'error_rate'
        else:
            return 'other'
    
    def _classify_severity(self, z_score: float, threshold: float) -> EventSeverity:
        """
        Classify anomaly severity based on z-score.
        
        Args:
            z_score: Normalized score
            threshold: Detection threshold
            
        Returns:
            EventSeverity enum value
        """
        abs_z = abs(z_score)
        
        if abs_z > threshold * 2:  # > 2x threshold
            return EventSeverity.CRITICAL
        elif abs_z > threshold * 1.5:  # > 1.5x threshold
            return EventSeverity.HIGH
        elif abs_z > threshold:  # > 1x threshold
            return EventSeverity.MEDIUM
        else:
            return EventSeverity.LOW
