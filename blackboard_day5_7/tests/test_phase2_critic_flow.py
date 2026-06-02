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


def ask_payload(
    question: str,
    selected_agent: str,
    answer: str,
    context: dict | None,
    rag: dict | None,
) -> dict:
    return {
        "question": question,
        "question_type": "Behavioral" if selected_agent == "Behavioral" else "Technical/Algorithm",
        "selected_agent": selected_agent,
        "answer": answer,
        "critic": critic_payload(),
        "blackboard_version": 301,
        "context_used": bool(context),
        "context_sources": ["resume", "jd", "knowledge"] if context else [],
        "context": context or {},
        "rag_used": bool(rag and rag.get("has_rag")),
        "rag_sources": rag.get("sources", []) if rag else [],
        "rag": rag or {},
    }


def test_technical_flow_final_answer_comes_from_critic(monkeypatch) -> None:
    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        answer = (
            "RESTful API models resources and uses HTTP methods. "
            "Key steps are stateless requests, clear URLs, and status codes. "
            "For example, GET /users/1 reads one user."
        )
        return ask_payload(question, "Tech/Code", answer, context, rag)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    outputs = orchestrator_v0._run_async_blocking(
        orchestrator_v0.phase2_orchestrator.dispatch(
            BBEvent(
                session_id="critic-tech",
                source_agent="test",
                type=EventType.MANUAL_INPUT,
                payload={"question": "What is RESTful API?"},
            )
        )
    )

    final = next(event for event in reversed(outputs) if event.type == EventType.ANSWER_FINAL)
    assert final.source_agent == "critic_agent"
    assert final.payload["selected_agent"] == "Tech/Code"
    assert final.payload["critic"]["approved"] is True


def test_behavioral_flow_final_answer_comes_from_critic(monkeypatch) -> None:
    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        answer = (
            "I would use the STAR structure. Situation: in my Atlas project, I worked on a local AI interview assistant. "
            "Task: I needed to connect manual, OCR, and audio inputs. Action: I built FastAPI endpoints and wired agents through the blackboard. "
            "Result: the MVP became easier to demo and debug."
        )
        return ask_payload(question, "Behavioral", answer, context, rag)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "Tell me about a project you are proud of."})

    assert response.status_code == 200
    body = response.json()
    assert body["selected_agent"] == "Behavioral"
    assert body["critic"]["approved"] is True
    assert body["context_used"] is True


def test_chitchat_does_not_trigger_critic(monkeypatch) -> None:
    async def fail_critic(self, event):
        raise AssertionError("CriticAgent should not run for ignored input")

    monkeypatch.setattr("app.agents.critic_agent.CriticAgent.handle", fail_critic)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "hello, nice weather."})

    assert response.status_code == 200
    body = response.json()
    assert body["question_type"] == "ignored"
    assert body["selected_agent"] == "Perception"
    assert body["answer"] == ""


def test_detected_but_unhandled_does_not_trigger_critic_or_500(monkeypatch) -> None:
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
    assert body["answer"] == ""


def test_critic_reject_still_returns_safe_final_answer(monkeypatch) -> None:
    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        return ask_payload(
            question,
            "Tech/Code",
            "As an AI, I cannot actually answer from personal experience.",
            context,
            rag,
        )

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "What is RESTful API?"})

    assert response.status_code == 200
    body = response.json()
    assert body["critic"]["approved"] is False
    assert body["answer"]
    assert "As an AI" not in body["answer"]
