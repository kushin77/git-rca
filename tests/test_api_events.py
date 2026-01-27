import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app import app
from src.connectors import git_connector as gc, ci_connector as cc
from src.store import sql_store


def test_api_events_empty(monkeypatch):
    # Ensure stores are empty
    monkeypatch.setattr(gc, 'EVENT_STORE', Path('/tmp/nonexistent_git_events.jsonl'))
    monkeypatch.setattr(cc, 'CI_EVENT_STORE', Path('/tmp/nonexistent_ci_events.jsonl'))
    # isolate SQL DB
    tmpdb = Path('/tmp/nonexistent_events.db')
    monkeypatch.setattr(sql_store, 'DB_PATH', tmpdb)
    sql_store.clear_db()

    client = app.test_client()
    resp = client.get('/api/events')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 0
    assert data['events'] == []


def test_api_events_with_data(tmp_path, monkeypatch):
    # Redirect stores to temp files
    git_file = tmp_path / 'g.jsonl'
    ci_file = tmp_path / 'c.jsonl'
    monkeypatch.setattr(gc, 'EVENT_STORE', git_file)
    monkeypatch.setattr(cc, 'CI_EVENT_STORE', ci_file)
    # isolate SQL DB for test
    db_file = tmp_path / 'events.db'
    monkeypatch.setattr(sql_store, 'DB_PATH', db_file)

    gc.clear_store()
    cc.clear_store()
    sql_store.clear_db()
    gc.ingest_event({"type": "push", "repo": "r/x", "commit": "abc"})
    cc.ingest_event({"status": "passed", "job": "build", "id": "1"})

    client = app.test_client()
    resp = client.get('/api/events')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['count'] == 2
    assert any(e.get('type') == 'push' for e in data['events'])
    assert any(e.get('status') == 'passed' for e in data['events'])

    # filtered by source=git
    resp = client.get('/api/events?source=git')
    data = resp.get_json()
    assert data['count'] == 1


def test_api_events_filters(tmp_path, monkeypatch):
    git_file = tmp_path / 'g2.jsonl'
    ci_file = tmp_path / 'c2.jsonl'
    monkeypatch.setattr(gc, 'EVENT_STORE', git_file)
    monkeypatch.setattr(cc, 'CI_EVENT_STORE', ci_file)
    # isolate DB
    db_file = tmp_path / 'events2.db'
    from src.store import sql_store
    monkeypatch.setattr(sql_store, 'DB_PATH', db_file)

    gc.clear_store()
    cc.clear_store()
    sql_store.clear_db()
    gc.ingest_event({"type": "push", "repo": "r/x", "commit": "a1", "timestamp": "2026-01-01T10:00:00Z"})
    gc.ingest_event({"type": "pull_request", "repo": "r/x", "id": 2, "timestamp": "2026-01-02T10:00:00Z"})
    cc.ingest_event({"type": "ci_job", "status": "passed", "job": "build", "timestamp": "2026-01-03T10:00:00Z"})

    client = app.test_client()
    # filter by type
    resp = client.get('/api/events?type=push')
    data = resp.get_json()
    assert data['count'] == 1

    # filter by repo
    resp = client.get('/api/events?repo=r/x')
    data = resp.get_json()
    assert data['count'] == 2

    # filter by since (only events on/after 2026-01-02)
    resp = client.get('/api/events?since=2026-01-02T00:00:00Z')
    data = resp.get_json()
    assert data['count'] == 2
