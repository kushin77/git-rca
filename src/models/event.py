"""
Event Model - Phase 3a

Defines the Event schema that links multiple signal sources (git, CI, logs, metrics, traces)
to investigations. Supports enterprise-scale RCA with rich event metadata.

Attributes:
    id (str): Unique event identifier (UUID)
    timestamp (str): When the event occurred (ISO timestamp)
    source (str): Event source: 'git', 'ci', 'logs', 'metrics', 'traces', 'manual'
    event_type (str): Type of event (e.g., 'commit', 'build_failure', 'error_spike')
    severity (str): Severity level: 'critical', 'high', 'medium', 'low', 'info'
    data (dict): Source-specific payload (JSON)
    tags (List[str]): Searchable tags
    investigation_ids (List[str]): Links to investigations
    source_id (str): External ID (e.g., commit hash, build ID)
    parsed_at (str): When we parsed the event (ISO timestamp)
    linked_at (str): When linked to investigation (ISO timestamp)
    metadata (dict): Additional context
    deleted_at (str): Soft delete timestamp (null if active)
    created_at (str): When event record was created (ISO timestamp)
"""

from datetime import datetime
from typing import Optional, List, Any
from enum import Enum
import uuid as uuid_lib


class EventSource(str, Enum):
    """Event source enumeration."""

    GIT = "git"
    CI = "ci"
    LOGS = "logs"
    METRICS = "metrics"
    TRACES = "traces"
    MANUAL = "manual"


class EventSeverity(str, Enum):
    """Event severity enumeration."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Event:
    """Event domain model supporting multiple signal sources."""

    def __init__(
        self,
        timestamp: str,
        source: str,
        event_type: str,
        severity: str = EventSeverity.MEDIUM,
        data: Optional[dict] = None,
        tags: Optional[List[str]] = None,
        investigation_ids: Optional[List[str]] = None,
        source_id: Optional[str] = None,
        parsed_at: Optional[str] = None,
        linked_at: Optional[str] = None,
        metadata: Optional[dict] = None,
        id: Optional[str] = None,
        created_at: Optional[str] = None,
        deleted_at: Optional[str] = None,
    ):
        """Initialize an Event.

        Args:
            timestamp: ISO timestamp of when event occurred
            source: Event source (git, ci, logs, metrics, traces, manual)
            event_type: Type of event
            severity: Event severity (critical, high, medium, low, info)
            data: Source-specific payload
            tags: Searchable tags
            investigation_ids: Linked investigation IDs
            source_id: External ID (commit hash, build ID, etc.)
            parsed_at: When we parsed the event
            linked_at: When linked to investigation
            metadata: Additional context
            id: Event ID (auto-generated if None)
            created_at: When event record created (auto-set if None)
            deleted_at: Soft delete timestamp (null if active)
        """
        self.id = id or str(uuid_lib.uuid4())
        self.timestamp = timestamp
        self.source = source  # Validate in store
        self.event_type = event_type
        self.severity = severity  # Validate in store
        self.data = data or {}
        self.tags = tags or []
        self.investigation_ids = investigation_ids or []
        self.source_id = source_id
        self.parsed_at = parsed_at or datetime.utcnow().isoformat()
        self.linked_at = linked_at
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.deleted_at = deleted_at

    def is_active(self) -> bool:
        """Check if event is active (not soft-deleted).

        Returns:
            True if event is active, False if soft-deleted
        """
        return self.deleted_at is None

    def link_to_investigation(self, investigation_id: str) -> None:
        """Link this event to an investigation.

        Args:
            investigation_id: Investigation ID to link
        """
        if investigation_id not in self.investigation_ids:
            self.investigation_ids.append(investigation_id)
        self.linked_at = datetime.utcnow().isoformat()

    def unlink_from_investigation(self, investigation_id: str) -> None:
        """Unlink this event from an investigation.

        Args:
            investigation_id: Investigation ID to unlink
        """
        if investigation_id in self.investigation_ids:
            self.investigation_ids.remove(investigation_id)

    def add_tag(self, tag: str) -> None:
        """Add a tag to this event.

        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this event.

        Args:
            tag: Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)

    def soft_delete(self) -> None:
        """Soft-delete this event."""
        self.deleted_at = datetime.utcnow().isoformat()

    def restore(self) -> None:
        """Restore a soft-deleted event."""
        self.deleted_at = None

    def to_dict(self) -> dict:
        """Convert event to dictionary.

        Returns:
            Dictionary representation of event
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "source": self.source,
            "event_type": self.event_type,
            "severity": self.severity,
            "data": self.data,
            "tags": self.tags,
            "investigation_ids": self.investigation_ids,
            "source_id": self.source_id,
            "parsed_at": self.parsed_at,
            "linked_at": self.linked_at,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "deleted_at": self.deleted_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Event":
        """Create Event from dictionary.

        Args:
            data: Dictionary with event fields

        Returns:
            Event instance
        """
        return Event(
            **{
                k: v
                for k, v in data.items()
                if k
                in [
                    "id",
                    "timestamp",
                    "source",
                    "event_type",
                    "severity",
                    "data",
                    "tags",
                    "investigation_ids",
                    "source_id",
                    "parsed_at",
                    "linked_at",
                    "metadata",
                    "created_at",
                    "deleted_at",
                ]
            }
        )

    def __repr__(self) -> str:
        """String representation."""
        return f"Event(id={self.id}, source={self.source}, type={self.event_type}, severity={self.severity})"


class EventStore:
    """Store for managing events"""

    def __init__(self):
        self.events: dict = {}

    def add(self, event: Event) -> None:
        """Add event to store"""
        self.events[event.id] = event

    def get(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self.events.get(event_id)

    def get_all(self) -> List[Event]:
        """Get all active events"""
        return [e for e in self.events.values() if e.is_active()]

    def delete(self, event_id: str) -> None:
        """Soft-delete an event"""
        if event_id in self.events:
            self.events[event_id].soft_delete()

    def update(self, event: Event) -> None:
        """Update event in store"""
        self.events[event.id] = event

    def count(self) -> int:
        """Count active events"""
        return len(self.get_all())


class EventLinkerResult:
    """Result of linking an event to investigations."""

    def __init__(
        self,
        event_id: str,
        investigation_ids: List[str],
        confidence_scores: dict,  # investigation_id -> score (0-1)
        linking_strategy: str,  # 'timestamp', 'component', 'tags', etc.
    ):
        """Initialize an EventLinkerResult.

        Args:
            event_id: Event that was linked
            investigation_ids: Linked investigation IDs
            confidence_scores: Mapping of investigation_id to confidence (0-1)
            linking_strategy: Which strategy was used for linking
        """
        self.event_id = event_id
        self.investigation_ids = investigation_ids
        self.confidence_scores = confidence_scores
        self.linking_strategy = linking_strategy
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "investigation_ids": self.investigation_ids,
            "confidence_scores": self.confidence_scores,
            "linking_strategy": self.linking_strategy,
            "created_at": self.created_at,
        }
