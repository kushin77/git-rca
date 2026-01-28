"""
Tests for Audit Logging Service
================================

Comprehensive test suite for audit logging, including:
- Audit entry creation and retrieval
- Filtering and searching
- User activity tracking
- Security event detection
- Audit statistics
"""

import pytest
from datetime import datetime, timedelta
from src.services.audit_logger import (
    AuditLogger,
    AuditEntry,
    OperationType,
    OperationStatus,
    ResourceType,
)


@pytest.fixture
def audit_logger():
    """Create a fresh audit logger for each test."""
    return AuditLogger()


class TestAuditEntry:
    """Tests for AuditEntry data class."""

    def test_audit_entry_creation(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            entry_id="entry-1",
            timestamp=datetime.utcnow(),
            user_id="user-123",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-456",
            status=OperationStatus.SUCCESS,
            details={"name": "Test Canvas"},
        )

        assert entry.entry_id == "entry-1"
        assert entry.user_id == "user-123"
        assert entry.operation_type == OperationType.CREATE
        assert entry.status == OperationStatus.SUCCESS

    def test_audit_entry_to_dict(self):
        """Test converting audit entry to dict."""
        entry = AuditEntry(
            entry_id="entry-1",
            timestamp=datetime(2026, 1, 28, 12, 0, 0),
            user_id="user-123",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-456",
            status=OperationStatus.SUCCESS,
            details={"name": "Test"},
        )

        data = entry.to_dict()

        assert data["entry_id"] == "entry-1"
        assert data["user_id"] == "user-123"
        assert data["operation_type"] == "create"
        assert data["resource_type"] == "canvas"
        assert data["status"] == "success"
        assert isinstance(data["timestamp"], str)

    def test_audit_entry_from_dict(self):
        """Test creating audit entry from dict."""
        data = {
            "entry_id": "entry-1",
            "timestamp": "2026-01-28T12:00:00",
            "user_id": "user-123",
            "operation_type": "create",
            "resource_type": "canvas",
            "resource_id": "canvas-456",
            "status": "success",
            "details": {"name": "Test"},
        }

        entry = AuditEntry.from_dict(data)

        assert entry.entry_id == "entry-1"
        assert entry.user_id == "user-123"
        assert entry.operation_type == OperationType.CREATE
        assert isinstance(entry.timestamp, datetime)


class TestAuditLoggerBasic:
    """Basic audit logger tests."""

    def test_log_operation(self, audit_logger):
        """Test logging an operation."""
        entry = audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={"name": "Test Canvas"},
        )

        assert entry.entry_id is not None
        assert entry.user_id == "user-1"
        assert entry.operation_type == OperationType.CREATE
        assert entry.status == OperationStatus.SUCCESS

    def test_log_operation_with_error(self, audit_logger):
        """Test logging a failed operation."""
        entry = audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.DELETE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.FAILURE,
            details={"action": "delete"},
            error_message="Canvas not found",
        )

        assert entry.status == OperationStatus.FAILURE
        assert entry.error_message == "Canvas not found"

    def test_log_operation_with_changes(self, audit_logger):
        """Test logging operation with changes tracked."""
        changes = {
            "before": {"nodes": 5},
            "after": {"nodes": 6},
        }

        entry = audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.UPDATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={"action": "add_node"},
            changes=changes,
        )

        assert entry.changes == changes

    def test_audit_count(self, audit_logger):
        """Test audit entry count."""
        assert audit_logger.audit_count() == 0

        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )

        assert audit_logger.audit_count() == 1


