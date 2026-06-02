import asyncio

from app.agents.rag_agent import RAGAgent
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType


def detected_event(question: str = "What is RESTful API?") -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=EventType.QUESTION_DETECTED,
        payload={"question": question, "question_type": "technical"},
    )


def test_rag_agent_emits_rag_chunk_with_knowledge_hit(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.agents.rag_agent.load_knowledge_text",
        lambda: "RESTful API uses resources, HTTP methods, and stateless requests.",
    )
    bus = InMemoryBlackboardBus()
    agent = RAGAgent(bus)

    outputs = asyncio.run(agent.run_once(detected_event()))

    assert len(outputs) == 1
    assert outputs[0].type == EventType.RAG_CHUNK
    assert outputs[0].payload["has_rag"] is True
    assert outputs[0].payload["sources"] == ["knowledge.txt"]


def test_rag_agent_emits_empty_rag_chunk_when_no_results(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.rag_agent.load_knowledge_text", lambda: "")
    bus = InMemoryBlackboardBus()
    agent = RAGAgent(bus)

    outputs = asyncio.run(agent.run_once(detected_event()))

    assert outputs[0].type == EventType.RAG_CHUNK
    assert outputs[0].payload["has_rag"] is False
    assert outputs[0].payload["chunks"] == []
    assert outputs[0].payload["sources"] == []


def test_rag_agent_uses_session_replay(monkeypatch) -> None:
    monkeypatch.setattr("app.agents.rag_agent.load_knowledge_text", lambda: "")
    bus = InMemoryBlackboardBus()
    bus.publish(
        BBEvent(
            session_id="session-1",
            source_agent="test",
            type=EventType.ANSWER_FINAL,
            payload={"answer": "RESTful API uses HTTP methods and stateless resources."},
        )
    )
    agent = RAGAgent(bus)

    outputs = asyncio.run(agent.run_once(detected_event()))

    assert outputs[0].payload["has_rag"] is True
    assert outputs[0].payload["sources"] == ["session_replay"]
    assert outputs[0].payload["chunks"][0]["event_type"] == "answer_final"


def test_rag_agent_error_emits_error_event(monkeypatch) -> None:
    def broken_loader():
        raise RuntimeError("knowledge failed")

    monkeypatch.setattr("app.agents.rag_agent.load_knowledge_text", broken_loader)
    bus = InMemoryBlackboardBus()
    agent = RAGAgent(bus)

    outputs = asyncio.run(agent.run_once(detected_event()))

    assert outputs[0].type == EventType.ERROR
    assert "knowledge failed" in outputs[0].payload["error"]
