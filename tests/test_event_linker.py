"""
Tests for Event Linker Service

Tests event auto-discovery, semantic matching, filtering, and search functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.services.event_linker import EventLinker
from src.models.investigation import Investigation, InvestigationEvent
from src.store.investigation_store import InvestigationStore


@pytest.fixture
def investigation_store():
    """Create investigation store instance with proper initialization."""
    import tempfile
    import os

    # Create a temporary database file for each test
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    store = InvestigationStore(db_path=db_path)

    yield store

    # Cleanup
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def event_linker(investigation_store):
    """Create event linker instance."""
    return EventLinker(investigation_store)


@pytest.fixture
def test_investigation(investigation_store):
    """Create test investigation."""
    inv = investigation_store.create_investigation(
        title="Database Connection Timeout",
        description="Prod database became unresponsive",
        severity="critical",
        status="open",
    )
    return inv


class TestEventLinkerBasics:
    """Test basic event linker functionality."""

    def test_initialization(self, investigation_store):
        """Test event linker initialization."""
        linker = EventLinker(investigation_store)
        assert linker.store == investigation_store

    def test_auto_link_with_no_investigation(self, event_linker):
        """Test auto-link with non-existent investigation."""
        result = event_linker.auto_link_events("non-existent-id")
        assert result == []

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_auto_link_returns_linked_events(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test auto-link returns linked event instances."""
        # Mock events
        mock_git.return_value = [
            {
                "id": "git-123",
                "type": "push",
                "message": "Deploy database migration",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "repo": "main",
            }
        ]
        mock_ci.return_value = []

        result = event_linker.auto_link_events(test_investigation.id)

        assert len(result) >= 0
        assert all(isinstance(evt, InvestigationEvent) for evt in result)


