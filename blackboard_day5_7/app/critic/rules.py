from __future__ import annotations

import re
from typing import Any, Dict, List


AI_TONE_PATTERNS = [
    "作为一个AI",
    "作为AI",
    "作为一个ai",
    "作为ai",
    "As an AI",
    "I'm an AI",
    "I cannot actually",
    "我不能真正",
]

FABRICATION_PATTERNS = [
    "我在某大厂",
    "提升了 300%",
    "提升300%",
    "带领 20 人团队",
    "带领20人团队",
    "千万级用户",
    "负责核心架构",
]

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_\-]{12,}",
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    r"\b1[3-9]\d{9}\b",
    r"\b\d{17}[\dXx]\b",
    r"(?i)\b(password|token|secret|api[_-]?key)\b\s*[:=]",
]


def review_answer(
    question: str,
    answer: str,
    question_type: str | None = None,
    selected_agent: str | None = None,
    context: dict | None = None,
    rag: dict | None = None,
) -> Dict[str, Any]:
    issues: list[str] = []
    suggestions: list[str] = []
    risk_flags: list[str] = []
    score = 100

    question_type_norm = (question_type or "").lower()
    answer = answer or ""

    if len(answer.strip()) < 20:
        issues.append("empty_or_too_short")
        suggestions.append("Provide a direct answer with definition, key points, and one example.")
        score -= 65

    if _contains_ai_tone(answer):
        issues.append("ai_tone")
        suggestions.append("Remove AI-assistant framing.")
        score -= 35

    if _contains_secret(answer):
        issues.append("possible_pii_or_secret")
        risk_flags.append("privacy")
        suggestions.append("Remove or redact possible personal data, credentials, tokens, or secrets.")
        score -= 60

    length_penalty = _length_penalty(answer, question_type_norm)
    if length_penalty:
        issues.append(length_penalty["issue"])
        suggestions.append(length_penalty["suggestion"])
        score -= int(length_penalty["penalty"])

    if question_type_norm in {"behavioral", "resume_followup"}:
        unsupported = _unsupported_resume_claims(answer, context or {})
        if unsupported:
            risk_flags.append("unsupported_resume_claim")
            suggestions.append(
                "Use resume-backed facts or phrase this as a suggested answer template."
            )
            score -= 15

    if question_type_norm in {"technical", "algorithm", "system_design"}:
        tech_issues = _technical_quality_issues(answer, question_type_norm)
        for issue, suggestion, penalty in tech_issues:
            issues.append(issue)
            suggestions.append(suggestion)
            score -= penalty

    score = max(0, min(100, score))
    approved = score >= 70 and not {"empty_or_too_short", "ai_tone", "possible_pii_or_secret"} & set(issues)
    final_answer = answer.strip() if approved else safe_final_answer(answer, question_type_norm, issues)

    return _critic_payload(
        approved=approved,
        score=score,
        issues=_unique(issues),
        suggestions=_unique(suggestions),
        risk_flags=_unique(risk_flags),
        final_answer=final_answer,
        selected_agent=selected_agent,
    )


def safe_final_answer(answer: str, question_type: str | None = None, issues: list[str] | None = None) -> str:
    issues = issues or []
    cleaned = _remove_ai_tone(answer or "").strip()

    if "empty_or_too_short" in issues or not cleaned:
        if (question_type or "").lower() in {"behavioral", "resume_followup"}:
            return (
                "可以按照 STAR 结构组织这个回答，但需要替换为你简历中的真实项目事实："
                "先说明背景和任务，再讲你采取的具体行动，最后用真实结果收尾。"
            )
        return "这个问题我建议从定义、关键点和例子三部分回答，并补充适用场景或限制。"

    if (question_type or "").lower() in {"behavioral", "resume_followup"} and (
        "unsupported_resume_claim" in issues
    ):
        return (
            cleaned
            + "\n\n注意：涉及项目经历的部分请只替换为你简历中真实存在的事实，"
            "没有证据的指标或经历不要直接陈述。"
        )

    return cleaned


