from __future__ import annotations

from typing import ClassVar, List, Set

from app.agents.base import Agent
from app.blackboard.events import BBEvent, EventType
from app.resume.context_loader import build_candidate_context


class ResumeAgent(Agent):
    name: ClassVar[str] = "resume_agent"
    subscribes_to: ClassVar[Set[EventType]] = {EventType.QUESTION_DETECTED}
    emits: ClassVar[Set[EventType]] = {EventType.CONTEXT_LOADED, EventType.ERROR}
    latency_budget_ms: ClassVar[int] = 100

    async def handle(self, event: BBEvent) -> List[BBEvent]:
        question = str(event.payload.get("question", "")).strip()
        question_type = str(event.payload.get("question_type", "unknown")).strip()

        try:
            context = build_candidate_context(question)
            return [
                BBEvent(
                    session_id=event.session_id,
                    source_agent=self.name,
                    type=EventType.CONTEXT_LOADED,
                    parent_event_id=event.event_id,
                    payload={
                        "question": question,
                        "question_type": question_type,
                        "resume_summary": context["resume_summary"],
                        "jd_summary": context["jd_summary"],
                        "knowledge_summary": context["knowledge_summary"],
                        "matched_snippets": context["matched_snippets"],
                        "constraints": context["constraints"],
                        "has_resume": bool(context["resume_raw"].strip()),
                        "has_jd": bool(context["jd_raw"].strip()),
                        "has_knowledge": bool(context["knowledge_raw"].strip()),
                    },
                )
            ]
        except Exception as exc:
            self.logger.exception("ResumeAgent failed to load candidate context")
            return [
                BBEvent(
                    session_id=event.session_id,
                    source_agent=self.name,
                    type=EventType.ERROR,
                    parent_event_id=event.event_id,
                    payload={
                        "question": question,
                        "question_type": question_type,
                        "error": str(exc),
                    },
                )
            ]
