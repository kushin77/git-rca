import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

DB_PATH: Path = Path(__file__).resolve().parent.parent / 'data' / 'dev_events.db'
DB_PATH.parent.mkdir(exist_ok=True)


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            payload TEXT NOT NULL,
            inserted_at TEXT NOT NULL
        )
        '''
    )
    conn.commit()
    conn.close()


from src.utils.retry import retry_on_exception


@retry_on_exception((Exception,), max_attempts=3, delay=0.05)
def insert_event(source: str, payload: Dict[str, Any]) -> None:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO events (source, payload, inserted_at) VALUES (?, ?, ?)',
        (source, json.dumps(payload, ensure_ascii=False), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def query_events(source: Optional[str] = None, limit: int = 50) -> List[Dict]:
    init_db()
    conn = _get_conn()
    cur = conn.cursor()
    if source:
        cur.execute('SELECT * FROM events WHERE source = ? ORDER BY id DESC LIMIT ?', (source, limit))
    else:
        cur.execute('SELECT * FROM events ORDER BY id DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()
    res: List[Dict] = []
    for r in rows:
        try:
            payload = json.loads(r['payload'])
        except Exception:
            payload = {}
        res.append({'id': r['id'], 'source': r['source'], 'payload': payload, 'inserted_at': r['inserted_at']})
    return res


def clear_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
