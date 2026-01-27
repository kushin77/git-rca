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
