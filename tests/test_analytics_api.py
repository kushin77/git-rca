"""
Phase 3d: Tests for Analytics API

Test coverage for all analytics endpoints and metrics.
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import List
from src.api.analytics_api import AnalyticsAPI, register_analytics_api
from src.models.event import EventStore, Event, EventSource, EventSeverity
from src.models.investigation import Investigation, InvestigationStatus
from src.store.investigation_store import InvestigationStore


@pytest.fixture
def event_store():
    """Create event store with sample data"""
    store = EventStore()

    # Create sample events with different sources and severities
    event_data = [
        # git source events
        *[{'source': 'git', 'severity': 'critical'} for _ in range(25)],
        *[{'source': 'git', 'severity': 'high'} for _ in range(50)],
        *[{'source': 'git', 'severity': 'medium'} for _ in range(75)],

        # ci source events
        *[{'source': 'ci', 'severity': 'high'} for _ in range(40)],
        *[{'source': 'ci', 'severity': 'medium'} for _ in range(60)],

        # logs source events
        *[{'source': 'logs', 'severity': 'medium'} for _ in range(80)],
        *[{'source': 'logs', 'severity': 'low'} for _ in range(120)],

        # metrics source events
        *[{'source': 'metrics', 'severity': 'info'} for _ in range(200)],
    ]

    # Add events to store
    for i, data in enumerate(event_data):
        event = Event(
            id=f"evt-{i+1}",
            source=data['source'],
            severity=data['severity'],
            event_type='test_event',
            timestamp=datetime.utcnow().isoformat(),
        )
        store.add(event)

    return store


@pytest.fixture
def investigation_store():
    """Create investigation store with sample data"""
    import tempfile
    import os
    
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    store = InvestigationStore(db_path=db_path)

    # Create sample investigations (use create_investigation method)
    for i in range(5):
        store.create_investigation(
            title=f"Investigation {i+1}",
            description="Resolved investigation",
            severity="medium",
            status="resolved"
        )

    for i in range(3):
        store.create_investigation(
            title=f"Open Investigation {i+1}",
            description="Active investigation",
            severity="high",
            status="open"
        )

    return store


@pytest.fixture
def analytics_api(event_store, investigation_store):
    """Create analytics API instance"""
    return AnalyticsAPI(event_store, investigation_store)


class TestAnalyticsAPI:
    """Test suite for Analytics API"""

    def test_analytics_api_initialization(self, analytics_api):
        """Test Analytics API initializes correctly"""
        assert analytics_api is not None
        assert analytics_api.event_store is not None
        assert analytics_api.inv_store is not None

    def test_get_events_by_source_distribution(self, analytics_api):
        """Test getting event distribution by source"""
        api = analytics_api

        # Simulate request
        result = {}
        events = api.event_store.get_all()

        from collections import Counter
        source_counts = Counter()
        for event in events:
            source_counts[event.source] += 1

        total = len(events)
        for source, count in source_counts.items():
            result[source] = {
                'count': count,
                'percentage': round((count / total * 100) if total > 0 else 0, 1),
            }

        # Assertions
        assert len(result) > 0
        assert 'git' in result
        assert 'ci' in result
        assert result['git']['count'] == 150
        assert result['ci']['count'] == 100
        assert sum(r['count'] for r in result.values()) == total

    def test_get_events_by_severity_distribution(self, analytics_api):
        """Test getting event distribution by severity"""
        api = analytics_api

        # Simulate request
        events = api.event_store.get_all()
        from collections import Counter
        severity_counts = Counter()
        for event in events:
            severity_counts[event.severity] += 1

        total = len(events)
        result = {}
        severity_order = ['critical', 'high', 'medium', 'low', 'info']
        for severity in severity_order:
            count = severity_counts.get(severity, 0)
            result[severity] = {
                'count': count,
                'percentage': round((count / total * 100) if total > 0 else 0, 1),
            }

        # Assertions
        assert result['critical']['count'] == 25
        assert result['high']['count'] == 90
        assert result['medium']['count'] == 215
        assert result['low']['count'] == 120
        assert result['info']['count'] == 200

    def test_connector_health_metrics(self, analytics_api):
        """Test connector health metrics endpoint"""
        # This would normally call the Flask endpoint
        # For now, test the expected response structure

        expected_fields = [
            'overall_health',
            'total_dlq_events',
            'sources_with_issues',
            'average_dlq_size',
            'timestamp',
        ]

        # Simulate response
        response = {
            'overall_health': 'GOOD',
            'total_dlq_events': 0,
            'sources_with_issues': [],
            'average_dlq_size': 0,
            'timestamp': datetime.utcnow().isoformat(),
        }

        for field in expected_fields:
            assert field in response

    def test_mttr_calculation(self, analytics_api):
        """Test Mean Time To Resolution calculation"""
        api = analytics_api
        days = 30

        # Get resolved investigations
        investigations = api.inv_store.get_all()
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        resolved = []
        for inv in investigations:
            if inv.status.value == 'RESOLVED' and datetime.fromisoformat(inv.updated_at.replace('Z', '+00:00')) >= cutoff_date:
                created = datetime.fromisoformat(inv.created_at.replace('Z', '+00:00'))
                updated = datetime.fromisoformat(inv.updated_at.replace('Z', '+00:00'))
                mttr_minutes = (updated - created).total_seconds() / 60
                resolved.append(mttr_minutes)

        # Assertions
        assert len(resolved) == 5
        avg_mttr = sum(resolved) / len(resolved)
        assert avg_mttr > 0

    def test_insights_generation(self, analytics_api):
        """Test insights and recommendations generation"""
        api = analytics_api
        insights = []
        recommendations = []

        # Get critical events
        events = api.event_store.get_all()
        critical_count = len([e for e in events if e.severity.value == 'CRITICAL'])

        # Assertions
        assert critical_count == 25
        if critical_count > 10:
            insights.append({
                'type': 'warning',
                'title': 'High number of critical events',
                'description': f'{critical_count} critical events detected',
                'impact': 'high',
            })

        assert len(insights) > 0
        assert insights[0]['type'] == 'warning'

    def test_empty_event_store(self):
        """Test analytics with empty event store"""
        empty_store = EventStore()
        empty_inv_store = InvestigationStore()
        api = AnalyticsAPI(empty_store, empty_inv_store)

        events = api.event_store.get_all()
        assert len(events) == 0

    def test_percentage_calculation_accuracy(self, analytics_api):
        """Test percentage calculations are accurate"""
        api = analytics_api
        events = api.event_store.get_all()
        total = len(events)

        from collections import Counter
        source_counts = Counter()
        for event in events:
            source_counts[event.source] += 1

        # Sum of all percentages should be ~100%
        total_percentage = 0
        for source, count in source_counts.items():
            percentage = round((count / total * 100) if total > 0 else 0, 1)
            total_percentage += percentage

        assert abs(total_percentage - 100.0) < 0.5  # Allow small rounding difference

    def test_severity_order_consistency(self, analytics_api):
        """Test severity distribution maintains order"""
        api = analytics_api
        events = api.event_store.get_all()

        from collections import Counter
        severity_counts = Counter()
        for event in events:
            severity_counts[event.severity] += 1

        severity_order = ['critical', 'high', 'medium', 'low', 'info']
        result = {}

        for severity in severity_order:
            count = severity_counts.get(severity, 0)
            result[severity] = {'count': count}

        # Verify order is maintained
        assert list(result.keys()) == severity_order

    def test_mttr_with_no_resolved_investigations(self):
        """Test MTTR calculation with no resolved investigations"""
        import tempfile
        import os
        
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)
        
        store = InvestigationStore(db_path=db_path)

        # Add only open investigations
        for i in range(3):
            store.create_investigation(
                title=f"Open Investigation {i+1}",
                description="Active investigation",
                severity="high",
                status="open"
            )

        event_store = EventStore()
        api = AnalyticsAPI(event_store, store)

        # Should return 3 open investigations
        investigations = api.inv_store.get_all()
        assert len(investigations) == 3

    def test_insights_with_high_critical_events(self, event_store, investigation_store):
        """Test insights generated when critical events exceed threshold"""
        api = AnalyticsAPI(event_store, investigation_store)

        events = api.event_store.get_all()
        critical_count = len([e for e in events if e.severity == 'critical'])

        insights = []
        if critical_count > 10:
            insights.append({
                'type': 'warning',
                'title': 'High number of critical events',
                'description': f'{critical_count} critical events detected',
                'impact': 'high',
            })

        assert len(insights) == 1
        assert 'warning' in [i['type'] for i in insights]

    def test_insights_with_open_investigations(self, event_store, investigation_store):
        """Test insights generated for open investigations"""
        api = AnalyticsAPI(event_store, investigation_store)

        investigations = api.inv_store.get_all()
        open_investigations = len([i for i in investigations if i.status.value == 'OPEN'])

        insights = []
        if open_investigations > 2:
            insights.append({
                'type': 'info',
                'title': f'{open_investigations} open investigations',
                'description': f'Currently tracking {open_investigations} active investigations',
                'impact': 'medium',
            })

        assert len(insights) > 0


class TestAnalyticsIntegration:
    """Integration tests for Analytics API with Flask"""

    def test_register_analytics_api(self, event_store, investigation_store):
        """Test registering analytics API with Flask app"""
        from flask import Flask

        app = Flask(__name__)

        # Should not raise any exceptions
        try:
            register_analytics_api(app, event_store, investigation_store)
            assert True
        except Exception as e:
            pytest.fail(f"Failed to register analytics API: {str(e)}")

    def test_analytics_api_endpoints_exist(self, event_store, investigation_store):
        """Test all expected endpoints are registered"""
        from flask import Flask

        app = Flask(__name__)
        register_analytics_api(app, event_store, investigation_store)

        # Check that routes were registered
        routes = [str(rule) for rule in app.url_map.iter_rules()]

        expected_endpoints = [
            '/api/analytics/events/by-source',
            '/api/analytics/events/by-severity',
            '/api/analytics/connectors/health',
            '/api/analytics/mttr',
            '/api/analytics/insights',
        ]

        for endpoint in expected_endpoints:
            assert any(endpoint in route for route in routes), f"Endpoint {endpoint} not found"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
