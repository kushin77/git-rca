"""
Phase 3e Integration Tests
===========================

Comprehensive integration tests for all Phase 3e components working together:
- Part 1: Audit Logging & Access Control
- Part 2: OpenTelemetry Tracing  
- Part 3: Prometheus Metrics & Canvas Versioning
- Part 4: Event Streaming
"""

import pytest
from datetime import datetime
from src.services.audit_logger import AuditLogger, OperationType, OperationStatus, ResourceType
from src.services.access_control import AccessControl, Role, Permission
from src.observability.tracing import initialize_tracing, get_tracing_manager, trace_operation
from src.observability.metrics import MetricsCollector
from src.models.canvas_version import VersionStore, ChangeType
from src.services.event_stream import EventStream, EventType, CanvasChangeEvent


class TestPhase3eIntegration:
    """Integration tests for all Phase 3e components."""
    
    def test_audit_access_control_integration(self):
        """Test audit logging with access control."""
        audit_logger = AuditLogger()
        access_control = AccessControl()
        
        # Assign admin role to user-1
        access_control.assign_role("user-1", Role.ADMIN, "system")
        
        # Check permission
        has_permission = access_control.check_permission("user-1", Permission.CANVAS_CREATE)
        assert has_permission
        
        # Log the permission check
        audit_logger.log_operation(
            user_id="system",
            operation_type=OperationType.ACCESS_GRANT,
            resource_type=ResourceType.PERMISSION,
            resource_id="user-1",
            status=OperationStatus.SUCCESS,
            details={"granted_permission": "canvas:create"},
        )
        
        # Retrieve audit trail
        trail = audit_logger.get_audit_trail("user-1")
        assert len(trail) > 0
        assert trail[0].operation_type == OperationType.ACCESS_GRANT
    
    def test_tracing_with_metrics(self):
        """Test tracing initialization with metrics."""
        initialize_tracing("test-service")
        tracing_manager = get_tracing_manager()
        metrics = MetricsCollector()
        
        # Record an operation
        metrics.record_operation("test_operation", "success", 0.05)
        
        # Verify tracing manager was initialized
        assert tracing_manager is not None
        
        # Verify metrics recorded
        assert metrics.canvas_operations_total.get(
            labels={"operation": "test_operation", "status": "success"}
        ) == 1.0
    
    def test_metrics_with_versioning(self):
        """Test metrics recording with version tracking."""
        metrics = MetricsCollector()
        version_store = VersionStore()
        
        # Create versions
        for i in range(3):
            version = version_store.create_version(
                canvas_id="canvas-1",
                canvas_data={"version": i},
                changes=[],
                author="user-1",
                message=f"Version {i}",
            )
            metrics.record_operation("create_version", "success", 0.01 * (i + 1))
        
        # Verify metrics recorded
        assert metrics.canvas_operations_total.get(
            labels={"operation": "create_version", "status": "success"}
        ) == 3.0
        
        # Verify versions created
        versions = version_store.get_canvas_versions("canvas-1")
        assert len(versions) == 3
    
    def test_access_control_with_event_auditing(self):
        """Test access control changes with event auditing."""
        access_control = AccessControl()
        event_stream = EventStream()
        received_events = []
        
        # Subscribe to permission events
        event_stream.subscribe(
            handler=lambda e: received_events.append(e),
            event_types={EventType.PERMISSION_GRANTED, EventType.PERMISSION_REVOKED},
        )
        
        # Assign role
        access_control.assign_role("user-1", Role.ANALYST, "system")
        
        # Publish permission granted event
        event = CanvasChangeEvent(
            event_type=EventType.PERMISSION_GRANTED,
            user_id="system",
            data={"user_id": "user-1", "role": "analyst"},
        )
        event_stream.publish(event)
        
        # Revoke role
        access_control.revoke_role("user-1", Role.ANALYST, "system")
        
        # Publish permission revoked event
        event = CanvasChangeEvent(
            event_type=EventType.PERMISSION_REVOKED,
            user_id="system",
            data={"user_id": "user-1", "role": "analyst"},
        )
        event_stream.publish(event)
        
        assert len(received_events) == 2
        assert received_events[0].event_type == EventType.PERMISSION_GRANTED
        assert received_events[1].event_type == EventType.PERMISSION_REVOKED
    
    def test_full_pipeline_simplified(self):
        """Test simplified full pipeline with all components."""
        audit_logger = AuditLogger()
        access_control = AccessControl()
        metrics = MetricsCollector()
        version_store = VersionStore()
        event_stream = EventStream()
        
        # Setup
        access_control.assign_role("user-1", Role.ANALYST, "system")
        canvas_id = "canvas-1"
        user_id = "user-1"
        
        # Verify access
        assert access_control.check_permission(user_id, Permission.CANVAS_CREATE)
        
        # Record metrics
        metrics.record_operation("create_canvas", "success", 0.05)
        
        # Log operation
        audit_logger.log_operation(
            user_id=user_id,
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id=canvas_id,
            status=OperationStatus.SUCCESS,
            details={"name": "Test Canvas"},
        )
        
        # Publish event
        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id=canvas_id,
            user_id=user_id,
            data={"name": "Test Canvas"},
        )
        events = []
        event_stream.subscribe(
            handler=lambda e: events.append(e),
            canvas_id=canvas_id,
        )
        event_stream.publish(event)
        
        # Create version
        version = version_store.create_version(
            canvas_id=canvas_id,
            canvas_data={"nodes": 0},
            changes=[],
            author=user_id,
        )
        
        # Verify all
        assert metrics.canvas_operations_total.get(
            labels={"operation": "create_canvas", "status": "success"}
        ) == 1.0
        
        versions = version_store.get_canvas_versions(canvas_id)
        assert len(versions) == 1
        
        assert len(events) == 1
        assert events[0].event_type == EventType.CANVAS_CREATED
    
    def test_access_denied_tracking(self):
        """Test tracking of denied access attempts."""
        access_control = AccessControl()
        audit_logger = AuditLogger()
        metrics = MetricsCollector()
        event_stream = EventStream()
        
        denied_events = []
        event_stream.subscribe(
            handler=lambda e: denied_events.append(e),
            user_id="user-1",
        )
        
        # User with limited permissions
        access_control.assign_role("user-1", Role.VIEWER, "system")
        
        # Try to create canvas (should be denied)
        can_create = access_control.check_permission("user-1", Permission.CANVAS_CREATE)
        assert not can_create
        
        # Record denied operation
        metrics.record_error("create_canvas", "access_denied")
        
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.DENIED,
            details={"reason": "Insufficient permissions"},
        )
        
        # Publish denial event
        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
            data={"error": "access_denied"},
        )
        event_stream.publish(event)
        
        # Verify
        assert metrics.canvas_errors_total.get(
            labels={"operation": "create_canvas", "error_type": "access_denied"}
        ) == 1.0
        assert len(denied_events) == 1
    
    def test_version_rollback_with_events(self):
        """Test version rollback with event tracking."""
        version_store = VersionStore()
        event_stream = EventStream()
        
        rollback_events = []
        event_stream.subscribe(
            handler=lambda e: rollback_events.append(e),
            event_types={EventType.VERSION_ROLLBACK},
        )
        
        # Create versions
        v1 = version_store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": 1, "edges": 0},
            changes=[],
            author="user-1",
        )
        
        v2 = version_store.create_version(
            canvas_id="canvas-1",
            canvas_data={"nodes": 1, "edges": 1},
            changes=[],
            author="user-1",
        )
        
        # Perform rollback
        rolled_back = version_store.rollback("canvas-1", v1.version_id)
        
        assert rolled_back == {"nodes": 1, "edges": 0}
        
        # Publish rollback event
        event = CanvasChangeEvent(
            event_type=EventType.VERSION_ROLLBACK,
            canvas_id="canvas-1",
            user_id="user-1",
            data={"from_version": 2, "to_version": 1},
        )
        event_stream.publish(event)
        
        # Verify
        assert len(rollback_events) == 1
        assert rollback_events[0].event_type == EventType.VERSION_ROLLBACK


