"""
Event Stream Service
=====================

Provides event streaming and pub/sub capabilities for canvas changes
and other system events. Enables real-time notifications and event-driven
architecture for investigation canvas operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
import uuid


class EventType(Enum):
    """Types of events that can be streamed."""

    # Canvas events
    CANVAS_CREATED = "canvas_created"
    CANVAS_UPDATED = "canvas_updated"
    CANVAS_DELETED = "canvas_deleted"
    CANVAS_REVERTED = "canvas_reverted"

    # Node events
    NODE_ADDED = "node_added"
    NODE_UPDATED = "node_updated"
    NODE_DELETED = "node_deleted"

    # Edge events
    EDGE_ADDED = "edge_added"
    EDGE_UPDATED = "edge_updated"
    EDGE_DELETED = "edge_deleted"

    # Access control events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"

    # Version events
    VERSION_CREATED = "version_created"
    VERSION_ROLLBACK = "version_rollback"

    # System events
    AUDIT_LOGGED = "audit_logged"
    METRIC_RECORDED = "metric_recorded"


@dataclass
class CanvasChangeEvent:
    """An event representing a change to the canvas."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = field(default=EventType.CANVAS_UPDATED)
    canvas_id: str = ""
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "canvas_id": self.canvas_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanvasChangeEvent":
        """Create event from dictionary."""
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=EventType(data.get("event_type", "canvas_updated")),
            canvas_id=data.get("canvas_id", ""),
            user_id=data.get("user_id", ""),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.utcnow().isoformat())
            ),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EventSubscription:
    """A subscription to events."""

    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    handler: Callable[[CanvasChangeEvent], None] = field(default=lambda x: None)
    event_types: Set[EventType] = field(default_factory=lambda: set(EventType))
    canvas_id: Optional[str] = None
    user_id: Optional[str] = None
    active: bool = True


