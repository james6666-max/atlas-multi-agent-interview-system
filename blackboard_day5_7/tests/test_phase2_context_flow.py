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


def ask_payload(question: str, selected_agent: str, context: dict | None, rag: dict | None = None) -> dict:
    return {
        "question": question,
        "question_type": "Behavioral" if selected_agent == "Behavioral" else "Technical/Algorithm",
        "selected_agent": selected_agent,
        "answer": f"{selected_agent} answer",
        "critic": critic_payload(),
        "blackboard_version": 101,
        "context_used": bool(context),
        "context_sources": ["resume", "jd", "knowledge"] if context else [],
        "context": context or {},
        "rag_used": bool(rag and rag.get("has_rag")),
        "rag_sources": rag.get("sources", []) if rag else [],
        "rag": rag or {},
    }


def test_technical_flow_passes_context_to_tech_agent(monkeypatch) -> None:
    contexts = []

    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        contexts.append((agent_hint, context))
        return ask_payload(question, "Tech/Code", context, rag)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "What is RESTful API?"})

    assert response.status_code == 200
    assert contexts and contexts[0][0] == "tech"
    assert contexts[0][1]["has_resume"] is True
    assert contexts[0][1]["matched_snippets"]


def test_behavioral_flow_passes_constraints_to_behavioral_agent(monkeypatch) -> None:
    contexts = []

    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        contexts.append((agent_hint, context))
        return ask_payload(question, "Behavioral", context, rag)

    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "Tell me about a project you are proud of."})

    assert response.status_code == 200
    assert contexts and contexts[0][0] == "behavioral"
    constraints = contexts[0][1]["constraints"]
    assert any("Use only resume/JD/knowledge facts" in item for item in constraints)
    assert any("STAR" in item for item in constraints)


def test_chitchat_does_not_trigger_resume_or_answer_agents(monkeypatch) -> None:
    def fail_context(question: str):
        raise AssertionError("ResumeAgent should not run for ignored input")

    async def fail_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        raise AssertionError("Answer agent should not run for ignored input")

    monkeypatch.setattr("app.agents.resume_agent.build_candidate_context", fail_context)
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fail_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "hello, nice weather."})

    assert response.status_code == 200
    body = response.json()
    assert body["question_type"] == "ignored"
    assert body["selected_agent"] == "Perception"
    assert body["answer"] == ""


def test_resume_agent_error_does_not_prevent_answer(monkeypatch) -> None:
    contexts = []

    def broken_context(question: str):
        raise RuntimeError("context failed")

    async def fake_pipeline(
        question: str,
        language: str = "Unknown",
        source: str = "manual_input",
        agent_hint: str | None = None,
        question_type: str | None = None,
        context: dict | None = None,
        rag: dict | None = None,
    ) -> dict:
        contexts.append(context)
        return ask_payload(question, "Tech/Code", context, rag)

    monkeypatch.setattr("app.agents.resume_agent.build_candidate_context", broken_context)
    monkeypatch.setattr(phase1_pipeline, "run_phase1_answer_pipeline", fake_pipeline)
    client = TestClient(orchestrator_v0.app)

    response = client.post("/ask", json={"question": "What is RESTful API?"})

    assert response.status_code == 200
    assert response.json()["selected_agent"] == "Tech/Code"
    assert contexts == [{}]
