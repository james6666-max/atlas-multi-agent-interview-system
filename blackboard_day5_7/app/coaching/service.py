from __future__ import annotations

"""Coaching / practice service.

Drives a turn-based mock interview:
  start -> question -> answer -> (score + adaptive follow-up) -> next question -> ... -> report

Offline-first: scoring uses the same rule-based critic engine as the live
interview path (app.critic.rules.review_answer), and questions come from the
deterministic bank unless an optional LLM generator is injected. No dependency
on orchestrator_v0, so it is fully unit-testable without a server or model.
"""

from typing import Any, Callable, Dict, List, Optional

from app.coaching import question_bank
from app.coaching.models import PracticeQuestion, PracticeState, PracticeTurn
from app.critic.rules import review_answer
from app.resume.context_loader import build_candidate_context

FOLLOWUP_SCORE_THRESHOLD = 75
MAX_FOLLOWUPS = 2
FOLLOWUP_TYPES = {"behavioral", "resume_followup"}

# Map practice question types to the answering agent label, for consistency
# with the live interview path.
_AGENT_BY_TYPE = {
    "technical": "Tech/Code",
    "algorithm": "Tech/Code",
    "system_design": "Tech/Code",
    "behavioral": "Behavioral",
    "resume_followup": "Behavioral",
}


class _Session:
    def __init__(self, session_id: str, plan: List[Dict], config: Dict[str, Any], language: str = "zh"):
        self.session_id = session_id
        self.queue: List[PracticeQuestion] = [PracticeQuestion(**item) for item in plan]
        self.total_planned = len(self.queue)
        self.cursor = 0
        self.turns: List[PracticeTurn] = []
        self.followups_used = 0
        self.asked_followups: set[str] = set()
        self.completed = False
        self.config = config
        self.language = language

    @property
    def current(self) -> Optional[PracticeQuestion]:
        if self.completed or self.cursor >= len(self.queue):
            return None
        return self.queue[self.cursor]


class CoachingService:
    def __init__(
        self,
        *,
        scorer: Callable[..., Dict[str, Any]] = review_answer,
        context_builder: Callable[[str], Dict[str, Any]] = build_candidate_context,
        llm_generate: Optional[Callable[[str], str]] = None,
        resume_provider: Optional[Callable[[], Dict[str, str]]] = None,
    ):
        self._scorer = scorer
        self._context_builder = context_builder
        self._llm_generate = llm_generate
        self._resume_provider = resume_provider
        self._sessions: Dict[str, _Session] = {}

    def _profile_hint(self, role: str = "", focus: str = "") -> str:
        parts = []
        try:
            from app.profile_store import profile_hint
            base = profile_hint()
            if base:
                parts.append(base)
        except Exception:
            pass
        if role:
            parts.append(f"目标职位: {role}")
        if focus:
            parts.append(f"重点方向: {focus}")
        # de-dup while preserving order
        seen, out = set(), []
        for p in parts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return " | ".join(out)

    def _load_sources(self) -> Dict[str, str]:
        if self._resume_provider is not None:
            data = self._resume_provider() or {}
            return {
                "resume": str(data.get("resume", "")),
                "jd": str(data.get("jd", "")),
                "knowledge": str(data.get("knowledge", "")),
            }
        # Derive from the context builder (reads resume.txt / jd.txt / knowledge.txt)
        ctx = self._context_builder("")
        return {
            "resume": str(ctx.get("resume_raw", "")),
            "jd": str(ctx.get("jd_raw", "")),
            "knowledge": str(ctx.get("knowledge_raw", "")),
        }

    def start(
        self,
        session_id: str,
        *,
        role: str = "",
        focus: str = "",
        num_questions: int = 5,
        language: str = "zh",
    ) -> PracticeState:
        sources = self._load_sources()
        hint = self._profile_hint(role=role, focus=focus)
        plan = question_bank.build_plan_with_llm(
            sources["resume"], sources["jd"], sources["knowledge"], num_questions,
            self._llm_generate, language, profile_hint=hint,
        )
        config = {
            "role": role,
            "focus": focus,
            "profile_hint": hint,
            "num_questions": len(plan),
            "language": language,
            "has_resume": bool(sources["resume"].strip()),
            "has_jd": bool(sources["jd"].strip()),
            "question_source": "llm+bank" if self._llm_generate else "bank",
        }
        self._sessions[session_id] = _Session(session_id, plan, config, language)
        return self.state(session_id)

    def submit_answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None or session.completed:
            raise ValueError("No active practice session. Call /practice/start first.")

        question = session.current
        if question is None:
            session.completed = True
            return {"completed": True, "feedback": None, "next_question": None, "state": self.state(session_id)}

        context = self._context_builder(question.question)
        critic = self._scorer(
            question=question.question,
            answer=answer or "",
            question_type=question.type,
            selected_agent=_AGENT_BY_TYPE.get(question.type, "Behavioral"),
            context=context,
            rag={},
        )
        score = int(critic.get("score", critic.get("final_score", 0)) or 0)
        session.turns.append(
            PracticeTurn(question=question, answer=answer or "", score=score, critic=critic)
        )

        # Adaptive follow-up: probe weak or experience-based answers, within budget.
        self._maybe_insert_followup(session, question, score)

        session.cursor += 1
        if session.cursor >= len(session.queue):
            session.completed = True

        return {
            "completed": session.completed,
            "feedback": critic,
            "score": score,
            "next_question": (None if session.completed else session.current.model_dump()),
            "state": self.state(session_id),
        }

    def _maybe_insert_followup(self, session: _Session, question: PracticeQuestion, score: int) -> None:
        if session.followups_used >= MAX_FOLLOWUPS:
            return
        if question.is_followup:
            return
        should = score < FOLLOWUP_SCORE_THRESHOLD or question.type in FOLLOWUP_TYPES
        if not should:
            return
        probe = question_bank.make_followup(question.type, session.asked_followups, session.language)
        if not probe:
            return
        session.asked_followups.add(probe)
        session.followups_used += 1
        followup = PracticeQuestion(
            id=f"{question.id}-f{session.followups_used}",
            index=question.index,
            type=question.type,
            topic=question.topic,
            question=probe,
            is_followup=True,
        )
        session.queue.insert(session.cursor + 1, followup)

    def state(self, session_id: str) -> PracticeState:
        session = self._sessions.get(session_id)
        if session is None:
            return PracticeState(session_id=session_id, active=False)
        return PracticeState(
            session_id=session_id,
            active=not session.completed,
            completed=session.completed,
            round_index=len(session.turns),
            total_planned=session.total_planned,
            queue_length=len(session.queue),
            followups_used=session.followups_used,
            current_question=session.current,
            answered=session.turns,
            config=session.config,
        )

    def report(self, session_id: str, language: str = "zh") -> Dict[str, Any]:
        language = language if language in {"zh", "en"} else "zh"
        session = self._sessions.get(session_id)
        if session is None or not session.turns:
            return {
                "session_id": session_id,
                "overall_score": 0,
                "summary": "尚无练习记录，请先开始一场模拟面试。" if language == "zh" else "No practice record yet. Start a mock interview first.",
                "strengths": [],
                "weaknesses": [],
                "by_type": {},
                "recommended_practice": [],
                "question_reviews": [],
            }
        config = {**session.config, "language": language}
        return build_practice_report(session_id, session.turns, config)


