from __future__ import annotations

from typing import Any, ClassVar, List, Set

from app.adapters import phase1_pipeline
from app.agents.base import Agent
from app.blackboard.events import BBEvent, EventType


BEHAVIORAL_QUESTION_TYPES = {"behavioral", "resume_followup"}


class BehavioralAgent(Agent):
    name: ClassVar[str] = "behavioral_agent"
    subscribes_to: ClassVar[Set[EventType]] = {EventType.QUESTION_DETECTED}
    emits: ClassVar[Set[EventType]] = {
        EventType.ANSWER_DRAFT,
        EventType.ERROR,
    }
    latency_budget_ms: ClassVar[int] = 800

    async def handle(self, event: BBEvent) -> List[BBEvent]:
        question = str(event.payload.get("question", "")).strip()
        question_type = str(event.payload.get("question_type", "unknown")).strip()
        normalized_type = question_type.lower()

        if normalized_type not in BEHAVIORAL_QUESTION_TYPES:
            return []
        if not question:
            return [
                self._event(
                    event,
                    EventType.ERROR,
                    {"question": "", "error": "BehavioralAgent received empty question"},
                )
            ]

        try:
            context = self._latest_context(event.session_id)
            rag = self._latest_rag(event.session_id)
            result = await phase1_pipeline.run_phase1_answer_pipeline(
                question=question,
                language=str(event.payload.get("language", "Unknown")),
                source=str(event.payload.get("source", "manual_input")),
                agent_hint="behavioral",
                question_type=normalized_type,
                context=context,
                rag=rag,
            )
            return self._answer_events(event, question, normalized_type, result)
        except Exception as exc:
            self.logger.exception("BehavioralAgent failed to run Phase 1 pipeline")
            return [self._event(event, EventType.ERROR, {"question": question, "error": str(exc)})]

    def _answer_events(
        self,
        parent: BBEvent,
        question: str,
        question_type: str,
        result: dict[str, Any],
    ) -> List[BBEvent]:
        answer = str(result.get("answer", ""))
        context = result.get("context") or {}
        rag = result.get("rag") or {}
        return [
            self._event(
                parent,
                EventType.ANSWER_DRAFT,
                {
                    "question": question,
                    "question_type": question_type,
                    "selected_agent": result.get("selected_agent", "Behavioral"),
                    "draft": answer,
                    "answer": answer,
                    "raw_result": result,
                    "context": context,
                    "rag": rag,
                    "context_used": bool(result.get("context_used")),
                    "context_sources": result.get("context_sources", []),
                    "context_constraints": context.get("constraints", []),
                    "rag_used": bool(result.get("rag_used")),
                    "rag_sources": result.get("rag_sources", []),
                    "guidance": (
                        "Use only existing resume/JD/knowledge facts. If facts are missing, "
                        "describe how to organize the answer without inventing details. Prefer STAR. "
                        "Resume/JD facts have higher priority than RAG chunks for experience-specific claims."
                    ),
                },
            )
        ]

    def _latest_context(self, session_id: str) -> dict[str, Any]:
        context_event = self.bus.latest(session_id, EventType.CONTEXT_LOADED)
        return context_event.payload if context_event else {}

    def _latest_rag(self, session_id: str) -> dict[str, Any]:
        rag_event = self.bus.latest(session_id, EventType.RAG_CHUNK)
        return rag_event.payload if rag_event else {}

    def _event(self, parent: BBEvent, event_type: EventType, payload: dict[str, Any]) -> BBEvent:
        return BBEvent(
            session_id=parent.session_id,
            source_agent=self.name,
            type=event_type,
            payload=payload,
            parent_event_id=parent.event_id,
        )
