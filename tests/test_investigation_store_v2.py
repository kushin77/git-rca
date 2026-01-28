"""
Tests for Investigation Store (Phase 3a Enhanced)

Test cases for:
- Investigation creation with 20+ fields
- Advanced queries (by component, service, priority, severity)
- Update, delete, restore operations
- Soft delete functionality
"""

import pytest
import os
import sqlite3
from src.models.investigation import (
    Investigation,
    InvestigationStatus,
    ImpactSeverity,
    Priority,
)
from src.store.investigation_store_v2 import InvestigationStore


@pytest.fixture
def inv_store():
    """Create a test investigation store with fresh database."""
    db_path = "data/test_investigations.db"
    # Clean up any existing test database
    if os.path.exists(db_path):
        os.remove(db_path)

    store = InvestigationStore(db_path)
    yield store

    # Clean up after test
    if os.path.exists(db_path):
        os.remove(db_path)


class TestInvestigationStoreCreation:
    """Test investigation creation and retrieval."""

    def test_create_investigation(self, inv_store):
        """Test creating a new investigation."""
        inv = Investigation(
            id="inv-001",
            title="API Timeout",
            status=InvestigationStatus.OPEN,
        )

        result = inv_store.create_investigation(inv)
        assert result is True

        # Verify we can retrieve it
        retrieved = inv_store.get_investigation(inv.id)
        assert retrieved is not None
        assert retrieved.id == inv.id
        assert retrieved.title == "API Timeout"

    def test_create_investigation_with_all_fields(self, inv_store):
        """Test creating investigation with all Phase 3a fields."""
        inv = Investigation(
            id="inv-002",
            title="Database Outage",
            description="Complete database service loss",
            status=InvestigationStatus.IN_PROGRESS,
            impact_severity=ImpactSeverity.CRITICAL,
            detected_at="2024-01-27T10:00:00",
            started_at="2024-01-27T10:05:00",
            root_cause="Connection pool exhaustion",
            remediation="Increased pool size",
            lessons_learned="Monitor pool metrics",
            component_affected="database-cluster",
            service_affected="production",
            tags=["database", "critical"],
            created_by="alice@example.com",
            assigned_to="bob@example.com",
            priority=Priority.P0,
        )

        result = inv_store.create_investigation(inv)
        assert result is True

        retrieved = inv_store.get_investigation(inv.id)
        assert retrieved.component_affected == "database-cluster"
        assert retrieved.priority == Priority.P0
        assert "database" in retrieved.tags

    def test_create_duplicate_investigation(self, inv_store):
        """Test that creating duplicate investigations fails gracefully."""
        inv = Investigation(
            id="inv-003",
            title="Test",
        )

        # First create should succeed
        assert inv_store.create_investigation(inv) is True

        # Second create should fail (duplicate)
        assert inv_store.create_investigation(inv) is False


class TestInvestigationStoreQueries:
    """Test advanced investigation queries."""

    def test_get_investigations_by_component(self, inv_store):
        """Test querying investigations by component."""
        inv1 = Investigation(
            id="inv-100",
            title="API Issue",
            component_affected="api-gateway",
        )
        inv2 = Investigation(
            id="inv-101",
            title="Database Issue",
            component_affected="database-cluster",
        )
        inv3 = Investigation(
            id="inv-102",
            title="Another API Issue",
            component_affected="api-gateway",
        )

        inv_store.create_investigation(inv1)
        inv_store.create_investigation(inv2)
        inv_store.create_investigation(inv3)

        # Query by component
        api_invs = inv_store.get_investigations_by_component("api-gateway")
        assert len(api_invs) == 2
        assert all(i.component_affected == "api-gateway" for i in api_invs)

    def test_get_investigations_by_service(self, inv_store):
        """Test querying investigations by service."""
        inv1 = Investigation(
            id="inv-110",
            title="Production Issue",
            service_affected="production",
        )
        inv2 = Investigation(
            id="inv-111",
            title="Staging Issue",
            service_affected="staging",
        )

        inv_store.create_investigation(inv1)
        inv_store.create_investigation(inv2)

        # Query by service
        prod_invs = inv_store.get_investigations_by_service("production")
        assert len(prod_invs) == 1
        assert prod_invs[0].service_affected == "production"

    def test_get_investigations_by_priority(self, inv_store):
        """Test querying investigations by priority."""
        inv1 = Investigation(
            id="inv-120",
            title="Critical Task",
            priority=Priority.P0,
        )
        inv2 = Investigation(
            id="inv-121",
            title="Minor Task",
            priority=Priority.P3,
        )

        inv_store.create_investigation(inv1)
        inv_store.create_investigation(inv2)

        # Query by priority
        critical_invs = inv_store.get_investigations_by_priority(Priority.P0)
        assert len(critical_invs) == 1
        assert critical_invs[0].priority == Priority.P0

    def test_get_investigations_by_severity(self, inv_store):
        """Test querying investigations by impact severity."""
        inv1 = Investigation(
            id="inv-130",
            title="Critical Impact",
            impact_severity=ImpactSeverity.CRITICAL,
        )
        inv2 = Investigation(
            id="inv-131",
            title="Low Impact",
            impact_severity=ImpactSeverity.LOW,
        )

        inv_store.create_investigation(inv1)
        inv_store.create_investigation(inv2)

        # Query by severity
        critical_invs = inv_store.get_investigations_by_severity(
            ImpactSeverity.CRITICAL
        )
        assert len(critical_invs) == 1
        assert critical_invs[0].impact_severity == ImpactSeverity.CRITICAL

    def test_get_investigations_by_status(self, inv_store):
        """Test querying investigations by status."""
        inv1 = Investigation(
            id="inv-140",
            title="Open Case",
            status=InvestigationStatus.OPEN,
        )
        inv2 = Investigation(
            id="inv-141",
            title="Closed Case",
            status=InvestigationStatus.CLOSED,
        )

        inv_store.create_investigation(inv1)
        inv_store.create_investigation(inv2)

        # Query by status
        open_invs = inv_store.get_investigations_by_status(InvestigationStatus.OPEN)
        assert len(open_invs) == 1
        assert open_invs[0].status == InvestigationStatus.OPEN


