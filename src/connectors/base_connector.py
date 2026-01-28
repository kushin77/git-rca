"""
Base Connector - Standardized interface with enterprise resilience patterns

Provides:
- Retry logic with exponential backoff
- Circuit breaker pattern (CLOSED → OPEN → HALF_OPEN)
- Dead letter queue for failed events
- Event transformation and validation
- Comprehensive error handling and logging
"""

import time
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
import logging
from src.models.event import Event, EventSource, EventSeverity


logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject requests
    HALF_OPEN = "half_open"    # Testing if service recovered


@dataclass
class RetryPolicy:
    """Retry configuration with exponential backoff."""
    max_retries: int = 3
    initial_delay: float = 1.0      # seconds
    max_delay: float = 30.0          # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt (0-based)."""
        if attempt < 0:
            return 0
        
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter (±10%)
            import random
            jitter_factor = 1 + (random.random() - 0.5) * 0.2
            delay *= jitter_factor
        
        return delay


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5        # Failures to trip circuit
    recovery_timeout: int = 60        # Seconds before half-open attempt
    success_threshold: int = 2        # Successes to close circuit from half-open


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fast-fail
    - HALF_OPEN: Testing recovery, allow limited requests
    """
    
    def __init__(self, config: CircuitBreakerConfig = None):
        """Initialize circuit breaker."""
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.utcnow()
    
    def record_success(self) -> None:
        """Record successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._set_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._set_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self._set_open()
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout elapsed
            timeout = timedelta(seconds=self.config.recovery_timeout)
            if datetime.utcnow() - self.last_failure_time > timeout:
                self._set_half_open()
                return True
            return False
        
        # HALF_OPEN: allow request
        return True
    
    def _set_closed(self) -> None:
        """Transition to CLOSED state."""
        if self.state != CircuitBreakerState.CLOSED:
            logger.info("Circuit breaker transitioning to CLOSED")
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_state_change = datetime.utcnow()
    
    def _set_open(self) -> None:
        """Transition to OPEN state."""
        if self.state != CircuitBreakerState.OPEN:
            logger.warning("Circuit breaker transitioning to OPEN")
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            self.last_state_change = datetime.utcnow()
    
    def _set_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        logger.info("Circuit breaker transitioning to HALF_OPEN")
        self.state = CircuitBreakerState.HALF_OPEN
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.utcnow()


class DeadLetterQueue:
    """
    Dead Letter Queue for storing failed events.
    
    Persists events that fail after all retries for later replay.
    """
    
    def __init__(self, db_path: str = "data/dlq.db"):
        """Initialize DLQ with SQLite storage."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dlq_events (
                    id TEXT PRIMARY KEY,
                    event TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    first_failure_at TEXT NOT NULL,
                    last_failure_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            conn.commit()
    
    def put(self, event: Event, error: str, retry_count: int) -> bool:
        """
        Store a failed event in DLQ.
        
        Args:
            event: Event that failed
            error: Error message
            retry_count: Number of retries attempted
            
        Returns:
            bool: True if stored successfully
        """
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO dlq_events
                    (id, event, error_message, retry_count, first_failure_at, last_failure_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.id,
                    json.dumps(event.to_dict()),
                    error,
                    retry_count,
                    now,
                    now,
                    now,
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store event in DLQ: {e}")
            return False
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Retrieve all events in DLQ."""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM dlq_events ORDER BY last_failure_at DESC')
                
                events = []
                for row in cursor.fetchall():
                    events.append({
                        'id': row[0],
                        'event': json.loads(row[1]),
                        'error_message': row[2],
                        'retry_count': row[3],
                        'first_failure_at': row[4],
                        'last_failure_at': row[5],
                        'created_at': row[6],
                    })
                return events
        except Exception as e:
            logger.error(f"Failed to retrieve DLQ events: {e}")
            return []
    
    def remove(self, event_id: str) -> bool:
        """Remove event from DLQ (after replay)."""
        import sqlite3
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM dlq_events WHERE id = ?', (event_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to remove event from DLQ: {e}")
            return False


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.
    
    Provides:
    - Standardized interface for event collection
    - Retry logic with exponential backoff
    - Circuit breaker for fault tolerance
    - Dead letter queue for failed events
    - Event validation and transformation
    """
    
    def __init__(self, 
                 source: EventSource,
                 retry_policy: RetryPolicy = None,
                 circuit_breaker_config: CircuitBreakerConfig = None,
                 dlq_path: str = "data/dlq.db"):
        """
        Initialize base connector.
        
        Args:
            source: EventSource enum value
            retry_policy: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
            dlq_path: Dead letter queue database path
        """
        self.source = source
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config)
        self.dlq = DeadLetterQueue(dlq_path)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def collect(self) -> List[Event]:
        """
        Collect events with retry and circuit breaker.
        
        Returns:
            List of Event objects
        """
        if not self.circuit_breaker.can_execute():
            self.logger.warning(f"Circuit breaker OPEN for {self.source.value}")
            return []
        
        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                events = self._collect_with_timeout()
                self.circuit_breaker.record_success()
                return events
            except Exception as e:
                self.logger.warning(f"Collection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.retry_policy.max_retries:
                    delay = self.retry_policy.get_delay(attempt)
                    self.logger.info(f"Retrying in {delay:.1f}s")
                    time.sleep(delay)
                else:
                    self.circuit_breaker.record_failure()
                    self.logger.error(f"Collection failed after {attempt + 1} attempts")
                    return []
        
        return []
    
    @abstractmethod
    def _collect_with_timeout(self) -> List[Event]:
        """
        Collect events from source. Implement in subclass.
        
        Should raise exception on failure (will be retried).
        
        Returns:
            List of Event objects
        """
        pass
    
    def _handle_event_failure(self, event: Event, error: str, retry_count: int) -> None:
        """Store failed event in DLQ."""
        self.dlq.put(event, error, retry_count)
        self.logger.error(f"Event {event.id} stored in DLQ: {error}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get connector status."""
        return {
            'source': self.source.value,
            'circuit_breaker_state': self.circuit_breaker.state.value,
            'failure_count': self.circuit_breaker.failure_count,
            'dlq_size': len(self.dlq.get_all()),
        }
