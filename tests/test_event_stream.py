"""
Tests for Event Stream Service
==============================

Comprehensive test suite for event streaming and pub/sub functionality.
"""

import pytest
from datetime import datetime, timezone
from src.services.event_stream import (
    CanvasChangeEvent,
    EventStream,
    EventSubscription,
    EventType,
    initialize_event_stream,
    get_event_stream,
    publish_event,
    subscribe_to_events,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_canvas_events(self):
        """Test canvas event types."""
        assert EventType.CANVAS_CREATED.value == "canvas_created"
        assert EventType.CANVAS_UPDATED.value == "canvas_updated"
        assert EventType.CANVAS_DELETED.value == "canvas_deleted"

    def test_node_events(self):
        """Test node event types."""
        assert EventType.NODE_ADDED.value == "node_added"
        assert EventType.NODE_UPDATED.value == "node_updated"
        assert EventType.NODE_DELETED.value == "node_deleted"

    def test_edge_events(self):
        """Test edge event types."""
        assert EventType.EDGE_ADDED.value == "edge_added"
        assert EventType.EDGE_UPDATED.value == "edge_updated"
        assert EventType.EDGE_DELETED.value == "edge_deleted"


class TestCanvasChangeEvent:
    """Tests for CanvasChangeEvent class."""

    def test_event_creation(self):
        """Test creating an event."""
        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
            data={"name": "Test Canvas"},
        )

        assert event.canvas_id == "canvas-1"
        assert event.user_id == "user-1"
        assert event.event_type == EventType.CANVAS_CREATED

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = CanvasChangeEvent(
            event_type=EventType.NODE_ADDED,
            canvas_id="canvas-1",
            user_id="user-1",
            data={"node_id": "n1"},
        )

        data = event.to_dict()

        assert data["event_type"] == "node_added"
        assert data["canvas_id"] == "canvas-1"
        assert "timestamp" in data

    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        event_dict = {
            "event_id": "evt-1",
            "event_type": "edge_added",
            "canvas_id": "canvas-1",
            "user_id": "user-1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"edge_id": "e1"},
            "metadata": {"source": "api"},
        }

        event = CanvasChangeEvent.from_dict(event_dict)

        assert event.event_id == "evt-1"
        assert event.event_type == EventType.EDGE_ADDED
        assert isinstance(event.timestamp, datetime)


class TestEventSubscription:
    """Tests for EventSubscription class."""

    def test_subscription_creation(self):
        """Test creating a subscription."""
        handler = lambda x: None
        subscription = EventSubscription(
            handler=handler,
            event_types={EventType.CANVAS_CREATED},
            canvas_id="canvas-1",
        )

        assert subscription.handler == handler
        assert EventType.CANVAS_CREATED in subscription.event_types
        assert subscription.canvas_id == "canvas-1"

    def test_subscription_activation(self):
        """Test subscription active status."""
        subscription = EventSubscription(handler=lambda x: None)

        assert subscription.active is True

        subscription.active = False
        assert subscription.active is False


