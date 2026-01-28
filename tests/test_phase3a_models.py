"""
Tests for Phase 3a - Expanded Investigation & Event Models

Test cases for:
- Expanded Investigation model (12+ new fields)
- Event model with multiple signal sources
- Event-Investigation linking
- Field validation and constraints
- Soft delete functionality
"""

import pytest
from datetime import datetime, timedelta
from src.models.investigation import (
    Investigation,
    InvestigationStatus,
    ImpactSeverity,
    Priority,
)
from src.models.event import Event, EventSource, EventSeverity


class TestInvestigationModel:
    """Test cases for expanded Investigation model."""

    def test_investigation_creation_minimal(self):
        """Test creating investigation with minimal required fields."""
        inv = Investigation(
            id="inv-001",
            title="Database outage",
        )

        assert inv.id == "inv-001"
        assert inv.title == "Database outage"
        assert inv.status == InvestigationStatus.OPEN
        assert inv.impact_severity == ImpactSeverity.MEDIUM
        assert inv.is_active()
        assert len(inv.tags) == 0
        assert len(inv.event_ids) == 0

    def test_investigation_creation_full(self):
        """Test creating investigation with all fields."""
        now = datetime.utcnow().isoformat()

        inv = Investigation(
            id="inv-002",
            title="API timeout",
            description="Users experiencing 500 errors",
            status=InvestigationStatus.IN_PROGRESS,
            impact_severity=ImpactSeverity.CRITICAL,
            detected_at=now,
            started_at=now,
            root_cause="Database query timeout",
            remediation="Add query timeout handling",
            lessons_learned="Implement query optimization",
            component_affected="api-gateway",
            service_affected="production",
            tags=["database", "timeout"],
            event_ids=["evt-001"],
            created_by="alice@example.com",
            assigned_to="bob@example.com",
            priority=Priority.P0,
        )

        assert inv.title == "API timeout"
        assert inv.status == InvestigationStatus.IN_PROGRESS
        assert inv.impact_severity == ImpactSeverity.CRITICAL
        assert inv.component_affected == "api-gateway"
        assert "database" in inv.tags
        assert "evt-001" in inv.event_ids
        assert inv.priority == Priority.P0
        assert inv.assigned_to == "bob@example.com"

    def test_investigation_root_cause_length_validation(self):
        """Test that root_cause field has 2000 character limit."""
        with pytest.raises(ValueError, match="root_cause must be <= 2000"):
            Investigation(id="inv-003", title="Test", root_cause="x" * 2001)

    def test_investigation_remediation_length_validation(self):
        """Test that remediation field has 2000 character limit."""
        with pytest.raises(ValueError, match="remediation must be <= 2000"):
            Investigation(id="inv-004", title="Test", remediation="x" * 2001)

    def test_investigation_lessons_learned_length_validation(self):
        """Test that lessons_learned field has 2000 character limit."""
        with pytest.raises(ValueError, match="lessons_learned must be <= 2000"):
            Investigation(id="inv-005", title="Test", lessons_learned="x" * 2001)

    def test_investigation_add_tag(self):
        """Test adding tags to investigation."""
        inv = Investigation(id="inv-006", title="Test")

        inv.add_tag("urgent")
        assert "urgent" in inv.tags

        # Adding same tag twice should not duplicate
        inv.add_tag("urgent")
        assert inv.tags.count("urgent") == 1

    def test_investigation_remove_tag(self):
        """Test removing tags from investigation."""
        inv = Investigation(id="inv-007", title="Test", tags=["urgent", "database"])

        inv.remove_tag("urgent")
        assert "urgent" not in inv.tags
        assert "database" in inv.tags

    def test_investigation_link_event(self):
        """Test linking events to investigation."""
        inv = Investigation(id="inv-008", title="Test")

        inv.link_event("evt-001")
        assert "evt-001" in inv.event_ids

        # Linking same event twice should not duplicate
        inv.link_event("evt-001")
        assert inv.event_ids.count("evt-001") == 1

    def test_investigation_unlink_event(self):
        """Test unlinking events from investigation."""
        inv = Investigation(
            id="inv-009", title="Test", event_ids=["evt-001", "evt-002"]
        )

        inv.unlink_event("evt-001")
        assert "evt-001" not in inv.event_ids
        assert "evt-002" in inv.event_ids

    def test_investigation_link_investigation(self):
        """Test linking related investigations."""
        inv = Investigation(id="inv-010", title="Test")

        inv.link_investigation("inv-011")
        assert "inv-011" in inv.related_investigation_ids

        # Linking same investigation twice should not duplicate
        inv.link_investigation("inv-011")
        assert inv.related_investigation_ids.count("inv-011") == 1

    def test_investigation_soft_delete(self):
        """Test soft-delete functionality."""
        inv = Investigation(id="inv-012", title="Test")
        assert inv.is_active()

        inv.soft_delete()
        assert not inv.is_active()
        assert inv.deleted_at is not None

    def test_investigation_restore(self):
        """Test restoring soft-deleted investigation."""
        inv = Investigation(id="inv-013", title="Test")
        inv.soft_delete()

        inv.restore()
        assert inv.is_active()
        assert inv.deleted_at is None

    def test_investigation_update(self):
        """Test updating investigation fields."""
        inv = Investigation(id="inv-014", title="Original title")
        original_created_at = inv.created_at

        inv.update(
            title="Updated title",
            status=InvestigationStatus.RESOLVED,
            root_cause="Found the bug",
        )

        assert inv.title == "Updated title"
        assert inv.status == InvestigationStatus.RESOLVED
        assert inv.root_cause == "Found the bug"
        assert inv.created_at == original_created_at  # Immutable
        assert inv.updated_at > original_created_at  # Updated

    def test_investigation_to_dict(self):
        """Test converting investigation to dictionary."""
        inv = Investigation(
            id="inv-015",
            title="Test",
            component_affected="service-a",
            tags=["tag1"],
            event_ids=["evt-001"],
        )

        data = inv.to_dict()
        assert data["id"] == "inv-015"
        assert data["title"] == "Test"
        assert data["component_affected"] == "service-a"
        assert "tag1" in data["tags"]
        assert "evt-001" in data["event_ids"]
        assert data["deleted_at"] is None

    def test_investigation_from_dict(self):
        """Test creating investigation from dictionary."""
        data = {
            "id": "inv-016",
            "title": "Test Incident",
            "status": InvestigationStatus.IN_PROGRESS,
            "impact_severity": ImpactSeverity.HIGH,
            "component_affected": "api-service",
            "priority": Priority.P1,
        }

        inv = Investigation.from_dict(data)
        assert inv.id == "inv-016"
        assert inv.title == "Test Incident"
        assert inv.status == InvestigationStatus.IN_PROGRESS
        assert inv.component_affected == "api-service"

    def test_investigation_timestamp_updates(self):
        """Test that updated_at is updated when fields change."""
        inv = Investigation(id="inv-017", title="Test")
        original_updated_at = inv.updated_at

        # Small delay to ensure timestamp differs
        import time

        time.sleep(0.01)

        inv.add_tag("new-tag")
        assert inv.updated_at > original_updated_at


