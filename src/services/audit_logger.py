"""
Audit Logging Service for Enterprise-Grade Security
======================================================

Provides comprehensive audit trail tracking for all operations,
user activities, and security-relevant events.

Key Responsibilities:
- Log all canvas operations (CRUD, analysis)
- Track user identity and authorization context
- Record operation details and state changes
- Provide immutable audit trail storage
- Enable security reviews and compliance reporting
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4
import json


class OperationType(str, Enum):
    """Types of operations that are audited."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    EXPORT = "export"
    ACCESS_GRANT = "access_grant"
    ACCESS_REVOKE = "access_revoke"
    VERSION_CREATE = "version_create"
    ROLLBACK = "rollback"


class OperationStatus(str, Enum):
    """Status of audited operations."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    PARTIAL = "partial"


class ResourceType(str, Enum):
    """Types of resources that can be audited."""

    CANVAS = "canvas"
    NODE = "node"
    EDGE = "edge"
    INVESTIGATION = "investigation"
    VERSION = "version"
    USER = "user"
    PERMISSION = "permission"


@dataclass
class AuditEntry:
    """Immutable record of a single audited operation."""

    entry_id: str  # Unique identifier for this audit entry
    timestamp: datetime  # When the operation occurred
    user_id: str  # Who performed the operation
    operation_type: OperationType  # What operation was performed
    resource_type: ResourceType  # What type of resource
    resource_id: str  # Which specific resource
    status: OperationStatus  # Did it succeed?
    details: Dict[str, Any]  # Operation-specific details
    changes: Optional[Dict[str, Any]] = None  # What changed (before/after)
    error_message: Optional[str] = None  # Error message if failed
    ip_address: Optional[str] = None  # Source IP (for security)
    user_agent: Optional[str] = None  # User agent (for tracking)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["operation_type"] = self.operation_type.value
        data["resource_type"] = self.resource_type.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Create from dictionary for retrieval/deserialization."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["operation_type"] = OperationType(data["operation_type"])
        data["resource_type"] = ResourceType(data["resource_type"])
        data["status"] = OperationStatus(data["status"])
        return cls(**data)


class AuditLogger:
    """
    Centralized audit logging for all operations.

    Tracks:
    - Who did what, when, and where
    - Success/failure of operations
    - Changes made to resources
    - Access control decisions
    - Security-relevant events
    """

    def __init__(self, store=None):
        """
        Initialize the audit logger.

        Args:
            store: Backend store for persisting audit entries
                   (defaults to in-memory store)
        """
        self.store = store or InMemoryAuditStore()
        self._entry_count = 0

    def log_operation(
        self,
        user_id: str,
        operation_type: OperationType,
        resource_type: ResourceType,
        resource_id: str,
        status: OperationStatus,
        details: Dict[str, Any],
        changes: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log a single operation.

        Args:
            user_id: User performing the operation
            operation_type: Type of operation (CREATE, UPDATE, etc.)
            resource_type: Type of resource affected
            resource_id: ID of the specific resource
            status: Whether operation succeeded
            details: Operation-specific details
            changes: Before/after changes if applicable
            error_message: Error message if operation failed
            ip_address: Source IP address
            user_agent: Source user agent

        Returns:
            AuditEntry: The created audit entry
        """
        entry = AuditEntry(
            entry_id=str(uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            details=details,
            changes=changes,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.store.add(entry)
        self._entry_count += 1
        return entry

    def get_audit_trail(self, resource_id: str) -> List[AuditEntry]:
        """
        Get all audit entries for a specific resource.

        Args:
            resource_id: The resource to get audit trail for

        Returns:
            List of AuditEntry objects in chronological order
        """
        return self.store.get_by_resource(resource_id)

    def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditEntry]:
        """
        Get all operations performed by a specific user.

        Args:
            user_id: The user to get activity for
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            List of AuditEntry objects in chronological order
        """
        entries = self.store.get_by_user(user_id)

        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]

        return entries

    def search_operations(
        self,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        resource_type: Optional[ResourceType] = None,
        status: Optional[OperationStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditEntry]:
        """
        Search audit entries with multiple filters.

        Args:
            user_id: Filter by user
            resource_id: Filter by resource
            operation_type: Filter by operation type
            resource_type: Filter by resource type
            status: Filter by status
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of matching AuditEntry objects
        """
        entries = self.store.get_all()

        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        if resource_id:
            entries = [e for e in entries if e.resource_id == resource_id]
        if operation_type:
            entries = [e for e in entries if e.operation_type == operation_type]
        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]
        if status:
            entries = [e for e in entries if e.status == status]
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]

        return entries

    def get_failed_operations(self) -> List[AuditEntry]:
        """Get all failed and denied operations."""
        return self.store.get_by_status(
            [
                OperationStatus.FAILURE,
                OperationStatus.DENIED,
            ]
        )

    def get_security_events(self) -> List[AuditEntry]:
        """Get all security-relevant events (access changes, etc.)."""
        return self.store.get_by_operation(
            [
                OperationType.ACCESS_GRANT,
                OperationType.ACCESS_REVOKE,
                OperationType.DELETE,
            ]
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        entries = self.store.get_all()

        operation_counts = {}
        user_counts = {}
        status_counts = {}

        for entry in entries:
            op_type = entry.operation_type.value
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1

            user_counts[entry.user_id] = user_counts.get(entry.user_id, 0) + 1

            status = entry.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_entries": len(entries),
            "by_operation": operation_counts,
            "by_user": user_counts,
            "by_status": status_counts,
            "date_range": {
                "earliest": entries[0].timestamp.isoformat() if entries else None,
                "latest": entries[-1].timestamp.isoformat() if entries else None,
            },
        }

    def audit_count(self) -> int:
        """Get total number of audit entries."""
        return self._entry_count


