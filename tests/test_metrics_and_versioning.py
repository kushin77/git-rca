"""
Tests for Metrics and Canvas Versioning
========================================

Comprehensive test suite for Prometheus metrics collection
and canvas version management.
"""

import pytest
from datetime import datetime
from src.observability.metrics import (
    Counter,
    Histogram,
    Gauge,
    MetricsCollector,
    initialize_metrics,
    get_metrics_collector,
)
from src.models.canvas_version import (
    CanvasVersion,
    VersionStore,
    Change,
    ChangeType,
)


# ============================================================================
# METRICS TESTS
# ============================================================================

class TestCounter:
    """Tests for Counter metric."""
    
    def test_counter_creation(self):
        """Test creating a counter."""
        counter = Counter("test_counter", "Test counter")
        assert counter.name == "test_counter"
        assert counter.get() == 0.0
    
    def test_counter_increment(self):
        """Test incrementing counter."""
        counter = Counter("test_counter", "Test counter")
        counter.inc()
        assert counter.get() == 1.0
        counter.inc(5)
        assert counter.get() == 6.0
    
    def test_counter_with_labels(self):
        """Test counter with labels."""
        counter = Counter("test_counter", "Test counter", ["status"])
        counter.inc(labels={"status": "success"})
        counter.inc(labels={"status": "failure"})
        
        assert counter.get(labels={"status": "success"}) == 1.0
        assert counter.get(labels={"status": "failure"}) == 1.0


class TestHistogram:
    """Tests for Histogram metric."""
    
    def test_histogram_creation(self):
        """Test creating a histogram."""
        hist = Histogram("test_hist", "Test histogram")
        assert hist.name == "test_hist"
        assert hist.get_count() == 0
    
    def test_histogram_observe(self):
        """Test observing values."""
        hist = Histogram("test_hist", "Test histogram")
        hist.observe(0.5)
        hist.observe(1.5)
        hist.observe(2.5)
        
        assert hist.get_count() == 3
        assert hist.get_sum() == 4.5
        assert hist.get_average() == 1.5
    
    def test_histogram_percentiles(self):
        """Test percentile calculations."""
        hist = Histogram("test_hist", "Test histogram")
        for i in range(1, 101):
            hist.observe(float(i))
        
        assert hist.get_percentile(50) > 0
        assert hist.get_percentile(90) > hist.get_percentile(50)
    
    def test_histogram_with_labels(self):
        """Test histogram with labels."""
        hist = Histogram("test_hist", "Test histogram", labels=["operation"])
        hist.observe(0.1, labels={"operation": "read"})
        hist.observe(0.2, labels={"operation": "read"})
        hist.observe(0.5, labels={"operation": "write"})
        
        assert hist.get_count(labels={"operation": "read"}) == 2
        assert hist.get_count(labels={"operation": "write"}) == 1


class TestGauge:
    """Tests for Gauge metric."""
    
    def test_gauge_creation(self):
        """Test creating a gauge."""
        gauge = Gauge("test_gauge", "Test gauge")
        assert gauge.get() == 0.0
    
    def test_gauge_set(self):
        """Test setting gauge value."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(42.0)
        assert gauge.get() == 42.0
    
    def test_gauge_increment_decrement(self):
        """Test incrementing and decrementing."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10.0)
        gauge.inc(5)
        assert gauge.get() == 15.0
        gauge.dec(3)
        assert gauge.get() == 12.0


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    def test_collector_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector()
        assert collector.canvas_operations_total is not None
        assert collector.operation_latency_seconds is not None
    
    def test_record_operation(self):
        """Test recording operation metric."""
        collector = MetricsCollector()
        collector.record_operation("create_canvas", "success", 0.123)
        
        assert collector.canvas_operations_total.get(
            labels={"operation": "create_canvas", "status": "success"}
        ) == 1.0
    
    def test_record_error(self):
        """Test recording error metric."""
        collector = MetricsCollector()
        collector.record_error("create_canvas", "validation_error")
        
        assert collector.canvas_errors_total.get(
            labels={"operation": "create_canvas", "error_type": "validation_error"}
        ) == 1.0
    
    def test_record_canvas_size(self):
        """Test recording canvas size metrics."""
        collector = MetricsCollector()
        collector.record_canvas_size(10, 5)
        
        assert collector.canvas_nodes_count.get_count() == 1
        assert collector.canvas_edges_count.get_count() == 1
    
    def test_export_prometheus_format(self):
        """Test exporting metrics in Prometheus format."""
        collector = MetricsCollector()
        collector.record_operation("test", "success", 0.1)
        
        export = collector.export_prometheus_format()
        
        assert "canvas_operations_total" in export
        assert "# TYPE" in export
        assert "# HELP" in export
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()
        collector.record_operation("test", "success", 0.1)
        
        # Check that the metric was recorded (with labels)
        assert collector.canvas_operations_total.get(
            labels={"operation": "test", "status": "success"}
        ) == 1.0
        
        collector.reset()
        
        # After reset, should be back to 0
        assert collector.canvas_operations_total.get(
            labels={"operation": "test", "status": "success"}
        ) == 0.0


# ============================================================================
# CANVAS VERSIONING TESTS
# ============================================================================

class TestChange:
    """Tests for Change class."""
    
    def test_change_creation(self):
        """Test creating a change."""
        change = Change(
            change_type=ChangeType.NODE_ADDED,
            details={"node_id": "n1", "name": "Node 1"},
        )
        
        assert change.change_type == ChangeType.NODE_ADDED
        assert change.details["node_id"] == "n1"
    
    def test_change_to_dict(self):
        """Test converting change to dictionary."""
        change = Change(
            change_type=ChangeType.EDGE_ADDED,
            details={"edge_id": "e1"},
        )
        
        data = change.to_dict()
        
        assert data["change_type"] == "edge_added"
        assert "timestamp" in data