class TestEventModel:
    """Test cases for Event model."""

    def test_event_creation_minimal(self):
        """Test creating event with minimal required fields."""
        now = datetime.utcnow().isoformat()

        event = Event(
            timestamp=now,
            source=EventSource.GIT,
            event_type="commit",
        )

        assert event.timestamp == now
        assert event.source == EventSource.GIT
        assert event.event_type == "commit"
        assert event.severity == EventSeverity.MEDIUM
        assert event.is_active()
        assert len(event.tags) == 0

    def test_event_creation_full(self):
        """Test creating event with all fields."""
        now = datetime.utcnow().isoformat()

        event = Event(
            timestamp=now,
            source=EventSource.METRICS,
            event_type="cpu_spike",
            severity=EventSeverity.CRITICAL,
            data={"cpu_percent": 95.2, "threshold": 80},
            tags=["metrics", "performance"],
            investigation_ids=["inv-001"],
            source_id="metric-12345",
            metadata={"host": "prod-01"},
        )

        assert event.source == EventSource.METRICS
        assert event.event_type == "cpu_spike"
        assert event.severity == EventSeverity.CRITICAL
        assert event.data["cpu_percent"] == 95.2
        assert "metrics" in event.tags
        assert "inv-001" in event.investigation_ids

    def test_event_sources(self):
        """Test all supported event sources."""
        now = datetime.utcnow().isoformat()

        sources = [
            EventSource.GIT,
            EventSource.CI,
            EventSource.LOGS,
            EventSource.METRICS,
            EventSource.TRACES,
            EventSource.MANUAL,
        ]

        for source in sources:
            event = Event(timestamp=now, source=source, event_type="test")
            assert event.source == source

    def test_event_severities(self):
        """Test all supported event severities."""
        now = datetime.utcnow().isoformat()

        severities = [
            EventSeverity.CRITICAL,
            EventSeverity.HIGH,
            EventSeverity.MEDIUM,
            EventSeverity.LOW,
            EventSeverity.INFO,
        ]

        for severity in severities:
            event = Event(
                timestamp=now,
                source=EventSource.LOGS,
                event_type="test",
                severity=severity,
            )
            assert event.severity == severity

    def test_event_link_to_investigation(self):
        """Test linking event to investigation."""
        now = datetime.utcnow().isoformat()
        event = Event(timestamp=now, source=EventSource.GIT, event_type="commit")

        event.link_to_investigation("inv-001")
        assert "inv-001" in event.investigation_ids
        assert event.linked_at is not None

    def test_event_unlink_from_investigation(self):
        """Test unlinking event from investigation."""
        now = datetime.utcnow().isoformat()
        event = Event(
            timestamp=now,
            source=EventSource.GIT,
            event_type="commit",
            investigation_ids=["inv-001", "inv-002"],
        )

        event.unlink_from_investigation("inv-001")
        assert "inv-001" not in event.investigation_ids
        assert "inv-002" in event.investigation_ids

    def test_event_add_tag(self):
        """Test adding tags to event."""
        now = datetime.utcnow().isoformat()
        event = Event(timestamp=now, source=EventSource.LOGS, event_type="error")

        event.add_tag("critical")
        assert "critical" in event.tags

        # Adding same tag twice should not duplicate
        event.add_tag("critical")
        assert event.tags.count("critical") == 1

    def test_event_remove_tag(self):
        """Test removing tags from event."""
        now = datetime.utcnow().isoformat()
        event = Event(
            timestamp=now,
            source=EventSource.LOGS,
            event_type="error",
            tags=["critical", "database"],
        )

        event.remove_tag("critical")
        assert "critical" not in event.tags
        assert "database" in event.tags

    def test_event_soft_delete(self):
        """Test soft-delete functionality."""
        now = datetime.utcnow().isoformat()
        event = Event(timestamp=now, source=EventSource.LOGS, event_type="test")
        assert event.is_active()

        event.soft_delete()
        assert not event.is_active()
        assert event.deleted_at is not None

    def test_event_restore(self):
        """Test restoring soft-deleted event."""
        now = datetime.utcnow().isoformat()
        event = Event(timestamp=now, source=EventSource.LOGS, event_type="test")
        event.soft_delete()

        event.restore()
        assert event.is_active()
        assert event.deleted_at is None

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        now = datetime.utcnow().isoformat()
        event = Event(
            timestamp=now,
            source=EventSource.CI,
            event_type="build_failure",
            severity=EventSeverity.HIGH,
            tags=["ci", "deployment"],
        )

        data = event.to_dict()
        assert data["source"] == EventSource.CI
        assert data["event_type"] == "build_failure"
        assert data["severity"] == EventSeverity.HIGH
        assert "ci" in data["tags"]

    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        now = datetime.utcnow().isoformat()
        data = {
            "timestamp": now,
            "source": EventSource.GIT,
            "event_type": "push",
            "severity": EventSeverity.MEDIUM,
            "tags": ["vcs"],
        }

        event = Event.from_dict(data)
        assert event.source == EventSource.GIT
        assert event.event_type == "push"
        assert "vcs" in event.tags

    def test_event_auto_generated_fields(self):
        """Test that id and timestamps are auto-generated."""
        now = datetime.utcnow().isoformat()
        event = Event(timestamp=now, source=EventSource.LOGS, event_type="test")

        assert event.id is not None
        assert len(event.id) > 0
        assert event.created_at is not None
        assert event.parsed_at is not None


