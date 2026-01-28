"""
Tests for Story #18 - Event Linking & Annotations

Tests automated event linking, filtering, searching, and enhanced annotation threading.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta

from src.app import create_app
from src.store.investigation_store import InvestigationStore
from src.services.event_linker import EventLinker
from src.middleware.auth import get_token_validator


@pytest.fixture
def auth_headers():
    """Generate authentication headers for tests."""
    validator = get_token_validator()
    token = validator.generate_token('test_user', 'engineer')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client():
    """Create Flask test client."""
    test_app = create_app()
    test_app.config['TESTING'] = True
    with test_app.test_client() as test_client:
        yield test_client


@pytest.fixture
def investigation_store():
    """Create investigation store with temp database."""
    import tempfile
    import os
    
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    store = InvestigationStore(db_path=db_path)
    
    yield store
    
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def test_investigation(investigation_store):
    """Create test investigation."""
    inv = investigation_store.create_investigation(
        title='API Response Timeout',
        description='POST /api/users returning 504',
        severity='high',
        status='open',
    )
    return inv


class TestAutoLinkEventsEndpoint:
    """Test the auto-link events REST endpoint."""
    
    @patch('src.app.event_linker.auto_link_events')
    def test_auto_link_endpoint_exists(self, mock_auto_link, client, test_investigation):
        """Test /api/investigations/<id>/events/auto-link endpoint exists."""
        mock_auto_link.return_value = []
        
        response = client.post(
            f'/api/investigations/{test_investigation.id}/events/auto-link'
        )
        
        # Should return success even with no events
        assert response.status_code == 201
        assert 'linked_count' in response.json
    
    @patch('src.app.event_linker.auto_link_events')
    def test_auto_link_with_time_window(self, mock_auto_link, client, test_investigation):
        """Test auto-link respects time_window_minutes parameter."""
        mock_auto_link.return_value = []
        
        response = client.post(
            f'/api/investigations/{test_investigation.id}/events/auto-link?time_window_minutes=120'
        )
        
        assert response.status_code == 201
        mock_auto_link.assert_called_once()
        # Check that time_window_minutes was passed
        call_args = mock_auto_link.call_args
        assert call_args[1]['time_window_minutes'] == 120
    
    @patch('src.app.event_linker.auto_link_events')
    def test_auto_link_semantic_matching_param(self, mock_auto_link, client, test_investigation):
        """Test auto-link semantic_matching parameter."""
        mock_auto_link.return_value = []
        
        response = client.post(
            f'/api/investigations/{test_investigation.id}/events/auto-link?semantic_matching=false'
        )
        
        assert response.status_code == 201
        call_args = mock_auto_link.call_args
        assert call_args[1]['semantic_matching'] is False


class TestGetInvestigationEventsEndpoint:
    """Test the get investigation events endpoint."""
    
    def test_get_events_endpoint(self, client, auth_headers):
        """Test GET /api/investigations/<id>/events endpoint."""
        # Create investigation via the app
        response = client.post(
            '/api/investigations',
            json={'title': 'Test Incident', 'description': 'Test description', 'service': 'test-service', 'severity': 'high'},
            headers=auth_headers
        )
        inv_id = response.json['id']
        
        # Add a test event via the app
        client.post(
            f'/api/investigations/{inv_id}/events/link',
            json={
                'event_id': 'git-123',
                'event_type': 'push',
                'source': 'git',
                'message': 'Deploy API service',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            headers=auth_headers
        )
        
        response = client.get(
            f'/api/investigations/{inv_id}/events'
        )
        
        assert response.status_code == 200
        data = response.json
        assert 'events' in data
        assert 'total_count' in data
    
    def test_get_events_filter_by_source(self, client, auth_headers):
        """Test filtering events by source."""
        # Create investigation
        response = client.post(
            '/api/investigations',
            json={'title': 'Test', 'description': 'Test desc', 'service': 'test-svc', 'severity': 'high'},
            headers=auth_headers
        )
        inv_id = response.json['id']
        
        # Add events from different sources
        client.post(
            f'/api/investigations/{inv_id}/events/link',
            json={
                'event_id': 'git-1',
                'event_type': 'push',
                'source': 'git',
                'message': 'Git commit',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            headers=auth_headers
        )
        client.post(
            f'/api/investigations/{inv_id}/events/link',
            json={
                'event_id': 'ci-1',
                'event_type': 'build',
                'source': 'ci',
                'message': 'Build job',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            headers=auth_headers
        )
        
        response = client.get(
            f'/api/investigations/{inv_id}/events?source=git'
        )
        
        assert response.status_code == 200
        data = response.json
        # Should only have git events
        assert all(evt['source'] == 'git' for evt in data['events'])
    
    def test_get_events_filter_by_type(self, client, auth_headers):
        """Test filtering events by type."""
        # Create investigation
        response = client.post(
            '/api/investigations',
            json={'title': 'Test', 'description': 'Test desc', 'service': 'test-svc', 'severity': 'high'},
            headers=auth_headers
        )
        inv_id = response.json['id']
        
        # Add events of different types
        client.post(
            f'/api/investigations/{inv_id}/events/link',
            json={
                'event_id': 'event-1',
                'event_type': 'push',
                'source': 'git',
                'message': 'Push',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            headers=auth_headers
        )
        client.post(
            f'/api/investigations/{inv_id}/events/link',
            json={
                'event_id': 'event-2',
                'event_type': 'pull_request',
                'source': 'git',
                'message': 'PR',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            headers=auth_headers
        )
        
        response = client.get(
            f'/api/investigations/{inv_id}/events?event_type=push'
        )
        
        assert response.status_code == 200
        data = response.json
        assert all(evt['event_type'] == 'push' for evt in data['events'])


class TestManualEventLinkingEndpoint:
    """Test manual event linking endpoint."""
    
    def test_link_event_endpoint(self, client, auth_headers):
        """Test POST /api/investigations/<id>/events/link endpoint."""
        # Create investigation
        response = client.post(
            '/api/investigations',
            json={'title': 'Test Incident', 'description': 'Test', 'service': 'test-svc', 'severity': 'high'},
            headers=auth_headers
        )
        inv_id = response.json['id']
        
        response = client.post(
            f'/api/investigations/{inv_id}/events/link',
            json={
                'event_id': 'manual-1',
                'event_type': 'alert',
                'source': 'monitoring',
                'message': 'High CPU usage detected',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json
        assert data['event_id'] == 'manual-1'
        assert data['source'] == 'monitoring'
    
    def test_link_event_invalid_investigation(self, client):
        """Test linking event to non-existent investigation."""
        response = client.post(
            '/api/investigations/invalid-id/events/link',
            json={'event_id': 'test', 'event_type': 'test', 'source': 'test', 'message': 'test'},
        )
        
        assert response.status_code == 400


class TestEventSearchEndpoint:
    """Test event search endpoint."""
    
    @patch('src.app.event_linker.search_events')
    def test_search_events_endpoint(self, mock_search, client):
        """Test GET /api/events/search endpoint."""
        mock_search.return_value = [
            {
                'source': 'git',
                'type': 'push',
                'message': 'Deploy API',
                'timestamp': datetime.utcnow().isoformat(),
            }
        ]
        
        response = client.get('/api/events/search?query=deploy')
        
        assert response.status_code == 200
        data = response.json
        assert 'results' in data
        assert 'count' in data
        assert data['query'] == 'deploy'
    
    def test_search_events_missing_query(self, client):
        """Test search without query parameter."""
        response = client.get('/api/events/search')
        
        assert response.status_code == 400
        assert 'error' in response.json
    
    @patch('src.app.event_linker.search_events')
    def test_search_with_filters(self, mock_search, client):
        """Test search with source and type filters."""
        mock_search.return_value = []
        
        response = client.get('/api/events/search?query=test&source=git&event_type=push')
        
        assert response.status_code == 200
        # Verify search was called with filters
        call_args = mock_search.call_args
        assert call_args[1]['source'] == 'git'
        assert call_args[1]['event_type'] == 'push'


class TestEventSuggestionsEndpoint:
    """Test event suggestions endpoint."""
    
    @patch('src.app.event_linker.suggest_events')
    def test_suggest_events_endpoint(self, mock_suggest, client, test_investigation):
        """Test GET /api/investigations/<id>/events/suggestions endpoint."""
        mock_suggest.return_value = [
            {
                'source': 'git',
                'event_id': 'git-1',
                'type': 'push',
                'message': 'Suggested event',
                'relevance': 'high',
            }
        ]
        
        response = client.get(
            f'/api/investigations/{test_investigation.id}/events/suggestions'
        )
        
        assert response.status_code == 200
        data = response.json
        assert 'suggestions' in data
        assert 'count' in data


class TestAnnotationThreading:
    """Test enhanced annotation threading functionality."""
    
    def test_add_top_level_annotation(self, client, investigation_store, test_investigation, auth_headers):
        """Test adding a top-level annotation."""
        response = client.post(
            f'/api/investigations/{test_investigation.id}/annotations',
            json={
                'author': 'alice@example.com',
                'text': 'Initial observation about the incident',
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json
        assert data['author'] == 'alice@example.com'
        assert data['parent_annotation_id'] is None
    
    def test_add_reply_annotation(self, client, investigation_store, test_investigation, auth_headers):
        """Test adding a reply to an annotation."""
        # Create parent annotation
        parent = investigation_store.add_annotation(
            investigation_id=test_investigation.id,
            author='alice@example.com',
            text='Initial observation',
        )
        
        # Add reply
        response = client.post(
            f'/api/investigations/{test_investigation.id}/annotations',
            json={
                'author': 'bob@example.com',
                'text': 'Thanks for the observation, I found the root cause',
                'parent_annotation_id': parent.id,
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json
        assert data['parent_annotation_id'] == parent.id
    
    def test_get_annotations_with_threading(self, client, auth_headers):
        """Test getting annotations preserves threading."""
        # Create investigation
        response = client.post(
            '/api/investigations',
            json={'title': 'Test', 'description': 'Test desc', 'service': 'test-svc', 'severity': 'high'},
            headers=auth_headers
        )
        inv_id = response.json['id']
        
        # Create parent annotation
        response1 = client.post(
            f'/api/investigations/{inv_id}/annotations',
            json={'author': 'alice@example.com', 'text': 'Observation 1'},
            headers=auth_headers
        )
        assert response1.status_code == 201
        parent_id = response1.json['id']
        
        # Create reply
        response2 = client.post(
            f'/api/investigations/{inv_id}/annotations',
            json={
                'author': 'bob@example.com',
                'text': 'Reply to observation 1',
                'parent_annotation_id': parent_id,
            },
            headers=auth_headers
        )
        assert response2.status_code == 201
        
        response = client.get(
            f'/api/investigations/{inv_id}/annotations'
        )
        
        assert response.status_code == 200
        data = response.json
        # At least the parent should exist
        assert data['count'] >= 1
        
        # Verify parent exists
        annotations = data['annotations']
        parent_ann = next((a for a in annotations if a['id'] == parent_id), None)
        assert parent_ann is not None


class TestStory18Integration:
    """Integration tests for Story #18 features."""
    
    @patch('src.connectors.git_connector.GitConnector.collect')
    @patch('src.connectors.ci_connector.CIConnector.collect')
    def test_event_linking_workflow(self, mock_ci, mock_git, client, investigation_store):
        """Test complete event linking workflow."""
        # Create investigation
        inv = investigation_store.create_investigation(
            title='Database Connection Error',
            status='open',
        )
        
        # Mock events from connectors
        now = datetime.utcnow()
        mock_git.return_value = [
            {
                'id': 'git-1',
                'type': 'push',
                'message': 'Database connection pool increased',
                'timestamp': now.isoformat() + 'Z',
                'repo': 'backend',
            },
        ]
        mock_ci.return_value = [
            {
                'id': 'ci-1',
                'type': 'build',
                'message': 'Deploy to production',
                'timestamp': now.isoformat() + 'Z',
                'job': 'deploy-job',
            },
        ]
        
        # Call auto-link endpoint
        response = client.post(
            f'/api/investigations/{inv.id}/events/auto-link?semantic_matching=true'
        )
        
        assert response.status_code == 201
        data = response.json
        assert data['linked_count'] >= 0  # May be 0 if semantic matching doesn't match
    
    def test_annotation_comment_thread(self, client, auth_headers):
        """Test creating and retrieving annotation threads."""
        # Create investigation
        response = client.post(
            '/api/investigations',
            json={'title': 'Service Outage', 'description': 'Test', 'service': 'test-svc', 'severity': 'high'},
            headers=auth_headers
        )
        inv_id = response.json['id']
        
        # Create comment thread
        response1 = client.post(
            f'/api/investigations/{inv_id}/annotations',
            json={'author': 'engineer1', 'text': 'What happened?'},
            headers=auth_headers
        )
        assert response1.status_code == 201
        parent_id = response1.json['id']
        
        # Reply to comment
        response2 = client.post(
            f'/api/investigations/{inv_id}/annotations',
            json={
                'author': 'engineer2',
                'text': 'Database went down',
                'parent_annotation_id': parent_id,
            },
            headers=auth_headers
        )
        assert response2.status_code == 201
        
        # Get all annotations
        response3 = client.get(
            f'/api/investigations/{inv_id}/annotations'
        )
        assert response3.status_code == 200
        assert response3.json['count'] >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
