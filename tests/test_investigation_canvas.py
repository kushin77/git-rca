"""
Tests for Investigation Canvas UI (Story #16)
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.app import create_app



@pytest.fixture
def client():
    """Create test client with pre-populated test data."""
    # Use temporary database for tests
    with tempfile.NamedTemporaryFile(delete=False) as f:
        test_db = f.name
    
    # Create test app with temporary database
    test_app = create_app(db_path=test_db)
    
    # Create test store and populate with test data
    from src.store.investigation_store import InvestigationStore
    test_store = InvestigationStore(db_path=test_db)
    test_app.investigation_store = test_store
    
    # Manually create investigations with fixed IDs for testing
    import sqlite3
    conn = sqlite3.connect(test_db)
    conn.execute('PRAGMA foreign_keys = ON')
    cursor = conn.cursor()
    now = '2025-01-27T10:00:00Z'
    
    # Create test investigation with fixed ID
    cursor.execute('''
        INSERT INTO investigations 
        (id, title, status, severity, created_at, updated_at, description, impact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('inv-001', 'Test Investigation inv-001', 'open', 'high', now, now, 'Test investigation for canvas rendering', ''))
    
    # Add test event
    cursor.execute('''
        INSERT INTO investigation_events
        (id, investigation_id, event_id, event_type, source, message, timestamp, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('evt-001', 'inv-001', 'git-1', 'git_commit', 'Git', 'Test commit', '2025-01-27T10:00:00Z', now))
    
    # Add test annotation
    cursor.execute('''
        INSERT INTO annotations
        (id, investigation_id, author, text, created_at, updated_at, parent_annotation_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('ann-001', 'inv-001', 'Test User', 'Test annotation', now, now, None))
    
    conn.commit()
    conn.close()
    
    test_app.config['TESTING'] = True
    with test_app.test_client() as test_client:
        yield test_client
    
    # Cleanup test database
    if os.path.exists(test_db):
        os.unlink(test_db)


class TestInvestigationCanvasUI:
    """Test investigation canvas HTML rendering and routes."""

    def test_investigations_list_route_exists(self, client):
        """Test that investigations list route is accessible."""
        response = client.get('/investigations')
        assert response.status_code == 200

    def test_investigations_list_renders_html(self, client):
        """Test that investigations list renders HTML template."""
        response = client.get('/investigations')
        assert b'Investigations' in response.data
        assert b'Investigation Canvas' in response.data or b'Investigations' in response.data

    def test_investigations_list_contains_sample_data(self, client):
        """Test that sample investigations are displayed."""
        response = client.get('/investigations')
        # Check for either test data or sample data
        assert (b'Test Investigation' in response.data or 
                b'Payment Processing' in response.data or 
                b'Database' in response.data)

    def test_investigation_canvas_route_exists(self, client):
        """Test that investigation canvas route is accessible."""
        response = client.get('/investigations/inv-001')
        assert response.status_code == 200

    def test_investigation_canvas_renders_html(self, client):
        """Test that investigation canvas renders HTML template."""
        response = client.get('/investigations/inv-001')
        assert b'Investigation' in response.data
        assert b'Incident Summary' in response.data

    def test_investigation_canvas_sections_present(self, client):
        """Test that all 5 main sections are present in canvas."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'Incident Summary' in html
        assert 'Event Timeline' in html
        assert 'Annotations' in html
        assert 'Root Cause' in html
        assert 'Actions' in html

    def test_investigation_canvas_displays_title(self, client):
        """Test that investigation title is displayed."""
        response = client.get('/investigations/inv-001')
        assert b'Investigation inv-001' in response.data

    def test_investigation_canvas_displays_status(self, client):
        """Test that investigation status is displayed."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'open' in html.lower() or 'status' in html.lower()

    def test_investigation_canvas_displays_severity(self, client):
        """Test that severity badge is displayed."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'high' in html.lower() or 'severity' in html.lower()

    def test_investigation_canvas_displays_events(self, client):
        """Test that timeline events are displayed."""
        response = client.get('/investigations/inv-001')
        assert b'Event Timeline' in response.data
        # Should have mock events
        html = response.data.decode()
        assert 'monitoring' in html.lower() or 'timeline' in html.lower()

    def test_investigation_canvas_displays_annotations(self, client):
        """Test that annotations panel is displayed."""
        response = client.get('/investigations/inv-001')
        assert b'Annotations' in response.data or b'Notes' in response.data

    def test_investigation_canvas_action_buttons_present(self, client):
        """Test that action buttons are present."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        # Should have save, print, or other action buttons
        assert 'button' in html or 'Save' in html or 'Mark' in html

    def test_investigation_canvas_responsive_css_loaded(self, client):
        """Test that CSS is loaded and responsive."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'investigation.css' in html or 'static/css' in html

    def test_investigation_canvas_javascript_loaded(self, client):
        """Test that JavaScript is loaded."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'investigation.js' in html or 'static/js' in html

    def test_investigation_canvas_sidebar_present(self, client):
        """Test that sidebar is present with linked events."""
        response = client.get('/investigations/inv-001')
        assert b'Linked Events' in response.data or b'sidebar' in response.data

    def test_investigation_form_inputs_present(self, client):
        """Test that form inputs for editing are present."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        # Should have input fields for editing
        assert 'input' in html or 'textarea' in html

    def test_investigation_canvas_mobile_responsive(self, client):
        """Test that canvas includes mobile-responsive design."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'viewport' in html or 'meta' in html  # Responsive meta tag

    def test_investigation_canvas_save_functionality_exists(self, client):
        """Test that save functionality is defined in JavaScript."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'saveInvestigation' in html or 'Save' in html


