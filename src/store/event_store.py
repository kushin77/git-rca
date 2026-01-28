"""
Event Store - Persistent storage and retrieval of events

Provides CRUD operations for Event objects and advanced queries for:
- Event retrieval by investigation
- Event retrieval by source type
- Event retrieval by time range
- Event filtering by severity and tags
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
from src.models.event import Event, EventSource, EventSeverity


class EventStore:
    """SQLite-based persistent storage for events."""
    
    def __init__(self, db_path: str = "data/events.db"):
        """Initialize event store with database connection."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    data TEXT,
                    tags TEXT,
                    investigation_ids TEXT,
                    source_id TEXT,
                    parsed_at TEXT,
                    linked_at TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    deleted_at TEXT,
                    UNIQUE(source_id, source)
                )
            ''')
            
            # Create indexes for common queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_source
                ON events(source)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_severity
                ON events(severity)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_created_at
                ON events(created_at)
            ''')
            
            # Event-Investigation junction table for many-to-many
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_investigations (
                    event_id TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    PRIMARY KEY (event_id, investigation_id),
                    FOREIGN KEY (event_id) REFERENCES events(id)
                )
            ''')
            
            conn.commit()
    
    def create_event(self, event: Event) -> bool:
        """
        Create a new event in the store.
        
        Args:
            event: Event object to store
            
        Returns:
            bool: True if successful, False if event already exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO events (
                        id, timestamp, source, event_type, severity,
                        data, tags, investigation_ids, source_id,
                        parsed_at, linked_at, metadata,
                        created_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.id,
                    event.timestamp,
                    event.source.value,
                    event.event_type,
                    event.severity.value,
                    json.dumps(event.data) if event.data else None,
                    json.dumps(event.tags) if event.tags else None,
                    json.dumps(event.investigation_ids) if event.investigation_ids else None,
                    event.source_id,
                    event.parsed_at,
                    event.linked_at,
                    json.dumps(event.metadata) if event.metadata else None,
                    event.created_at,
                    event.deleted_at,
                ))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Event already exists
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """
        Retrieve a single event by ID.
        
        Args:
            event_id: Event ID to retrieve
            
        Returns:
            Event object or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_event(row)
    
    def get_events_by_investigation(self, investigation_id: str) -> List[Event]:
        """
        Retrieve all events linked to an investigation.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            List of Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Query events that have this investigation in their investigation_ids
            cursor.execute('''
                SELECT * FROM events
                WHERE investigation_ids IS NOT NULL
                AND deleted_at IS NULL
                ORDER BY timestamp DESC
            ''')
            
            events = []
            for row in cursor.fetchall():
                event = self._row_to_event(row)
                if investigation_id in event.investigation_ids:
                    events.append(event)
            
            return events
    
    def get_events_by_source(self, source: EventSource) -> List[Event]:
        """
        Retrieve all events from a specific source.
        
        Args:
            source: EventSource enum value
            
        Returns:
            List of Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM events
                WHERE source = ? AND deleted_at IS NULL
                ORDER BY timestamp DESC
            ''', (source.value,))
            
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def get_events_by_timestamp_range(self, start: str, end: str) -> List[Event]:
        """
        Retrieve events within a time range.
        
        Args:
            start: ISO format start timestamp
            end: ISO format end timestamp
            
        Returns:
            List of Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM events
                WHERE timestamp >= ? AND timestamp <= ?
                AND deleted_at IS NULL
                ORDER BY timestamp DESC
            ''', (start, end))
            
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def get_events_by_severity(self, severity: EventSeverity) -> List[Event]:
        """
        Retrieve all events of a specific severity.
        
        Args:
            severity: EventSeverity enum value
            
        Returns:
            List of Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM events
                WHERE severity = ? AND deleted_at IS NULL
                ORDER BY timestamp DESC
            ''', (severity.value,))
            
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def get_events_by_tag(self, tag: str) -> List[Event]:
        """
        Retrieve all events with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of Event objects
        """
        events = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM events
                WHERE tags IS NOT NULL AND deleted_at IS NULL
                ORDER BY timestamp DESC
            ''')
            
            for row in cursor.fetchall():
                event = self._row_to_event(row)
                if tag in event.tags:
                    events.append(event)
        
        return events
    
    def update_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields of an event.
        
        Args:
            event_id: Event ID to update
            updates: Dictionary of field updates
            
        Returns:
            bool: True if successful, False if event not found
        """
        event = self.get_event(event_id)
        if not event:
            return False
        
        # Update event object
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        # Save back to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE events SET
                    severity = ?,
                    tags = ?,
                    investigation_ids = ?,
                    linked_at = ?,
                    metadata = ?
                WHERE id = ?
            ''', (
                event.severity.value,
                json.dumps(event.tags) if event.tags else None,
                json.dumps(event.investigation_ids) if event.investigation_ids else None,
                event.linked_at,
                json.dumps(event.metadata) if event.metadata else None,
                event_id,
            ))
            
            conn.commit()
            return True
    
    def link_event_to_investigation(self, event_id: str, investigation_id: str) -> bool:
        """
        Link an event to an investigation.
        
        Args:
            event_id: Event ID
            investigation_id: Investigation ID
            
        Returns:
            bool: True if successful
        """
        event = self.get_event(event_id)
        if not event:
            return False
        
        event.link_to_investigation(investigation_id)
        event.linked_at = datetime.utcnow().isoformat()
        
        return self.update_event(event_id, {
            'investigation_ids': event.investigation_ids,
            'linked_at': event.linked_at
        })
    
    def delete_event(self, event_id: str) -> bool:
        """
        Soft delete an event.
        
        Args:
            event_id: Event ID to delete
            
        Returns:
            bool: True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE events
                SET deleted_at = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), event_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def restore_event(self, event_id: str) -> bool:
        """
        Restore a soft-deleted event.
        
        Args:
            event_id: Event ID to restore
            
        Returns:
            bool: True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE events
                SET deleted_at = NULL
                WHERE id = ?
            ''', (event_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_all_events(self, include_deleted: bool = False) -> List[Event]:
        """
        Retrieve all events.
        
        Args:
            include_deleted: If True, include soft-deleted events
            
        Returns:
            List of Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if include_deleted:
                cursor.execute('SELECT * FROM events ORDER BY timestamp DESC')
            else:
                cursor.execute('''
                    SELECT * FROM events
                    WHERE deleted_at IS NULL
                    ORDER BY timestamp DESC
                ''')
            
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def search_events(self, 
                     source: Optional[EventSource] = None,
                     severity: Optional[EventSeverity] = None,
                     event_type: Optional[str] = None,
                     tag: Optional[str] = None,
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None) -> List[Event]:
        """
        Advanced search for events with multiple filters.
        
        Args:
            source: Filter by event source
            severity: Filter by severity
            event_type: Filter by event type
            tag: Filter by tag
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            
        Returns:
            List of matching Event objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM events WHERE deleted_at IS NULL'
            params = []
            
            if source:
                query += ' AND source = ?'
                params.append(source.value)
            
            if severity:
                query += ' AND severity = ?'
                params.append(severity.value)
            
            if event_type:
                query += ' AND event_type = ?'
                params.append(event_type)
            
            if start_time:
                query += ' AND timestamp >= ?'
                params.append(start_time)
            
            if end_time:
                query += ' AND timestamp <= ?'
                params.append(end_time)
            
            query += ' ORDER BY timestamp DESC'
            
            cursor.execute(query, params)
            events = [self._row_to_event(row) for row in cursor.fetchall()]
            
            # Filter by tag if specified (requires JSON parsing)
            if tag:
                events = [e for e in events if tag in e.tags]
            
            return events
    
    def _row_to_event(self, row: tuple) -> Event:
        """Convert database row to Event object."""
        return Event(
            id=row[0],
            timestamp=row[1],
            source=EventSource(row[2]),
            event_type=row[3],
            severity=EventSeverity(row[4]),
            data=json.loads(row[5]) if row[5] else None,
            tags=json.loads(row[6]) if row[6] else None,
            investigation_ids=json.loads(row[7]) if row[7] else None,
            source_id=row[8],
            parsed_at=row[9],
            linked_at=row[10],
            metadata=json.loads(row[11]) if row[11] else None,
            created_at=row[12],
            deleted_at=row[13],
        )
