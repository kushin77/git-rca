import json
from pathlib import Path
from typing import Dict, Iterable, List
import json

# Simple file-backed CI connector for development: stores CI events as JSON lines.
from src.store import sql_store
from src.connectors import validator

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CI_EVENT_STORE = DATA_DIR / "dev_ci_events.jsonl"


def ingest_event(event: Dict) -> None:
    """Append a CI event (dict) to the local dev event store and DB after validation."""
    if not validator.validate_event(event):
        return
    with CI_EVENT_STORE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    try:
        sql_store.insert_event("ci", event)
    except Exception:
        pass


def ingest_events(events: Iterable[Dict]) -> None:
    for e in events:
        ingest_event(e)


def load_events(limit: int = 100) -> List[Dict]:
    """Load up to `limit` most recent events (file order is append order)."""
    if not CI_EVENT_STORE.exists():
        return []
    res: List[Dict] = []
    with CI_EVENT_STORE.open("r", encoding="utf-8") as f:
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
    """Remove the dev CI event store file (test helper)."""
    try:
        CI_EVENT_STORE.unlink()
    except FileNotFoundError:
        pass
