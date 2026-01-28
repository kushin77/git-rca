"""
Investigation Model - Phase 3a Expanded

Defines the data structure for investigations using comprehensive field set.
An investigation represents a root cause analysis session tracking an incident.

Attributes (Phase 3a Expanded):
    id (str): Unique investigation identifier (UUID)
    title (str): Investigation title/incident summary
    description (str): Detailed incident description
    status (str): Status: 'open', 'in_progress', 'resolved', 'closed'
    impact_severity (str): Impact: 'critical', 'high', 'medium', 'low'

    Timeline:
    detected_at (str): When incident was detected (ISO timestamp)
    started_at (str): When investigation started (ISO timestamp)
    resolved_at (str): When incident was resolved (optional, ISO timestamp)

    Analysis:
    root_cause (str): Identified root cause (optional, 2000 char limit)
    remediation (str): Fix implementation plan (optional, 2000 char limit)
    lessons_learned (str): Lessons learned (optional, 2000 char limit)

    Component Tracking:
    component_affected (str): Affected component/service name
    service_affected (str): Affected service (e.g., 'production', 'staging')

    Relationships:
    tags (List[str]): Searchable tags
    event_ids (List[str]): Linked event IDs
    related_investigation_ids (List[str]): Related investigations

    Ownership:
    created_by (str): User ID who created investigation
    assigned_to (str): User ID investigation is assigned to (optional)
    priority (str): 'p0', 'p1', 'p2', 'p3'

    Timestamps:
    created_at (str): When investigation record created (ISO timestamp)
    updated_at (str): When investigation last updated (ISO timestamp)
    deleted_at (str): When soft-deleted (null if active, ISO timestamp)
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid as uuid_lib


class InvestigationStatus(str, Enum):
    """Investigation status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ImpactSeverity(str, Enum):
    """Impact severity enumeration."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Priority(str, Enum):
    """Priority enumeration."""

    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class Investigation:
    """Investigation domain model (Phase 3a - Expanded)."""

    def __init__(
        self,
        id: Optional[str] = None,
        title: str = "",
        description: str = "",
        status: str = InvestigationStatus.OPEN,
        impact_severity: str = ImpactSeverity.MEDIUM,
        # Backwards-compatible alias for older code/tests
        severity: Optional[str] = None,
        detected_at: Optional[str] = None,
        started_at: Optional[str] = None,
        resolved_at: Optional[str] = None,
        root_cause: str = "",
        remediation: str = "",
        lessons_learned: str = "",
        component_affected: str = "",
        service_affected: str = "",
        tags: Optional[List[str]] = None,
        event_ids: Optional[List[str]] = None,
        related_investigation_ids: Optional[List[str]] = None,
        created_by: str = "",
        assigned_to: Optional[str] = None,
        priority: str = Priority.P2,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        deleted_at: Optional[str] = None,
    ):
        """Initialize an Investigation (Phase 3a Expanded).

        Args:
            id: Unique investigation identifier (UUID)
            title: Investigation title
            description: Detailed description
            status: 'open', 'in_progress', 'resolved', or 'closed'
            impact_severity: 'critical', 'high', 'medium', or 'low'
            detected_at: When incident was detected
            started_at: When investigation started
            resolved_at: When incident was resolved (optional)
            root_cause: Root cause analysis (optional, max 2000 chars)
            remediation: Fix implementation plan (optional, max 2000 chars)
            lessons_learned: Lessons learned (optional, max 2000 chars)
            component_affected: Affected component name
            service_affected: Affected service
            tags: Searchable tags
            event_ids: Linked event IDs
            related_investigation_ids: Related investigation IDs
            created_by: User ID who created investigation
            assigned_to: User ID investigation assigned to (optional)
            priority: 'p0', 'p1', 'p2', or 'p3'
            created_at: When investigation record created (auto-set if None)
            updated_at: When investigation last updated (auto-set if None)
            deleted_at: When soft-deleted (null if active)
        """
        # Validate field lengths
        if len(root_cause) > 2000:
            raise ValueError("root_cause must be <= 2000 characters")
        if len(remediation) > 2000:
            raise ValueError("remediation must be <= 2000 characters")
        if len(lessons_learned) > 2000:
            raise ValueError("lessons_learned must be <= 2000 characters")

        # Generate id if not provided for convenience in tests and callers
        self.id = id or str(uuid_lib.uuid4())
        self.title = title
        self.description = description
        self.status = status
        # Coerce legacy `severity` -> `impact_severity` if provided
        if severity:
            self.impact_severity = severity
        else:
            self.impact_severity = impact_severity
        self.detected_at = detected_at or datetime.utcnow().isoformat()
        self.started_at = started_at or datetime.utcnow().isoformat()
        self.resolved_at = resolved_at
        self.root_cause = root_cause
        self.remediation = remediation
        self.lessons_learned = lessons_learned
        self.component_affected = component_affected
        self.service_affected = service_affected
        self.tags = tags or []
        self.event_ids = event_ids or []
        self.related_investigation_ids = related_investigation_ids or []
        self.created_by = created_by
        self.assigned_to = assigned_to
        self.priority = priority
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.deleted_at = deleted_at

    def is_active(self) -> bool:
        """Check if investigation is active (not soft-deleted).

        Returns:
            True if active, False if soft-deleted
        """
        return self.deleted_at is None

    def add_tag(self, tag: str) -> None:
        """Add a tag to investigation.

        Args:
            tag: Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
        self._update_timestamp()

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from investigation.

        Args:
            tag: Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)
        self._update_timestamp()

    def link_event(self, event_id: str) -> None:
        """Link an event to this investigation.

        Args:
            event_id: Event ID to link
        """
        if event_id not in self.event_ids:
            self.event_ids.append(event_id)
        self._update_timestamp()

    def unlink_event(self, event_id: str) -> None:
        """Unlink an event from this investigation.

        Args:
            event_id: Event ID to unlink
        """
        if event_id in self.event_ids:
            self.event_ids.remove(event_id)
        self._update_timestamp()

    def link_investigation(self, investigation_id: str) -> None:
        """Link a related investigation.

        Args:
            investigation_id: Investigation ID to link
        """
        if investigation_id not in self.related_investigation_ids:
            self.related_investigation_ids.append(investigation_id)
        self._update_timestamp()

    def soft_delete(self) -> None:
        """Soft-delete this investigation."""
        self.deleted_at = datetime.utcnow().isoformat()
        self._update_timestamp()

    def restore(self) -> None:
        """Restore a soft-deleted investigation."""
        self.deleted_at = None
        self._update_timestamp()

    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Convert investigation to dictionary.

        Returns:
            Dictionary representation of investigation
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "impact_severity": self.impact_severity,
            # Backwards compatibility
            "severity": self.severity,
            "detected_at": self.detected_at,
            "started_at": self.started_at,
            "resolved_at": self.resolved_at,
            "root_cause": self.root_cause,
            "remediation": self.remediation,
            "lessons_learned": self.lessons_learned,
            "component_affected": self.component_affected,
            "service_affected": self.service_affected,
            "tags": self.tags,
            "event_ids": self.event_ids,
            "related_investigation_ids": self.related_investigation_ids,
            "created_by": self.created_by,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deleted_at": self.deleted_at,
        }

    def update(self, **kwargs) -> None:
        """Update investigation fields.

        Args:
            **kwargs: Field names and values to update
        """
        # List of immutable fields
        immutable = {"id", "created_at", "created_by"}

        for key, value in kwargs.items():
            if hasattr(self, key) and key not in immutable:
                # Validate field lengths for text fields
                if key == "root_cause" and len(value) > 2000:
                    raise ValueError("root_cause must be <= 2000 characters")
                if key == "remediation" and len(value) > 2000:
                    raise ValueError("remediation must be <= 2000 characters")
                if key == "lessons_learned" and len(value) > 2000:
                    raise ValueError("lessons_learned must be <= 2000 characters")

                setattr(self, key, value)

        self._update_timestamp()

    @staticmethod
    def from_dict(data: dict) -> "Investigation":
        """Create Investigation from dictionary.

        Args:
            data: Dictionary with investigation fields

        Returns:
            Investigation instance
        """
        # Accept legacy 'severity' key when present
        init_kwargs = {
            k: v
            for k, v in data.items()
            if k
            in [
                "id",
                "title",
                "description",
                "status",
                "impact_severity",
                "detected_at",
                "started_at",
                "resolved_at",
                "root_cause",
                "remediation",
                "lessons_learned",
                "component_affected",
                "service_affected",
                "tags",
                "event_ids",
                "related_investigation_ids",
                "created_by",
                "assigned_to",
                "priority",
                "created_at",
                "updated_at",
                "deleted_at",
            ]
        }
        if "severity" in data and "impact_severity" not in init_kwargs:
            init_kwargs["severity"] = data["severity"]

        return Investigation(**init_kwargs)

    def __repr__(self) -> str:
        """String representation."""
        return f"Investigation(id={self.id}, title={self.title}, status={self.status}, severity={self.impact_severity})"

    @property
    def severity(self) -> str:
        """Backward-compatible severity property (returns impact_severity)."""
        return self.impact_severity