class InMemoryAuditStore:
    """In-memory store for audit entries (suitable for development/testing)."""

    def __init__(self):
        self.entries: Dict[str, AuditEntry] = {}
        self.by_resource: Dict[str, List[str]] = {}  # resource_id -> [entry_ids]
        self.by_user: Dict[str, List[str]] = {}  # user_id -> [entry_ids]

    def add(self, entry: AuditEntry) -> None:
        """Add an audit entry."""
        self.entries[entry.entry_id] = entry

        # Index by resource
        if entry.resource_id not in self.by_resource:
            self.by_resource[entry.resource_id] = []
        self.by_resource[entry.resource_id].append(entry.entry_id)

        # Index by user
        if entry.user_id not in self.by_user:
            self.by_user[entry.user_id] = []
        self.by_user[entry.user_id].append(entry.entry_id)

    def get(self, entry_id: str) -> Optional[AuditEntry]:
        """Get a specific audit entry."""
        return self.entries.get(entry_id)

    def get_all(self) -> List[AuditEntry]:
        """Get all audit entries, sorted by timestamp."""
        entries = list(self.entries.values())
        entries.sort(key=lambda e: e.timestamp)
        return entries

    def get_by_resource(self, resource_id: str) -> List[AuditEntry]:
        """Get all entries for a resource."""
        entry_ids = self.by_resource.get(resource_id, [])
        entries = [self.entries[eid] for eid in entry_ids]
        entries.sort(key=lambda e: e.timestamp)
        return entries

    def get_by_user(self, user_id: str) -> List[AuditEntry]:
        """Get all entries for a user."""
        entry_ids = self.by_user.get(user_id, [])
        entries = [self.entries[eid] for eid in entry_ids]
        entries.sort(key=lambda e: e.timestamp)
        return entries

    def get_by_status(self, statuses: List[OperationStatus]) -> List[AuditEntry]:
        """Get all entries with specific statuses."""
        entries = [e for e in self.entries.values() if e.status in statuses]
        entries.sort(key=lambda e: e.timestamp)
        return entries

    def get_by_operation(self, operations: List[OperationType]) -> List[AuditEntry]:
        """Get all entries with specific operation types."""
        entries = [e for e in self.entries.values() if e.operation_type in operations]
        entries.sort(key=lambda e: e.timestamp)
        return entries

    def count(self) -> int:
        """Get total number of entries."""
        return len(self.entries)
