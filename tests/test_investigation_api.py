"""
Tests for Investigation API Backend

Tests the SQLAlchemy models, SQL store, and Flask API endpoints.
Covers CRUD operations, filtering, and data integrity.
"""

import pytest
import os
import tempfile
from datetime import datetime

from src.models.investigation import Investigation, InvestigationEvent, Annotation
from src.store.investigation_store import InvestigationStore


class TestInvestigationModel:
    """Test Investigation domain model."""

    def test_create_investigation(self):
        """Test creating an investigation."""
        inv = Investigation(
            id="inv-001",
            title="Test Investigation",
            status="open",
            severity="high",
        )
        assert inv.id == "inv-001"
        assert inv.title == "Test Investigation"
        assert inv.status == "open"
        assert inv.severity == "high"

    def test_investigation_to_dict(self):
        """Test converting investigation to dictionary."""
        inv = Investigation(
            id="inv-001",
            title="Test",
            status="open",
            severity="high",
            root_cause="Bug in code",
        )
        data = inv.to_dict()
        assert data["id"] == "inv-001"
        assert data["title"] == "Test"
        assert data["root_cause"] == "Bug in code"

    def test_investigation_from_dict(self):
        """Test creating investigation from dictionary."""
        data = {
            "id": "inv-001",
            "title": "Test",
            "status": "open",
            "severity": "high",
        }
        inv = Investigation.from_dict(data)
        assert inv.id == "inv-001"
        assert inv.title == "Test"

    def test_investigation_update(self):
        """Test updating investigation fields."""
        inv = Investigation(id="inv-001", title="Test")
        original_created = inv.created_at
        original_updated = inv.updated_at

        inv.update(title="Updated", status="closed")
        assert inv.title == "Updated"
        assert inv.status == "closed"
        assert inv.created_at == original_created  # Created should not change
        assert inv.updated_at > original_updated  # Updated should change


class TestAnnotationModel:
    """Test Annotation domain model."""

    def test_create_annotation(self):
        """Test creating an annotation."""
        ann = Annotation(
            id="ann-001",
            investigation_id="inv-001",
            author="Alice",
            text="This is a note",
        )
        assert ann.id == "ann-001"
        assert ann.author == "Alice"
        assert ann.text == "This is a note"

    def test_annotation_threading(self):
        """Test annotation reply threading."""
        parent = Annotation(
            id="ann-001",
            investigation_id="inv-001",
            author="Alice",
            text="Parent note",
        )
        reply = Annotation(
            id="ann-002",
            investigation_id="inv-001",
            author="Bob",
            text="Reply note",
            parent_annotation_id="ann-001",
        )
        assert reply.parent_annotation_id == "ann-001"

    def test_annotation_update(self):
        """Test updating annotation text."""
        ann = Annotation(
            id="ann-001",
            investigation_id="inv-001",
            author="Alice",
            text="Original",
        )
        original_updated = ann.updated_at
        ann.update("Updated")
        assert ann.text == "Updated"
        assert ann.updated_at > original_updated


