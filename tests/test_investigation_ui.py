from src.app import create_app


def test_investigation_canvas_renders():
    app = create_app(db_path=':memory:')
    client = app.test_client()

    resp = client.get('/investigations/test-123')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'Investigation Canvas' in body
    assert 'Demo Investigation' in body or 'test-123' in body
