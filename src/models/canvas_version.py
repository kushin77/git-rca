"""
Canvas Versioning System
=======================

Provides version history tracking and rollback capabilities for canvases.

Key Responsibilities:
- Create and manage canvas versions
- Track changes between versions
- Support version rollback
- Provide version comparison
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import uuid4


class ChangeType(str, Enum):
    """Types of changes tracked in versions."""
    CANVAS_CREATED = "canvas_created"
    CANVAS_UPDATED = "canvas_updated"
    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    NODE_UPDATED = "node_updated"
    EDGE_ADDED = "edge_added"
    EDGE_REMOVED = "edge_removed"
    EDGE_UPDATED = "edge_updated"
    METADATA_CHANGED = "metadata_changed"


@dataclass
class Change:
    """Represents a single change in a version."""
    change_type: ChangeType
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'change_type': self.change_type.value,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class CanvasVersion:
    """Represents a version of a canvas."""
    
    version_id: str
    canvas_id: str
    version_number: int
    previous_version_id: Optional[str]
    data: Dict[str, Any]  # Complete canvas snapshot
    changes: List[Change]  # What changed from previous version
    author: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'version_id': self.version_id,
            'canvas_id': self.canvas_id,
            'version_number': self.version_number,
            'previous_version_id': self.previous_version_id,
            'data': self.data,
            'changes': [c.to_dict() for c in self.changes],
            'author': self.author,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanvasVersion':
        """Create from dictionary."""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['changes'] = [
            Change(
                change_type=ChangeType(c['change_type']),
                details=c['details'],
                timestamp=datetime.fromisoformat(c['timestamp']),
            )
            for c in data.get('changes', [])
        ]
        return cls(**data)


class VersionStore:
    """
    Manages canvas versions with full history tracking.
    
    Provides:
    - Version creation and storage
    - Version retrieval and listing
    - Rollback capabilities
    - Version comparison
    """
    
    def __init__(self):
        """Initialize version store."""
        self.versions: Dict[str, CanvasVersion] = {}
        self.canvas_versions: Dict[str, List[str]] = {}  # canvas_id -> [version_ids]
        self.version_counter: Dict[str, int] = {}  # canvas_id -> next version number
    
    def create_version(
        self,
        canvas_id: str,
        canvas_data: Dict[str, Any],
        changes: List[Change],
        author: str,
        message: str = "",
    ) -> CanvasVersion:
        """
        Create a new canvas version.
        
        Args:
            canvas_id: ID of the canvas
            canvas_data: Complete canvas snapshot
            changes: List of changes from previous version
            author: User creating the version
            message: Version message/description
        
        Returns:
            CanvasVersion: The created version
        """
        if canvas_id not in self.version_counter:
            self.version_counter[canvas_id] = 1
        else:
            self.version_counter[canvas_id] += 1
        
        version_number = self.version_counter[canvas_id]
        previous_version_id = None
        
        # Get the previous version ID if versions exist
        if canvas_id in self.canvas_versions and self.canvas_versions[canvas_id]:
            previous_version_id = self.canvas_versions[canvas_id][-1]
        
        version = CanvasVersion(
            version_id=str(uuid4()),
            canvas_id=canvas_id,
            version_number=version_number,
            previous_version_id=previous_version_id,
            data=canvas_data,
            changes=changes,
            author=author,
            message=message,
        )
        
        self.versions[version.version_id] = version
        
        if canvas_id not in self.canvas_versions:
            self.canvas_versions[canvas_id] = []
        self.canvas_versions[canvas_id].append(version.version_id)
        
        return version
    
    def get_version(self, version_id: str) -> Optional[CanvasVersion]:
        """Get a specific version."""
        return self.versions.get(version_id)
    
    def get_canvas_versions(self, canvas_id: str) -> List[CanvasVersion]:
        """Get all versions of a canvas."""
        version_ids = self.canvas_versions.get(canvas_id, [])
        versions = [self.versions[vid] for vid in version_ids]
        return versions
    
    def get_latest_version(self, canvas_id: str) -> Optional[CanvasVersion]:
        """Get the latest version of a canvas."""
        versions = self.get_canvas_versions(canvas_id)
        return versions[-1] if versions else None
    
    def get_version_by_number(self, canvas_id: str, version_number: int) -> Optional[CanvasVersion]:
        """Get a specific version by number."""
        versions = self.get_canvas_versions(canvas_id)
        for v in versions:
            if v.version_number == version_number:
                return v
        return None
    
    def rollback(self, canvas_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        """
        Rollback canvas to a specific version.
        
        Args:
            canvas_id: Canvas to rollback
            version_id: Version to rollback to
        
        Returns:
            Canvas data from that version, or None if not found
        """
        version = self.get_version(version_id)
        if not version or version.canvas_id != canvas_id:
            return None
        return version.data
    
    def get_version_diff(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """
        Compare two versions.
        
        Args:
            version_id1: First version
            version_id2: Second version
        
        Returns:
            Dictionary with differences
        """
        v1 = self.get_version(version_id1)
        v2 = self.get_version(version_id2)
        
        if not v1 or not v2:
            return {}
        
        return {
            'version1_id': version_id1,
            'version1_number': v1.version_number,
            'version2_id': version_id2,
            'version2_number': v2.version_number,
            'changes': [c.to_dict() for c in v2.changes],  # Changes from v1 to v2
        }
    
    def get_version_history(self, canvas_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get version history for a canvas.
        
        Args:
            canvas_id: Canvas to get history for
            limit: Maximum number of versions to return
        
        Returns:
            List of version summaries
        """
        versions = self.get_canvas_versions(canvas_id)
        
        # Return latest versions first
        history = []
        for version in reversed(versions[-limit:]):
            history.append({
                'version_id': version.version_id,
                'version_number': version.version_number,
                'author': version.author,
                'timestamp': version.timestamp.isoformat(),
                'message': version.message,
                'changes_count': len(version.changes),
            })
        
        return history
    
    def get_version_count(self, canvas_id: str) -> int:
        """Get total version count for a canvas."""
        return len(self.get_canvas_versions(canvas_id))
    
    def compare_with_latest(self, canvas_id: str, version_id: str) -> Dict[str, Any]:
        """
        Compare a version with the latest version.
        
        Args:
            canvas_id: Canvas ID
            version_id: Version to compare
        
        Returns:
            Comparison result
        """
        version = self.get_version(version_id)
        latest = self.get_latest_version(canvas_id)
        
        if not version or not latest:
            return {}
        
        return {
            'comparing_version': version_id,
            'comparing_number': version.version_number,
            'latest_version': latest.version_id,
            'latest_number': latest.version_number,
            'versions_ahead': latest.version_number - version.version_number,
        }
