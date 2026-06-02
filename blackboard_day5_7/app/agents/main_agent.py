from __future__ import annotations

from typing import Any, ClassVar, List, Set

from app.adapters import phase1_pipeline
from app.agents.base import Agent
from app.blackboard.events import BBEvent, EventType


class MainAgent(Agent):
    name: ClassVar[str] = "main_agent"
    subscribes_to: ClassVar[Set[EventType]] = {
        EventType.QUESTION_DETECTED,
    }
    emits: ClassVar[Set[EventType]] = {
        EventType.ANSWER_DRAFT,
        EventType.CRITIQUE_NOTE,
        EventType.ANSWER_FINAL,
        EventType.ERROR,
    }
    latency_budget_ms: ClassVar[int] = 800

    async def handle(self, event: BBEvent) -> List[BBEvent]:
        question = self._extract_question(event.payload)
        if not question:
            return [
                self._event(
                    event,
                    EventType.ERROR,
                    {"question": "", "error": "MainAgent received empty question"},
                )
            ]

        try:
            result = await phase1_pipeline.run_phase1_answer_pipeline(
                question=question,
                language=str(event.payload.get("language", "Unknown")),
                source=str(event.payload.get("source", "manual_input")),
            )
            answer = str(result.get("answer", ""))
            critic = result.get("critic")

            outputs = [
                self._event(
                    event,
                    EventType.ANSWER_DRAFT,
                    {
                        "question": question,
                        "draft": answer,
                        "raw_result": result,
                    },
                )
            ]

            if critic:
                outputs.append(
                    self._event(
                        event,
                        EventType.CRITIQUE_NOTE,
                        {
                            "question": question,
                            "critic": critic,
                        },
                    )
                )

            outputs.append(
                self._event(
                    event,
                    EventType.ANSWER_FINAL,
                    {
                        "question": question,
                        "answer": answer,
                        "critic": critic,
                        "raw_result": result,
                    },
                )
            )
            return outputs
        except Exception as exc:
            self.logger.exception("MainAgent failed to run Phase 1 pipeline")
            return [
                self._event(
                    event,
                    EventType.ERROR,
                    {"question": question, "error": str(exc)},
                )
            ]

    @staticmethod
    def _extract_question(payload: dict[str, Any]) -> str:
        for key in ("question", "text", "input", "transcript"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _event(self, parent: BBEvent, event_type: EventType, payload: dict[str, Any]) -> BBEvent:
        return BBEvent(
            session_id=parent.session_id,
            source_agent=self.name,
            type=event_type,
            payload=payload,
            parent_event_id=parent.event_id,
        )
