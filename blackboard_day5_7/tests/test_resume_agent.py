import asyncio

from app.agents.resume_agent import ResumeAgent
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType
from app.resume.context_loader import build_candidate_context, load_candidate_context


def detected_event(question: str, question_type: str = "behavioral") -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=EventType.QUESTION_DETECTED,
        payload={"question": question, "question_type": question_type},
    )


def write_context_files(tmp_path) -> None:
    (tmp_path / "resume.txt").write_text(
        "Atlas project: built FastAPI backend, Electron React frontend, Ollama, Whisper OCR, and Blackboard state.\n"
        "Solved a difficult latency issue by profiling OCR and async API calls.",
        encoding="utf-8",
    )
    (tmp_path / "jd.txt").write_text(
        "Role requires Python, FastAPI, React, system design, teamwork, and communication.",
        encoding="utf-8",
    )
    (tmp_path / "knowledge.txt").write_text(
        "RESTful API uses resources, HTTP methods, stateless design, and clear status codes.",
        encoding="utf-8",
    )


def test_load_candidate_context_reads_existing_files(tmp_path) -> None:
    write_context_files(tmp_path)

    context = load_candidate_context(base_dir=tmp_path)

    assert "Atlas project" in context["resume"]
    assert "FastAPI" in context["jd"]
    assert "RESTful API" in context["knowledge"]


def test_load_candidate_context_missing_files_do_not_crash(tmp_path) -> None:
    context = load_candidate_context(base_dir=tmp_path)

    assert context == {"resume": "", "jd": "", "knowledge": ""}


def test_build_candidate_context_includes_source_snippets(tmp_path) -> None:
    write_context_files(tmp_path)

    context = build_candidate_context("What is RESTful API?", base_dir=tmp_path)

    assert context["matched_snippets"]
    assert all("source" in snippet for snippet in context["matched_snippets"])


def test_behavioral_question_matches_project_experience(tmp_path) -> None:
    write_context_files(tmp_path)

    context = build_candidate_context("Tell me about a project you are proud of.", base_dir=tmp_path)

    assert any(snippet["source"] == "resume" for snippet in context["matched_snippets"])
    assert any("project" in keyword for snippet in context["matched_snippets"] for keyword in snippet["keywords"])


def test_technical_question_matches_technical_snippet(tmp_path) -> None:
    write_context_files(tmp_path)

    context = build_candidate_context("What is RESTful API?", base_dir=tmp_path)

    assert any(snippet["source"] == "knowledge" for snippet in context["matched_snippets"])


def test_resume_agent_emits_context_loaded(monkeypatch, tmp_path) -> None:
    write_context_files(tmp_path)

    def fake_build_candidate_context(question: str):
        return build_candidate_context(question, base_dir=tmp_path)

    monkeypatch.setattr("app.agents.resume_agent.build_candidate_context", fake_build_candidate_context)
    bus = InMemoryBlackboardBus()
    agent = ResumeAgent(bus)

    outputs = asyncio.run(agent.run_once(detected_event("Tell me about a project.")))

    assert len(outputs) == 1
    assert outputs[0].type == EventType.CONTEXT_LOADED
    assert outputs[0].payload["has_resume"] is True
    assert outputs[0].payload["has_jd"] is True
    assert outputs[0].payload["has_knowledge"] is True
    assert outputs[0].payload["constraints"]


def test_resume_agent_missing_files_emit_empty_context(monkeypatch, tmp_path) -> None:
    def fake_build_candidate_context(question: str):
        return build_candidate_context(question, base_dir=tmp_path)

    monkeypatch.setattr("app.agents.resume_agent.build_candidate_context", fake_build_candidate_context)
    bus = InMemoryBlackboardBus()
    agent = ResumeAgent(bus)

    outputs = asyncio.run(agent.run_once(detected_event("Tell me about a project.")))

    assert outputs[0].type == EventType.CONTEXT_LOADED
    assert outputs[0].payload["has_resume"] is False
    assert outputs[0].payload["has_jd"] is False
    assert outputs[0].payload["has_knowledge"] is False