class EventStream:
    """Manages event streaming with publish/subscribe pattern."""

    def __init__(self):
        """Initialize the event stream."""
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.event_history: List[CanvasChangeEvent] = []
        self.max_history_size = 10000
        self.event_handlers: Dict[str, List[Callable]] = {}

    def publish(self, event: CanvasChangeEvent) -> None:
        """Publish an event to all matching subscribers.

        Args:
            event: The event to publish
        """
        # Add to history
        self._add_to_history(event)

        # Notify subscribers
        for subscription in self.subscriptions.values():
            if self._matches_subscription(event, subscription):
                try:
                    subscription.handler(event)
                except Exception:
                    # Handler error - don't propagate
                    pass

    def subscribe(
        self,
        handler: Callable[[CanvasChangeEvent], None],
        event_types: Optional[Set[EventType]] = None,
        canvas_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Subscribe to events.

        Args:
            handler: Function to call when matching event is published
            event_types: Types of events to subscribe to (None = all)
            canvas_id: Filter by canvas ID (None = all canvases)
            user_id: Filter by user ID (None = all users)

        Returns:
            Subscription ID
        """
        subscription = EventSubscription(
            handler=handler,
            event_types=event_types or set(EventType),
            canvas_id=canvas_id,
            user_id=user_id,
        )

        self.subscriptions[subscription.subscription_id] = subscription
        return subscription.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: ID of subscription to remove

        Returns:
            True if subscription existed and was removed
        """
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            return True
        return False

    def get_subscriptions(self) -> List[EventSubscription]:
        """Get all active subscriptions.

        Returns:
            List of subscriptions
        """
        return [s for s in self.subscriptions.values() if s.active]

    def pause_subscription(self, subscription_id: str) -> bool:
        """Pause a subscription temporarily.

        Args:
            subscription_id: ID of subscription to pause

        Returns:
            True if subscription was paused
        """
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].active = False
            return True
        return False

    def resume_subscription(self, subscription_id: str) -> bool:
        """Resume a paused subscription.

        Args:
            subscription_id: ID of subscription to resume

        Returns:
            True if subscription was resumed
        """
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].active = True
            return True
        return False

    def get_event_history(
        self,
        canvas_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[CanvasChangeEvent]:
        """Get event history with optional filters.

        Args:
            canvas_id: Filter by canvas ID
            event_type: Filter by event type
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        filtered = self.event_history

        if canvas_id:
            filtered = [e for e in filtered if e.canvas_id == canvas_id]

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        # Return most recent first
        return list(reversed(filtered[-limit:]))

    def get_event_by_id(self, event_id: str) -> Optional[CanvasChangeEvent]:
        """Get a specific event by ID.

        Args:
            event_id: ID of event to retrieve

        Returns:
            Event if found, None otherwise
        """
        for event in self.event_history:
            if event.event_id == event_id:
                return event
        return None

    def get_canvas_events(
        self,
        canvas_id: str,
        limit: int = 100,
    ) -> List[CanvasChangeEvent]:
        """Get all events for a specific canvas.

        Args:
            canvas_id: ID of canvas
            limit: Maximum number of events

        Returns:
            List of events
        """
        return self.get_event_history(canvas_id=canvas_id, limit=limit)

    def get_user_events(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[CanvasChangeEvent]:
        """Get all events triggered by a specific user.

        Args:
            user_id: ID of user
            limit: Maximum number of events

        Returns:
            List of events
        """
        filtered = [e for e in self.event_history if e.user_id == user_id]
        return list(reversed(filtered[-limit:]))

    def get_event_count(self, canvas_id: Optional[str] = None) -> int:
        """Get count of events.

        Args:
            canvas_id: Optional canvas ID to filter

        Returns:
            Number of events
        """
        if canvas_id:
            return len([e for e in self.event_history if e.canvas_id == canvas_id])
        return len(self.event_history)

    def clear_history(self) -> int:
        """Clear all event history.

        Returns:
            Number of events cleared
        """
        count = len(self.event_history)
        self.event_history = []
        return count

    def _add_to_history(self, event: CanvasChangeEvent) -> None:
        """Add event to history, maintaining size limit."""
        self.event_history.append(event)

        # Trim history if too large
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size :]

    def _matches_subscription(
        self,
        event: CanvasChangeEvent,
        subscription: EventSubscription,
    ) -> bool:
        """Check if event matches subscription filters."""
        if not subscription.active:
            return False

        # Check event type
        if (
            subscription.event_types
            and event.event_type not in subscription.event_types
        ):
            return False

        # Check canvas ID filter
        if subscription.canvas_id and event.canvas_id != subscription.canvas_id:
            return False

        # Check user ID filter
        if subscription.user_id and event.user_id != subscription.user_id:
            return False

        return True


# Global event stream instance
_event_stream: Optional[EventStream] = None


def initialize_event_stream() -> EventStream:
    """Initialize the global event stream.

    Returns:
        The event stream instance
    """
    global _event_stream
    _event_stream = EventStream()
    return _event_stream


def get_event_stream() -> EventStream:
    """Get the global event stream instance.

    Returns:
        The event stream instance

    Raises:
        RuntimeError: If event stream not initialized
    """
    global _event_stream
    if _event_stream is None:
        _event_stream = initialize_event_stream()
    return _event_stream


def publish_event(event: CanvasChangeEvent) -> None:
    """Publish an event to the global stream.

    Args:
        event: Event to publish
    """
    get_event_stream().publish(event)


def subscribe_to_events(
    handler: Callable[[CanvasChangeEvent], None],
    event_types: Optional[Set[EventType]] = None,
    canvas_id: Optional[str] = None,
) -> str:
    """Subscribe to events in the global stream.

    Args:
        handler: Callback function
        event_types: Event types to subscribe to
        canvas_id: Optional canvas filter

    Returns:
        Subscription ID
    """
    return get_event_stream().subscribe(
        handler=handler,
        event_types=event_types,
        canvas_id=canvas_id,
    )