class TestCanvasVersion:
    """Tests for CanvasVersion class."""
    
    def test_version_creation(self):
        """Test creating a version."""
        version = CanvasVersion(
            version_id="v1",
            canvas_id="canvas-1",
            version_number=1,
            previous_version_id=None,
            data={"nodes": [], "edges": []},
            changes=[],
            author="user-1",
            message="Initial version",
        )
        
        assert version.version_id == "v1"
        assert version.version_number == 1
        assert version.author == "user-1"
    
    def test_version_to_dict(self):
        """Test converting version to dictionary."""
        version = CanvasVersion(
            version_id="v1",
            canvas_id="canvas-1",
            version_number=1,
            previous_version_id=None,
            data={"nodes": []},
            changes=[],
            author="user-1",
        )
        
        data = version.to_dict()
        
        assert data["version_id"] == "v1"
        assert data["canvas_id"] == "canvas-1"
        assert "timestamp" in data
    
    def test_version_from_dict(self):
        """Test creating version from dictionary."""
        data = {
            "version_id": "v1",
            "canvas_id": "canvas-1",
            "version_number": 1,
            "previous_version_id": None,
            "data": {},
            "changes": [],
            "author": "user-1",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Test",
        }
        
        version = CanvasVersion.from_dict(data)
        
        assert version.version_id == "v1"
        assert isinstance(version.timestamp, datetime)


class TestVersionStore:
    """Tests for VersionStore."""
    
    def test_store_initialization(self):
        """Test initializing version store."""
        store = VersionStore()
        assert len(store.versions) == 0
        assert len(store.canvas_versions) == 0
    
    def test_create_version(self):
        """Test creating a version."""
        store = VersionStore()
        
        version = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": [], "edges": []},
            changes=[],
            author="user-1",
            message="Initial version",
        )
        
        assert version.version_number == 1
        assert version.canvas_id == "canvas-1"
        assert version.author == "user-1"
    
    def test_create_multiple_versions(self):
        """Test creating multiple versions."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": 1},
            changes=[],
            author="user-1",
        )
        v2 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": 2},
            changes=[],
            author="user-1",
        )
        
        assert v1.version_number == 1
        assert v2.version_number == 2
        assert v2.previous_version_id == v1.version_id
    
    def test_get_version(self):
        """Test retrieving a version."""
        store = VersionStore()
        
        version = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": []},
            changes=[],
            author="user-1",
        )
        
        retrieved = store.get_version(version.version_id)
        
        assert retrieved == version
    
    def test_get_canvas_versions(self):
        """Test getting all versions of a canvas."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={},
            changes=[],
            author="user-1",
        )
        v2 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={},
            changes=[],
            author="user-1",
        )
        
        versions = store.get_canvas_versions("canvas-1")
        
        assert len(versions) == 2
        assert v1 in versions
        assert v2 in versions
    
    def test_get_latest_version(self):
        """Test getting latest version."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"version": 1},
            changes=[],
            author="user-1",
        )
        v2 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"version": 2},
            changes=[],
            author="user-1",
        )
        
        latest = store.get_latest_version("canvas-1")
        
        assert latest == v2
    
    def test_get_version_by_number(self):
        """Test getting version by number."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={},
            changes=[],
            author="user-1",
        )
        
        retrieved = store.get_version_by_number("canvas-1", 1)
        
        assert retrieved == v1
    
    def test_rollback(self):
        """Test rolling back to a version."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"value": 1},
            changes=[],
            author="user-1",
        )
        v2 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"value": 2},
            changes=[],
            author="user-1",
        )
        
        rolled_back = store.rollback("canvas-1", v1.version_id)
        
        assert rolled_back == {"value": 1}
    
    def test_get_version_diff(self):
        """Test comparing two versions."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": 1},
            changes=[],
            author="user-1",
        )
        
        change = Change(
            change_type=ChangeType.NODE_ADDED,
            details={"node_id": "n1"},
        )
        v2 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": 2},
            changes=[change],
            author="user-1",
        )
        
        diff = store.get_version_diff(v1.version_id, v2.version_id)
        
        assert diff["version1_number"] == 1
        assert diff["version2_number"] == 2
        assert len(diff["changes"]) == 1
    
    def test_get_version_history(self):
        """Test getting version history."""
        store = VersionStore()
        
        for i in range(5):
            store.create_version(
                canvas_id="canvas-1",
                canvas_data={"version": i},
                changes=[],
                author="user-1",
                message=f"Version {i}",
            )
        
        history = store.get_version_history("canvas-1", limit=3)
        
        assert len(history) == 3
        # Should be in reverse order (latest first)
        assert history[0]["version_number"] == 5
        assert history[-1]["version_number"] == 3
    
    def test_get_version_count(self):
        """Test getting version count."""
        store = VersionStore()
        
        for _ in range(3):
            store.create_version(
                canvas_id="canvas-1",
                canvas_data={},
                changes=[],
                author="user-1",
            )
        
        count = store.get_version_count("canvas-1")
        
        assert count == 3
    
    def test_compare_with_latest(self):
        """Test comparing version with latest."""
        store = VersionStore()
        
        v1 = store.create_version(
            canvas_id="canvas-1",
            canvas_data={},
            changes=[],
            author="user-1",
        )
        
        for _ in range(3):
            store.create_version(
                canvas_id="canvas-1",
                canvas_data={},
                changes=[],
                author="user-1",
            )
        
        comparison = store.compare_with_latest("canvas-1", v1.version_id)
        
        assert comparison["comparing_number"] == 1
        assert comparison["latest_number"] == 4
        assert comparison["versions_ahead"] == 3
