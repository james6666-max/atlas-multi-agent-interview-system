from __future__ import annotations

import json
import os
import shutil
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = Path(__file__).resolve().parent
QUESTIONS_PATH = EVAL_ROOT / "phase2_questions.json"
RESULTS_DIR = EVAL_ROOT / "results"
BLACKBOARD_PATH = BACKEND_ROOT / "blackboard_instance.json"


def main() -> int:
    os.environ["USE_OLLAMA"] = "false"
    sys.path.insert(0, str(BACKEND_ROOT))

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    backup_path = _backup_blackboard()
    try:
        from fastapi.testclient import TestClient
        import orchestrator_v0

        client = TestClient(orchestrator_v0.app)
        cases = [_run_case(client, item) for item in questions]
        summary = _summarize(cases)
        _write_results(summary)
        _print_summary(summary)
        return 0 if summary["failed_cases_count"] == 0 else 1
    finally:
        _restore_blackboard(backup_path)


def _run_case(client, item: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.post("/ask", json={"question": item["question"]})
    latency_ms = int((time.perf_counter() - started) * 1000)
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}

    answer = str(body.get("answer", ""))
    expected_type = item["expected_question_type"]
    actual_type = _normalize_question_type(str(body.get("question_type", "")), expected_type)
    selected_agent = str(body.get("selected_agent", ""))
    should_answer_actual = bool(answer.strip())

    checks = {
        "question_type": actual_type == expected_type,
        "selected_agent": _selected_agent_matches(selected_agent, item["expected_selected_agent"]),
        "should_answer": should_answer_actual == bool(item["should_answer"]),
        "must_not_include": not _contains_any(answer, item.get("must_not_include_any", [])),
        "must_include": True if not item["should_answer"] else _contains_any(answer, item.get("must_include_any", [])),
    }

    score = sum(1 for passed in checks.values() if passed)
    return {
        "id": item["id"],
        "question": item["question"],
        "expected_question_type": expected_type,
        "actual_question_type": actual_type,
        "expected_selected_agent": item["expected_selected_agent"],
        "actual_selected_agent": selected_agent,
        "should_answer": item["should_answer"],
        "answer": answer,
        "critic": body.get("critic"),
        "context_used": body.get("context_used"),
        "rag_used": body.get("rag_used"),
        "status_code": response.status_code,
        "latency_ms": latency_ms,
        "checks": checks,
        "score": score,
        "max_score": 5,
        "passed": score == 5 and response.status_code == 200,
        "notes": item.get("notes", ""),
    }


def _summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [case["latency_ms"] for case in cases]
    total_score = sum(case["score"] for case in cases)
    max_score = sum(case["max_score"] for case in cases)
    by_category: dict[str, dict[str, Any]] = {}
    for case in cases:
        category = case["id"].split("_", 1)[0]
        bucket = by_category.setdefault(category, {"cases": 0, "score": 0, "max_score": 0, "passed": 0})
        bucket["cases"] += 1
        bucket["score"] += case["score"]
        bucket["max_score"] += case["max_score"]
        bucket["passed"] += 1 if case["passed"] else 0

    for bucket in by_category.values():
        bucket["accuracy"] = round(bucket["score"] / bucket["max_score"], 4) if bucket["max_score"] else 0.0

    failed_cases = [case for case in cases if not case["passed"]]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_cases": len(cases),
        "total_score": total_score,
        "max_score": max_score,
        "accuracy": round(total_score / max_score, 4) if max_score else 0.0,
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0,
        "p95_latency_ms": _p95(latencies),
        "by_category": by_category,
        "failed_cases_count": len(failed_cases),
        "failed_cases": failed_cases,
        "cases": cases,
    }


def _write_results(summary: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp_path = RESULTS_DIR / f"phase2_eval_{timestamp}.json"
    latest_path = RESULTS_DIR / "phase2_eval_latest.json"
    data = json.dumps(summary, ensure_ascii=False, indent=2)
    timestamp_path.write_text(data, encoding="utf-8")
    latest_path.write_text(data, encoding="utf-8")


def _print_summary(summary: dict[str, Any]) -> None:
    print(f"total_score: {summary['total_score']}")
    print(f"max_score: {summary['max_score']}")
    print(f"accuracy: {summary['accuracy']}")
    print(f"avg_latency_ms: {summary['avg_latency_ms']}")
    print(f"p95_latency_ms: {summary['p95_latency_ms']}")
    print(f"failed_cases_count: {summary['failed_cases_count']}")
    print("by_category:")
    for category, bucket in summary["by_category"].items():
        print(f"  {category}: {bucket['score']}/{bucket['max_score']} accuracy={bucket['accuracy']} passed={bucket['passed']}/{bucket['cases']}")


def _normalize_question_type(actual: str, expected: str) -> str:
    lowered = actual.strip().lower()
    if expected in {"technical", "algorithm"} and lowered in {"technical/algorithm", "technical", "algorithm"}:
        return expected
    if expected == "system_design" and lowered in {"system design", "system_design"}:
        return expected
    if expected in {"behavioral", "resume_followup"} and lowered in {"behavioral", "resume_followup"}:
        return expected
    return lowered


def _selected_agent_matches(actual: str, expected: str) -> bool:
    if expected == "Tech/Code":
        return "tech" in actual.lower() or "code" in actual.lower()
    return actual == expected


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * 0.95))
    return ordered[index]


def _backup_blackboard() -> Path | None:
    if not BLACKBOARD_PATH.exists():
        return None
    backup_path = BLACKBOARD_PATH.with_suffix(".json.eval.bak")
    shutil.copy2(BLACKBOARD_PATH, backup_path)
    return backup_path


def _restore_blackboard(backup_path: Path | None) -> None:
    if backup_path and backup_path.exists():
        shutil.copy2(backup_path, BLACKBOARD_PATH)
        backup_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
