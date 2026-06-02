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


def ask_payload(question: str, answer: str = "mock answer") -> dict:
    return {
        "question": question,
        "question_type": "technical",
        "selected_agent": "Tech/Code",
        "answer": answer,
        "critic": critic_payload(),
        "blackboard_version": 789,
    }


def test_ask_complete_question_flows_through_perception_to_main_agent(monkeypatch) -> None:
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
        calls.append(question)
        return ask_payload(question, "phase2 perception answer")

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "解释一下数据库索引为什么能加速查询。"})

    assert response.status_code == 200
    body = response.json()
    assert calls == ["解释一下数据库索引为什么能加速查询。"]
    assert body["answer"] == "phase2 perception answer"


def test_ask_chitchat_is_ignored_without_main_agent_or_phase1_fallback(monkeypatch) -> None:
    async def fail_if_called(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        raise AssertionError("MainAgent pipeline should not be called for chitchat")

    def fail_fallback(req):
        raise AssertionError("Phase1 fallback should not be called for ignored input")

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fail_if_called)
    monkeypatch.setattr(orchestrator_v0, "_ask_phase1_impl", fail_fallback)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "你好，今天天气不错。"})

    assert response.status_code == 200
    body = response.json()
    assert body["question_type"] == "ignored"
    assert body["selected_agent"] == "Perception"
    assert body["answer"] == ""


def test_phase2_exception_still_falls_back_to_phase1(monkeypatch) -> None:
    def broken_phase2(req):
        raise RuntimeError("phase2 crashed")

    def fake_phase1(req):
        return orchestrator_v0.AskResponse(**ask_payload(req.question, "phase1 fallback"))

    monkeypatch.setattr(orchestrator_v0, "_ask_phase2_impl", broken_phase2)
    monkeypatch.setattr(orchestrator_v0, "_ask_phase1_impl", fake_phase1)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "解释一下数据库索引。"})

    assert response.status_code == 200
    assert response.json()["answer"] == "phase1 fallback"
