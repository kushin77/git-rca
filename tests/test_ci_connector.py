import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.connectors import ci_connector as cc


def test_ci_ingest_and_load(tmp_path, monkeypatch):
    tmp_file = tmp_path / "ci_events.jsonl"
    monkeypatch.setattr(cc, "CI_EVENT_STORE", tmp_file)
    # isolate SQL DB for test
    db_file = tmp_path / "events.db"
    from src.store import sql_store

    monkeypatch.setattr(sql_store, "DB_PATH", db_file)

    sample = {"status": "passed", "job": "build", "id": "job-1"}
    cc.clear_store()
    sql_store.clear_db()
    cc.ingest_event(sample)
    events = cc.load_events()
    assert len(events) == 1
    assert events[0]["status"] == "passed"

    cc.ingest_events(
        [
            {"status": "failed", "job": "test", "id": "job-2"},
            {"status": "skipped", "job": "lint", "id": "job-3"},
        ]
    )
    events = cc.load_events(limit=10)
    assert len(events) == 3

    cc.clear_store()
    assert cc.load_events() == []
