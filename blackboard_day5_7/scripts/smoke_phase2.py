from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
BLACKBOARD_PATH = BACKEND_ROOT / "blackboard_instance.json"


def main() -> int:
    os.environ["USE_OLLAMA"] = "false"
    sys.path.insert(0, str(BACKEND_ROOT))

    backup_path = _backup_blackboard()
    try:
        from fastapi.testclient import TestClient
        import orchestrator_v0

        client = TestClient(orchestrator_v0.app)
        checks = [
            ("config/status", lambda: _check_status(client)),
            ("config/llm", lambda: _check_llm_config(client)),
            ("ask technical", lambda: _check_technical(client)),
            ("ask behavioral", lambda: _check_behavioral(client)),
            ("ask ignored", lambda: _check_ignored(client)),
            ("ask_stream", lambda: _check_stream(client)),
            ("trace", lambda: _check_trace(client)),
            ("blackboard", lambda: _check_blackboard(client)),
            ("practice loop", lambda: _check_practice(client)),
        ]

        failures: list[str] = []
        for name, check in checks:
            try:
                check()
                print(f"[PASS] {name}")
            except AssertionError as exc:
                failures.append(f"{name}: {exc}")
                print(f"[FAIL] {name}: {exc}")

        if failures:
            print("Phase2 smoke failed.")
            return 1

        print("Phase2 smoke passed.")
        return 0
    finally:
        _restore_blackboard(backup_path)


def _check_practice(client) -> None:
    start = client.post("/practice/start", json={"num_questions": 3, "session_id": "smoke"})
    assert start.status_code == 200, start.text
    state = start.json()
    assert state["active"] is True
    assert state["total_planned"] == 3
    assert state["current_question"], "expected a first question"

    answer = client.post("/practice/answer", json={"answer": "smoke test answer", "session_id": "smoke"})
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert "feedback" in result and result["feedback"], "expected critic feedback"
    assert isinstance(result.get("score"), int)
    assert "state" in result

    report = client.get("/practice/report", params={"session_id": "smoke"})
    assert report.status_code == 200, report.text
    rep = report.json()
    assert rep["session_id"] == "smoke"
    assert len(rep["question_reviews"]) >= 1


def _check_status(client) -> None:
    response = client.get("/config/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "use_ollama" in body


def _check_technical(client) -> None:
    body = _ask(client, "What is RESTful API?")
    assert "Tech" in body["selected_agent"] or "Code" in body["selected_agent"]
    assert body["answer"]
    assert "critic" in body
    assert "context_used" in body
    assert "rag_used" in body


def _check_behavioral(client) -> None:
    body = _ask(client, "Tell me about a project you are most proud of.")
    assert "Behavioral" in body["selected_agent"]
    assert body["answer"]
    assert "critic" in body
    assert "context_used" in body
    assert "rag_used" in body


def _check_ignored(client) -> None:
    body = _ask(client, "hello, nice weather.")
    assert body["question_type"] == "ignored"
    assert body["selected_agent"] == "Perception"
    assert body["answer"] == ""
    assert body["context_used"] is False
    assert body["rag_used"] is False


def _check_llm_config(client) -> None:
    response = client.get("/config/llm")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("cloud_api_key") == "", "api key must never be returned"
    assert "cloud_api_key_set" in body
    assert body.get("mode") in {"hybrid", "local", "cloud"}


def _check_stream(client) -> None:
    response = client.post("/ask_stream", json={"question": "What is a hash map and its time complexity?"})
    assert response.status_code == 200, response.text
    events = []
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:"):].strip()))
    types = [event["type"] for event in events]
    assert "delta" in types, types
    assert "final" in types, types
    assert types[-1] == "done", types
    final = next(event for event in events if event["type"] == "final")
    assert final["answer"], "stream produced empty answer"
    assert "approved" in final["critic"]


def _check_trace(client) -> None:
    body = _ask(client, "What is RESTful API?")
    session_id = body.get("session_id")
    assert session_id, "ask response must include session_id"
    response = client.get(f"/trace/{session_id}")
    assert response.status_code == 200, response.text
    trace = response.json()
    types = {step["type"] for step in trace["steps"]}
    assert "manual_input" in types, types
    assert "answer_final" in types, types


def _check_blackboard(client) -> None:
    response = client.get("/blackboard")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict)


def _ask(client, question: str) -> dict:
    response = client.post("/ask", json={"question": question})
    assert response.status_code == 200, response.text
    return response.json()


def _backup_blackboard() -> Path | None:
    if not BLACKBOARD_PATH.exists():
        return None
    backup_path = BLACKBOARD_PATH.with_suffix(".json.smoke.bak")
    shutil.copy2(BLACKBOARD_PATH, backup_path)
    return backup_path


def _restore_blackboard(backup_path: Path | None) -> None:
    if backup_path and backup_path.exists():
        shutil.copy2(backup_path, BLACKBOARD_PATH)
        backup_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