class InvestigationEvent:
    """Links an investigation to an event from git/CI/monitoring."""

    def __init__(
        self,
        id: str,
        investigation_id: str,
        event_id: str,
        event_type: str,  # 'git_commit', 'ci_build', 'monitoring_alert'
        source: str,  # 'Git', 'Jenkins', 'DataDog', etc.
        message: str,
        timestamp: str,
        created_at: Optional[str] = None,
    ):
        """Initialize an InvestigationEvent link.

        Args:
            id: Unique event link identifier
            investigation_id: Parent investigation ID
            event_id: Event ID from git/CI/monitoring system
            event_type: Type of event
            source: Source system
            message: Event message/description
            timestamp: Event timestamp
            created_at: ISO timestamp of link creation
        """
        self.id = id
        self.investigation_id = investigation_id
        self.event_id = event_id
        self.event_type = event_type
        self.source = source
        self.message = message
        self.timestamp = timestamp
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "message": self.message,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
        }


class Annotation:
    """Annotation/note attached to an investigation with optional threading."""

    def __init__(
        self,
        id: str,
        investigation_id: str,
        author: str,
        text: str,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        parent_annotation_id: Optional[str] = None,
    ):
        """Initialize an Annotation.

        Args:
            id: Unique annotation identifier
            investigation_id: Parent investigation ID
            author: Author name/email
            text: Annotation text
            created_at: ISO timestamp of creation
            updated_at: ISO timestamp of update
            parent_annotation_id: For threaded replies, parent annotation ID
        """
        self.id = id
        self.investigation_id = investigation_id
        self.author = author
        self.text = text
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.parent_annotation_id = parent_annotation_id

    def to_dict(self) -> dict:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "author": self.author,
            "text": self.text,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_annotation_id": self.parent_annotation_id,
        }

    def update(self, text: str) -> None:
        """Update annotation text.

        Args:
            text: New annotation text
        """
        self.text = text
        self.updated_at = datetime.utcnow().isoformat()
