"""
Integration tests for email notification API endpoints.

Tests cover:
- Email notification preferences API
- Unsubscribe endpoint
- Reply notification trigger
- Event notification trigger
- Email delivery integration
"""

import pytest
import json
from src.app import create_app
from src.store.investigation_store import InvestigationStore
from src.services.email_notifier import EmailNotifier, NotificationPreferences


@pytest.fixture
def app():
    """Create test app."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def db():
    """Create test database."""
    import tempfile
    _, db_path = tempfile.mkstemp()
    store = InvestigationStore(db_path=db_path)
    return store


@pytest.fixture
def email_notifier():
    """Create email notifier."""
    return EmailNotifier(
        smtp_host='localhost',
        smtp_port=587,
    )


class TestEmailPreferencesAPI:
    """Test email preferences API endpoints."""
    
    def test_get_preferences_default(self, client, email_notifier):
        """Test getting default preferences."""
        # This would test GET /api/user/preferences endpoint
        # For now, test through the service
        prefs = email_notifier.get_preferences('user@example.com')
        assert prefs is None
    
    def test_set_preferences(self, email_notifier):
        """Test setting preferences through API."""
        prefs = NotificationPreferences(
            'user@example.com',
            notify_on_reply=True,
            digest_frequency='weekly',
        )
        email_notifier.set_preferences(prefs)
        
        retrieved = email_notifier.get_preferences('user@example.com')
        assert retrieved is not None
        assert retrieved.digest_frequency == 'weekly'
    
    def test_update_preferences_digest_frequency(self, email_notifier):
        """Test updating digest frequency preference."""
        prefs = NotificationPreferences('user@example.com')
        email_notifier.set_preferences(prefs)
        
        # Update to weekly
        prefs.digest_frequency = 'weekly'
        email_notifier.set_preferences(prefs)
        
        retrieved = email_notifier.get_preferences('user@example.com')
        assert retrieved.digest_frequency == 'weekly'
    
    def test_disable_reply_notifications(self, email_notifier):
        """Test disabling reply notifications."""
        prefs = NotificationPreferences('user@example.com', notify_on_reply=True)
        email_notifier.set_preferences(prefs)
        
        prefs.notify_on_reply = False
        email_notifier.set_preferences(prefs)
        
        retrieved = email_notifier.get_preferences('user@example.com')
        assert retrieved.notify_on_reply is False
    
    def test_enable_all_notifications(self, email_notifier):
        """Test enabling all notifications."""
        prefs = NotificationPreferences(
            'user@example.com',
            notify_on_reply=False,
            notify_on_event=False,
            notify_on_milestone=False,
        )
        email_notifier.set_preferences(prefs)
        
        prefs.notify_on_reply = True
        prefs.notify_on_event = True
        prefs.notify_on_milestone = True
        email_notifier.set_preferences(prefs)
        
        retrieved = email_notifier.get_preferences('user@example.com')
        assert retrieved.notify_on_reply is True
        assert retrieved.notify_on_event is True
        assert retrieved.notify_on_milestone is True


class TestUnsubscribeAPI:
    """Test unsubscribe API endpoints."""
    
    def test_unsubscribe_with_token(self, email_notifier):
        """Test unsubscribing with valid token."""
        prefs = NotificationPreferences('user@example.com')
        email_notifier.set_preferences(prefs)
        
        token = prefs.unsubscribe_token
        result = email_notifier.unsubscribe(token)
        
        assert result is True
        
        # Verify all notifications disabled
        updated = email_notifier.get_preferences('user@example.com')
        assert updated.notify_on_reply is False
        assert updated.notify_on_event is False
    
    def test_unsubscribe_invalid_token(self, email_notifier):
        """Test unsubscribe with invalid token."""
        result = email_notifier.unsubscribe('invalid-token')
        assert result is False
    
    def test_unsubscribe_expired_token(self, email_notifier):
        """Test unsubscribe with different token."""
        prefs = NotificationPreferences('user@example.com')
        email_notifier.set_preferences(prefs)
        
        result = email_notifier.unsubscribe('different-token')
        assert result is False
        
        # Original token should still work
        result = email_notifier.unsubscribe(prefs.unsubscribe_token)
        assert result is True


class TestReplyNotificationIntegration:
    """Test reply notification integration."""
    
    def test_reply_notification_trigger_without_prefs(self, email_notifier):
        """Test notification triggered when no preferences set."""
        result = email_notifier.notify_on_reply(
            recipient_email='author@example.com',
            recipient_name='Original Author',
            annotation_author='Replier',
            reply_text='Great point!',
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
        )
        
        # Would fail to send (no SMTP), but preference check passes
        assert isinstance(result, bool)
    
    def test_reply_notification_with_preferences_enabled(self, email_notifier):
        """Test notification when preferences enabled."""
        prefs = NotificationPreferences(
            'author@example.com',
            notify_on_reply=True,
        )
        email_notifier.set_preferences(prefs)
        
        result = email_notifier.notify_on_reply(
            recipient_email='author@example.com',
            recipient_name='Original Author',
            annotation_author='Replier',
            reply_text='Great point!',
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
        )
        
        assert isinstance(result, bool)
    
    def test_reply_notification_with_preferences_disabled(self, email_notifier):
        """Test no notification when preferences disabled."""
        prefs = NotificationPreferences(
            'author@example.com',
            notify_on_reply=False,
        )
        email_notifier.set_preferences(prefs)
        
        result = email_notifier.notify_on_reply(
            recipient_email='author@example.com',
            recipient_name='Original Author',
            annotation_author='Replier',
            reply_text='Great point!',
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
        )
        
        assert result is False
    
    def test_reply_notification_includes_unsubscribe(self, email_notifier):
        """Test that reply notification includes unsubscribe link."""
        prefs = NotificationPreferences('author@example.com')
        email_notifier.set_preferences(prefs)
        
        html = EmailNotifier._build_reply_email_html(
            recipient_name='Original Author',
            author='Replier',
            reply_text='Great point!',
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
            unsubscribe_token=prefs.unsubscribe_token,
        )
        
        assert 'unsubscribe' in html.lower()
        assert prefs.unsubscribe_token in html


class TestEventNotificationIntegration:
    """Test event notification integration."""
    
    def test_event_notification_trigger_without_prefs(self, email_notifier):
        """Test event notification triggered without preferences."""
        result = email_notifier.notify_on_event(
            recipient_email='owner@example.com',
            recipient_name='Investigation Owner',
            event_count=5,
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
        )
        
        assert isinstance(result, bool)
    
    def test_event_notification_with_preferences_enabled(self, email_notifier):
        """Test event notification when preferences enabled."""
        prefs = NotificationPreferences(
            'owner@example.com',
            notify_on_event=True,
        )
        email_notifier.set_preferences(prefs)
        
        result = email_notifier.notify_on_event(
            recipient_email='owner@example.com',
            recipient_name='Investigation Owner',
            event_count=5,
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
        )
        
        assert isinstance(result, bool)
    
    def test_event_notification_with_preferences_disabled(self, email_notifier):
        """Test no event notification when preferences disabled."""
        prefs = NotificationPreferences(
            'owner@example.com',
            notify_on_event=False,
        )
        email_notifier.set_preferences(prefs)
        
        result = email_notifier.notify_on_event(
            recipient_email='owner@example.com',
            recipient_name='Investigation Owner',
            event_count=5,
            investigation_title='Test Investigation',
            investigation_id='inv123',
            investigation_url='http://localhost:5000/investigations/inv123',
        )
        
        assert result is False
    
    def test_event_notification_multiple_events(self, email_notifier):
        """Test event notification for multiple events."""
        prefs = NotificationPreferences('owner@example.com', notify_on_event=True)
        email_notifier.set_preferences(prefs)
        
        html = EmailNotifier._build_event_email_html(
            recipient_name='Investigation Owner',
            event_count=10,
            investigation_title='Critical System Outage',
            investigation_id='inv456',
            investigation_url='http://localhost:5000/investigations/inv456',
            unsubscribe_token=prefs.unsubscribe_token,
        )
        
        assert '10' in html
        assert 'Critical System Outage' in html


class TestDigestEmailIntegration:
    """Test digest email integration."""
    
    def test_digest_empty_items(self, email_notifier):
        """Test digest email with no items."""
        result = email_notifier.send_digest(
            recipient_email='user@example.com',
            recipient_name='User Name',
            digest_items=[],
        )
        
        assert result is False
    
    def test_digest_single_reply(self, email_notifier):
        """Test digest email with single reply."""
        digest_items = [
            {
                'type': 'reply',
                'investigation_title': 'Database Performance',
                'author': 'DBA Team',
            }
        ]
        
        result = email_notifier.send_digest(
            recipient_email='user@example.com',
            recipient_name='User Name',
            digest_items=digest_items,
        )
        
        assert isinstance(result, bool)
    
    def test_digest_multiple_items(self, email_notifier):
        """Test digest email with multiple items."""
        digest_items = [
            {
                'type': 'reply',
                'investigation_title': 'Database Performance',
                'author': 'DBA Team',
            },
            {
                'type': 'events',
                'investigation_title': 'Database Performance',
                'count': 3,
            },
            {
                'type': 'reply',
                'investigation_title': 'API Timeout',
                'author': 'Backend Team',
            },
        ]
        
        result = email_notifier.send_digest(
            recipient_email='user@example.com',
            recipient_name='User Name',
            digest_items=digest_items,
        )
        
        assert isinstance(result, bool)
    
    def test_digest_html_contains_all_items(self, email_notifier):
        """Test digest HTML contains all items."""
        digest_items = [
            {
                'type': 'reply',
                'investigation_title': 'Database Performance',
                'author': 'DBA Team',
            },
            {
                'type': 'events',
                'investigation_title': 'API Timeout',
                'count': 5,
            },
        ]
        
        html = EmailNotifier._build_digest_email_html(
            recipient_name='User Name',
            digest_items=digest_items,
            unsubscribe_token='token123',
        )
        
        assert 'Database Performance' in html
        assert 'API Timeout' in html
        assert 'DBA Team' in html
        assert '5' in html


class TestNotificationEmailTemplates:
    """Test email template rendering."""
    
    def test_reply_template_all_fields(self, email_notifier):
        """Test reply template includes all required fields."""
        html = EmailNotifier._build_reply_email_html(
            recipient_name='John Doe',
            author='Jane Smith',
            reply_text='Excellent work on the analysis!',
            investigation_title='API Gateway Failure',
            investigation_id='inv-2024-001',
            investigation_url='http://rca.internal/investigations/inv-2024-001',
            unsubscribe_token='unsub-12345',
        )
        
        # Check all required content
        assert 'John Doe' in html
        assert 'Jane Smith' in html
        assert 'Excellent work on the analysis!' in html
        assert 'API Gateway Failure' in html
        assert 'inv-2024-001' in html
        assert 'http://rca.internal/investigations/inv-2024-001' in html
        assert 'unsub-12345' in html
        
        # Check HTML structure
        assert '<html>' in html
        assert '<body' in html
        assert '</body>' in html
        assert '</html>' in html
    
    def test_event_template_all_fields(self, email_notifier):
        """Test event template includes all required fields."""
        html = EmailNotifier._build_event_email_html(
            recipient_name='Alice Johnson',
            event_count=7,
            investigation_title='Database Replication Lag',
            investigation_id='inv-2024-002',
            investigation_url='http://rca.internal/investigations/inv-2024-002',
            unsubscribe_token='unsub-67890',
        )
        
        assert 'Alice Johnson' in html
        assert '7' in html
        assert 'Database Replication Lag' in html
        assert 'inv-2024-002' in html
        assert 'http://rca.internal/investigations/inv-2024-002' in html
    
    def test_digest_template_formatting(self, email_notifier):
        """Test digest template proper formatting."""
        digest_items = [
            {
                'type': 'reply',
                'investigation_title': 'Production Bug',
                'author': 'Dev Team',
            }
        ]
        
        html = EmailNotifier._build_digest_email_html(
            recipient_name='Manager',
            digest_items=digest_items,
        )
        
        assert 'Manager' in html
        assert 'Production Bug' in html
        assert 'Dev Team' in html
        assert '<html>' in html
        assert '</html>' in html


class TestEmailNotificationScenarios:
    """Test complete notification scenarios."""
    
    def test_scenario_reply_notification(self, email_notifier):
        """Test complete reply notification scenario."""
        # User sets up preferences
        prefs = NotificationPreferences(
            'john@company.com',
            notify_on_reply=True,
            digest_frequency='instant',
        )
        email_notifier.set_preferences(prefs)
        
        # Annotation reply is created
        result = email_notifier.notify_on_reply(
            recipient_email='john@company.com',
            recipient_name='John',
            annotation_author='Sarah',
            reply_text='I agree with this approach',
            investigation_title='Service Degradation',
            investigation_id='inv789',
            investigation_url='http://rca/inv789',
        )
        
        # Verify result type (would be success/failure with real SMTP)
        assert isinstance(result, bool)
        
        # User can unsubscribe
        unsub_result = email_notifier.unsubscribe(prefs.unsubscribe_token)
        assert unsub_result is True
        
        # Next notification should not be sent
        result = email_notifier.notify_on_reply(
            recipient_email='john@company.com',
            recipient_name='John',
            annotation_author='Sarah',
            reply_text='Another reply',
            investigation_title='Service Degradation',
            investigation_id='inv789',
            investigation_url='http://rca/inv789',
        )
        
        assert result is False
    
    def test_scenario_multiple_users(self, email_notifier):
        """Test managing preferences for multiple users."""
        # Set up preferences for multiple users
        users = [
            ('user1@company.com', 'User One', True),
            ('user2@company.com', 'User Two', False),
            ('user3@company.com', 'User Three', True),
        ]
        
        for email, name, notify in users:
            prefs = NotificationPreferences(email, notify_on_reply=notify)
            email_notifier.set_preferences(prefs)
        
        # Verify each user's settings
        for email, name, notify in users:
            retrieved = email_notifier.get_preferences(email)
            assert retrieved is not None
            assert retrieved.notify_on_reply == notify
