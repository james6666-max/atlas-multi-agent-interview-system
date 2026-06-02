from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType


def make_event(event_type: EventType, payload: dict | None = None) -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=event_type,
        payload=payload or {},
    )


def test_publish_then_replay_returns_event() -> None:
    bus = InMemoryBlackboardBus()
    event = make_event(EventType.MANUAL_INPUT, {"text": "hello"})

    published = bus.publish(event)

    assert published is event
    assert bus.replay("session-1") == [event]


def test_latest_returns_last_event_by_type() -> None:
    bus = InMemoryBlackboardBus()
    first = make_event(EventType.MANUAL_INPUT, {"text": "first"})
    draft = make_event(EventType.ANSWER_DRAFT, {"answer": "draft"})
    second = make_event(EventType.MANUAL_INPUT, {"text": "second"})

    bus.publish(first)
    bus.publish(draft)
    bus.publish(second)

    assert bus.latest("session-1") == second
    assert bus.latest("session-1", EventType.MANUAL_INPUT) == second
    assert bus.latest("session-1", EventType.ANSWER_DRAFT) == draft
    assert bus.latest("missing") is None


def test_dump_session_json_is_blackboard_instance_compatible() -> None:
    bus = InMemoryBlackboardBus()
    bus.publish(make_event(EventType.OCR_TEXT, {"text": "question"}))

    dumped = bus.dump_session_json("session-1")

    assert dumped[0]["session_id"] == "session-1"
    assert dumped[0]["type"] == "ocr_text"
    assert dumped[0]["payload"] == {"text": "question"}