def build_practice_report(session_id: str, turns: List[PracticeTurn], config: Dict[str, Any]) -> Dict[str, Any]:
    scores = [turn.score for turn in turns]
    overall = int(round(sum(scores) / len(scores))) if scores else 0

    by_type: Dict[str, Dict[str, Any]] = {}
    all_issues: List[str] = []
    all_suggestions: List[str] = []
    for turn in turns:
        bucket = by_type.setdefault(turn.question.type, {"count": 0, "score_sum": 0})
        bucket["count"] += 1
        bucket["score_sum"] += turn.score
        critic = turn.critic or {}
        all_issues.extend(str(i) for i in (critic.get("issues") or critic.get("specific_issues") or []))
        all_suggestions.extend(str(s) for s in (critic.get("suggestions") or []))
    for bucket in by_type.values():
        bucket["avg_score"] = int(round(bucket["score_sum"] / bucket["count"])) if bucket["count"] else 0

    strengths: List[str] = []
    best = max(turns, key=lambda t: t.score)
    worst = min(turns, key=lambda t: t.score)
    if best.score >= 80:
        strengths.append(f"「{_short(best.question.question)}」回答较好({best.score} 分)。")
    high_types = [t for t, b in by_type.items() if b["avg_score"] >= 80]
    if high_types:
        strengths.append("以下题型表现稳定:" + "、".join(high_types) + "。")
    if not strengths:
        strengths.append("已完成本轮练习,继续积累样本可以更准地定位强弱项。")

    weaknesses = list(dict.fromkeys(all_issues))[:5] or ["暂无明显共性问题,可继续提升回答的具体性与结构。"]

    recommended = list(dict.fromkeys(all_suggestions))[:5]
    if worst.score < 75:
        recommended.insert(0, f"重点重练:「{_short(worst.question.question)}」({worst.score} 分)。")
    if not recommended:
        recommended = ["把每个回答练成 60 秒和 2 分钟两个版本,突出判断、行动和结果。"]

    return {
        "session_id": session_id,
        "overall_score": overall,
        "summary": f"本场共练习 {len(turns)} 题,平均分 {overall}。",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "by_type": by_type,
        "recommended_practice": recommended,
        "best_question": best.question.question,
        "weakest_question": worst.question.question,
        "question_reviews": [
            {
                "question": turn.question.question,
                "type": turn.question.type,
                "is_followup": turn.question.is_followup,
                "score": turn.score,
                "main_weakness": (turn.critic or {}).get("main_weakness", "none"),
                "issues": (turn.critic or {}).get("issues", []),
            }
            for turn in turns
        ],
        "config": config,
    }


def _short(text: str, limit: int = 28) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"