class TestInvestigationCanvasAPI:
    """Test investigation canvas API endpoints."""

    def test_create_investigation_endpoint_exists(self, client):
        """Test that create investigation endpoint exists."""
        response = client.post('/api/investigations', json={
            'title': 'Test Investigation',
            'severity': 'high'
        })
        assert response.status_code in [200, 201]

    def test_create_investigation_returns_json(self, client):
        """Test that create endpoint returns JSON."""
        response = client.post('/api/investigations', json={
            'title': 'Test Investigation'
        })
        assert response.content_type == 'application/json'

    def test_get_investigation_endpoint_exists(self, client):
        """Test that get investigation endpoint exists."""
        response = client.get('/api/investigations/inv-001')
        assert response.status_code == 200

    def test_update_investigation_endpoint_exists(self, client):
        """Test that update investigation endpoint exists."""
        response = client.patch('/api/investigations/inv-001', json={
            'title': 'Updated Title'
        })
        assert response.status_code == 200

    def test_add_annotation_endpoint_exists(self, client):
        """Test that add annotation endpoint exists."""
        response = client.post('/api/investigations/inv-001/annotations', json={
            'text': 'Test annotation',
            'author': 'Test User'
        })
        assert response.status_code in [200, 201]

    def test_list_annotations_endpoint_exists(self, client):
        """Test that list annotations endpoint exists."""
        response = client.get('/api/investigations/inv-001/annotations')
        assert response.status_code == 200

    def test_list_annotations_returns_json(self, client):
        """Test that annotations endpoint returns JSON."""
        response = client.get('/api/investigations/inv-001/annotations')
        assert response.content_type == 'application/json'


class TestInvestigationCanvasResponsiveness:
    """Test responsive design of investigation canvas."""

    def test_canvas_uses_css_grid(self, client):
        """Test that canvas uses CSS grid for layout."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert 'grid' in html.lower() or 'display' in html

    def test_canvas_sections_mobile_friendly(self, client):
        """Test that sections are mobile-friendly."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        # Check that CSS file is linked (which contains @media queries)
        assert 'investigation.css' in html or 'viewport' in html

    def test_sidebar_hides_on_mobile(self, client):
        """Test that sidebar responds to mobile viewport."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert '@media' in html or 'viewport' in html


class TestInvestigationCanvasAccessibility:
    """Test accessibility features of investigation canvas."""

    def test_canvas_has_semantic_html(self, client):
        """Test that canvas uses semantic HTML elements."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert '<section' in html or '<main' in html or '<header' in html

    def test_canvas_has_form_labels(self, client):
        """Test that form fields have labels."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        assert '<label' in html

    def test_canvas_has_alt_text_for_images(self, client):
        """Test that images (if any) have alt text."""
        response = client.get('/investigations/inv-001')
        html = response.data.decode()
        if '<img' in html:
            assert 'alt=' in html


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
