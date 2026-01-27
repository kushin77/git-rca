import sqlite3
import uuid
import datetime
from typing import Optional, List, Dict


class SqlStore:
    def __init__(self, db_path: str = "investigations.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                status TEXT,
                severity TEXT,
                root_cause TEXT,
                fix TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
            )
            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS investigation_events (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                event_id TEXT,
                event_type TEXT,
                source TEXT,
                message TEXT,
                timestamp TEXT,
                created_at TEXT
            )
            """
            )

            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                event_id TEXT,
                author TEXT,
                text TEXT,
                parent_annotation_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
            )
            conn.commit()

    def create_investigation(self, title: str, severity: str = "medium", status: str = "open", description: Optional[str] = None) -> Dict:
        now = datetime.datetime.utcnow().isoformat()
        inv_id = f"inv-{uuid.uuid4().hex[:8]}"
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO investigations (id, title, description, status, severity, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (inv_id, title, description, status, severity, now, now),
            )
            conn.commit()
        return self.get_investigation(inv_id)

    def get_investigation(self, inv_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, title, description, status, severity, root_cause, fix, created_at, updated_at FROM investigations WHERE id = ?", (inv_id,))
            row = cur.fetchone()
            if not row:
                return None
            keys = ["id", "title", "description", "status", "severity", "root_cause", "fix", "created_at", "updated_at"]
            return dict(zip(keys, row))

    def update_investigation(self, inv_id: str, fields: Dict) -> Optional[Dict]:
        allowed = {"title", "description", "status", "severity", "root_cause", "fix"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_investigation(inv_id)
        updates["updated_at"] = datetime.datetime.utcnow().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        params = list(updates.values()) + [inv_id]
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE investigations SET {set_clause} WHERE id = ?", params)
            if cur.rowcount == 0:
                return None
            conn.commit()
        return self.get_investigation(inv_id)

    def list_investigations(self, status: Optional[str] = None, severity: Optional[str] = None) -> List[Dict]:
        q = "SELECT id, title, description, status, severity, root_cause, fix, created_at, updated_at FROM investigations"
        clauses = []
        params = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if severity:
            clauses.append("severity = ?")
            params.append(severity)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at DESC"
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(q, params)
            rows = cur.fetchall()
        keys = ["id", "title", "description", "status", "severity", "root_cause", "fix", "created_at", "updated_at"]
        return [dict(zip(keys, r)) for r in rows]

    # Event linking
    def add_event(self, investigation_id: str, event_id: str, event_type: str = "generic", source: str = "unknown", message: Optional[str] = None, timestamp: Optional[str] = None) -> Dict:
        now = datetime.datetime.utcnow().isoformat()
        ev_id = f"ev-{uuid.uuid4().hex[:8]}"
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO investigation_events (id, investigation_id, event_id, event_type, source, message, timestamp, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (ev_id, investigation_id, event_id, event_type, source, message, timestamp or now, now),
            )
            conn.commit()
        return {
            "id": ev_id,
            "investigation_id": investigation_id,
            "event_id": event_id,
            "event_type": event_type,
            "source": source,
            "message": message,
            "timestamp": timestamp or now,
            "created_at": now,
        }

    def list_events(self, investigation_id: str) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, investigation_id, event_id, event_type, source, message, timestamp, created_at FROM investigation_events WHERE investigation_id = ? ORDER BY created_at DESC",
                (investigation_id,),
            )
            rows = cur.fetchall()
        keys = ["id", "investigation_id", "event_id", "event_type", "source", "message", "timestamp", "created_at"]
        return [dict(zip(keys, r)) for r in rows]

    # Annotations
    def add_annotation(self, investigation_id: str, author: str, text: str, event_id: Optional[str] = None, parent_annotation_id: Optional[str] = None) -> Dict:
        now = datetime.datetime.utcnow().isoformat()
        ann_id = f"ann-{uuid.uuid4().hex[:8]}"
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO annotations (id, investigation_id, event_id, author, text, parent_annotation_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (ann_id, investigation_id, event_id, author, text, parent_annotation_id, now, now),
            )
            conn.commit()
        return {
            "id": ann_id,
            "investigation_id": investigation_id,
            "event_id": event_id,
            "author": author,
            "text": text,
            "parent_annotation_id": parent_annotation_id,
            "created_at": now,
            "updated_at": now,
        }

    def list_annotations(self, investigation_id: str) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, investigation_id, event_id, author, text, parent_annotation_id, created_at, updated_at FROM annotations WHERE investigation_id = ? ORDER BY created_at ASC",
                (investigation_id,),
            )
            rows = cur.fetchall()
        keys = ["id", "investigation_id", "event_id", "author", "text", "parent_annotation_id", "created_at", "updated_at"]
        return [dict(zip(keys, r)) for r in rows]

    def update_annotation(self, annotation_id: str, text: str) -> Optional[Dict]:
        now = datetime.datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE annotations SET text = ?, updated_at = ? WHERE id = ?", (text, now, annotation_id))
            if cur.rowcount == 0:
                return None
            conn.commit()
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, investigation_id, event_id, author, text, parent_annotation_id, created_at, updated_at FROM annotations WHERE id = ?", (annotation_id,))
            row = cur.fetchone()
            if not row:
                return None
            keys = ["id", "investigation_id", "event_id", "author", "text", "parent_annotation_id", "created_at", "updated_at"]
            return dict(zip(keys, row))

    def delete_annotation(self, annotation_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
            deleted = cur.rowcount > 0
            if deleted:
                conn.commit()
            return deleted