def _critic_payload(
    approved: bool,
    score: int,
    issues: list[str],
    suggestions: list[str],
    risk_flags: list[str],
    final_answer: str,
    selected_agent: str | None,
) -> Dict[str, Any]:
    human_like_score = 0.65 if "ai_tone" in issues else 0.9
    privacy_score = 0.2 if "possible_pii_or_secret" in issues else 1.0
    resume_alignment_score = 0.55 if "unsupported_resume_claim" in risk_flags else 0.8

    notes = suggestions or ["Answer passed rule-based critic checks."]
    return {
        "approved": approved,
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "risk_flags": risk_flags,
        "final_answer": final_answer,
        "clarity_score": round(score / 100, 2),
        "correctness_score": round(score / 100, 2),
        "human_like_score": human_like_score,
        "resume_alignment_score": resume_alignment_score,
        "privacy_score": privacy_score,
        "jd_alignment_score": 0.8,
        "jd_alignment_notes": [],
        "final_score": score,
        "main_weakness": issues[0] if issues else "none",
        "specific_issues": issues,
        "rewrite_strategy": "Keep concise and evidence-backed." if approved else "Use the safe final answer.",
        "should_rewrite": not approved,
        "critic_notes": notes,
        "improved_answer_suggestion": "\n".join(f"- {item}" for item in notes),
        "human_like_rewrite": {},
        "followup_questions": {},
        "selected_agent_reviewed": selected_agent,
    }


def _contains_ai_tone(answer: str) -> bool:
    lowered = answer.lower()
    return any(pattern.lower() in lowered for pattern in AI_TONE_PATTERNS)


def _remove_ai_tone(answer: str) -> str:
    cleaned = answer
    for pattern in AI_TONE_PATTERNS:
        cleaned = re.sub(re.escape(pattern), "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _contains_secret(answer: str) -> bool:
    return any(re.search(pattern, answer or "") for pattern in SECRET_PATTERNS)


def _length_penalty(answer: str, question_type: str) -> dict[str, Any] | None:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", answer))
    english_words = len(re.findall(r"[A-Za-z][A-Za-z0-9_'-]*", answer))
    length = max(chinese_chars, english_words)

    if question_type in {"technical", "algorithm", "system_design"}:
        if 0 < length < 40:
            return {"issue": "answer_too_short", "suggestion": "Add key reasoning and a concrete example.", "penalty": 20}
        if length > 900:
            return {"issue": "answer_too_long", "suggestion": "Shorten the answer for interview delivery.", "penalty": 10}
    if question_type in {"behavioral", "resume_followup"}:
        if 0 < length < 60:
            return {"issue": "behavioral_answer_too_short", "suggestion": "Add STAR details backed by resume facts.", "penalty": 20}
        if length > 1000:
            return {"issue": "behavioral_answer_too_long", "suggestion": "Make the STAR answer more concise.", "penalty": 10}
    return None


def _unsupported_resume_claims(answer: str, context: dict) -> bool:
    matched_text = " ".join(
        str(snippet.get("text", ""))
        for snippet in context.get("matched_snippets", []) or []
        if isinstance(snippet, dict)
    )
    evidence = " ".join(
        [
            matched_text,
            str(context.get("resume_summary", "")),
            str(context.get("jd_summary", "")),
            str(context.get("knowledge_summary", "")),
        ]
    )
    evidence_lower = evidence.lower()
    for pattern in FABRICATION_PATTERNS:
        if pattern.lower() in answer.lower() and pattern.lower() not in evidence_lower:
            return True
    return False


def _technical_quality_issues(answer: str, question_type: str) -> list[tuple[str, str, int]]:
    lowered = answer.lower()
    issues: list[tuple[str, str, int]] = []
    if question_type == "algorithm" and not any(term in lowered for term in ["complexity", "time", "space", "复杂度"]):
        issues.append(("missing_complexity", "Add time and space complexity.", 12))
    if question_type == "system_design" and not any(term in lowered for term in ["trade-off", "tradeoff", "bottleneck", "扩展", "瓶颈", "权衡"]):
        issues.append(("missing_tradeoff_or_bottleneck", "Mention trade-offs or bottlenecks.", 12))
    if question_type == "technical" and not any(term in lowered for term in ["example", "例如", "比如", "步骤", "key"]):
        issues.append(("missing_example_or_steps", "Add a brief example or key steps.", 8))
    return issues


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