class TestEventStream:
    """Tests for EventStream."""

    def test_stream_initialization(self):
        """Test initializing event stream."""
        stream = EventStream()

        assert len(stream.subscriptions) == 0
        assert len(stream.event_history) == 0

    def test_publish_event(self):
        """Test publishing an event."""
        stream = EventStream()
        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )

        stream.publish(event)

        assert len(stream.event_history) == 1
        assert stream.event_history[0] == event

    def test_subscribe_and_notify(self):
        """Test subscribing to events and receiving notifications."""
        stream = EventStream()
        received = []

        def handler(event):
            received.append(event)

        subscription_id = stream.subscribe(
            handler=handler,
            event_types={EventType.CANVAS_CREATED},
        )

        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )

        stream.publish(event)

        assert len(received) == 1
        assert received[0] == event

    def test_subscribe_multiple_handlers(self):
        """Test multiple subscribers receiving same event."""
        stream = EventStream()
        received1 = []
        received2 = []

        stream.subscribe(handler=lambda e: received1.append(e))
        stream.subscribe(handler=lambda e: received2.append(e))

        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )

        stream.publish(event)

        assert len(received1) == 1
        assert len(received2) == 1

    def test_event_type_filtering(self):
        """Test filtering by event type."""
        stream = EventStream()
        received = []

        stream.subscribe(
            handler=lambda e: received.append(e),
            event_types={EventType.NODE_ADDED},
        )

        # Publish node added event
        event1 = CanvasChangeEvent(
            event_type=EventType.NODE_ADDED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event1)

        # Publish canvas updated event (should not be received)
        event2 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event2)

        assert len(received) == 1
        assert received[0].event_type == EventType.NODE_ADDED

    def test_canvas_id_filtering(self):
        """Test filtering by canvas ID."""
        stream = EventStream()
        received = []

        stream.subscribe(
            handler=lambda e: received.append(e),
            canvas_id="canvas-1",
        )

        # Publish for canvas-1
        event1 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event1)

        # Publish for canvas-2 (should not be received)
        event2 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-2",
            user_id="user-1",
        )
        stream.publish(event2)

        assert len(received) == 1
        assert received[0].canvas_id == "canvas-1"

    def test_user_id_filtering(self):
        """Test filtering by user ID."""
        stream = EventStream()
        received = []

        stream.subscribe(
            handler=lambda e: received.append(e),
            user_id="user-1",
        )

        # Publish from user-1
        event1 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event1)

        # Publish from user-2
        event2 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-2",
        )
        stream.publish(event2)

        assert len(received) == 1
        assert received[0].user_id == "user-1"

    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        stream = EventStream()
        received = []

        sub_id = stream.subscribe(handler=lambda e: received.append(e))

        event1 = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event1)

        assert len(received) == 1

        stream.unsubscribe(sub_id)

        event2 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event2)

        # Should still be 1 since we unsubscribed
        assert len(received) == 1

    def test_pause_resume_subscription(self):
        """Test pausing and resuming subscriptions."""
        stream = EventStream()
        received = []

        sub_id = stream.subscribe(handler=lambda e: received.append(e))

        event1 = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event1)
        assert len(received) == 1

        # Pause subscription
        stream.pause_subscription(sub_id)

        event2 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event2)
        assert len(received) == 1  # Still 1

        # Resume subscription
        stream.resume_subscription(sub_id)

        event3 = CanvasChangeEvent(
            event_type=EventType.NODE_ADDED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event3)
        assert len(received) == 2

    def test_get_subscriptions(self):
        """Test retrieving all subscriptions."""
        stream = EventStream()

        sub1 = stream.subscribe(handler=lambda e: None)
        sub2 = stream.subscribe(handler=lambda e: None)

        subscriptions = stream.get_subscriptions()

        assert len(subscriptions) == 2

    def test_event_history_retrieval(self):
        """Test retrieving event history."""
        stream = EventStream()

        for i in range(5):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id=f"user-{i}",
            )
            stream.publish(event)

        history = stream.get_event_history(limit=3)

        # Should be in reverse order (most recent first)
        assert len(history) == 3
        assert history[0].user_id == "user-4"
        assert history[2].user_id == "user-2"

    def test_get_event_by_id(self):
        """Test retrieving event by ID."""
        stream = EventStream()

        event = CanvasChangeEvent(
            event_id="evt-123",
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event)

        retrieved = stream.get_event_by_id("evt-123")

        assert retrieved == event

    def test_get_canvas_events(self):
        """Test getting all events for a canvas."""
        stream = EventStream()

        for i in range(3):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id="user-1",
            )
            stream.publish(event)

        for i in range(2):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-2",
                user_id="user-1",
            )
            stream.publish(event)

        canvas1_events = stream.get_canvas_events("canvas-1")

        assert len(canvas1_events) == 3
        assert all(e.canvas_id == "canvas-1" for e in canvas1_events)

    def test_get_user_events(self):
        """Test getting all events by a user."""
        stream = EventStream()

        for _ in range(3):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id="user-1",
            )
            stream.publish(event)

        for _ in range(2):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id="user-2",
            )
            stream.publish(event)

        user1_events = stream.get_user_events("user-1")

        assert len(user1_events) == 3
        assert all(e.user_id == "user-1" for e in user1_events)

    def test_get_event_count(self):
        """Test getting event count."""
        stream = EventStream()

        for _ in range(5):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id="user-1",
            )
            stream.publish(event)

        assert stream.get_event_count() == 5
        assert stream.get_event_count(canvas_id="canvas-1") == 5
        assert stream.get_event_count(canvas_id="canvas-2") == 0

    def test_event_type_filtering_multiple(self):
        """Test filtering by multiple event types."""
        stream = EventStream()
        received = []

        stream.subscribe(
            handler=lambda e: received.append(e),
            event_types={EventType.NODE_ADDED, EventType.EDGE_ADDED},
        )

        # Should receive NODE_ADDED
        event1 = CanvasChangeEvent(
            event_type=EventType.NODE_ADDED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event1)

        # Should receive EDGE_ADDED
        event2 = CanvasChangeEvent(
            event_type=EventType.EDGE_ADDED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event2)

        # Should NOT receive CANVAS_UPDATED
        event3 = CanvasChangeEvent(
            event_type=EventType.CANVAS_UPDATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        stream.publish(event3)

        assert len(received) == 2

    def test_clear_history(self):
        """Test clearing event history."""
        stream = EventStream()

        for _ in range(5):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id="user-1",
            )
            stream.publish(event)

        assert stream.get_event_count() == 5

        cleared = stream.clear_history()

        assert cleared == 5
        assert stream.get_event_count() == 0

    def test_history_size_limit(self):
        """Test that history respects size limit."""
        stream = EventStream()
        stream.max_history_size = 100

        # Publish more than max
        for i in range(150):
            event = CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id=f"user-{i}",
            )
            stream.publish(event)

        # Should only have max_history_size events
        assert len(stream.event_history) == 100
        # Should have the latest 100 (from 50-149)
        assert stream.event_history[0].user_id == "user-50"


