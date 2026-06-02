import asyncio

from app.adapters import phase1_pipeline
from app.agents.tech_agent import TechAgent
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType


def critic_payload() -> dict:
    return {
        "final_score": 88,
        "critic_notes": [],
    }


def event(question_type: str) -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=EventType.QUESTION_DETECTED,
        payload={"question": "mock question", "question_type": question_type},
    )


async def fake_pipeline(
    question: str,
    language: str = "Unknown",
    source: str = "manual_input",
    agent_hint: str | None = None,
    question_type: str | None = None,
    context: dict | None = None,
    rag: dict | None = None,
) -> dict:
    return {
        "question": question,
        "question_type": question_type,
        "selected_agent": "Tech/Code",
        "answer": f"{agent_hint}:{question_type}:answer",
        "critic": critic_payload(),
        "blackboard_version": 1,
        "context_used": bool(context),
        "context_sources": ["resume"] if context else [],
        "context": context or {},
        "rag_used": bool(rag and rag.get("has_rag")),
        "rag_sources": rag.get("sources", []) if rag else [],
        "rag": rag or {},
    }


def assert_answer_final(outputs, expected_type: str) -> None:
    assert [event.type for event in outputs] == [EventType.ANSWER_DRAFT]
    assert outputs[-1].payload["question_type"] == expected_type
    assert outputs[-1].payload["selected_agent"] == "Tech/Code"
    assert outputs[-1].payload["draft"]


def test_technical_routes_to_tech_agent(monkeypatch) -> None:
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    outputs = asyncio.run(TechAgent(InMemoryBlackboardBus()).run_once(event("technical")))

    assert_answer_final(outputs, "technical")


def test_algorithm_routes_to_tech_agent(monkeypatch) -> None:
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    outputs = asyncio.run(TechAgent(InMemoryBlackboardBus()).run_once(event("algorithm")))

    assert_answer_final(outputs, "algorithm")


def test_system_design_routes_to_tech_agent(monkeypatch) -> None:
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    outputs = asyncio.run(TechAgent(InMemoryBlackboardBus()).run_once(event("system_design")))

    assert_answer_final(outputs, "system_design")


def test_behavioral_is_ignored_by_tech_agent(monkeypatch) -> None:
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    outputs = asyncio.run(TechAgent(InMemoryBlackboardBus()).run_once(event("behavioral")))

    assert outputs == []


def test_resume_followup_is_ignored_by_tech_agent(monkeypatch) -> None:
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    outputs = asyncio.run(TechAgent(InMemoryBlackboardBus()).run_once(event("resume_followup")))

    assert outputs == []
