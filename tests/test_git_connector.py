import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.connectors import git_connector as gc


def test_ingest_and_load(tmp_path, monkeypatch):
    # Redirect the EVENT_STORE to a temp file for isolated test
    tmp_file = tmp_path / 'events.jsonl'
    monkeypatch.setattr(gc, 'EVENT_STORE', tmp_file)
    # isolate SQL DB for test
    db_file = tmp_path / 'events.db'
    from src.store import sql_store
    monkeypatch.setattr(sql_store, 'DB_PATH', db_file)

    sample = {"type": "push", "repo": "example/repo", "commit": "abc123"}
    gc.clear_store()
    sql_store.clear_db()
    gc.ingest_event(sample)
    events = gc.load_events()
    assert len(events) == 1
    assert events[0]['type'] == 'push'

    # ingest multiple
    gc.ingest_events([
        {"type": "pull_request", "repo": "example/repo", "id": 1},
        {"type": "branch", "repo": "example/repo", "name": "feature/x"},
    ])
    events = gc.load_events(limit=10)
    assert len(events) == 3

    # clear store
    gc.clear_store()
    assert gc.load_events() == []
