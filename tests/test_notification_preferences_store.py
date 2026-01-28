"""
Tests for notification preferences persistence store.

Tests:
- Create, read, update, delete preferences
- Unsubscribe token lookup
- Digest frequency queries
- Database persistence across restarts
"""

import pytest
import os
import tempfile
import sqlite3
from src.store.notification_preferences_store import NotificationPreferencesStore
from src.services.email_notifier import NotificationPreferences


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def store(temp_db):
    """Create store instance with temp database."""
    return NotificationPreferencesStore(temp_db)


class TestNotificationPreferencesStore:
    """Test notification preferences database persistence."""

    def test_create_preferences(self, store):
        """Test creating new preferences."""
        prefs = store.create_preferences(
            user_email="alice@example.com",
            notify_on_reply=True,
            notify_on_event=True,
            notify_on_milestone=False,
            digest_frequency="daily",
        )

        assert prefs.user_email == "alice@example.com"
        assert prefs.notify_on_reply is True
        assert prefs.notify_on_event is True
        assert prefs.notify_on_milestone is False
        assert prefs.digest_frequency == "daily"
        assert prefs.unsubscribe_token is not None

    def test_get_preferences_exists(self, store):
        """Test retrieving existing preferences."""
        # Create
        store.create_preferences(
            user_email="bob@example.com",
            notify_on_reply=True,
            digest_frequency="weekly",
        )

        # Retrieve
        prefs = store.get_preferences("bob@example.com")

        assert prefs is not None
        assert prefs.user_email == "bob@example.com"
        assert prefs.notify_on_reply is True
        assert prefs.digest_frequency == "weekly"

    def test_get_preferences_not_exists(self, store):
        """Test retrieving non-existent preferences returns None."""
        prefs = store.get_preferences("nonexistent@example.com")
        assert prefs is None

    def test_update_preferences(self, store):
        """Test updating existing preferences."""
        # Create
        token = store.create_preferences(
            user_email="charlie@example.com",
            notify_on_reply=True,
            notify_on_event=True,
        ).unsubscribe_token

        # Update
        prefs = NotificationPreferences(
            user_email="charlie@example.com",
            notify_on_reply=False,
            notify_on_event=True,
            notify_on_milestone=True,
            digest_frequency="never",
            unsubscribe_token=token,
        )
        store.update_preferences(prefs)

        # Verify
        updated = store.get_preferences("charlie@example.com")
        assert updated.notify_on_reply is False
        assert updated.notify_on_milestone is True
        assert updated.digest_frequency == "never"

    def test_set_preferences_creates_new(self, store):
        """Test set_preferences creates new if not exists."""
        prefs = NotificationPreferences(
            user_email="dave@example.com",
            notify_on_reply=True,
            digest_frequency="daily",
        )
        store.set_preferences(prefs)

        retrieved = store.get_preferences("dave@example.com")
        assert retrieved is not None
        assert retrieved.user_email == "dave@example.com"

    def test_set_preferences_updates_existing(self, store):
        """Test set_preferences updates existing."""
        # Create initial
        token = store.create_preferences(
            user_email="eve@example.com",
            notify_on_reply=True,
        ).unsubscribe_token

        # Update via set
        prefs = NotificationPreferences(
            user_email="eve@example.com",
            notify_on_reply=False,
            notify_on_event=False,
            unsubscribe_token=token,
        )
        store.set_preferences(prefs)

        # Verify updated
        retrieved = store.get_preferences("eve@example.com")
        assert retrieved.notify_on_reply is False
        assert retrieved.notify_on_event is False

    def test_delete_preferences(self, store):
        """Test deleting preferences."""
        # Create
        store.create_preferences(user_email="frank@example.com")

        # Delete
        deleted = store.delete_preferences("frank@example.com")
        assert deleted is True

        # Verify deleted
        prefs = store.get_preferences("frank@example.com")
        assert prefs is None

    def test_delete_preferences_not_exists(self, store):
        """Test deleting non-existent preferences."""
        deleted = store.delete_preferences("notfound@example.com")
        assert deleted is False

    def test_get_preferences_by_token(self, store):
        """Test retrieving preferences by unsubscribe token."""
        prefs = store.create_preferences(user_email="grace@example.com")

        # Retrieve by token
        found = store.get_preferences_by_token(prefs.unsubscribe_token)

        assert found is not None
        assert found.user_email == "grace@example.com"

    def test_get_preferences_by_token_not_found(self, store):
        """Test retrieving with invalid token."""
        found = store.get_preferences_by_token("invalid-token-xyz")
        assert found is None

    def test_list_all_preferences(self, store):
        """Test listing all preferences."""
        # Create multiple
        store.create_preferences(user_email="user1@example.com")
        store.create_preferences(user_email="user2@example.com")
        store.create_preferences(user_email="user3@example.com")

        # List
        all_prefs = store.list_all_preferences()

        assert len(all_prefs) == 3
        emails = [p.user_email for p in all_prefs]
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails
        assert "user3@example.com" in emails

    def test_get_preferences_by_digest_frequency(self, store):
        """Test querying by digest frequency."""
        # Create preferences with different frequencies
        store.create_preferences(
            user_email="daily1@example.com",
            digest_frequency="daily",
            notify_on_event=True,
        )
        store.create_preferences(
            user_email="daily2@example.com",
            digest_frequency="daily",
            notify_on_event=True,
        )
        store.create_preferences(
            user_email="weekly1@example.com",
            digest_frequency="weekly",
            notify_on_event=True,
        )
        store.create_preferences(
            user_email="never1@example.com",
            digest_frequency="never",
            notify_on_event=False,
        )

        # Query daily
        daily = store.get_preferences_by_digest_frequency("daily")
        assert len(daily) == 2
        assert all(p.digest_frequency == "daily" for p in daily)

        # Query weekly
        weekly = store.get_preferences_by_digest_frequency("weekly")
        assert len(weekly) == 1
        assert weekly[0].user_email == "weekly1@example.com"

        # Query never (should exclude)
        never = store.get_preferences_by_digest_frequency("never")
        assert len(never) == 0  # notify_on_event=False, so excluded

    def test_persistence_across_instances(self, temp_db):
        """Test that data persists across store instances."""
        # Create with first instance
        store1 = NotificationPreferencesStore(temp_db)
        store1.create_preferences(
            user_email="persist@example.com",
            notify_on_reply=True,
            digest_frequency="daily",
        )

        # Read with second instance
        store2 = NotificationPreferencesStore(temp_db)
        prefs = store2.get_preferences("persist@example.com")

        assert prefs is not None
        assert prefs.user_email == "persist@example.com"
        assert prefs.notify_on_reply is True
        assert prefs.digest_frequency == "daily"

    def test_unsubscribe_token_uniqueness(self, store):
        """Test that unsubscribe tokens are unique."""
        prefs1 = store.create_preferences(user_email="unique1@example.com")
        prefs2 = store.create_preferences(user_email="unique2@example.com")

        assert prefs1.unsubscribe_token != prefs2.unsubscribe_token

    def test_create_duplicate_email_raises_error(self, store):
        """Test that creating duplicate email raises error."""
        store.create_preferences(user_email="dup@example.com")

        with pytest.raises(sqlite3.IntegrityError):
            store.create_preferences(user_email="dup@example.com")

    def test_preference_defaults(self, store):
        """Test default values for preferences."""
        prefs = store.create_preferences(user_email="defaults@example.com")

        assert prefs.notify_on_reply is True
        assert prefs.notify_on_event is True
        assert prefs.notify_on_milestone is True
        assert prefs.digest_frequency == "daily"


