"""
Email Notification Service

Handles sending email notifications for annotation replies, digest emails,
and notification preference management.

This service integrates with the investigation system to notify users when:
1. Their annotations receive replies
2. New events are linked to their investigations
3. Investigations reach specific milestones
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict, Any
import json
import uuid

from src.store.investigation_store import InvestigationStore


class NotificationPreferences:
    """User notification preferences."""
    
    def __init__(
        self,
        user_email: str,
        notify_on_reply: bool = True,
        notify_on_event: bool = True,
        notify_on_milestone: bool = True,
        digest_frequency: str = 'daily',  # daily, weekly, never
        unsubscribe_token: Optional[str] = None,
    ):
        self.user_email = user_email
        self.notify_on_reply = notify_on_reply
        self.notify_on_event = notify_on_event
        self.notify_on_milestone = notify_on_milestone
        self.digest_frequency = digest_frequency
        self.unsubscribe_token = unsubscribe_token or str(uuid.uuid4())
        self.created_at = datetime.now(UTC).isoformat()
        self.updated_at = datetime.now(UTC).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'user_email': self.user_email,
            'notify_on_reply': self.notify_on_reply,
            'notify_on_event': self.notify_on_event,
            'notify_on_milestone': self.notify_on_milestone,
            'digest_frequency': self.digest_frequency,
            'unsubscribe_token': self.unsubscribe_token,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


class EmailNotifier:
    """Service for sending email notifications."""
    
    def __init__(
        self,
        smtp_host: str = 'localhost',
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: str = 'noreply@git-rca.local',
        from_name: str = 'Git RCA Workspace',
        db_path: str = 'investigations.db',
    ):
        """Initialize email notifier.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_username: SMTP username (optional)
            smtp_password: SMTP password (optional)
            from_email: From email address
            from_name: From display name
            db_path: Path to SQLite database file for preferences persistence
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name
        
        # Import preferences store here to avoid circular imports
        from src.store.notification_preferences_store import NotificationPreferencesStore
        self.preferences_store = NotificationPreferencesStore(db_path)
    
    def set_preferences(self, preferences: NotificationPreferences) -> None:
        """Set notification preferences for a user (persists to database).
        
        Args:
            preferences: NotificationPreferences instance
        """
        self.preferences_store.set_preferences(preferences)
    
    def get_preferences(self, user_email: str) -> Optional[NotificationPreferences]:
        """Get notification preferences for a user (loads from database).
        
        Args:
            user_email: User email address
            
        Returns:
            NotificationPreferences or None if not found
        """
        return self.preferences_store.get_preferences(user_email)
    
    def notify_on_reply(
        self,
        recipient_email: str,
        recipient_name: str,
        annotation_author: str,
        reply_text: str,
        investigation_title: str,
        investigation_id: str,
        investigation_url: str,
    ) -> bool:
        """Send email notification for annotation reply.
        
        Args:
            recipient_email: Email address of original commenter
            recipient_name: Name of original commenter
            annotation_author: Author of the reply
            reply_text: Text of the reply
            investigation_title: Investigation title
            investigation_id: Investigation ID
            investigation_url: URL to investigation
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Check preferences
        prefs = self.get_preferences(recipient_email)
        if prefs and not prefs.notify_on_reply:
            return False
        
        subject = f"New reply on '{investigation_title}' - Git RCA"
        
        # Build email content
        body_html = self._build_reply_email_html(
            recipient_name,
            annotation_author,
            reply_text,
            investigation_title,
            investigation_id,
            investigation_url,
            prefs.unsubscribe_token if prefs else None,
        )
        
        body_text = self._build_reply_email_text(
            recipient_name,
            annotation_author,
            reply_text,
            investigation_title,
            investigation_url,
        )
        
        return self._send_email(recipient_email, subject, body_html, body_text)
    
    def notify_on_event(
        self,
        recipient_email: str,
        recipient_name: str,
        event_count: int,
        investigation_title: str,
        investigation_id: str,
        investigation_url: str,
    ) -> bool:
        """Send email notification for event linking.
        
        Args:
            recipient_email: Email address of investigation owner
            recipient_name: Name of investigation owner
            event_count: Number of events linked
            investigation_title: Investigation title
            investigation_id: Investigation ID
            investigation_url: URL to investigation
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Check preferences
        prefs = self.get_preferences(recipient_email)
        if prefs and not prefs.notify_on_event:
            return False
        
        subject = f"{event_count} new events linked to '{investigation_title}' - Git RCA"
        
        # Build email content
        body_html = self._build_event_email_html(
            recipient_name,
            event_count,
            investigation_title,
            investigation_id,
            investigation_url,
            prefs.unsubscribe_token if prefs else None,
        )
        
        body_text = self._build_event_email_text(
            recipient_name,
            event_count,
            investigation_title,
            investigation_url,
        )
        
        return self._send_email(recipient_email, subject, body_html, body_text)
    
    def send_digest(
        self,
        recipient_email: str,
        recipient_name: str,
        digest_items: List[Dict[str, Any]],
    ) -> bool:
        """Send digest email with multiple notifications.
        
        Args:
            recipient_email: Email address
            recipient_name: Name
            digest_items: List of digest items (replies, events, etc.)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not digest_items:
            return False
        
        prefs = self.get_preferences(recipient_email)
        subject = f"Git RCA Daily Digest - {len(digest_items)} updates"
        
        # Build email content
        body_html = self._build_digest_email_html(
            recipient_name,
            digest_items,
            prefs.unsubscribe_token if prefs else None,
        )
        
        body_text = self._build_digest_email_text(
            recipient_name,
            digest_items,
        )
        
        return self._send_email(recipient_email, subject, body_html, body_text)
    
    def unsubscribe(self, token: str) -> bool:
        """Unsubscribe user from all notifications.
        
        Args:
            token: Unsubscribe token
            
        Returns:
            True if unsubscribed, False if token invalid
        """
        # Find preferences by token in database
        prefs = self.preferences_store.get_preferences_by_token(token)
        if not prefs:
            return False
        
        # Mark all notifications as disabled
        prefs.notify_on_reply = False
        prefs.notify_on_event = False
        prefs.notify_on_milestone = False
        
        # Update in database
        self.preferences_store.update_preferences(prefs)
        return True
    
    # Helper methods
    
    def _send_email(
        self,
        recipient_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> bool:
        """Send email via SMTP.
        
        Args:
            recipient_email: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            # Attach text and HTML parts
            msg.attach(MIMEText(body_text, 'plain'))
            msg.attach(MIMEText(body_html, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                
                server.sendmail(self.from_email, recipient_email, msg.as_string())
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    @staticmethod
    def _build_reply_email_html(
        recipient_name: str,
        author: str,
        reply_text: str,
        investigation_title: str,
        investigation_id: str,
        investigation_url: str,
        unsubscribe_token: Optional[str] = None,
    ) -> str:
        """Build HTML email for reply notification."""
        unsubscribe_link = f"{investigation_url.rsplit('/', 1)[0]}/unsubscribe?token={unsubscribe_token}" if unsubscribe_token else ""
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>New Reply on Investigation</h2>
                    
                    <p>Hi {recipient_name},</p>
                    
                    <p><strong>{author}</strong> replied to your comment on <strong>{investigation_title}</strong>:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                        <p style="margin: 0; white-space: pre-wrap;">{reply_text}</p>
                    </div>
                    
                    <p>
                        <a href="{investigation_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            View Investigation
                        </a>
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #999;">
                        Investigation ID: {investigation_id}<br>
                        {f'<a href="{unsubscribe_link}" style="color: #999;">Unsubscribe from notifications</a>' if unsubscribe_token else ''}
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_reply_email_text(
        recipient_name: str,
        author: str,
        reply_text: str,
        investigation_title: str,
        investigation_url: str,
    ) -> str:
        """Build plain text email for reply notification."""
        return f"""
Hi {recipient_name},

{author} replied to your comment on "{investigation_title}":

---
{reply_text}
---

View the investigation: {investigation_url}
        """
    
    @staticmethod
    def _build_event_email_html(
        recipient_name: str,
        event_count: int,
        investigation_title: str,
        investigation_id: str,
        investigation_url: str,
        unsubscribe_token: Optional[str] = None,
    ) -> str:
        """Build HTML email for event notification."""
        unsubscribe_link = f"{investigation_url.rsplit('/', 1)[0]}/unsubscribe?token={unsubscribe_token}" if unsubscribe_token else ""
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>New Events Linked</h2>
                    
                    <p>Hi {recipient_name},</p>
                    
                    <p><strong>{event_count} new event(s)</strong> have been linked to <strong>{investigation_title}</strong>.</p>
                    
                    <p>These events may provide important context for your investigation:</p>
                    
                    <p>
                        <a href="{investigation_url}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Review Events
                        </a>
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #999;">
                        Investigation ID: {investigation_id}<br>
                        {f'<a href="{unsubscribe_link}" style="color: #999;">Unsubscribe from notifications</a>' if unsubscribe_token else ''}
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_event_email_text(
        recipient_name: str,
        event_count: int,
        investigation_title: str,
        investigation_url: str,
    ) -> str:
        """Build plain text email for event notification."""
        return f"""
Hi {recipient_name},

{event_count} new event(s) have been linked to "{investigation_title}".

These events may provide important context for your investigation.

Review events: {investigation_url}
        """
    
    @staticmethod
    def _build_digest_email_html(
        recipient_name: str,
        digest_items: List[Dict[str, Any]],
        unsubscribe_token: Optional[str] = None,
    ) -> str:
        """Build HTML email for digest notification."""
        items_html = ""
        for item in digest_items:
            if item['type'] == 'reply':
                items_html += f"""
                <div style="margin: 15px 0; padding: 15px; background-color: #f9f9f9; border-left: 3px solid #007bff;">
                    <p style="margin: 0 0 10px 0;"><strong>Reply on "{item['investigation_title']}"</strong></p>
                    <p style="margin: 0; color: #666;"><em>By {item['author']}</em></p>
                </div>
                """
            elif item['type'] == 'events':
                items_html += f"""
                <div style="margin: 15px 0; padding: 15px; background-color: #f9f9f9; border-left: 3px solid #28a745;">
                    <p style="margin: 0 0 10px 0;"><strong>{item['count']} new events on "{item['investigation_title']}"</strong></p>
                </div>
                """
        
        unsubscribe_link = f"https://git-rca.local/unsubscribe?token={unsubscribe_token}" if unsubscribe_token else ""
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Git RCA Daily Digest</h2>
                    
                    <p>Hi {recipient_name},</p>
                    
                    <p>You have <strong>{len(digest_items)} update(s)</strong> from your investigations:</p>
                    
                    {items_html}
                    
                    <p>
                        <a href="https://git-rca.local/investigations" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            View All Investigations
                        </a>
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="font-size: 12px; color: #999;">
                        {f'<a href="{unsubscribe_link}" style="color: #999;">Unsubscribe from digest emails</a>' if unsubscribe_token else ''}
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_digest_email_text(
        recipient_name: str,
        digest_items: List[Dict[str, Any]],
    ) -> str:
        """Build plain text email for digest notification."""
        items_text = "\n".join([
            f"- {item['type'].upper()}: {item.get('investigation_title', 'N/A')}"
            for item in digest_items
        ])
        
        return f"""
Hi {recipient_name},

You have {len(digest_items)} update(s) from your investigations:

{items_text}

View all investigations: https://git-rca.local/investigations
        """