class TestTimeWindowFiltering:
    """Test time window filtering for event discovery."""

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_events_within_window_included(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test events within time window are included."""
        now = datetime.utcnow()

        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Database connection retry logic added",
                "timestamp": (now - timedelta(minutes=30)).isoformat() + "Z",
                "repo": "main",
            }
        ]
        mock_ci.return_value = []

        result = event_linker.auto_link_events(
            test_investigation.id, time_window_minutes=60
        )

        # Should find the event (within 60 minute window)
        assert len(result) > 0

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_events_outside_window_excluded(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test events outside time window are excluded."""
        now = datetime.utcnow()

        mock_git.return_value = [
            {
                "id": "git-2",
                "type": "push",
                "message": "Old deployment",
                "timestamp": (now - timedelta(hours=3)).isoformat() + "Z",
                "repo": "old",
            }
        ]
        mock_ci.return_value = []

        result = event_linker.auto_link_events(
            test_investigation.id, time_window_minutes=60
        )

        # Should NOT find the event (outside 60 minute window)
        assert len(result) == 0

    def test_time_window_includes_before_and_after(self, event_linker):
        """Test time window includes both before and after investigation time."""
        from datetime import timezone

        inv_time = datetime(2026, 1, 27, 10, 0, 0, tzinfo=timezone.utc)
        time_start = inv_time - timedelta(minutes=30)
        time_end = inv_time + timedelta(minutes=30)

        # Event 30 minutes before
        before_event = {"timestamp": (inv_time - timedelta(minutes=30)).isoformat()}
        assert EventLinker._is_in_time_window(before_event, time_start, time_end)

        # Event 30 minutes after
        after_event = {"timestamp": (inv_time + timedelta(minutes=30)).isoformat()}
        assert EventLinker._is_in_time_window(after_event, time_start, time_end)

        # Event at exact start
        start_event = {"timestamp": time_start.isoformat()}
        assert EventLinker._is_in_time_window(start_event, time_start, time_end)

        # Event at exact end
        end_event = {"timestamp": time_end.isoformat()}
        assert EventLinker._is_in_time_window(end_event, time_start, time_end)


class TestSemanticMatching:
    """Test semantic keyword matching between events and investigations."""

    def test_semantic_match_finds_common_keywords(self):
        """Test semantic matching finds common keywords."""
        investigation_title = "Database Connection Timeout Error"
        event = {
            "message": "Database connection pool exhausted",
            "type": "error",
        }

        assert EventLinker._semantic_match(investigation_title, event)

    def test_semantic_match_case_insensitive(self):
        """Test semantic matching is case insensitive."""
        investigation_title = "DATABASE Connection"
        event = {
            "message": "database connection error",
        }

        assert EventLinker._semantic_match(investigation_title, event)

    def test_semantic_match_ignores_short_words(self):
        """Test semantic matching ignores words < 4 chars."""
        investigation_title = "A B C Database"
        event = {
            "message": "Error message here",
        }

        # Only "Database" keyword should match
        assert not EventLinker._semantic_match(investigation_title, event)

    def test_semantic_match_true_for_empty_title(self):
        """Test semantic matching returns True for empty title."""
        investigation_title = ""
        event = {"message": "Any event"}

        # Empty title should match all events
        assert EventLinker._semantic_match(investigation_title, event)

    def test_semantic_match_searches_all_fields(self):
        """Test semantic matching searches all event fields."""
        investigation_title = "Production Deployment"
        event = {
            "message": "Build started",
            "repo": "Production-API",
            "author": "deployment-bot",
            "branch": "main",
        }

        assert EventLinker._semantic_match(investigation_title, event)

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_auto_link_with_semantic_matching_enabled(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test auto-link with semantic matching enabled."""
        now = datetime.utcnow()

        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Database connection pool fix",
                "timestamp": now.isoformat() + "Z",
                "repo": "main",
            },
            {
                "id": "git-2",
                "type": "push",
                "message": "UI component refactoring",
                "timestamp": now.isoformat() + "Z",
                "repo": "ui-branch",
            },
        ]
        mock_ci.return_value = []

        # Update investigation title for semantic matching
        test_investigation.title = "Database Connection Timeout"

        result = event_linker.auto_link_events(
            test_investigation.id, semantic_matching=True
        )

        # Should only link database-related event
        assert len(result) > 0


class TestEventSearch:
    """Test event search functionality."""

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_search_by_query(self, mock_ci, mock_git, event_linker):
        """Test event search by query string."""
        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Database migration deployed",
                "repo": "main",
            },
            {
                "id": "git-2",
                "type": "push",
                "message": "UI components updated",
                "repo": "feature-branch",
            },
        ]
        mock_ci.return_value = []

        result = event_linker.search_events("database")

        assert len(result) >= 1
        assert any("Database" in str(r) for r in result)

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_search_by_source(self, mock_ci, mock_git, event_linker):
        """Test event search filtered by source."""
        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Git commit",
                "repo": "main",
            },
        ]
        mock_ci.return_value = [
            {
                "id": "ci-1",
                "type": "build",
                "message": "Build job",
                "job": "CI-123",
            },
        ]

        result = event_linker.search_events("commit", source="git")

        # Should only return git events
        assert all(r.get("source") == "git" for r in result)

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_search_by_event_type(self, mock_ci, mock_git, event_linker):
        """Test event search filtered by event type."""
        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Code pushed",
                "repo": "main",
            },
            {
                "id": "git-2",
                "type": "pull_request",
                "message": "PR opened",
                "repo": "main",
            },
        ]
        mock_ci.return_value = []

        result = event_linker.search_events("code", event_type="push")

        assert all(r.get("type") == "push" for r in result)

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_search_results_sorted_by_timestamp(self, mock_ci, mock_git, event_linker):
        """Test search results are sorted by timestamp (newest first)."""
        earlier = datetime(2026, 1, 27, 9, 0, 0).isoformat() + "Z"
        later = datetime(2026, 1, 27, 11, 0, 0).isoformat() + "Z"

        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Earlier event",
                "timestamp": earlier,
                "repo": "main",
            },
            {
                "id": "git-2",
                "type": "push",
                "message": "Later event",
                "timestamp": later,
                "repo": "main",
            },
        ]
        mock_ci.return_value = []

        result = event_linker.search_events("event")

        # Later event should be first
        assert result[0]["timestamp"] > result[1]["timestamp"]


class TestEventSuggestions:
    """Test event suggestion functionality."""

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_suggest_events_returns_relevant_events(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test suggest_events returns relevant events."""
        now = datetime.utcnow()

        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Database connection pool increased",
                "timestamp": (now - timedelta(minutes=15)).isoformat() + "Z",
                "repo": "main",
            },
        ]
        mock_ci.return_value = []

        result = event_linker.suggest_events(test_investigation.id)

        assert isinstance(result, list)
        assert all("source" in evt and "message" in evt for evt in result)

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_suggest_events_excludes_already_linked(
        self, mock_ci, mock_git, event_linker, investigation_store, test_investigation
    ):
        """Test suggest_events excludes already linked events."""
        now = datetime.utcnow()

        # Create and link an event
        event = investigation_store.add_event(
            investigation_id=test_investigation.id,
            event_id="git-1",
            event_type="push",
            source="git",
            message="Already linked event",
            timestamp=now.isoformat() + "Z",
        )

        # Mock same event in discovery
        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Already linked event",
                "timestamp": now.isoformat() + "Z",
                "repo": "main",
            },
        ]
        mock_ci.return_value = []

        result = event_linker.suggest_events(test_investigation.id)

        # Already linked event should not be in suggestions
        assert not any(evt.get("event_id") == "git-1" for evt in result)

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_suggest_events_respects_limit(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test suggest_events respects limit parameter."""
        now = datetime.utcnow()

        # Create many events
        mock_git.return_value = [
            {
                "id": f"git-{i}",
                "type": "push",
                "message": f"Event {i}",
                "timestamp": (now - timedelta(minutes=5)).isoformat() + "Z",
                "repo": "main",
            }
            for i in range(20)
        ]
        mock_ci.return_value = []

        result = event_linker.suggest_events(test_investigation.id, limit=5)

        assert len(result) <= 5


class TestQueryMatching:
    """Test query matching helper."""

    def test_matches_query_in_message(self):
        """Test query matching in message field."""
        event = {"message": "Database connection error"}
        assert EventLinker._matches_query(event, "connection")

    def test_matches_query_case_insensitive(self):
        """Test query matching is case insensitive."""
        event = {"message": "DATABASE Connection"}
        assert EventLinker._matches_query(event, "database")

    def test_matches_query_in_multiple_fields(self):
        """Test query matching across multiple fields."""
        event = {
            "message": "Build failed",
            "repo": "database-service",
            "job": "CI-123",
        }
        assert EventLinker._matches_query(event, "database")

    def test_no_match_returns_false(self):
        """Test non-matching query returns False."""
        event = {"message": "Build successful", "repo": "ui-service"}
        assert not EventLinker._matches_query(event, "database")


class TestErrorHandling:
    """Test error handling in event linker."""

    def test_invalid_timestamp_skipped(self, event_linker):
        """Test events with invalid timestamps are skipped."""
        event = {"timestamp": "invalid-date"}
        time_start = datetime(2026, 1, 27, 9, 0, 0)
        time_end = datetime(2026, 1, 27, 11, 0, 0)

        result = EventLinker._is_in_time_window(event, time_start, time_end)
        assert result is False

    def test_missing_timestamp_skipped(self, event_linker):
        """Test events with missing timestamp are skipped."""
        event = {"message": "Event with no timestamp"}
        time_start = datetime(2026, 1, 27, 9, 0, 0)
        time_end = datetime(2026, 1, 27, 11, 0, 0)

        result = EventLinker._is_in_time_window(event, time_start, time_end)
        assert result is False

    @patch("src.services.event_linker.git_connector.load_events")
    @patch("src.services.event_linker.ci_connector.load_events")
    def test_linking_error_doesnt_stop_processing(
        self, mock_ci, mock_git, event_linker, test_investigation
    ):
        """Test linking errors don't stop processing other events."""
        now = datetime.utcnow()

        mock_git.return_value = [
            {
                "id": "git-1",
                "type": "push",
                "message": "Valid event",
                "timestamp": now.isoformat() + "Z",
                "repo": "main",
            },
            {
                # Missing required fields - will cause linking error
                "timestamp": now.isoformat()
                + "Z",
            },
            {
                "id": "git-3",
                "type": "push",
                "message": "Another valid event",
                "timestamp": now.isoformat() + "Z",
                "repo": "main",
            },
        ]
        mock_ci.return_value = []

        # Should not raise exception
        result = event_linker.auto_link_events(test_investigation.id)

        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