class TestEventInvestigationLinking:
    """Test cases for Event-Investigation relationships."""

    def test_link_multiple_events_to_investigation(self):
        """Test linking multiple events to single investigation."""
        now = datetime.utcnow().isoformat()
        inv = Investigation(id="inv-100", title="Multi-event incident")

        for i in range(5):
            inv.link_event(f"evt-{i}")

        assert len(inv.event_ids) == 5
        for i in range(5):
            assert f"evt-{i}" in inv.event_ids

    def test_link_investigation_to_event(self):
        """Test linking investigation to event."""
        now = datetime.utcnow().isoformat()
        event = Event(timestamp=now, source=EventSource.LOGS, event_type="error")
        inv = Investigation(id="inv-101", title="Test")

        event.link_to_investigation(inv.id)
        assert inv.id in event.investigation_ids

    def test_event_investigation_bidirectional_linking(self):
        """Test that both sides of relationship can be tracked."""
        now = datetime.utcnow().isoformat()
        inv = Investigation(id="inv-102", title="Test")
        event = Event(timestamp=now, source=EventSource.GIT, event_type="commit")

        # Link from investigation side
        inv.link_event(event.id)
        # Link from event side
        event.link_to_investigation(inv.id)

        assert event.id in inv.event_ids
        assert inv.id in event.investigation_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