class TestIntegrationWithEmailNotifier:
    """Test integration between store and EmailNotifier."""

    def test_email_notifier_uses_persistent_store(self, temp_db):
        """Test that EmailNotifier saves and loads from persistent store."""
        from src.services.email_notifier import EmailNotifier

        # Create notifier with temp database
        notifier = EmailNotifier(db_path=temp_db)

        # Set preferences
        prefs = NotificationPreferences(
            user_email="integration@example.com",
            notify_on_reply=True,
            digest_frequency="weekly",
        )
        notifier.set_preferences(prefs)

        # Create new notifier instance (same database)
        notifier2 = EmailNotifier(db_path=temp_db)

        # Verify preferences persisted
        retrieved = notifier2.get_preferences("integration@example.com")
        assert retrieved is not None
        assert retrieved.digest_frequency == "weekly"

    def test_unsubscribe_persists(self, temp_db):
        """Test that unsubscribe operations persist."""
        from src.services.email_notifier import EmailNotifier

        notifier = EmailNotifier(db_path=temp_db)

        # Create preferences
        prefs = NotificationPreferences(
            user_email="unsub@example.com",
            notify_on_reply=True,
            notify_on_event=True,
        )
        notifier.set_preferences(prefs)
        retrieved = notifier.get_preferences("unsub@example.com")
        token = retrieved.unsubscribe_token

        # Unsubscribe
        result = notifier.unsubscribe(token)
        assert result is True

        # Verify persisted across notifier instances
        notifier2 = EmailNotifier(db_path=temp_db)
        updated = notifier2.get_preferences("unsub@example.com")
        assert updated.notify_on_reply is False
        assert updated.notify_on_event is False
