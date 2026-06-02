from fastapi.testclient import TestClient

import orchestrator_v0
from app.adapters import phase1_pipeline
from app.blackboard.events import BBEvent, EventType


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


def ask_payload(question: str, agent_hint: str | None, question_type: str | None) -> dict:
    selected_agent = "Behavioral" if agent_hint == "behavioral" else "Tech/Code"
    return {
        "question": question,
        "question_type": question_type or "unknown",
        "selected_agent": selected_agent,
        "answer": f"{selected_agent} answered",
        "critic": critic_payload(),
        "blackboard_version": 99,
        "context_used": True,
        "context_sources": ["resume", "jd", "knowledge"],
        "context": {"constraints": ["For behavioral questions, prefer STAR structure."]},
        "rag_used": True,
        "rag_sources": ["knowledge.txt"],
        "rag": {"has_rag": True, "sources": ["knowledge.txt"]},
    }


def test_technical_question_routes_to_tech_agent(monkeypatch) -> None:
    calls = []

    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        calls.append((agent_hint, question_type))
        return ask_payload(question, agent_hint, question_type)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "What is RESTful API?"})

    assert response.status_code == 200
    body = response.json()
    assert calls == [("tech", "technical")]
    assert "Tech" in body["selected_agent"] or "Code" in body["selected_agent"]


def test_behavioral_question_routes_to_behavioral_agent(monkeypatch) -> None:
    calls = []

    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        calls.append((agent_hint, question_type))
        return ask_payload(question, agent_hint, question_type)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post(
        "/ask",
        json={"question": "Tell me about a time you solved a difficult technical problem."},
    )

    assert response.status_code == 200
    body = response.json()
    assert calls == [("behavioral", "behavioral")]
    assert "Behavioral" in body["selected_agent"]


def test_chitchat_is_ignored_without_answer_agent_or_phase1_fallback(monkeypatch) -> None:
    async def fail_if_called(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        raise AssertionError("Answer pipeline should not be called for chitchat")

    def fail_fallback(req):
        raise AssertionError("Ignored input must not fall back to Phase1")

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fail_if_called)
    monkeypatch.setattr(orchestrator_v0, "_ask_phase1_impl", fail_fallback)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "hello, nice weather."})

    assert response.status_code == 200
    body = response.json()
    assert body["question_type"] == "ignored"
    assert body["selected_agent"] == "Perception"
    assert body["answer"] == ""


def test_detected_but_unhandled_does_not_fallback_or_500(monkeypatch) -> None:
    async def unhandled_dispatch(event):
        return [
            BBEvent(
                session_id=event.session_id,
                source_agent="test",
                type=EventType.QUESTION_DETECTED,
                payload={"question": event.payload["question"], "question_type": "unknown"},
                parent_event_id=event.event_id,
            )
        ]

    def fail_fallback(req):
        raise AssertionError("Unhandled detected question must not fall back to Phase1")

    monkeypatch.setattr(orchestrator_v0.phase2_orchestrator, "dispatch", unhandled_dispatch)
    monkeypatch.setattr(orchestrator_v0, "_ask_phase1_impl", fail_fallback)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "What about this?"})

    assert response.status_code == 200
    body = response.json()
    assert body["question_type"] == "unknown"
    assert body["selected_agent"] == "Perception"
    assert body["answer"] == ""
