import asyncio

from app.adapters import phase1_pipeline
from app.agents.main_agent import MainAgent
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.registry import AgentRegistry


def critic_payload() -> dict:
    return {
        "clarity_score": 0.9,
        "correctness_score": 0.9,
        "human_like_score": 0.8,
        "resume_alignment_score": 0.7,
        "privacy_score": 1.0,
        "jd_alignment_score": 0.6,
        "jd_alignment_notes": ["ok"],
        "final_score": 85,
        "main_weakness": "none",
        "specific_issues": [],
        "rewrite_strategy": "keep",
        "should_rewrite": False,
        "critic_notes": [],
        "improved_answer_suggestion": "ok",
        "human_like_rewrite": {},
        "followup_questions": {},
    }


def pipeline_result(question: str = "mock question") -> dict:
    return {
        "question": question,
        "question_type": "Behavioral",
        "selected_agent": "Behavioral",
        "answer": "mock answer",
        "critic": critic_payload(),
        "blackboard_version": 123,
    }


def make_manual_event(payload: dict) -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=EventType.QUESTION_DETECTED,
        payload=payload,
    )


def test_main_agent_consumes_question_detected_and_emits_answer_final(monkeypatch) -> None:
    async def fake_pipeline(question: str, language: str = "Unknown", source: str = "manual_input") -> dict:
        return pipeline_result(question)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    bus = InMemoryBlackboardBus()
    agent = MainAgent(bus)

    outputs = asyncio.run(agent.run_once(make_manual_event({"text": "hello"})))

    assert [event.type for event in outputs] == [
        EventType.ANSWER_DRAFT,
        EventType.CRITIQUE_NOTE,
        EventType.ANSWER_FINAL,
    ]
    assert outputs[-1].payload["answer"] == "mock answer"
    assert bus.latest("session-1", EventType.ANSWER_FINAL) == outputs[-1]


def test_orchestrator_dispatches_to_main_agent(monkeypatch) -> None:
    async def fake_pipeline(question: str, language: str = "Unknown", source: str = "manual_input") -> dict:
        return pipeline_result(question)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    bus = InMemoryBlackboardBus()
    registry = AgentRegistry()
    registry.register(MainAgent(bus))
    orchestrator = Orchestrator(bus, registry)

    outputs = asyncio.run(orchestrator.dispatch(make_manual_event({"question": "hello"})))

    assert any(event.type == EventType.ANSWER_FINAL for event in outputs)
    assert bus.replay("session-1")[0].type == EventType.QUESTION_DETECTED
    assert bus.replay("session-1")[-1].type == EventType.ANSWER_FINAL


def test_main_agent_emits_error_when_pipeline_fails(monkeypatch) -> None:
    async def broken_pipeline(question: str, language: str = "Unknown", source: str = "manual_input") -> dict:
        raise RuntimeError("pipeline failed")

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", broken_pipeline)
    bus = InMemoryBlackboardBus()
    agent = MainAgent(bus)

    outputs = asyncio.run(agent.run_once(make_manual_event({"question": "hello"})))

    assert len(outputs) == 1
    assert outputs[0].type == EventType.ERROR
    assert "pipeline failed" in outputs[0].payload["error"]


def test_main_agent_does_not_consume_manual_input(monkeypatch) -> None:
    async def fake_pipeline(question: str, language: str = "Unknown", source: str = "manual_input") -> dict:
        return pipeline_result(question)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    bus = InMemoryBlackboardBus()
    agent = MainAgent(bus)
    event = BBEvent(
        session_id="session-1",
        source_agent="test",
        type=EventType.MANUAL_INPUT,
        payload={"question": "hello"},
    )

    outputs = asyncio.run(agent.run_once(event))

    assert outputs == []
    assert bus.replay("session-1") == []
