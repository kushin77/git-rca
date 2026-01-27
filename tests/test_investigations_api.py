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

        # Events
        resp = client.post(f'/api/investigations/{inv_id}/events', json={'event_type': 'alert', 'source': 'unit-test', 'message': 'an event'})
        assert resp.status_code == 201
        ev = resp.get_json()
        assert ev['investigation_id'] == inv_id
        resp = client.get(f'/api/investigations/{inv_id}/events')
        assert resp.status_code == 200
        evs = resp.get_json()
        assert isinstance(evs, list) and len(evs) >= 1

        # Annotations
        resp = client.post(f'/api/investigations/{inv_id}/annotations', json={'author': 'tester', 'text': 'an annotation'})
        assert resp.status_code == 201
        ann = resp.get_json()
        assert ann['investigation_id'] == inv_id
        ann_id = ann['id']
        resp = client.get(f'/api/investigations/{inv_id}/annotations')
        assert resp.status_code == 200
        anns = resp.get_json()
        assert any(a['id'] == ann_id for a in anns)

        # Patch annotation
        resp = client.patch(f'/api/investigations/{inv_id}/annotations/{ann_id}', json={'text': 'updated'})
        assert resp.status_code == 200
        patched = resp.get_json()
        assert patched['text'] == 'updated'

        # Delete annotation
        resp = client.delete(f'/api/investigations/{inv_id}/annotations/{ann_id}')
        assert resp.status_code == 204
        resp = client.get(f'/api/investigations/{inv_id}/annotations')
        anns = resp.get_json()
        assert not any(a['id'] == ann_id for a in anns)

    finally:
        os.close(db_fd)
        try:
            os.remove(db_path)
        except Exception:
            pass
