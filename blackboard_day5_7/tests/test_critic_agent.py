import asyncio

from app.agents.critic_agent import CriticAgent
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType


def draft_event(answer: str, question_type: str = "technical") -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="tech_agent",
        type=EventType.ANSWER_DRAFT,
        payload={
            "question": "What is RESTful API?",
            "question_type": question_type,
            "selected_agent": "Tech/Code",
            "draft": answer,
            "answer": answer,
            "raw_result": {
                "question": "What is RESTful API?",
                "question_type": "Technical/Algorithm",
                "selected_agent": "Tech/Code",
                "answer": answer,
                "critic": {},
                "blackboard_version": 1,
            },
            "context": {"constraints": ["Use only resume/JD/knowledge facts."]},
            "rag": {"has_rag": True, "sources": ["knowledge.txt"]},
            "context_used": True,
            "context_sources": ["resume"],
            "rag_used": True,
            "rag_sources": ["knowledge.txt"],
        },
    )


def test_critic_agent_approves_good_draft() -> None:
    answer = (
        "RESTful API models resources and exposes them through HTTP methods. "
        "Key steps are using GET, POST, PUT, and DELETE consistently, keeping requests stateless, "
        "and returning clear status codes. For example, GET /users/1 reads a user."
    )

    outputs = asyncio.run(CriticAgent(InMemoryBlackboardBus()).run_once(draft_event(answer)))

    assert [event.type for event in outputs] == [
        EventType.CRITIQUE_NOTE,
        EventType.ANSWER_APPROVED,
        EventType.ANSWER_FINAL,
    ]
    assert outputs[-1].source_agent == "critic_agent"
    assert outputs[-1].payload["critic"]["approved"] is True


def test_critic_agent_rejects_ai_tone_and_still_emits_final() -> None:
    outputs = asyncio.run(
        CriticAgent(InMemoryBlackboardBus()).run_once(
            draft_event("As an AI, I cannot actually have interview experience.")
        )
    )

    assert [event.type for event in outputs] == [
        EventType.CRITIQUE_NOTE,
        EventType.ANSWER_REJECTED,
        EventType.ANSWER_FINAL,
    ]
    assert outputs[-1].payload["critic"]["approved"] is False
    assert "As an AI" not in outputs[-1].payload["answer"]


def test_critic_agent_empty_draft_gets_safe_final_answer() -> None:
    outputs = asyncio.run(CriticAgent(InMemoryBlackboardBus()).run_once(draft_event("")))

    assert outputs[-1].type == EventType.ANSWER_FINAL
    assert outputs[-1].payload["answer"]
    assert outputs[-1].payload["critic"]["approved"] is False


def test_critic_agent_preserves_context_and_rag_flags() -> None:
    outputs = asyncio.run(CriticAgent(InMemoryBlackboardBus()).run_once(draft_event("RESTful API uses resources, HTTP methods, and stateless requests. For example, GET reads resources.")))

    final = outputs[-1]
    assert final.payload["context_used"] is True
    assert final.payload["context_sources"] == ["resume"]
    assert final.payload["rag_used"] is True
    assert final.payload["rag_sources"] == ["knowledge.txt"]


def test_critic_agent_ignores_non_draft_event() -> None:
    event = BBEvent(
        session_id="session-1",
        source_agent="test",
        type=EventType.QUESTION_DETECTED,
        payload={"question": "What is API?"},
    )

    outputs = asyncio.run(CriticAgent(InMemoryBlackboardBus()).run_once(event))

    assert outputs == []
