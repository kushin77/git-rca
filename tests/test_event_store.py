"""
Tests for Event Store - Database persistence and querying

Test cases for:
- Event creation and retrieval
- Event updates and soft deletes
- Advanced queries (by source, severity, timestamp, tags)
- Event-Investigation linking
"""

import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from src.models.event import Event, EventSource, EventSeverity
from src.store.event_store import EventStore


@pytest.fixture
def event_store():
    """Create a test event store with fresh database."""
    db_path = "data/test_events.db"
    # Clean up any existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    store = EventStore(db_path)
    yield store
    
    # Clean up after test
    if os.path.exists(db_path):
        os.remove(db_path)


class TestEventStoreCreation:
    """Test event creation and retrieval."""
    
    def test_create_event(self, event_store):
        """Test creating a new event."""
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.GIT,
            event_type="commit",
        )
        
        result = event_store.create_event(event)
        assert result is True
        
        # Verify we can retrieve it
        retrieved = event_store.get_event(event.id)
        assert retrieved is not None
        assert retrieved.id == event.id
        assert retrieved.event_type == "commit"
    
    def test_create_duplicate_event(self, event_store):
        """Test that creating duplicate events fails gracefully."""
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.CI,
            event_type="build",
            source_id="build-123",
        )
        
        # First create should succeed
        assert event_store.create_event(event) is True
        
        # Second create should fail (duplicate)
        assert event_store.create_event(event) is False
    
    def test_get_nonexistent_event(self, event_store):
        """Test retrieving a non-existent event."""
        result = event_store.get_event("nonexistent-id")
        assert result is None
    
    def test_create_event_with_all_fields(self, event_store):
        """Test creating event with all fields."""
        now = datetime.utcnow().isoformat()
        event = Event(
            timestamp=now,
            source=EventSource.METRICS,
            event_type="cpu_spike",
            severity=EventSeverity.CRITICAL,
            data={"cpu": 95.2, "threshold": 80},
            tags=["performance", "alert"],
            investigation_ids=["inv-001"],
            source_id="metric-001",
            metadata={"host": "prod-01"},
        )
        
        assert event_store.create_event(event) is True
        
        retrieved = event_store.get_event(event.id)
        assert retrieved.source == EventSource.METRICS
        assert retrieved.severity == EventSeverity.CRITICAL
        assert retrieved.data["cpu"] == 95.2
        assert "performance" in retrieved.tags


class TestEventStoreQueries:
    """Test advanced event queries."""
    
    def test_get_events_by_source(self, event_store):
        """Test querying events by source."""
        now = datetime.utcnow().isoformat()
        
        # Create events from different sources
        git_event = Event(timestamp=now, source=EventSource.GIT, event_type="commit")
        ci_event = Event(timestamp=now, source=EventSource.CI, event_type="build")
        logs_event = Event(timestamp=now, source=EventSource.LOGS, event_type="error")
        
        event_store.create_event(git_event)
        event_store.create_event(ci_event)
        event_store.create_event(logs_event)
        
        # Query by source
        git_events = event_store.get_events_by_source(EventSource.GIT)
        assert len(git_events) == 1
        assert git_events[0].source == EventSource.GIT
        
        ci_events = event_store.get_events_by_source(EventSource.CI)
        assert len(ci_events) == 1
        assert ci_events[0].source == EventSource.CI
    
    def test_get_events_by_severity(self, event_store):
        """Test querying events by severity."""
        now = datetime.utcnow().isoformat()
        
        # Create events with different severities
        critical = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            severity=EventSeverity.CRITICAL,
        )
        high = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="warning",
            severity=EventSeverity.HIGH,
        )
        
        event_store.create_event(critical)
        event_store.create_event(high)
        
        # Query by severity
        critical_events = event_store.get_events_by_severity(EventSeverity.CRITICAL)
        assert len(critical_events) == 1
        assert critical_events[0].severity == EventSeverity.CRITICAL
        
        high_events = event_store.get_events_by_severity(EventSeverity.HIGH)
        assert len(high_events) == 1
    
    def test_get_events_by_tag(self, event_store):
        """Test querying events by tag."""
        now = datetime.utcnow().isoformat()
        
        event1 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            tags=["database", "critical"],
        )
        event2 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="warning",
            tags=["api", "timeout"],
        )
        event3 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="info",
            tags=["database", "maintenance"],
        )
        
        event_store.create_event(event1)
        event_store.create_event(event2)
        event_store.create_event(event3)
        
        # Query by tag
        db_events = event_store.get_events_by_tag("database")
        assert len(db_events) == 2
        assert all("database" in e.tags for e in db_events)
    
    def test_get_events_by_timestamp_range(self, event_store):
        """Test querying events by timestamp range."""
        base = datetime.utcnow()
        
        event1 = Event(
            timestamp=(base - timedelta(hours=2)).isoformat(),
            source=EventSource.LOGS,
            event_type="error",
        )
        event2 = Event(
            timestamp=base.isoformat(),
            source=EventSource.LOGS,
            event_type="error",
        )
        event3 = Event(
            timestamp=(base + timedelta(hours=2)).isoformat(),
            source=EventSource.LOGS,
            event_type="error",
        )
        
        event_store.create_event(event1)
        event_store.create_event(event2)
        event_store.create_event(event3)
        
        # Query within range
        start = (base - timedelta(hours=1)).isoformat()
        end = (base + timedelta(hours=1)).isoformat()
        
        events = event_store.get_events_by_timestamp_range(start, end)
        assert len(events) == 1
        assert events[0].id == event2.id
    
    def test_search_events_with_multiple_filters(self, event_store):
        """Test advanced search with multiple filters."""
        now = datetime.utcnow().isoformat()
        
        # Create variety of events
        event1 = Event(
            timestamp=now,
            source=EventSource.GIT,
            event_type="commit",
            severity=EventSeverity.LOW,
            tags=["vcs"],
        )
        event2 = Event(
            timestamp=now,
            source=EventSource.METRICS,
            event_type="cpu_spike",
            severity=EventSeverity.CRITICAL,
            tags=["performance"],
        )
        event3 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            severity=EventSeverity.CRITICAL,
            tags=["api"],
        )
        
        event_store.create_event(event1)
        event_store.create_event(event2)
        event_store.create_event(event3)
        
        # Search: CRITICAL severity + METRICS source
        results = event_store.search_events(
            source=EventSource.METRICS,
            severity=EventSeverity.CRITICAL,
        )
        assert len(results) == 1
        assert results[0].source == EventSource.METRICS
        
        # Search: CRITICAL severity (all sources)
        results = event_store.search_events(severity=EventSeverity.CRITICAL)
        assert len(results) == 2
        
        # Search: With tag filter
        results = event_store.search_events(tag="api")
        assert len(results) == 1
        assert results[0].event_type == "error"


