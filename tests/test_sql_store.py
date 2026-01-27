import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.store import sql_store


def test_sql_insert_and_query(tmp_path, monkeypatch):
    # Redirect DB path to temporary file
    db_file = tmp_path / 'events.db'
    monkeypatch.setattr(sql_store, 'DB_PATH', db_file)
    sql_store.clear_db()

    sql_store.insert_event('git', {'type': 'push', 'repo': 'r/x', 'commit': 'abc'})
    sql_store.insert_event('ci', {'status': 'passed', 'job': 'build'})

    all_events = sql_store.query_events(limit=10)
    assert len(all_events) == 2

    git_events = sql_store.query_events(source='git', limit=10)
    assert len(git_events) == 1
    assert git_events[0]['payload']['type'] == 'push'

    sql_store.clear_db()
    assert not db_file.exists()
