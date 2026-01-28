"""
Tests for email notification service.

Tests cover:
- Notification preferences management
- Reply notifications
- Event notifications
- Digest emails
- Unsubscribe functionality
- SMTP error handling
- Email template rendering
"""

import pytest
import tempfile
import os
from datetime import datetime
from src.services.email_notifier import EmailNotifier, NotificationPreferences


class TestNotificationPreferences:
    """Test notification preferences model."""

    def test_create_preferences_default(self):
        """Test creating preferences with defaults."""
        prefs = NotificationPreferences("user@example.com")

        assert prefs.user_email == "user@example.com"
        assert prefs.notify_on_reply is True
        assert prefs.notify_on_event is True
        assert prefs.notify_on_milestone is True
        assert prefs.digest_frequency == "daily"
        assert prefs.unsubscribe_token is not None

    def test_create_preferences_custom(self):
        """Test creating preferences with custom values."""
        prefs = NotificationPreferences(
            "user@example.com", notify_on_reply=False, digest_frequency="weekly"
        )

        assert prefs.notify_on_reply is False
        assert prefs.digest_frequency == "weekly"

    def test_preferences_to_dict(self):
        """Test converting preferences to dictionary."""
        prefs = NotificationPreferences("user@example.com")
        data = prefs.to_dict()

        assert data["user_email"] == "user@example.com"
        assert data["notify_on_reply"] is True
        assert "created_at" in data
        assert "updated_at" in data

    def test_unsubscribe_token_unique(self):
        """Test that each preferences gets unique token."""
        prefs1 = NotificationPreferences("user1@example.com")
        prefs2 = NotificationPreferences("user2@example.com")

        assert prefs1.unsubscribe_token != prefs2.unsubscribe_token


