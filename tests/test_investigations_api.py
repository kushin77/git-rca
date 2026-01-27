import os
import tempfile
import json
from src.app import create_app


def test_create_get_patch_list_investigation():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    try:
        app = create_app(db_path=db_path)
        client = app.test_client()

        # Create
        resp = client.post('/api/investigations', json={'title': 'Test', 'severity': 'critical'})
        assert resp.status_code == 201
        data = resp.get_json()
        inv_id = data['id']
        assert data['title'] == 'Test'

        # Get
        resp = client.get(f'/api/investigations/{inv_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['severity'] == 'critical'

        # Patch
        resp = client.patch(f'/api/investigations/{inv_id}', json={'root_cause': 'database leak', 'status': 'closed'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['root_cause'] == 'database leak'
        assert data['status'] == 'closed'

        # List filter
        resp = client.get('/api/investigations?status=closed')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert any(i['id'] == inv_id for i in data)

    finally:
        os.close(db_fd)
        try:
            os.remove(db_path)
        except Exception:
            pass
