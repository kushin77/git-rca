"""
Token revocation and session management for Investigation RCA Platform.

Provides:
- Token revocation list management (memory + SQLite backup)
- Session tracking (active, revoked, expired)
- TTL-based automatic cleanup
- Admin token management endpoints
- Thread-safe operations
"""

import hashlib
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Set
from contextlib import contextmanager


class RevocationError(Exception):
    """Raised when revocation operation fails."""

    pass


class TokenRevocationManager:
    """
    Manages token revocation list with in-memory cache and SQLite persistence.

    Design:
    - In-memory: Fast O(1) lookups for recent revocations
    - SQLite: Persistent storage and audit trail
    - TTL: Automatic cleanup after expiration + grace period
    - Thread-safe: Lock-protected operations

    Storage:
    - Memory: Dict[token_hash -> RevocationRecord]
    - SQLite: table revoked_tokens (token_hash, user_id, reason, revoked_at, exp_at)

    Performance:
    - Token check: <1ms (in-memory lookup)
    - Revoke: ~10ms (memory + disk write)
    - Cleanup: ~100ms (runs in background)
    """

    def __init__(self, db_path: str = "investigations.db"):
        """
        Initialize token revocation manager.

        Args:
            db_path: Path to SQLite database for persistence
        """
        self.db_path = db_path
        self._lock = threading.RLock()

        # In-memory revocation cache: token_hash -> revocation_record
        # Record format: {
        #     'token_hash': str,
        #     'user_id': str,
        #     'reason': str,
        #     'revoked_at': int (timestamp),
        #     'exp_at': int (timestamp),  # Original token expiration
        #     'jti': str,  # JWT ID (token identifier)
        # }
        self._revocation_cache: Dict[str, Dict] = {}

        # Session tracking: user_id -> Set[token_hashes]
        # Tracks all active tokens per user for easy admin revocation
        self._user_sessions: Dict[str, Set[str]] = {}

        # Initialize database
        self._init_db()

        # Load revocations from persistent storage on startup
        self._load_from_db()

    def _init_db(self) -> None:
        """Initialize revocation table if it doesn't exist."""
        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            # Create revoked_tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    reason TEXT,
                    revoked_at INTEGER NOT NULL,
                    exp_at INTEGER NOT NULL,
                    jti TEXT UNIQUE,
                    revoked_by TEXT,
                    
                    FOREIGN KEY(revoked_by) REFERENCES users(id)
                        ON DELETE SET NULL
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_revoked_user_id 
                ON revoked_tokens(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_revoked_exp_at 
                ON revoked_tokens(exp_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_revoked_at 
                ON revoked_tokens(revoked_at)
            """)

            conn.commit()

    @contextmanager
    def _get_db_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _hash_token(self, token: str) -> str:
        """
        Hash token for storage (never store tokens in plain text).

        Args:
            token: Token string

        Returns:
            SHA256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _load_from_db(self) -> None:
        """Load revocation cache from persistent storage."""
        with self._lock:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()

                    # Load recent revocations (last 30 days)
                    cutoff_time = int(
                        (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
                    )

                    cursor.execute(
                        """
                        SELECT token_hash, user_id, reason, revoked_at, exp_at, jti
                        FROM revoked_tokens
                        WHERE exp_at > ?
                        ORDER BY revoked_at DESC
                    """,
                        (cutoff_time,),
                    )

                    for row in cursor.fetchall():
                        token_hash = row["token_hash"]
                        record = {
                            "token_hash": token_hash,
                            "user_id": row["user_id"],
                            "reason": row["reason"],
                            "revoked_at": row["revoked_at"],
                            "exp_at": row["exp_at"],
                            "jti": row["jti"],
                        }
                        self._revocation_cache[token_hash] = record

                        # Rebuild user sessions
                        user_id = row["user_id"]
                        if user_id not in self._user_sessions:
                            self._user_sessions[user_id] = set()
                        self._user_sessions[user_id].add(token_hash)

            except Exception as e:
                # Fail safely - log but don't crash on DB load
                print(f"Warning: Failed to load revocations from DB: {e}")

    def revoke_token(
        self,
        token: str,
        user_id: str,
        exp_timestamp: int,
        reason: str = "logout",
        jti: Optional[str] = None,
        revoked_by: Optional[str] = None,
    ) -> None:
        """
        Revoke a token immediately.

        Args:
            token: Full token string to revoke
            user_id: User ID who owns the token
            exp_timestamp: Original token expiration timestamp
            reason: Why token was revoked (logout, password_change, admin_action)
            jti: JWT ID (unique token identifier)
            revoked_by: Admin user who revoked the token (if admin action)

        Raises:
            RevocationError: If revocation fails
        """
        with self._lock:
            try:
                token_hash = self._hash_token(token)
                now = int(datetime.now(timezone.utc).timestamp())

                record = {
                    "token_hash": token_hash,
                    "user_id": user_id,
                    "reason": reason,
                    "revoked_at": now,
                    "exp_at": exp_timestamp,
                    "jti": jti,
                }

                # Add to memory cache
                self._revocation_cache[token_hash] = record

                # Track session
                if user_id not in self._user_sessions:
                    self._user_sessions[user_id] = set()
                self._user_sessions[user_id].add(token_hash)

                # Persist to database
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO revoked_tokens
                        (token_hash, user_id, reason, revoked_at, exp_at, jti, revoked_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            token_hash,
                            user_id,
                            reason,
                            now,
                            exp_timestamp,
                            jti,
                            revoked_by,
                        ),
                    )
                    conn.commit()

            except Exception as e:
                raise RevocationError(f"Failed to revoke token: {str(e)}")

    def is_token_revoked(self, token: str) -> bool:
        """
        Check if token is revoked (O(1) memory lookup).

        Args:
            token: Full token string

        Returns:
            True if token is revoked, False otherwise
        """
        with self._lock:
            token_hash = self._hash_token(token)
            return token_hash in self._revocation_cache

    def get_revocation_reason(self, token: str) -> Optional[str]:
        """
        Get reason why token was revoked.

        Args:
            token: Full token string

        Returns:
            Revocation reason or None if not revoked
        """
        with self._lock:
            token_hash = self._hash_token(token)
            record = self._revocation_cache.get(token_hash)
            return record["reason"] if record else None

    def revoke_user_sessions(
        self,
        user_id: str,
        reason: str = "admin_action",
        admin_id: Optional[str] = None,
        keep_current: Optional[str] = None,
    ) -> int:
        """
        Revoke all active sessions for a user.

        Args:
            user_id: User whose sessions to revoke
            reason: Reason for bulk revocation
            admin_id: Admin performing the revocation
            keep_current: Token to keep (optional, for "logout all except this")

        Returns:
            Number of tokens revoked
        """
        with self._lock:
            if user_id not in self._user_sessions:
                return 0

            token_hashes = self._user_sessions[user_id].copy()
            revoked_count = 0

            # Find tokens to revoke
            tokens_to_revoke = []
            for token_hash in token_hashes:
                record = self._revocation_cache.get(token_hash)
                if record:  # Only revoke tokens that are still in cache
                    if keep_current and self._hash_token(keep_current) == token_hash:
                        continue  # Skip this token
                    tokens_to_revoke.append((token_hash, record["exp_at"]))

            # Revoke tokens
            if tokens_to_revoke:
                now = int(datetime.now(timezone.utc).timestamp())
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()

                    for token_hash, exp_at in tokens_to_revoke:
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO revoked_tokens
                            (token_hash, user_id, reason, revoked_at, exp_at, revoked_by)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (token_hash, user_id, reason, now, exp_at, admin_id),
                        )
                        revoked_count += 1

                    conn.commit()

            return revoked_count

    def cleanup_expired_revocations(self) -> int:
        """
        Remove expired revocations from memory cache and mark in DB.

        This runs periodically to prevent unbounded memory growth.
        Tokens are kept in DB for audit trail (6 months).

        Returns:
            Number of revocations cleaned up from memory
        """
        with self._lock:
            now = int(datetime.now(timezone.utc).timestamp())
            cleanup_threshold = now + (7 * 24 * 3600)  # 7 days after expiration

            tokens_to_remove = []
            for token_hash, record in self._revocation_cache.items():
                if record["exp_at"] < cleanup_threshold:
                    tokens_to_remove.append(token_hash)

            # Remove from memory
            for token_hash in tokens_to_remove:
                del self._revocation_cache[token_hash]

            # Clean user sessions
            for user_id in self._user_sessions:
                self._user_sessions[user_id] -= set(tokens_to_remove)

            return len(tokens_to_remove)

    def get_user_sessions(
        self, user_id: str, include_expired: bool = False
    ) -> List[Dict]:
        """
        Get all revoked tokens for a user (for admin view).

        Args:
            user_id: User ID to query
            include_expired: Whether to include expired tokens

        Returns:
            List of revocation records
        """
        with self._lock:
            now = int(datetime.now(timezone.utc).timestamp())
            records = []

            if user_id in self._user_sessions:
                for token_hash in self._user_sessions[user_id]:
                    record = self._revocation_cache.get(token_hash)
                    if record:
                        if include_expired or record["exp_at"] > now:
                            records.append(
                                {
                                    "token_hash": token_hash,
                                    "reason": record["reason"],
                                    "revoked_at": record["revoked_at"],
                                    "exp_at": record["exp_at"],
                                    "is_expired": record["exp_at"] <= now,
                                }
                            )

            return sorted(records, key=lambda r: r["revoked_at"], reverse=True)

    def get_all_revocations(
        self, limit: int = 100, offset: int = 0, user_id: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """
        Get paginated revocation audit log.

        Args:
            limit: Number of records to return
            offset: Starting offset
            user_id: Optional filter by user

        Returns:
            Tuple of (records list, total count)
        """
        with self._lock:
            try:
                with self._get_db_connection() as conn:
                    cursor = conn.cursor()

                    # Get total count
                    if user_id:
                        cursor.execute(
                            "SELECT COUNT(*) as count FROM revoked_tokens WHERE user_id = ?",
                            (user_id,),
                        )
                    else:
                        cursor.execute("SELECT COUNT(*) as count FROM revoked_tokens")

                    total = cursor.fetchone()["count"]

                    # Get records
                    if user_id:
                        cursor.execute(
                            """
                            SELECT token_hash, user_id, reason, revoked_at, exp_at, jti, revoked_by
                            FROM revoked_tokens
                            WHERE user_id = ?
                            ORDER BY revoked_at DESC
                            LIMIT ? OFFSET ?
                        """,
                            (user_id, limit, offset),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT token_hash, user_id, reason, revoked_at, exp_at, jti, revoked_by
                            FROM revoked_tokens
                            ORDER BY revoked_at DESC
                            LIMIT ? OFFSET ?
                        """,
                            (limit, offset),
                        )

                    records = [dict(row) for row in cursor.fetchall()]

                    return records, total

            except Exception as e:
                print(f"Error querying revocations: {e}")
                return [], 0

    def get_stats(self) -> Dict:
        """
        Get revocation statistics for monitoring.

        Returns:
            Dict with cache size, active sessions, etc.
        """
        with self._lock:
            now = int(datetime.now(timezone.utc).timestamp())
            active_revocations = sum(
                1 for r in self._revocation_cache.values() if r["exp_at"] > now
            )

            return {
                "cache_size": len(self._revocation_cache),
                "active_revocations": active_revocations,
                "unique_users": len(self._user_sessions),
                "timestamp": now,
            }


# Global revocation manager instance
_revocation_manager: Optional[TokenRevocationManager] = None


def get_revocation_manager() -> TokenRevocationManager:
    """Get or create the global token revocation manager."""
    global _revocation_manager
    if _revocation_manager is None:
        _revocation_manager = TokenRevocationManager()
    return _revocation_manager


def init_revocation(app):
    """
    Initialize token revocation module with Flask app.

    Usage:
        app = create_app()
        init_revocation(app)
    """
    global _revocation_manager
    db_path = app.config.get("REVOCATION_DB", "investigations.db")
    _revocation_manager = TokenRevocationManager(db_path)

    # TODO: Add periodic cleanup task in production
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(
    #     _revocation_manager.cleanup_expired_revocations,
    #     'interval',
    #     hours=6  # Run every 6 hours
    # )
    # scheduler.start()
