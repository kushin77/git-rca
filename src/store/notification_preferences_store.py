"""
Notification Preferences Store - SQL Data Access Layer

Provides CRUD operations for user notification preferences using SQLite.
Handles database initialization and persistence of email notification settings.

This store bridges NotificationPreferences model and SQLite database.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from src.services.email_notifier import NotificationPreferences


class NotificationPreferencesStore:
    """Data access layer for notification preferences."""

    def __init__(self, db_path: str = "investigations.db"):
        """Initialize the notification preferences store.

        Args:
            db_path: Path to SQLite database file (shares with investigations)
        """
        self.db_path = db_path
        self.initialize()

    def initialize(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Notification preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_email TEXT PRIMARY KEY,
                notify_on_reply INTEGER DEFAULT 1,
                notify_on_event INTEGER DEFAULT 1,
                notify_on_milestone INTEGER DEFAULT 1,
                digest_frequency TEXT DEFAULT 'daily',
                unsubscribe_token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Unsubscribe tokens index (for fast lookup by token)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_unsubscribe_token
            ON notification_preferences(unsubscribe_token)
        """)

        conn.commit()
        conn.close()

    def create_preferences(
        self,
        user_email: str,
        notify_on_reply: bool = True,
        notify_on_event: bool = True,
        notify_on_milestone: bool = True,
        digest_frequency: str = "daily",
        unsubscribe_token: Optional[str] = None,
    ) -> NotificationPreferences:
        """Create new notification preferences for a user.

        Args:
            user_email: User email address
            notify_on_reply: Notify on annotation replies
            notify_on_event: Notify on new events
            notify_on_milestone: Notify on milestones
            digest_frequency: 'instant', 'daily', 'weekly', 'never'
            unsubscribe_token: Custom unsubscribe token (auto-generated if None)

        Returns:
            NotificationPreferences instance

        Raises:
            sqlite3.IntegrityError: If user email already exists
        """
        token = unsubscribe_token or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO notification_preferences (
                    user_email,
                    notify_on_reply,
                    notify_on_event,
                    notify_on_milestone,
                    digest_frequency,
                    unsubscribe_token,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_email,
                    int(notify_on_reply),
                    int(notify_on_event),
                    int(notify_on_milestone),
                    digest_frequency,
                    token,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return NotificationPreferences(
            user_email=user_email,
            notify_on_reply=notify_on_reply,
            notify_on_event=notify_on_event,
            notify_on_milestone=notify_on_milestone,
            digest_frequency=digest_frequency,
            unsubscribe_token=token,
        )

    def get_preferences(self, user_email: str) -> Optional[NotificationPreferences]:
        """Get notification preferences for a user.

        Args:
            user_email: User email address

        Returns:
            NotificationPreferences instance or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT user_email, notify_on_reply, notify_on_event,
                       notify_on_milestone, digest_frequency, unsubscribe_token
                FROM notification_preferences
                WHERE user_email = ?
            """,
                (user_email,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return NotificationPreferences(
                user_email=row[0],
                notify_on_reply=bool(row[1]),
                notify_on_event=bool(row[2]),
                notify_on_milestone=bool(row[3]),
                digest_frequency=row[4],
                unsubscribe_token=row[5],
            )
        finally:
            conn.close()

    def get_preferences_by_token(
        self, unsubscribe_token: str
    ) -> Optional[NotificationPreferences]:
        """Get notification preferences by unsubscribe token.

        Args:
            unsubscribe_token: Unsubscribe token

        Returns:
            NotificationPreferences instance or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT user_email, notify_on_reply, notify_on_event,
                       notify_on_milestone, digest_frequency, unsubscribe_token
                FROM notification_preferences
                WHERE unsubscribe_token = ?
            """,
                (unsubscribe_token,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return NotificationPreferences(
                user_email=row[0],
                notify_on_reply=bool(row[1]),
                notify_on_event=bool(row[2]),
                notify_on_milestone=bool(row[3]),
                digest_frequency=row[4],
                unsubscribe_token=row[5],
            )
        finally:
            conn.close()

    def update_preferences(self, preferences: NotificationPreferences) -> None:
        """Update notification preferences for a user.

        Args:
            preferences: NotificationPreferences instance with updated values
        """
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE notification_preferences
                SET notify_on_reply = ?,
                    notify_on_event = ?,
                    notify_on_milestone = ?,
                    digest_frequency = ?,
                    updated_at = ?
                WHERE user_email = ?
            """,
                (
                    int(preferences.notify_on_reply),
                    int(preferences.notify_on_event),
                    int(preferences.notify_on_milestone),
                    preferences.digest_frequency,
                    now,
                    preferences.user_email,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def set_preferences(self, preferences: NotificationPreferences) -> None:
        """Set notification preferences (create or update).

        Args:
            preferences: NotificationPreferences instance
        """
        # Check if exists
        if self.get_preferences(preferences.user_email):
            self.update_preferences(preferences)
        else:
            self.create_preferences(
                user_email=preferences.user_email,
                notify_on_reply=preferences.notify_on_reply,
                notify_on_event=preferences.notify_on_event,
                notify_on_milestone=preferences.notify_on_milestone,
                digest_frequency=preferences.digest_frequency,
                unsubscribe_token=preferences.unsubscribe_token,
            )

    def delete_preferences(self, user_email: str) -> bool:
        """Delete notification preferences for a user.

        Args:
            user_email: User email address

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                DELETE FROM notification_preferences
                WHERE user_email = ?
            """,
                (user_email,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_all_preferences(self) -> List[NotificationPreferences]:
        """List all notification preferences.

        Returns:
            List of NotificationPreferences instances
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT user_email, notify_on_reply, notify_on_event,
                       notify_on_milestone, digest_frequency, unsubscribe_token
                FROM notification_preferences
                ORDER BY created_at DESC
            """)

            preferences = []
            for row in cursor.fetchall():
                preferences.append(
                    NotificationPreferences(
                        user_email=row[0],
                        notify_on_reply=bool(row[1]),
                        notify_on_event=bool(row[2]),
                        notify_on_milestone=bool(row[3]),
                        digest_frequency=row[4],
                        unsubscribe_token=row[5],
                    )
                )

            return preferences
        finally:
            conn.close()

    def get_preferences_by_digest_frequency(
        self, frequency: str
    ) -> List[NotificationPreferences]:
        """Get all users with a specific digest frequency.

        Useful for scheduled digest email jobs.

        Args:
            frequency: 'instant', 'daily', 'weekly', 'never'

        Returns:
            List of NotificationPreferences instances
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT user_email, notify_on_reply, notify_on_event,
                       notify_on_milestone, digest_frequency, unsubscribe_token
                FROM notification_preferences
                WHERE digest_frequency = ? AND notify_on_event = 1
                ORDER BY user_email
            """,
                (frequency,),
            )

            preferences = []
            for row in cursor.fetchall():
                preferences.append(
                    NotificationPreferences(
                        user_email=row[0],
                        notify_on_reply=bool(row[1]),
                        notify_on_event=bool(row[2]),
                        notify_on_milestone=bool(row[3]),
                        digest_frequency=row[4],
                        unsubscribe_token=row[5],
                    )
                )

            return preferences
        finally:
            conn.close()
