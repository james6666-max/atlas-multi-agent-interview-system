import asyncio

import pytest

from app.agents.base import Agent
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.registry import AgentRegistry


def make_event(event_type: EventType) -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=event_type,
        payload={"text": "question"},
    )


class EchoAgent(Agent):
    name = "echo"
    subscribes_to = {EventType.MANUAL_INPUT}
    emits = {EventType.QUESTION_DETECTED}

    async def handle(self, event: BBEvent) -> list[BBEvent]:
        return [
            BBEvent(
                session_id=event.session_id,
                source_agent=self.name,
                type=EventType.QUESTION_DETECTED,
                payload={"question": event.payload["text"]},
                parent_event_id=event.event_id,
            )
        ]


class BadEmitAgent(Agent):
    name = "bad_emit"
    subscribes_to = {EventType.MANUAL_INPUT}
    emits = {EventType.QUESTION_DETECTED}

    async def handle(self, event: BBEvent) -> list[BBEvent]:
        return [
            BBEvent(
                session_id=event.session_id,
                source_agent=self.name,
                type=EventType.ERROR,
                payload={"error": "undeclared"},
                parent_event_id=event.event_id,
            )
        ]


def test_agent_only_handles_subscribed_events() -> None:
    bus = InMemoryBlackboardBus()
    agent = EchoAgent(bus)

    outputs = asyncio.run(agent.run_once(make_event(EventType.OCR_TEXT)))

    assert outputs == []
    assert bus.replay("session-1") == []


def test_agent_publishes_declared_outputs() -> None:
    bus = InMemoryBlackboardBus()
    agent = EchoAgent(bus)

    outputs = asyncio.run(agent.run_once(make_event(EventType.MANUAL_INPUT)))

    assert len(outputs) == 1
    assert outputs[0].type == EventType.QUESTION_DETECTED
    assert bus.latest("session-1", EventType.QUESTION_DETECTED) == outputs[0]


def test_agent_cannot_emit_undeclared_event_type() -> None:
    bus = InMemoryBlackboardBus()
    agent = BadEmitAgent(bus)

    with pytest.raises(ValueError, match="undeclared event type"):
        asyncio.run(agent.run_once(make_event(EventType.MANUAL_INPUT)))

    assert bus.replay("session-1") == []


def test_orchestrator_dispatches_event_to_matching_agent() -> None:
    bus = InMemoryBlackboardBus()
    registry = AgentRegistry()
    registry.register(EchoAgent(bus))
    orchestrator = Orchestrator(bus, registry)
    event = make_event(EventType.MANUAL_INPUT)

    outputs = asyncio.run(orchestrator.dispatch(event))

    assert len(outputs) == 1
    assert outputs[0].type == EventType.QUESTION_DETECTED
    assert bus.replay("session-1") == [event, outputs[0]]