class TestEventStoreUpdates:
    """Test event updates."""
    
    def test_update_event(self, event_store):
        """Test updating event fields."""
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.LOGS,
            event_type="error",
            severity=EventSeverity.MEDIUM,
        )
        
        event_store.create_event(event)
        
        # Update severity
        result = event_store.update_event(event.id, {
            'severity': EventSeverity.CRITICAL
        })
        assert result is True
        
        # Verify update
        updated = event_store.get_event(event.id)
        assert updated.severity == EventSeverity.CRITICAL
    
    def test_link_event_to_investigation(self, event_store):
        """Test linking event to investigation."""
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.GIT,
            event_type="commit",
        )
        
        event_store.create_event(event)
        
        # Link to investigation
        result = event_store.link_event_to_investigation(event.id, "inv-001")
        assert result is True
        
        # Verify link
        updated = event_store.get_event(event.id)
        assert "inv-001" in updated.investigation_ids
        assert updated.linked_at is not None


class TestEventStoreDeletion:
    """Test soft delete functionality."""
    
    def test_soft_delete_event(self, event_store):
        """Test soft-deleting an event."""
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.LOGS,
            event_type="error",
        )
        
        event_store.create_event(event)
        
        # Soft delete
        result = event_store.delete_event(event.id)
        assert result is True
        
        # Should not appear in queries
        all_events = event_store.get_all_events(include_deleted=False)
        assert all(e.id != event.id for e in all_events)
        
        # But should appear when including deleted
        all_events = event_store.get_all_events(include_deleted=True)
        assert any(e.id == event.id for e in all_events)
    
    def test_restore_event(self, event_store):
        """Test restoring a soft-deleted event."""
        event = Event(
            timestamp=datetime.utcnow().isoformat(),
            source=EventSource.LOGS,
            event_type="error",
        )
        
        event_store.create_event(event)
        event_store.delete_event(event.id)
        
        # Restore
        result = event_store.restore_event(event.id)
        assert result is True
        
        # Should appear in queries again
        all_events = event_store.get_all_events(include_deleted=False)
        assert any(e.id == event.id for e in all_events)


class TestEventStoreRetrieval:
    """Test various retrieval operations."""
    
    def test_get_all_events(self, event_store):
        """Test retrieving all events."""
        now = datetime.utcnow().isoformat()
        
        for i in range(5):
            event = Event(
                timestamp=now,
                source=EventSource.LOGS,
                event_type=f"event-{i}",
            )
            event_store.create_event(event)
        
        all_events = event_store.get_all_events()
        assert len(all_events) == 5
    
    def test_get_events_by_investigation(self, event_store):
        """Test retrieving events linked to investigation."""
        now = datetime.utcnow().isoformat()
        
        # Create events with investigation links
        event1 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            investigation_ids=["inv-001"],
        )
        event2 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            investigation_ids=["inv-001", "inv-002"],
        )
        event3 = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            investigation_ids=["inv-002"],
        )
        
        event_store.create_event(event1)
        event_store.create_event(event2)
        event_store.create_event(event3)
        
        # Query by investigation
        inv_events = event_store.get_events_by_investigation("inv-001")
        assert len(inv_events) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