class TestPhase3eComponentsIsolation:
    """Tests ensuring components work in isolation."""
    
    def test_audit_logger_isolation(self):
        """Test audit logger works independently."""
        logger = AuditLogger()
        
        for i in range(5):
            logger.log_operation(
                user_id=f"user-{i}",
                operation_type=OperationType.CREATE,
                resource_type=ResourceType.CANVAS,
                resource_id=f"canvas-{i}",
                status=OperationStatus.SUCCESS,
                details={},
            )
        
        trail = logger.get_audit_trail("canvas-2")
        assert len(trail) == 1
        assert trail[0].user_id == "user-2"
    
    def test_metrics_collector_isolation(self):
        """Test metrics collector works independently."""
        metrics = MetricsCollector()
        
        for op in ["create", "read", "update", "delete"]:
            metrics.record_operation(op, "success", 0.1)
        
        assert metrics.canvas_operations_total.get(
            labels={"operation": "create", "status": "success"}
        ) == 1.0
    
    def test_event_stream_isolation(self):
        """Test event stream works independently."""
        stream = EventStream()
        events = []
        
        stream.subscribe(
            handler=lambda e: events.append(e),
            event_types={EventType.CANVAS_CREATED},
        )
        
        for i in range(5):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_CREATED,
                canvas_id=f"canvas-{i}",
                user_id="user-1",
            )
            stream.publish(event)
        
        assert len(events) == 5
    
    def test_version_store_isolation(self):
        """Test version store works independently."""
        store = VersionStore()
        
        for i in range(3):
            store.create_version(
                canvas_id="canvas-1",
                canvas_data={"version": i},
                changes=[],
                author="user-1",
            )
        
        versions = store.get_canvas_versions("canvas-1")
        assert len(versions) == 3