class TestAuditLoggerRetrieval:
    """Tests for retrieving audit entries."""

    def test_get_audit_trail(self, audit_logger):
        """Test retrieving audit trail for a resource."""
        # Create multiple entries for the same resource
        for i in range(3):
            audit_logger.log_operation(
                user_id=f"user-{i}",
                operation_type=OperationType.UPDATE,
                resource_type=ResourceType.CANVAS,
                resource_id="canvas-1",
                status=OperationStatus.SUCCESS,
                details={"iteration": i},
            )

        trail = audit_logger.get_audit_trail("canvas-1")

        assert len(trail) == 3
        assert all(e.resource_id == "canvas-1" for e in trail)

    def test_get_user_activity(self, audit_logger):
        """Test retrieving activity for a user."""
        # Create entries from different users
        for i in range(3):
            audit_logger.log_operation(
                user_id="user-1" if i < 2 else "user-2",
                operation_type=OperationType.CREATE,
                resource_type=ResourceType.CANVAS,
                resource_id=f"canvas-{i}",
                status=OperationStatus.SUCCESS,
                details={},
            )

        activity = audit_logger.get_user_activity("user-1")

        assert len(activity) == 2
        assert all(e.user_id == "user-1" for e in activity)

    def test_get_user_activity_with_date_range(self, audit_logger):
        """Test retrieving user activity within date range."""
        now = datetime.utcnow()
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)

        # Log entry
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )

        # Should find with correct date range
        activity = audit_logger.get_user_activity(
            "user-1",
            start_date=past,
            end_date=future,
        )
        assert len(activity) == 1

        # Should not find with wrong date range
        activity = audit_logger.get_user_activity(
            "user-1",
            start_date=future,
            end_date=now + timedelta(days=2),
        )
        assert len(activity) == 0


class TestAuditLoggerSearch:
    """Tests for searching audit entries."""

    def test_search_operations_by_type(self, audit_logger):
        """Test searching by operation type."""
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.DELETE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-2",
            status=OperationStatus.SUCCESS,
            details={},
        )

        creates = audit_logger.search_operations(operation_type=OperationType.CREATE)

        assert len(creates) == 1
        assert creates[0].operation_type == OperationType.CREATE

    def test_search_operations_by_status(self, audit_logger):
        """Test searching by operation status."""
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.DELETE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-2",
            status=OperationStatus.FAILURE,
            details={},
        )

        failures = audit_logger.search_operations(status=OperationStatus.FAILURE)

        assert len(failures) == 1
        assert failures[0].status == OperationStatus.FAILURE

    def test_search_operations_multiple_filters(self, audit_logger):
        """Test searching with multiple filters."""
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-2",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.UPDATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )

        results = audit_logger.search_operations(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
        )

        assert len(results) == 1
        assert results[0].user_id == "user-1"
        assert results[0].operation_type == OperationType.CREATE


class TestAuditLoggerSecurity:
    """Tests for security-related audit features."""

    def test_get_failed_operations(self, audit_logger):
        """Test retrieving failed operations."""
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.DELETE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-2",
            status=OperationStatus.FAILURE,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.UPDATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-3",
            status=OperationStatus.DENIED,
            details={},
        )

        failures = audit_logger.get_failed_operations()

        assert len(failures) == 2
        assert all(
            e.status in [OperationStatus.FAILURE, OperationStatus.DENIED]
            for e in failures
        )

    def test_get_security_events(self, audit_logger):
        """Test retrieving security events."""
        audit_logger.log_operation(
            user_id="admin-1",
            operation_type=OperationType.ACCESS_GRANT,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={"granted_to": "user-1"},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-2",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="admin-1",
            operation_type=OperationType.DELETE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-2",
            status=OperationStatus.SUCCESS,
            details={},
        )

        security_events = audit_logger.get_security_events()

        assert len(security_events) == 2
        assert any(
            e.operation_type == OperationType.ACCESS_GRANT for e in security_events
        )
        assert any(e.operation_type == OperationType.DELETE for e in security_events)


class TestAuditLoggerStats:
    """Tests for audit statistics."""

    def test_get_stats(self, audit_logger):
        """Test getting audit statistics."""
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-1",
            operation_type=OperationType.UPDATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-1",
            status=OperationStatus.SUCCESS,
            details={},
        )
        audit_logger.log_operation(
            user_id="user-2",
            operation_type=OperationType.CREATE,
            resource_type=ResourceType.CANVAS,
            resource_id="canvas-2",
            status=OperationStatus.SUCCESS,
            details={},
        )

        stats = audit_logger.get_stats()

        assert stats["total_entries"] == 3
        assert "create" in stats["by_operation"]
        assert "update" in stats["by_operation"]
        assert stats["by_operation"]["create"] == 2
        assert stats["by_user"]["user-1"] == 2
        assert stats["by_user"]["user-2"] == 1
        assert stats["by_status"]["success"] == 3
        assert stats["date_range"]["earliest"] is not None
        assert stats["date_range"]["latest"] is not None
