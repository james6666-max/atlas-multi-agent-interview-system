import json
import os

os.environ["USE_OLLAMA"] = "false"  # stub mode: no network / no model needed

from fastapi.testclient import TestClient  # noqa: E402

import orchestrator_v0  # noqa: E402

client = TestClient(orchestrator_v0.app)


def _sse_events(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:"):].strip()))
    return events


def test_ask_stream_technical_emits_meta_delta_final_done():
    resp = client.post("/ask_stream", json={"question": "What is a hash map and its time complexity?"})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    types = [e["type"] for e in events]
    assert "meta" in types and "delta" in types and "final" in types
    assert types[-1] == "done"

    meta = next(e for e in events if e["type"] == "meta")
    assert meta["selected_agent"] == "Tech/Code"

    final = next(e for e in events if e["type"] == "final")
    assert final["answer"]
    assert "critic" in final and "approved" in final["critic"]

    # streamed requests also produce a real trace
    sid = final["session_id"]
    assert sid
    trace = client.get(f"/trace/{sid}").json()
    trace_types = {step["type"] for step in trace["steps"]}
    assert {"manual_input", "question_detected", "answer_final"} <= trace_types


def test_ask_stream_persists_history_for_report():
    question = "Explain how a bloom filter works and when you would use one."
    resp = client.post("/ask_stream", json={"question": question})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    assert any(e["type"] == "final" for e in events)

    # The streamed turn must land in the blackboard history so the
    # post-interview report reflects what was actually asked in the live UI.
    history = orchestrator_v0.store.read().get("history", [])
    assert any(item.get("question") == question for item in history)

    report = client.get("/report/session").json()
    assert any(r.get("question") == question for r in report["question_reviews"])


def test_ask_stream_ignored_has_no_final():
    resp = client.post("/ask_stream", json={"question": "hello, nice weather."})
    assert resp.status_code == 200
    events = _sse_events(resp.text)
    types = [e["type"] for e in events]
    assert "ignored" in types
    assert "final" not in types
    assert types[-1] == "done"


def test_ask_returns_session_id_and_trace_is_real():
    resp = client.post("/ask", json={"question": "What is a hash map and its time complexity?"})
    assert resp.status_code == 200
    body = resp.json()
    sid = body["session_id"]
    assert sid

    trace = client.get(f"/trace/{sid}")
    assert trace.status_code == 200
    tbody = trace.json()
    event_types = {step["type"] for step in tbody["steps"]}
    # Real event chain recorded on the bus
    assert "manual_input" in event_types
    assert "question_detected" in event_types
    assert "answer_final" in event_types
    assert tbody["count"] >= 4


def test_config_llm_get_never_leaks_key():
    resp = client.get("/config/llm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cloud_api_key"] == ""
    assert "cloud_api_key_set" in body
    assert "mode" in body
