"""
Investigation Model

Defines the data structure and ORM mapping for investigations using SQLAlchemy.
An investigation represents a root cause analysis session tracking an incident.

Attributes:
    id (str): Unique investigation identifier (primary key)
    title (str): Investigation title/incident summary
    status (str): Investigation status: 'open', 'closed', 'resolved'
    severity (str): Severity level: 'critical', 'high', 'medium', 'low'
    created_at (str): ISO timestamp of investigation creation
    updated_at (str): ISO timestamp of last update
    root_cause (str): Identified root cause (filled during investigation)
    fix (str): Implementation plan for the fix
    prevention (str): Measures to prevent recurrence
    description (str): Detailed incident description
    impact (str): Business impact assessment
"""

from datetime import datetime
from typing import Optional


class Investigation:
    """Investigation domain model (no ORM dependency in model itself)."""
    
    def __init__(
        self,
        id: str,
        title: str,
        status: str = 'open',
        severity: str = 'medium',
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        root_cause: str = '',
        fix: str = '',
        prevention: str = '',
        description: str = '',
        impact: str = '',
    ):
        """Initialize an Investigation.
        
        Args:
            id: Unique investigation identifier
            title: Investigation title
            status: 'open', 'closed', or 'resolved'
            severity: 'critical', 'high', 'medium', or 'low'
            created_at: ISO timestamp of creation (auto-set if None)
            updated_at: ISO timestamp of update (auto-set if None)
            root_cause: Root cause analysis text
            fix: Fix implementation plan
            prevention: Prevention measures
            description: Detailed description
            impact: Business impact
        """
        self.id = id
        self.title = title
        self.status = status
        self.severity = severity
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.root_cause = root_cause
        self.fix = fix
        self.prevention = prevention
        self.description = description
        self.impact = impact

    def to_dict(self) -> dict:
        """Convert investigation to dictionary.
        
        Returns:
            Dictionary representation of investigation
        """
        return {
            'id': self.id,
            'title': self.title,
            'status': self.status,
            'severity': self.severity,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'root_cause': self.root_cause,
            'fix': self.fix,
            'prevention': self.prevention,
            'description': self.description,
            'impact': self.impact,
        }

    def update(self, **kwargs) -> None:
        """Update investigation fields.
        
        Args:
            **kwargs: Field names and values to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key != 'id' and key != 'created_at':
                setattr(self, key, value)
        self.updated_at = datetime.utcnow().isoformat()

    @staticmethod
    def from_dict(data: dict) -> 'Investigation':
        """Create Investigation from dictionary.
        
        Args:
            data: Dictionary with investigation fields
            
        Returns:
            Investigation instance
        """
        return Investigation(**{k: v for k, v in data.items() if k in [
            'id', 'title', 'status', 'severity', 'created_at', 'updated_at',
            'root_cause', 'fix', 'prevention', 'description', 'impact'
        ]})


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
            'id': self.id,
            'investigation_id': self.investigation_id,
            'event_id': self.event_id,
            'event_type': self.event_type,
            'source': self.source,
            'message': self.message,
            'timestamp': self.timestamp,
            'created_at': self.created_at,
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
            'id': self.id,
            'investigation_id': self.investigation_id,
            'author': self.author,
            'text': self.text,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'parent_annotation_id': self.parent_annotation_id,
        }

    def update(self, text: str) -> None:
        """Update annotation text.
        
        Args:
            text: New annotation text
        """
        self.text = text
        self.updated_at = datetime.utcnow().isoformat()
