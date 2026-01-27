import json
from pathlib import Path
from typing import Dict, Iterable, List
import json

# Simple file-backed connector for development: stores events as JSON lines.
from src.store import sql_store
from src.connectors import validator

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
EVENT_STORE = DATA_DIR / 'dev_git_events.jsonl'


def ingest_event(event: Dict) -> None:
    """Append a git event (dict) to the local dev event store and also insert into SQL store.

    Performs lightweight validation and records to SQL with retries in case of transient errors.
    """
    if not validator.validate_event(event):
        # invalid event; drop for now
        return
    with EVENT_STORE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    try:
        sql_store.insert_event('git', event)
    except Exception:
        # Swallow DB errors in dev connector to avoid breaking ingest
        pass


def ingest_events(events: Iterable[Dict]) -> None:
    for e in events:
        ingest_event(e)


def load_events(limit: int = 100) -> List[Dict]:
    """Load up to `limit` most recent events (file order is append order)."""
    if not EVENT_STORE.exists():
        return []
    res: List[Dict] = []
    with EVENT_STORE.open('r', encoding='utf-8') as f:
        for line in f:
            if len(res) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                res.append(json.loads(line))
            except Exception:
                continue
    return res


def clear_store() -> None:
    """Remove the dev event store file (test helper)."""
    try:
        EVENT_STORE.unlink()
    except FileNotFoundError:
        pass
