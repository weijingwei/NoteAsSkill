"""EventBus 测试"""
import pytest
from app.core.event_bus import EventBus, Event, EventType, get_event_bus


class TestEventBus:
    def _get_bus(self):
        """获取干净的 EventBus 实例"""
        bus = EventBus()
        bus.clear_subscribers()
        return bus

    def test_subscribe_and_publish(self):
        bus = self._get_bus()

        received = []
        def handler(event):
            received.append(event)

        bus.subscribe(EventType.NOTE_CREATED, handler)
        bus.publish(Event(EventType.NOTE_CREATED, data="test-note"))

        assert len(received) == 1
        assert received[0].data == "test-note"

    def test_publish_simple(self):
        bus = self._get_bus()

        received = []
        def handler(event):
            received.append(event)

        bus.subscribe(EventType.NOTE_DELETED, handler)
        bus.publish_simple(EventType.NOTE_DELETED, data="deleted-note", source="test")

        assert len(received) == 1
        assert received[0].data == "deleted-note"
        assert received[0].source == "test"

    def test_unsubscribe(self):
        bus = self._get_bus()

        call_count = [0]
        def handler(event):
            call_count[0] += 1

        bus.subscribe(EventType.NOTE_UPDATED, handler)
        bus.publish(Event(EventType.NOTE_UPDATED))
        bus.unsubscribe(EventType.NOTE_UPDATED, handler)
        bus.publish(Event(EventType.NOTE_UPDATED))

        assert call_count[0] == 1

    def test_multiple_subscribers(self):
        bus = self._get_bus()

        results = []
        def handler1(event):
            results.append("h1")
        def handler2(event):
            results.append("h2")

        bus.subscribe(EventType.CONFIG_CHANGED, handler1)
        bus.subscribe(EventType.CONFIG_CHANGED, handler2)
        bus.publish(Event(EventType.CONFIG_CHANGED))

        assert "h1" in results
        assert "h2" in results

    def test_subscriber_count(self):
        bus = self._get_bus()

        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 0

        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 2

    def test_clear_all_subscribers(self):
        bus = self._get_bus()

        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        bus.subscribe(EventType.NOTE_DELETED, lambda e: None)

        bus.clear_subscribers()
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 0
        assert bus.get_subscriber_count(EventType.NOTE_DELETED) == 0

    def test_clear_single_event_type(self):
        bus = self._get_bus()

        bus.subscribe(EventType.NOTE_CREATED, lambda e: None)
        bus.subscribe(EventType.NOTE_DELETED, lambda e: None)

        bus.clear_subscribers(EventType.NOTE_CREATED)
        assert bus.get_subscriber_count(EventType.NOTE_CREATED) == 0
        assert bus.get_subscriber_count(EventType.NOTE_DELETED) == 1

    def test_event_timestamp_auto_generated(self):
        event = Event(EventType.NOTE_CREATED)
        assert event.timestamp != ""

    def test_error_in_callback_doesnt_crash(self):
        bus = self._get_bus()

        def bad_handler(event):
            raise ValueError("test error")

        bus.subscribe(EventType.NOTE_MOVED, bad_handler)
        # 不应抛出异常
        bus.publish(Event(EventType.NOTE_MOVED))

    def test_duplicate_subscription_ignored(self):
        bus = self._get_bus()

        call_count = [0]
        def handler(event):
            call_count[0] += 1

        bus.subscribe(EventType.NOTE_CREATED, handler)
        bus.subscribe(EventType.NOTE_CREATED, handler)  # 重复订阅
        bus.publish(Event(EventType.NOTE_CREATED))

        assert call_count[0] == 1

    def test_publish_to_unsubscribed_event_type(self):
        bus = self._get_bus()
        # 没有订阅者时发布不应报错
        bus.publish(Event(EventType.NOTE_CREATED))

    def test_unsubscribe_nonexistent_callback(self):
        bus = self._get_bus()
        # 取消未订阅的回调不应报错
        bus.unsubscribe(EventType.NOTE_CREATED, lambda e: None)


class TestEvent:
    def test_event_with_all_fields(self):
        event = Event(
            type=EventType.NOTE_CREATED,
            data={"id": 1},
            source="test",
            timestamp="2024-01-01T00:00:00"
        )
        assert event.type == EventType.NOTE_CREATED
        assert event.data == {"id": 1}
        assert event.source == "test"
        assert event.timestamp == "2024-01-01T00:00:00"


class TestGetEventBus:
    def test_returns_singleton(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2
        bus1.clear_subscribers()
