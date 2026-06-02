from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_CHUNK_CHARS = 600


def load_knowledge_text(base_dir: Path | None = None) -> str:
    """Load knowledge.txt from the writable data dir. Missing files are empty."""
    from app.paths import data_dir
    root = base_dir or data_dir()
    path = root / "knowledge.txt"
    try:
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def extract_query_terms(question: str) -> List[str]:
    lowered = (question or "").lower()
    terms: list[str] = []
    terms.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_+#.-]{1,}", lowered))
    terms.extend(re.findall(r"[\u4e00-\u9fff]{2,}", lowered))

    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        expanded.extend(_expand_term(term))
    return _unique_terms(expanded)


def split_passages(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    if not text.strip():
        return []

    raw_parts = [
        part.strip()
        for part in re.split(r"\n\s*\n|\r\n\s*\r\n", text)
        if part.strip()
    ]
    if len(raw_parts) <= 1:
        raw_parts = [line.strip() for line in text.splitlines() if line.strip()]

    passages: list[str] = []
    for part in raw_parts:
        cleaned = "\n".join(line.strip() for line in part.splitlines() if line.strip())
        while len(cleaned) > max_chars:
            passages.append(_trim(cleaned[:max_chars], max_chars))
            cleaned = cleaned[max_chars:].strip()
        if cleaned:
            passages.append(_trim(cleaned, max_chars))

    return passages


def score_passage(passage: str, terms: List[str]) -> int:
    lowered = (passage or "").lower()
    score = 0
    for term in terms:
        normalized = term.lower().strip()
        if normalized and normalized in lowered:
            score += 1
    return score


def retrieve_local_knowledge(
    question: str,
    knowledge_text: str,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    terms = extract_query_terms(question)
    scored = []
    for passage in split_passages(knowledge_text):
        score = score_passage(passage, terms)
        if score > 0:
            scored.append((score, passage))

    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [
        {
            "source": "knowledge.txt",
            "text": _trim(passage),
            "score": score,
            "rank": index + 1,
        }
        for index, (score, passage) in enumerate(scored[:top_k])
    ]


def retrieve_session_history(
    question: str,
    events: List[Any],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    terms = extract_query_terms(question)
    current = re.sub(r"\s+", " ", question or "").strip().lower()
    candidates: list[tuple[int, str, str]] = []

    for event in events:
        event_type = _event_type_value(event)
        if event_type not in {
            "question_detected",
            "context_loaded",
            "rag_chunk",
            "answer_draft",
            "answer_final",
        }:
            continue

        text = _event_text(event)
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        if not normalized or normalized == current:
            continue

        score = score_passage(text, terms)
        if score > 0:
            candidates.append((score, event_type, text))

    candidates.sort(key=lambda item: (-item[0], len(item[2])))
    return [
        {
            "source": "session_replay",
            "event_type": event_type,
            "text": _trim(text),
            "score": score,
            "rank": index + 1,
        }
        for index, (score, event_type, text) in enumerate(candidates[:top_k])
    ]


def _event_type_value(event: Any) -> str:
    event_type = getattr(event, "type", "")
    return str(getattr(event_type, "value", event_type))


def _event_payload(event: Any) -> dict:
    payload = getattr(event, "payload", {})
    return payload if isinstance(payload, dict) else {}


def _event_text(event: Any) -> str:
    payload = _event_payload(event)
    parts: list[str] = []
    for key in (
        "question",
        "answer",
        "draft",
        "resume_summary",
        "jd_summary",
        "knowledge_summary",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

    for snippet in payload.get("matched_snippets", []) or []:
        if isinstance(snippet, dict):
            text = snippet.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

    for chunk in payload.get("chunks", []) or []:
        if isinstance(chunk, dict):
            text = chunk.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

    return "\n".join(parts)


def _expand_term(term: str) -> list[str]:
    mapping = {
        "api": ["rest", "restful", "http"],
        "restful": ["rest", "api", "http"],
        "react": ["frontend", "ui"],
        "fastapi": ["api", "backend"],
        "project": ["system", "implemented", "responsible"],
        "算法": ["复杂度", "数组", "链表", "二叉树"],
        "项目": ["系统", "负责", "实现", "开发"],
        "技术": ["python", "fastapi", "react", "electron"],
    }
    return mapping.get(term.lower(), [])


def _unique_terms(terms: list[str]) -> list[str]:
    seen = set()
    unique = []
    for term in terms:
        normalized = term.strip().lower()
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _trim(text: str, max_chars: int = MAX_CHUNK_CHARS) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "...[truncated]"
