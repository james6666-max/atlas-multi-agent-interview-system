from fastapi.testclient import TestClient

import orchestrator_v0
from app.adapters import phase1_pipeline


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


def ask_payload(question: str = "mock question", answer: str = "mock answer") -> dict:
    return {
        "question": question,
        "question_type": "Behavioral",
        "selected_agent": "Behavioral",
        "answer": answer,
        "critic": critic_payload(),
        "blackboard_version": 456,
    }


def test_ask_uses_phase2_orchestrator_with_mocked_pipeline(monkeypatch) -> None:
    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        return ask_payload(question=question, answer="phase2 answer")

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "请用 STAR 法介绍一次项目经历。"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["question_type"] == "Behavioral"
    assert body["critic"]["approved"] is False
    assert body["critic"]["main_weakness"] in {"empty_or_too_short", "behavioral_answer_too_short"}


def test_ask_falls_back_to_phase1_when_phase2_fails(monkeypatch) -> None:
    def broken_phase2(req):
        raise RuntimeError("phase2 failed")

    def fake_phase1(req):
        return orchestrator_v0.AskResponse(**ask_payload(req.question, "phase1 fallback"))

    monkeypatch.setattr(orchestrator_v0, "_ask_phase2_impl", broken_phase2)
    monkeypatch.setattr(orchestrator_v0, "_ask_phase1_impl", fake_phase1)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "fallback question"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "phase1 fallback"
    assert body["question"] == "fallback question"
