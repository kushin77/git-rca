"""
Investigation Store - SQL Data Access Layer

Provides CRUD operations for investigations, events, and annotations using SQLite.
Handles database initialization, migrations, and transactional operations.

This store bridges the domain models and SQLite database.
"""

import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.models.investigation import Investigation, InvestigationEvent, Annotation


class InvestigationStore:
    """Data access layer for investigations."""
    
    def __init__(self, db_path: str = 'investigations.db'):
        """Initialize the investigation store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.initialize()

    def initialize(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')  # Enable cascade deletes
        cursor = conn.cursor()
        
        # Investigations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                severity TEXT DEFAULT 'medium',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                root_cause TEXT DEFAULT '',
                fix TEXT DEFAULT '',
                prevention TEXT DEFAULT '',
                description TEXT DEFAULT '',
                impact TEXT DEFAULT ''
            )
        ''')
        
        # Investigation events junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigation_events (
                id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE
            )
        ''')
        
        # Annotations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                parent_annotation_id TEXT,
                FOREIGN KEY (investigation_id) REFERENCES investigations(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_annotation_id) REFERENCES annotations(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()

    def create_investigation(
        self,
        title: str,
        status: str = 'open',
        severity: str = 'medium',
        description: str = '',
        impact: str = '',
    ) -> Investigation:
        """Create a new investigation.
        
        Args:
            title: Investigation title
            status: Status ('open', 'closed', 'resolved')
            severity: Severity ('critical', 'high', 'medium', 'low')
            description: Detailed description
            impact: Business impact
            
        Returns:
            Created Investigation instance
        """
        investigation_id = f'inv-{uuid.uuid4().hex[:8]}'
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO investigations 
            (id, title, status, severity, created_at, updated_at, description, impact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (investigation_id, title, status, severity, now, now, description, impact))
        
        conn.commit()
        conn.close()
        
        return Investigation(
            id=investigation_id,
            title=title,
            status=status,
            severity=severity,
            created_at=now,
            updated_at=now,
            description=description,
            impact=impact,
        )

    def get_investigation(self, investigation_id: str) -> Optional[Investigation]:
        """Retrieve an investigation by ID.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            Investigation instance or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM investigations WHERE id = ?', (investigation_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_investigation(row)

    def list_investigations(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Investigation]:
        """List investigations with optional filtering.
        
        Args:
            status: Filter by status
            severity: Filter by severity
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of Investigation instances
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM investigations WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_investigation(row) for row in rows]

    def update_investigation(
        self,
        investigation_id: str,
        **fields,
    ) -> Optional[Investigation]:
        """Update an investigation.
        
        Args:
            investigation_id: Investigation ID
            **fields: Fields to update (title, status, severity, root_cause, fix, prevention, impact, description)
            
        Returns:
            Updated Investigation instance or None if not found
        """
        investigation = self.get_investigation(investigation_id)
        if not investigation:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Only allow updating specific fields
        allowed_fields = {
            'title', 'status', 'severity', 'root_cause',
            'fix', 'prevention', 'description', 'impact'
        }
        
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
        update_fields['updated_at'] = datetime.utcnow().isoformat()
        
        set_clause = ', '.join([f'{k} = ?' for k in update_fields.keys()])
        values = list(update_fields.values()) + [investigation_id]
        
        cursor.execute(
            f'UPDATE investigations SET {set_clause} WHERE id = ?',
            values,
        )
        
        conn.commit()
        conn.close()
        
        investigation.update(**update_fields)
        return investigation

    def delete_investigation(self, investigation_id: str) -> bool:
        """Delete an investigation (cascades to events and annotations).
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')  # Enable cascade deletes
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM investigations WHERE id = ?', (investigation_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted

    def add_event(
        self,
        investigation_id: str,
        event_id: str,
        event_type: str,
        source: str,
        message: str,
        timestamp: str,
    ) -> InvestigationEvent:
        """Link an event to an investigation.
        
        Args:
            investigation_id: Investigation ID
            event_id: Event ID from git/CI/monitoring
            event_type: Type of event
            source: Source system
            message: Event message
            timestamp: Event timestamp
            
        Returns:
            Created InvestigationEvent instance
        """
        link_id = f'evt-{uuid.uuid4().hex[:8]}'
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO investigation_events
            (id, investigation_id, event_id, event_type, source, message, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (link_id, investigation_id, event_id, event_type, source, message, timestamp, now))
        
        conn.commit()
        conn.close()
        
        return InvestigationEvent(
            id=link_id,
            investigation_id=investigation_id,
            event_id=event_id,
            event_type=event_type,
            source=source,
            message=message,
            timestamp=timestamp,
            created_at=now,
        )

    def get_investigation_events(self, investigation_id: str) -> List[InvestigationEvent]:
        """Get all events linked to an investigation.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            List of InvestigationEvent instances
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM investigation_events WHERE investigation_id = ? ORDER BY timestamp DESC',
            (investigation_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_event(row) for row in rows]

    def add_annotation(
        self,
        investigation_id: str,
        author: str,
        text: str,
        parent_annotation_id: Optional[str] = None,
    ) -> Annotation:
        """Add an annotation to an investigation.
        
        Args:
            investigation_id: Investigation ID
            author: Author name/email
            text: Annotation text
            parent_annotation_id: Parent annotation ID for threaded replies
            
        Returns:
            Created Annotation instance
        """
        annotation_id = f'ann-{uuid.uuid4().hex[:8]}'
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO annotations
            (id, investigation_id, author, text, created_at, updated_at, parent_annotation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (annotation_id, investigation_id, author, text, now, now, parent_annotation_id))
        
        conn.commit()
        conn.close()
        
        return Annotation(
            id=annotation_id,
            investigation_id=investigation_id,
            author=author,
            text=text,
            created_at=now,
            updated_at=now,
            parent_annotation_id=parent_annotation_id,
        )

    def get_annotations(
        self,
        investigation_id: str,
        parent_annotation_id: Optional[str] = None,
    ) -> List[Annotation]:
        """Get annotations for an investigation.
        
        Args:
            investigation_id: Investigation ID
            parent_annotation_id: If set, only get replies to this annotation
            
        Returns:
            List of Annotation instances
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if parent_annotation_id:
            cursor.execute(
                'SELECT * FROM annotations WHERE investigation_id = ? AND parent_annotation_id = ? ORDER BY created_at ASC',
                (investigation_id, parent_annotation_id),
            )
        else:
            cursor.execute(
                'SELECT * FROM annotations WHERE investigation_id = ? AND parent_annotation_id IS NULL ORDER BY created_at DESC',
                (investigation_id,),
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_annotation(row) for row in rows]

    def update_annotation(
        self,
        annotation_id: str,
        text: str,
    ) -> Optional[Annotation]:
        """Update annotation text.
        
        Args:
            annotation_id: Annotation ID
            text: New text
            
        Returns:
            Updated Annotation instance or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        cursor.execute(
            'UPDATE annotations SET text = ?, updated_at = ? WHERE id = ?',
            (text, now, annotation_id),
        )
        
        deleted = cursor.rowcount > 0
        conn.commit()
        
        if not deleted:
            conn.close()
            return None
        
        cursor.execute('SELECT * FROM annotations WHERE id = ?', (annotation_id,))
        row = cursor.fetchone()
        conn.close()
        
        return self._row_to_annotation(row)

    def delete_annotation(self, annotation_id: str) -> bool:
        """Delete an annotation.
        
        Args:
            annotation_id: Annotation ID
            
        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM annotations WHERE id = ?', (annotation_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        
        return deleted

    # Helper methods
    
    @staticmethod
    def _row_to_investigation(row) -> Investigation:
        """Convert database row to Investigation instance."""
        return Investigation(
            id=row[0],
            title=row[1],
            status=row[2],
            severity=row[3],
            created_at=row[4],
            updated_at=row[5],
            root_cause=row[6],
            fix=row[7],
            prevention=row[8],
            description=row[9],
            impact=row[10],
        )

    @staticmethod
    def _row_to_event(row) -> InvestigationEvent:
        """Convert database row to InvestigationEvent instance."""
        return InvestigationEvent(
            id=row[0],
            investigation_id=row[1],
            event_id=row[2],
            event_type=row[3],
            source=row[4],
            message=row[5],
            timestamp=row[6],
            created_at=row[7],
        )

    @staticmethod
    def _row_to_annotation(row) -> Annotation:
        """Convert database row to Annotation instance."""
        return Annotation(
            id=row[0],
            investigation_id=row[1],
            author=row[2],
            text=row[3],
            created_at=row[4],
            updated_at=row[5],
            parent_annotation_id=row[6],
        )
