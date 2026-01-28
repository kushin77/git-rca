"""
Phase 3c: Tests for Canvas UI API

Focuses on core API endpoint testing.
"""

import pytest
import json
from flask import Flask
from src.api.canvas_ui_api import CanvasUIAPI, register_canvas_ui_api
from src.models.canvas import Canvas, CanvasStore, NodeType, EdgeType, CanvasNode, CanvasEdge
from src.models.investigation import Investigation
from src.store.investigation_store import InvestigationStore


@pytest.fixture
def app():
    """Create Flask test app"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def canvas_store():
    """Create canvas store"""
    return CanvasStore()


@pytest.fixture
def investigation_store(tmp_path):
    """Create investigation store with sample data"""
    db_path = tmp_path / "test.db"
    
    store = InvestigationStore(db_path=str(db_path))

    # Add sample investigation and store the ID for use in tests
    inv = store.create_investigation(
        title="Test Investigation",
        description="Test",
        status="open"
    )
    # Store the ID as a class attribute for access in tests
    store.test_inv_id = inv.id

    return store


@pytest.fixture
def client(app, canvas_store, investigation_store):
    """Create test client with registered APIs"""
    register_canvas_ui_api(app, canvas_store, investigation_store)
    return app.test_client(), app, canvas_store, investigation_store


class TestCanvasUIAPI:
    """Test suite for Canvas UI API"""

    def test_create_canvas(self, client):
        """Test creating a new canvas"""
        test_client, app, store, inv_store = client
        inv_id = inv_store.test_inv_id

        response = test_client.post('/api/canvas', json={
            'investigation_id': inv_id,
            'title': 'Test Canvas',
            'description': 'Test description',
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'Test Canvas'
        assert data['investigation_id'] == inv_id
        assert 'id' in data

    def test_create_canvas_missing_investigation_id(self, client):
        """Test creating canvas without investigation_id"""
        test_client, app, store, inv_store = client

        response = test_client.post('/api/canvas', json={
            'title': 'Test Canvas',
        })

        assert response.status_code == 400

    def test_create_canvas_missing_title(self, client):
        """Test creating canvas without title"""
        test_client, app, store, inv_store = client
        inv_id = inv_store.test_inv_id

        response = test_client.post('/api/canvas', json={
            'investigation_id': inv_id,
        })

        assert response.status_code == 400

    def test_create_canvas_nonexistent_investigation(self, client):
        """Test creating canvas with nonexistent investigation"""
        test_client, app, store, inv_store = client

        response = test_client.post('/api/canvas', json={
            'investigation_id': 'nonexistent-xxx',
            'title': 'Test Canvas',
        })

        assert response.status_code == 404

    def test_register_canvas_ui_api(self, app, canvas_store, investigation_store):
        """Test registering canvas API with Flask app"""
        try:
            register_canvas_ui_api(app, canvas_store, investigation_store)
            assert True
        except Exception as e:
            pytest.fail(f"Failed to register canvas API: {str(e)}")

    def test_canvas_api_endpoints_exist(self, app, canvas_store, investigation_store):
        """Test all expected endpoints are registered"""
        register_canvas_ui_api(app, canvas_store, investigation_store)

        # Check that routes were registered
        routes = [str(rule) for rule in app.url_map.iter_rules()]

        expected_endpoints = [
            '/api/canvas/<canvas_id>',
            '/api/canvas',
            '/api/canvas/<canvas_id>/nodes',
            '/api/canvas/<canvas_id>/edges',
            '/api/canvas/<canvas_id>/analysis',
        ]

        for endpoint in expected_endpoints:
            # Check if the pattern exists (routes may have methods)
            assert any(endpoint.replace('<canvas_id>', '') in route for route in routes), \
                f"Endpoint pattern {endpoint} not found in routes"


class TestCanvasUIIntegration:
    """Integration tests for Canvas UI"""

    def test_full_workflow_create_and_operate_on_canvas(self, client):
        """Test complete workflow: create canvas, add nodes/edges, get analysis"""
        test_client, app, canvas_store, inv_store = client
        inv_id = inv_store.test_inv_id

        # 1. Create canvas
        response = test_client.post('/api/canvas', json={
            'investigation_id': inv_id,
            'title': 'Test Workflow Canvas',
        })
        assert response.status_code == 201
        canvas_id = json.loads(response.data)['id']

        # 2. Add node to canvas
        response = test_client.post(f'/api/canvas/{canvas_id}/nodes', json={
            'type': 'EVENT',
            'title': 'Test Event Node',
        })
        assert response.status_code == 201
        node_data = json.loads(response.data)
        node_id = node_data['id']

        # 3. Get canvas and verify node was added
        response = test_client.get(f'/api/canvas/{canvas_id}')
        assert response.status_code == 200
        canvas_data = json.loads(response.data)
        assert len(canvas_data['nodes']) == 1

        # 4. Get analysis
        response = test_client.get(f'/api/canvas/{canvas_id}/analysis')
        assert response.status_code == 200
        analysis = json.loads(response.data)
        assert analysis['node_count'] == 1
        assert 'insights' in analysis

        # 5. Update canvas
        response = test_client.put(f'/api/canvas/{canvas_id}', json={
            'title': 'Updated Canvas Title',
        })
        assert response.status_code == 200
        updated_canvas = json.loads(response.data)
        assert updated_canvas['title'] == 'Updated Canvas Title'

        # 6. Delete canvas
        response = test_client.delete(f'/api/canvas/{canvas_id}')
        assert response.status_code == 204

        # 7. Verify canvas is deleted
        response = test_client.get(f'/api/canvas/{canvas_id}')