class TestGlobalEventStream:
    """Tests for global event stream functions."""

    def test_initialize_event_stream(self):
        """Test initializing global event stream."""
        stream = initialize_event_stream()

        assert stream is not None
        assert isinstance(stream, EventStream)

    def test_get_event_stream(self):
        """Test getting global event stream."""
        initialize_event_stream()
        stream = get_event_stream()

        assert stream is not None

    def test_publish_event_global(self):
        """Test publishing via global function."""
        initialize_event_stream()
        received = []

        subscribe_to_events(handler=lambda e: received.append(e))

        event = CanvasChangeEvent(
            event_type=EventType.CANVAS_CREATED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        publish_event(event)

        assert len(received) == 1

    def test_subscribe_to_events_global(self):
        """Test subscribing via global function."""
        initialize_event_stream()
        received = []

        sub_id = subscribe_to_events(
            handler=lambda e: received.append(e),
            event_types={EventType.NODE_ADDED},
        )

        assert sub_id is not None

        event = CanvasChangeEvent(
            event_type=EventType.NODE_ADDED,
            canvas_id="canvas-1",
            user_id="user-1",
        )
        publish_event(event)

        assert len(received) == 1


# Integration test combining multiple event stream features
class TestEventStreamIntegration:
    """Integration tests for event stream."""

    def test_complex_subscription_scenario(self):
        """Test complex scenario with multiple subscriptions and filters."""
        stream = EventStream()

        canvas1_events = []
        user1_events = []
        node_events = []

        # Subscribe to canvas 1 events
        stream.subscribe(
            handler=lambda e: canvas1_events.append(e),
            canvas_id="canvas-1",
        )

        # Subscribe to user 1 events
        stream.subscribe(
            handler=lambda e: user1_events.append(e),
            user_id="user-1",
        )

        # Subscribe to node events
        stream.subscribe(
            handler=lambda e: node_events.append(e),
            event_types={EventType.NODE_ADDED, EventType.NODE_DELETED},
        )

        # Publish various events
        events = [
            CanvasChangeEvent(
                event_type=EventType.NODE_ADDED, canvas_id="canvas-1", user_id="user-1"
            ),
            CanvasChangeEvent(
                event_type=EventType.EDGE_ADDED, canvas_id="canvas-1", user_id="user-2"
            ),
            CanvasChangeEvent(
                event_type=EventType.NODE_ADDED, canvas_id="canvas-2", user_id="user-1"
            ),
            CanvasChangeEvent(
                event_type=EventType.CANVAS_UPDATED,
                canvas_id="canvas-1",
                user_id="user-1",
            ),
        ]

        for event in events:
            stream.publish(event)

        # Verify subscriptions received correct events
        assert len(canvas1_events) == 3  # NODE_ADDED, EDGE_ADDED, CANVAS_UPDATED
        assert (
            len(user1_events) == 3
        )  # NODE_ADDED (c1), NODE_ADDED (c2), CANVAS_UPDATED
        assert len(node_events) == 2  # NODE_ADDED (c1), NODE_ADDED (c2)
