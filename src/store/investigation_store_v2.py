"""
Investigation Store - SQL Data Access Layer (Phase 3a Enhanced)

Provides CRUD operations for investigations with expanded Phase 3a data model.
Supports:
- 20+ investigation fields (component, service, priority, impact severity, etc.)
- Advanced queries (by component, service, priority, impact severity)
- Event-Investigation many-to-many relationships
- Soft deletes and restoration
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.models.investigation import (
    Investigation,
    InvestigationStatus,
    ImpactSeverity,
    Priority,
)


class InvestigationStore:
    """SQLite-based persistent storage for investigations."""

    def __init__(self, db_path: str = "data/investigations.db"):
        """Initialize investigation store with database connection."""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main investigations table with Phase 3a fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'open',
                    impact_severity TEXT DEFAULT 'medium',
                    detected_at TEXT,
                    started_at TEXT,
                    resolved_at TEXT,
                    root_cause TEXT,
                    remediation TEXT,
                    lessons_learned TEXT,
                    component_affected TEXT,
                    service_affected TEXT,
                    tags TEXT,
                    event_ids TEXT,
                    related_investigation_ids TEXT,
                    created_by TEXT,
                    assigned_to TEXT,
                    priority TEXT DEFAULT 'p2',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_investigations_status
                ON investigations(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_investigations_priority
                ON investigations(priority)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_investigations_component
                ON investigations(component_affected)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_investigations_service
                ON investigations(service_affected)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_investigations_created_at
                ON investigations(created_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_investigations_impact_severity
                ON investigations(impact_severity)
            """)

            conn.commit()

    def create_investigation(self, investigation: Investigation) -> bool:
        """
        Create a new investigation in the store.

        Args:
            investigation: Investigation object to store

        Returns:
            bool: True if successful, False if investigation already exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO investigations (
                        id, title, description, status, impact_severity,
                        detected_at, started_at, resolved_at,
                        root_cause, remediation, lessons_learned,
                        component_affected, service_affected,
                        tags, event_ids, related_investigation_ids,
                        created_by, assigned_to, priority,
                        created_at, updated_at, deleted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        investigation.id,
                        investigation.title,
                        investigation.description,
                        investigation.status.value,
                        investigation.impact_severity.value,
                        investigation.detected_at,
                        investigation.started_at,
                        investigation.resolved_at,
                        investigation.root_cause,
                        investigation.remediation,
                        investigation.lessons_learned,
                        investigation.component_affected,
                        investigation.service_affected,
                        json.dumps(investigation.tags) if investigation.tags else None,
                        (
                            json.dumps(investigation.event_ids)
                            if investigation.event_ids
                            else None
                        ),
                        (
                            json.dumps(investigation.related_investigation_ids)
                            if investigation.related_investigation_ids
                            else None
                        ),
                        investigation.created_by,
                        investigation.assigned_to,
                        investigation.priority.value,
                        investigation.created_at,
                        investigation.updated_at,
                        investigation.deleted_at,
                    ),
                )

                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Investigation already exists

    def get_investigation(self, investigation_id: str) -> Optional[Investigation]:
        """
        Retrieve a single investigation by ID.

        Args:
            investigation_id: Investigation ID to retrieve

        Returns:
            Investigation object or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM investigations WHERE id = ?", (investigation_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_investigation(row)

    def get_investigations_by_component(self, component: str) -> List[Investigation]:
        """
        Retrieve all investigations affecting a component.

        Args:
            component: Component name

        Returns:
            List of Investigation objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM investigations
                WHERE component_affected = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
            """,
                (component,),
            )

            return [self._row_to_investigation(row) for row in cursor.fetchall()]

    def get_investigations_by_service(self, service: str) -> List[Investigation]:
        """
        Retrieve all investigations affecting a service.

        Args:
            service: Service name

        Returns:
            List of Investigation objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM investigations
                WHERE service_affected = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
            """,
                (service,),
            )

            return [self._row_to_investigation(row) for row in cursor.fetchall()]

    def get_investigations_by_priority(self, priority: Priority) -> List[Investigation]:
        """
        Retrieve all investigations with a specific priority.

        Args:
            priority: Priority enum value

        Returns:
            List of Investigation objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM investigations
                WHERE priority = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
            """,
                (priority.value,),
            )

            return [self._row_to_investigation(row) for row in cursor.fetchall()]

    def get_investigations_by_severity(
        self, severity: ImpactSeverity
    ) -> List[Investigation]:
        """
        Retrieve all investigations with a specific impact severity.

        Args:
            severity: ImpactSeverity enum value

        Returns:
            List of Investigation objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM investigations
                WHERE impact_severity = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
            """,
                (severity.value,),
            )

            return [self._row_to_investigation(row) for row in cursor.fetchall()]

    def get_investigations_by_status(
        self, status: InvestigationStatus
    ) -> List[Investigation]:
        """
        Retrieve all investigations with a specific status.

        Args:
            status: InvestigationStatus enum value

        Returns:
            List of Investigation objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM investigations
                WHERE status = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
            """,
                (status.value,),
            )

            return [self._row_to_investigation(row) for row in cursor.fetchall()]

    def update_investigation(
        self, investigation_id: str, updates: Dict[str, Any]
    ) -> bool:
        """
        Update specific fields of an investigation.

        Args:
            investigation_id: Investigation ID to update
            updates: Dictionary of field updates

        Returns:
            bool: True if successful, False if investigation not found
        """
        investigation = self.get_investigation(investigation_id)
        if not investigation:
            return False

        # Update investigation object
        for key, value in updates.items():
            if hasattr(investigation, key):
                setattr(investigation, key, value)

        # Update timestamp
        investigation.updated_at = datetime.utcnow().isoformat()

        # Save back to database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE investigations SET
                    title = ?,
                    description = ?,
                    status = ?,
                    impact_severity = ?,
                    root_cause = ?,
                    remediation = ?,
                    lessons_learned = ?,
                    component_affected = ?,
                    service_affected = ?,
                    tags = ?,
                    event_ids = ?,
                    related_investigation_ids = ?,
                    assigned_to = ?,
                    priority = ?,
                    updated_at = ?
                WHERE id = ?
            """,
                (
                    investigation.title,
                    investigation.description,
                    investigation.status.value,
                    investigation.impact_severity.value,
                    investigation.root_cause,
                    investigation.remediation,
                    investigation.lessons_learned,
                    investigation.component_affected,
                    investigation.service_affected,
                    json.dumps(investigation.tags) if investigation.tags else None,
                    (
                        json.dumps(investigation.event_ids)
                        if investigation.event_ids
                        else None
                    ),
                    (
                        json.dumps(investigation.related_investigation_ids)
                        if investigation.related_investigation_ids
                        else None
                    ),
                    investigation.assigned_to,
                    investigation.priority.value,
                    investigation.updated_at,
                    investigation_id,
                ),
            )

            conn.commit()
            return True

    def delete_investigation(self, investigation_id: str) -> bool:
        """
        Soft delete an investigation.

        Args:
            investigation_id: Investigation ID to delete

        Returns:
            bool: True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE investigations
                SET deleted_at = ?
                WHERE id = ?
            """,
                (datetime.utcnow().isoformat(), investigation_id),
            )

            conn.commit()
            return cursor.rowcount > 0

    def restore_investigation(self, investigation_id: str) -> bool:
        """
        Restore a soft-deleted investigation.

        Args:
            investigation_id: Investigation ID to restore

        Returns:
            bool: True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE investigations
                SET deleted_at = NULL
                WHERE id = ?
            """,
                (investigation_id,),
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_all_investigations(
        self, include_deleted: bool = False
    ) -> List[Investigation]:
        """
        Retrieve all investigations.

        Args:
            include_deleted: If True, include soft-deleted investigations

        Returns:
            List of Investigation objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if include_deleted:
                cursor.execute("SELECT * FROM investigations ORDER BY created_at DESC")
            else:
                cursor.execute("""
                    SELECT * FROM investigations
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                """)

            return [self._row_to_investigation(row) for row in cursor.fetchall()]

    def _row_to_investigation(self, row: tuple) -> Investigation:
        """Convert database row to Investigation object."""
        return Investigation(
            id=row[0],
            title=row[1],
            description=row[2],
            status=InvestigationStatus(row[3]),
            impact_severity=ImpactSeverity(row[4]),
            detected_at=row[5],
            started_at=row[6],
            resolved_at=row[7],
            root_cause=row[8],
            remediation=row[9],
            lessons_learned=row[10],
            component_affected=row[11],
            service_affected=row[12],
            tags=json.loads(row[13]) if row[13] else None,
            event_ids=json.loads(row[14]) if row[14] else None,
            related_investigation_ids=json.loads(row[15]) if row[15] else None,
            created_by=row[16],
            assigned_to=row[17],
            priority=Priority(row[18]),
            created_at=row[19],
            updated_at=row[20],
            deleted_at=row[21],
        )