class TestInvestigationStore:
    """Test Investigation SQL data store."""

    @pytest.fixture
    def store(self):
        """Create temporary store for testing."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            db_path = f.name

        store = InvestigationStore(db_path=db_path)
        yield store

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_store_initialization(self, store):
        """Test that store initializes database."""
        # If we can create an investigation, initialization worked
        inv = store.create_investigation(title="Test")
        assert inv.id is not None

    def test_create_investigation(self, store):
        """Test creating an investigation in store."""
        inv = store.create_investigation(
            title="Payment Processing Timeout",
            status="open",
            severity="high",
            description="Payment service timeout",
            impact="Customers unable to pay",
        )
        assert inv.id is not None
        assert inv.title == "Payment Processing Timeout"
        assert inv.status == "open"
        assert inv.severity == "high"
        assert inv.created_at is not None

    def test_get_investigation(self, store):
        """Test retrieving an investigation."""
        created = store.create_investigation(
            title="Test Investigation",
            severity="critical",
        )
        retrieved = store.get_investigation(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test Investigation"
        assert retrieved.severity == "critical"

    def test_get_nonexistent_investigation(self, store):
        """Test retrieving nonexistent investigation."""
        inv = store.get_investigation("nonexistent")
        assert inv is None

    def test_list_investigations(self, store):
        """Test listing investigations."""
        store.create_investigation(title="Investigation 1", severity="high")
        store.create_investigation(title="Investigation 2", severity="medium")
        store.create_investigation(title="Investigation 3", severity="critical")

        investigations = store.list_investigations()
        assert len(investigations) >= 3
        assert all(isinstance(inv, Investigation) for inv in investigations)

    def test_list_investigations_with_severity_filter(self, store):
        """Test filtering investigations by severity."""
        store.create_investigation(title="Critical Issue", severity="critical")
        store.create_investigation(title="High Issue", severity="high")
        store.create_investigation(title="Medium Issue", severity="medium")

        critical = store.list_investigations(severity="critical")
        assert all(inv.severity == "critical" for inv in critical)

    def test_list_investigations_with_status_filter(self, store):
        """Test filtering investigations by status."""
        store.create_investigation(title="Open", status="open")
        store.create_investigation(title="Closed", status="closed")

        open_invs = store.list_investigations(status="open")
        assert all(inv.status == "open" for inv in open_invs)

    def test_update_investigation(self, store):
        """Test updating an investigation."""
        inv = store.create_investigation(title="Original Title")

        updated = store.update_investigation(
            inv.id,
            title="Updated Title",
            status="closed",
            root_cause="Found the bug",
        )
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.status == "closed"
        assert updated.root_cause == "Found the bug"

    def test_update_nonexistent_investigation(self, store):
        """Test updating nonexistent investigation."""
        result = store.update_investigation("nonexistent", title="New Title")
        assert result is None

    def test_delete_investigation(self, store):
        """Test deleting an investigation."""
        inv = store.create_investigation(title="To Delete")

        deleted = store.delete_investigation(inv.id)
        assert deleted is True

        retrieved = store.get_investigation(inv.id)
        assert retrieved is None

    def test_delete_nonexistent_investigation(self, store):
        """Test deleting nonexistent investigation."""
        deleted = store.delete_investigation("nonexistent")
        assert deleted is False

    def test_add_event_to_investigation(self, store):
        """Test linking an event to investigation."""
        inv = store.create_investigation(title="Investigation")

        event = store.add_event(
            investigation_id=inv.id,
            event_id="git-commit-123",
            event_type="git_commit",
            source="Git",
            message="Deployed new version",
            timestamp="2025-01-27T10:00:00Z",
        )
        assert event.id is not None
        assert event.investigation_id == inv.id
        assert event.event_type == "git_commit"

    def test_get_investigation_events(self, store):
        """Test retrieving events for investigation."""
        inv = store.create_investigation(title="Investigation")

        store.add_event(
            investigation_id=inv.id,
            event_id="git-1",
            event_type="git_commit",
            source="Git",
            message="Commit 1",
            timestamp="2025-01-27T10:00:00Z",
        )
        store.add_event(
            investigation_id=inv.id,
            event_id="ci-1",
            event_type="ci_build",
            source="Jenkins",
            message="Build 1",
            timestamp="2025-01-27T11:00:00Z",
        )

        events = store.get_investigation_events(inv.id)
        assert len(events) == 2
        assert all(isinstance(e, InvestigationEvent) for e in events)

    def test_add_annotation(self, store):
        """Test adding annotation to investigation."""
        inv = store.create_investigation(title="Investigation")

        ann = store.add_annotation(
            investigation_id=inv.id,
            author="Alice",
            text="This looks like a deployment issue",
        )
        assert ann.id is not None
        assert ann.author == "Alice"
        assert ann.investigation_id == inv.id

    def test_add_threaded_annotation(self, store):
        """Test adding reply to annotation."""
        inv = store.create_investigation(title="Investigation")

        parent = store.add_annotation(
            investigation_id=inv.id,
            author="Alice",
            text="Parent note",
        )

        reply = store.add_annotation(
            investigation_id=inv.id,
            author="Bob",
            text="I agree",
            parent_annotation_id=parent.id,
        )
        assert reply.parent_annotation_id == parent.id

    def test_get_annotations(self, store):
        """Test retrieving annotations."""
        inv = store.create_investigation(title="Investigation")

        store.add_annotation(inv.id, "Alice", "Note 1")
        store.add_annotation(inv.id, "Bob", "Note 2")

        annotations = store.get_annotations(inv.id)
        assert len(annotations) == 2
        assert all(isinstance(a, Annotation) for a in annotations)

    def test_get_threaded_annotations(self, store):
        """Test retrieving replies to annotation."""
        inv = store.create_investigation(title="Investigation")

        parent = store.add_annotation(inv.id, "Alice", "Parent")
        store.add_annotation(inv.id, "Bob", "Reply 1", parent_annotation_id=parent.id)
        store.add_annotation(inv.id, "Carol", "Reply 2", parent_annotation_id=parent.id)

        replies = store.get_annotations(inv.id, parent_annotation_id=parent.id)
        assert len(replies) == 2
        assert all(a.parent_annotation_id == parent.id for a in replies)

    def test_update_annotation(self, store):
        """Test updating annotation text."""
        inv = store.create_investigation(title="Investigation")
        ann = store.add_annotation(inv.id, "Alice", "Original")

        updated = store.update_annotation(ann.id, "Updated text")
        assert updated is not None
        assert updated.text == "Updated text"

    def test_delete_annotation(self, store):
        """Test deleting annotation."""
        inv = store.create_investigation(title="Investigation")
        ann = store.add_annotation(inv.id, "Alice", "Note")

        deleted = store.delete_annotation(ann.id)
        assert deleted is True

    def test_cascade_delete(self, store):
        """Test that deleting investigation cascades to events and annotations."""
        inv = store.create_investigation(title="Investigation")

        # Add event and annotation
        event = store.add_event(
            inv.id, "evt-1", "git_commit", "Git", "Commit", "2025-01-27T10:00:00Z"
        )
        ann = store.add_annotation(inv.id, "Alice", "Note")

        # Delete investigation
        store.delete_investigation(inv.id)

        # Verify related data is gone
        assert store.get_investigation(inv.id) is None
        assert len(store.get_investigation_events(inv.id)) == 0
        assert len(store.get_annotations(inv.id)) == 0