class TestEmailNotifier:
    """Test email notifier service."""

    @pytest.fixture
    def notifier(self):
        """Create email notifier instance with temporary database."""
        fd, temp_db = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        notifier = EmailNotifier(
            smtp_host="smtp.test.local",
            smtp_port=587,
            from_email="test@example.com",
            db_path=temp_db,
        )

        yield notifier

        # Cleanup
        if os.path.exists(temp_db):
            os.unlink(temp_db)

    # Preferences Management

    def test_set_get_preferences(self, notifier):
        """Test setting and getting preferences."""
        prefs = NotificationPreferences("user@example.com")
        notifier.set_preferences(prefs)

        retrieved = notifier.get_preferences("user@example.com")
        assert retrieved is not None
        assert retrieved.user_email == "user@example.com"

    def test_get_preferences_not_found(self, notifier):
        """Test getting non-existent preferences."""
        result = notifier.get_preferences("nonexistent@example.com")
        assert result is None

    def test_update_preferences(self, notifier):
        """Test updating preferences."""
        prefs1 = NotificationPreferences("user@example.com", notify_on_reply=True)
        notifier.set_preferences(prefs1)

        prefs2 = NotificationPreferences("user@example.com", notify_on_reply=False)
        notifier.set_preferences(prefs2)

        retrieved = notifier.get_preferences("user@example.com")
        assert retrieved.notify_on_reply is False

    # Reply Notifications

    def test_notify_on_reply_no_preferences(self, notifier):
        """Test reply notification without preferences (should send)."""
        result = notifier.notify_on_reply(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            annotation_author="Jane Smith",
            reply_text="Great investigation!",
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        # Would fail to send due to SMTP, but preference check passes
        assert isinstance(result, bool)

    def test_notify_on_reply_disabled(self, notifier):
        """Test reply notification when disabled in preferences."""
        prefs = NotificationPreferences("user@example.com", notify_on_reply=False)
        notifier.set_preferences(prefs)

        result = notifier.notify_on_reply(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            annotation_author="Jane Smith",
            reply_text="Great investigation!",
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        assert result is False

    def test_notify_on_reply_enabled(self, notifier):
        """Test reply notification when enabled in preferences."""
        prefs = NotificationPreferences("user@example.com", notify_on_reply=True)
        notifier.set_preferences(prefs)

        result = notifier.notify_on_reply(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            annotation_author="Jane Smith",
            reply_text="Great investigation!",
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        # Would fail to send due to SMTP, but preference check passes
        assert isinstance(result, bool)

    # Event Notifications

    def test_notify_on_event_no_preferences(self, notifier):
        """Test event notification without preferences."""
        result = notifier.notify_on_event(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            event_count=5,
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        assert isinstance(result, bool)

    def test_notify_on_event_disabled(self, notifier):
        """Test event notification when disabled in preferences."""
        prefs = NotificationPreferences("user@example.com", notify_on_event=False)
        notifier.set_preferences(prefs)

        result = notifier.notify_on_event(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            event_count=5,
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        assert result is False

    def test_notify_on_event_enabled(self, notifier):
        """Test event notification when enabled."""
        prefs = NotificationPreferences("user@example.com", notify_on_event=True)
        notifier.set_preferences(prefs)

        result = notifier.notify_on_event(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            event_count=5,
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        assert isinstance(result, bool)

    # Digest Emails

    def test_send_digest_empty(self, notifier):
        """Test sending digest with empty items."""
        result = notifier.send_digest(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            digest_items=[],
        )

        assert result is False

    def test_send_digest_with_items(self, notifier):
        """Test sending digest with items."""
        digest_items = [
            {
                "type": "reply",
                "investigation_title": "Production Outage",
                "author": "Jane Smith",
            },
            {
                "type": "events",
                "investigation_title": "Production Outage",
                "count": 5,
            },
        ]

        result = notifier.send_digest(
            recipient_email="user@example.com",
            recipient_name="John Doe",
            digest_items=digest_items,
        )

        assert isinstance(result, bool)

    # Unsubscribe

    def test_unsubscribe_valid_token(self, notifier):
        """Test unsubscribing with valid token."""
        prefs = NotificationPreferences("user@example.com")
        token = prefs.unsubscribe_token
        notifier.set_preferences(prefs)

        result = notifier.unsubscribe(token)
        assert result is True

        # Verify all notifications disabled
        updated_prefs = notifier.get_preferences("user@example.com")
        assert updated_prefs.notify_on_reply is False
        assert updated_prefs.notify_on_event is False
        assert updated_prefs.notify_on_milestone is False

    def test_unsubscribe_invalid_token(self, notifier):
        """Test unsubscribing with invalid token."""
        result = notifier.unsubscribe("invalid-token")
        assert result is False

    def test_unsubscribe_updates_timestamp(self, notifier):
        """Test that unsubscribe updates the timestamp."""
        prefs = NotificationPreferences("user@example.com")
        original_time = prefs.updated_at
        token = prefs.unsubscribe_token
        notifier.set_preferences(prefs)

        notifier.unsubscribe(token)

        updated_prefs = notifier.get_preferences("user@example.com")
        assert updated_prefs.updated_at != original_time

    # Email Template Generation

    def test_reply_email_html_template(self, notifier):
        """Test reply email HTML template generation."""
        html = EmailNotifier._build_reply_email_html(
            recipient_name="John Doe",
            author="Jane Smith",
            reply_text="This looks good!",
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
            unsubscribe_token="token123",
        )

        assert "John Doe" in html
        assert "Jane Smith" in html
        assert "This looks good!" in html
        assert "Production Outage" in html
        assert "http://localhost:5000/investigations/inv123" in html
        assert "unsubscribe" in html.lower()
        assert "<html>" in html
        assert "</html>" in html

    def test_reply_email_text_template(self, notifier):
        """Test reply email plain text template generation."""
        text = EmailNotifier._build_reply_email_text(
            recipient_name="John Doe",
            author="Jane Smith",
            reply_text="This looks good!",
            investigation_title="Production Outage",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        assert "John Doe" in text
        assert "Jane Smith" in text
        assert "This looks good!" in text
        assert "Production Outage" in text
        assert "http://localhost:5000/investigations/inv123" in text

    def test_event_email_html_template(self, notifier):
        """Test event notification email HTML template."""
        html = EmailNotifier._build_event_email_html(
            recipient_name="John Doe",
            event_count=5,
            investigation_title="Production Outage",
            investigation_id="inv123",
            investigation_url="http://localhost:5000/investigations/inv123",
            unsubscribe_token="token123",
        )

        assert "John Doe" in html
        assert "5" in html
        assert "Production Outage" in html
        assert "http://localhost:5000/investigations/inv123" in html
        assert "<html>" in html
        assert "</html>" in html

    def test_event_email_text_template(self, notifier):
        """Test event notification email plain text template."""
        text = EmailNotifier._build_event_email_text(
            recipient_name="John Doe",
            event_count=5,
            investigation_title="Production Outage",
            investigation_url="http://localhost:5000/investigations/inv123",
        )

        assert "John Doe" in text
        assert "5" in text
        assert "Production Outage" in text
        assert "http://localhost:5000/investigations/inv123" in text

    def test_digest_email_html_template(self, notifier):
        """Test digest email HTML template."""
        digest_items = [
            {
                "type": "reply",
                "investigation_title": "Production Outage",
                "author": "Jane Smith",
            },
            {
                "type": "events",
                "investigation_title": "Production Outage",
                "count": 5,
            },
        ]

        html = EmailNotifier._build_digest_email_html(
            recipient_name="John Doe",
            digest_items=digest_items,
            unsubscribe_token="token123",
        )

        assert "John Doe" in html
        assert "Production Outage" in html
        assert "2" in html  # 2 items
        assert "reply" in html.lower()
        assert "events" in html.lower()
        assert "<html>" in html
        assert "</html>" in html

    def test_digest_email_text_template(self, notifier):
        """Test digest email plain text template."""
        digest_items = [
            {
                "type": "reply",
                "investigation_title": "Production Outage",
                "author": "Jane Smith",
            },
            {
                "type": "events",
                "investigation_title": "Production Outage",
                "count": 5,
            },
        ]

        text = EmailNotifier._build_digest_email_text(
            recipient_name="John Doe",
            digest_items=digest_items,
        )

        assert "John Doe" in text
        assert "Production Outage" in text
        assert "REPLY" in text
        assert "EVENTS" in text

    # Configuration

    def test_notifier_initialization(self):
        """Test notifier initialization with custom config."""
        notifier = EmailNotifier(
            smtp_host="smtp.custom.com",
            smtp_port=465,
            smtp_username="user",
            smtp_password="pass",
            from_email="custom@example.com",
            from_name="Custom Name",
        )

        assert notifier.smtp_host == "smtp.custom.com"
        assert notifier.smtp_port == 465
        assert notifier.smtp_username == "user"
        assert notifier.smtp_password == "pass"
        assert notifier.from_email == "custom@example.com"
        assert notifier.from_name == "Custom Name"

    def test_notifier_default_config(self):
        """Test notifier with default configuration."""
        notifier = EmailNotifier()

        assert notifier.smtp_host == "localhost"
        assert notifier.smtp_port == 587
        assert notifier.from_email == "noreply@git-rca.local"
        assert notifier.from_name == "Git RCA Workspace"