class TestInvestigationStoreUpdates:
    """Test investigation updates."""

    def test_update_investigation(self, inv_store):
        """Test updating investigation fields."""
        inv = Investigation(
            id="inv-200",
            title="Original Title",
            priority=Priority.P3,
        )

        inv_store.create_investigation(inv)

        # Update fields
        result = inv_store.update_investigation(
            inv.id,
            {
                "title": "Updated Title",
                "priority": Priority.P0,
            },
        )
        assert result is True

        # Verify update
        updated = inv_store.get_investigation(inv.id)
        assert updated.title == "Updated Title"
        assert updated.priority == Priority.P0

    def test_update_nonexistent_investigation(self, inv_store):
        """Test updating a non-existent investigation."""
        result = inv_store.update_investigation("nonexistent-id", {"title": "New"})
        assert result is False


class TestInvestigationStoreDeletion:
    """Test soft delete functionality."""

    def test_soft_delete_investigation(self, inv_store):
        """Test soft-deleting an investigation."""
        inv = Investigation(
            id="inv-300",
            title="To Delete",
        )

        inv_store.create_investigation(inv)

        # Soft delete
        result = inv_store.delete_investigation(inv.id)
        assert result is True

        # Should not appear in queries
        all_invs = inv_store.get_all_investigations(include_deleted=False)
        assert all(i.id != inv.id for i in all_invs)

        # But should appear when including deleted
        all_invs = inv_store.get_all_investigations(include_deleted=True)
        assert any(i.id == inv.id for i in all_invs)

    def test_restore_investigation(self, inv_store):
        """Test restoring a soft-deleted investigation."""
        inv = Investigation(
            id="inv-310",
            title="To Restore",
        )

        inv_store.create_investigation(inv)
        inv_store.delete_investigation(inv.id)

        # Restore
        result = inv_store.restore_investigation(inv.id)
        assert result is True

        # Should appear in queries again
        all_invs = inv_store.get_all_investigations(include_deleted=False)
        assert any(i.id == inv.id for i in all_invs)


class TestInvestigationStoreRetrieval:
    """Test various retrieval operations."""

    def test_get_all_investigations(self, inv_store):
        """Test retrieving all investigations."""
        for i in range(5):
            inv = Investigation(
                id=f"inv-{400+i}",
                title=f"Investigation {i}",
            )
            inv_store.create_investigation(inv)

        all_invs = inv_store.get_all_investigations()
        assert len(all_invs) == 5

    def test_get_all_investigations_excludes_deleted(self, inv_store):
        """Test that deleted investigations are excluded by default."""
        inv1 = Investigation(id="inv-410", title="Keep")
        inv2 = Investigation(id="inv-411", title="Delete")

        inv_store.create_investigation(inv1)
        inv_store.create_investigation(inv2)
        inv_store.delete_investigation(inv2.id)

        all_invs = inv_store.get_all_investigations(include_deleted=False)
        assert len(all_invs) == 1
        assert all_invs[0].id == inv1.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
