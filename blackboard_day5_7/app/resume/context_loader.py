from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_SUMMARY_CHARS = 1200
MAX_SNIPPET_CHARS = 500

SPECIAL_KEYWORDS = {
    "项目": ["项目", "负责", "实现", "开发", "系统"],
    "project": ["project", "responsible", "implemented", "system"],
    "实习": ["实习", "工作", "公司"],
    "internship": ["internship", "work", "company"],
    "困难": ["困难", "挑战", "解决", "问题"],
    "difficult": ["difficult", "challenge", "solved", "problem"],
    "团队": ["团队", "合作", "沟通", "冲突"],
    "team": ["team", "collaboration", "communication", "conflict"],
    "技术": ["python", "fastapi", "react", "electron", "ollama", "whisper", "ocr"],
    "technical": ["python", "fastapi", "react", "electron", "ollama", "whisper", "ocr"],
}

CONSTRAINTS = [
    "Use only resume/JD/knowledge facts for experience-specific claims.",
    "If evidence is missing, suggest a safe framing instead of inventing details.",
    "For behavioral questions, prefer STAR structure.",
]


def load_text_file(path: Path) -> str:
    try:
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_candidate_context(base_dir: Path | None = None) -> Dict[str, str]:
    from app.paths import data_dir
    root = base_dir or data_dir()
    return {
        "resume": load_text_file(root / "resume.txt"),
        "jd": load_text_file(root / "jd.txt"),
        "knowledge": load_text_file(root / "knowledge.txt"),
    }


def build_candidate_context(question: str, base_dir: Path | None = None) -> Dict[str, Any]:
    files = load_candidate_context(base_dir=base_dir)
    keywords = extract_keywords(question)
    matched_snippets: List[dict] = []

    for source, text in files.items():
        matched_snippets.extend(find_relevant_snippets(text, keywords, source))

    return {
        "resume_raw": files["resume"],
        "jd_raw": files["jd"],
        "knowledge_raw": files["knowledge"],
        "resume_summary": summarize(files["resume"]),
        "jd_summary": summarize(files["jd"]),
        "knowledge_summary": summarize(files["knowledge"]),
        "matched_snippets": matched_snippets,
        "constraints": list(CONSTRAINTS),
    }


def summarize(text: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "...[truncated]"


def extract_keywords(question: str) -> list[str]:
    lowered = (question or "").lower()
    keywords: list[str] = []

    keywords.extend(re.findall(r"[a-zA-Z][a-zA-Z0-9_+#.-]{1,}", lowered))
    keywords.extend(re.findall(r"[\u4e00-\u9fff]{2,}", lowered))

    for trigger, additions in SPECIAL_KEYWORDS.items():
        if trigger in lowered:
            keywords.extend(additions)

    return _unique_keywords(keywords)


def find_relevant_snippets(
    text: str,
    keywords: list[str],
    source: str,
    max_snippets: int = 3,
) -> list[dict]:
    if not text.strip():
        return []

    chunks = [
        chunk.strip()
        for chunk in re.split(r"\n\s*\n|\n", text)
        if chunk.strip()
    ]
    if not chunks:
        chunks = [text.strip()]

    snippets: list[dict] = []
    for chunk in chunks:
        lowered = chunk.lower()
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        if matched:
            snippets.append(
                {
                    "source": source,
                    "text": _trim_snippet(chunk),
                    "match": "keyword",
                    "keywords": matched[:5],
                }
            )
        if len(snippets) >= max_snippets:
            return snippets

    if not snippets:
        snippets.append(
            {
                "source": source,
                "text": _trim_snippet(chunks[0]),
                "match": "fallback",
                "keywords": [],
            }
        )

    return snippets


def _trim_snippet(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= MAX_SNIPPET_CHARS:
        return cleaned
    return cleaned[:MAX_SNIPPET_CHARS].rstrip() + "...[truncated]"


def _unique_keywords(keywords: list[str]) -> list[str]:
    seen = set()
    unique = []
    for keyword in keywords:
        normalized = keyword.strip().lower()
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique
