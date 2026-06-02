from __future__ import annotations

from typing import Any, ClassVar, List, Set

from app.agents.base import Agent
from app.blackboard.events import BBEvent, EventType
from app.critic.rules import review_answer


class CriticAgent(Agent):
    name: ClassVar[str] = "critic_agent"
    subscribes_to: ClassVar[Set[EventType]] = {EventType.ANSWER_DRAFT}
    emits: ClassVar[Set[EventType]] = {
        EventType.CRITIQUE_NOTE,
        EventType.ANSWER_APPROVED,
        EventType.ANSWER_REJECTED,
        EventType.ANSWER_FINAL,
        EventType.ERROR,
    }
    latency_budget_ms: ClassVar[int] = 100

    async def handle(self, event: BBEvent) -> List[BBEvent]:
        try:
            question = str(event.payload.get("question", "")).strip()
            question_type = str(event.payload.get("question_type", "")).strip()
            selected_agent = str(event.payload.get("selected_agent", "")).strip()
            answer = str(event.payload.get("answer") or event.payload.get("draft") or "").strip()
            context = event.payload.get("context") if isinstance(event.payload.get("context"), dict) else {}
            rag = event.payload.get("rag") if isinstance(event.payload.get("rag"), dict) else {}
            raw_result = event.payload.get("raw_result")
            if not isinstance(raw_result, dict):
                raw_result = {}

            critic = review_answer(
                question=question,
                answer=answer,
                question_type=question_type,
                selected_agent=selected_agent,
                context=context,
                rag=rag,
            )
            final_answer = str(critic.get("final_answer") or answer)
            final_payload = self._final_payload(
                event=event,
                question=question,
                question_type=question_type,
                selected_agent=selected_agent,
                answer=final_answer,
                critic=critic,
                raw_result=raw_result,
            )

            outputs = [
                self._event(
                    event,
                    EventType.CRITIQUE_NOTE,
                    {
                        "question": question,
                        "question_type": question_type,
                        "selected_agent": selected_agent,
                        "approved": bool(critic.get("approved")),
                        "score": critic.get("score", 0),
                        "issues": critic.get("issues", []),
                        "suggestions": critic.get("suggestions", []),
                        "risk_flags": critic.get("risk_flags", []),
                    },
                )
            ]

            if critic.get("approved"):
                outputs.append(self._event(event, EventType.ANSWER_APPROVED, final_payload))
            else:
                outputs.append(
                    self._event(
                        event,
                        EventType.ANSWER_REJECTED,
                        {
                            "question": question,
                            "question_type": question_type,
                            "selected_agent": selected_agent,
                            "rejected_answer": answer,
                            "safe_answer": final_answer,
                            "critic": critic,
                            "raw_result": raw_result,
                        },
                    )
                )

            outputs.append(self._event(event, EventType.ANSWER_FINAL, final_payload))
            return outputs
        except Exception as exc:
            self.logger.exception("CriticAgent failed")
            return [self._event(event, EventType.ERROR, {"error": str(exc)})]

    def _final_payload(
        self,
        event: BBEvent,
        question: str,
        question_type: str,
        selected_agent: str,
        answer: str,
        critic: dict[str, Any],
        raw_result: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(raw_result)
        merged.update(
            {
                "question": raw_result.get("question", question),
                "question_type": raw_result.get("question_type", question_type),
                "selected_agent": raw_result.get("selected_agent", selected_agent),
                "answer": answer,
                "critic": critic,
                "context_used": bool(event.payload.get("context_used")),
                "context_sources": event.payload.get("context_sources", []),
                "rag_used": bool(event.payload.get("rag_used")),
                "rag_sources": event.payload.get("rag_sources", []),
            }
        )
        return {
            "question": question,
            "question_type": question_type,
            "selected_agent": selected_agent,
            "answer": answer,
            "critic": critic,
            "raw_result": merged,
            "context_used": bool(event.payload.get("context_used")),
            "context_sources": event.payload.get("context_sources", []),
            "rag_used": bool(event.payload.get("rag_used")),
            "rag_sources": event.payload.get("rag_sources", []),
        }

    def _event(self, parent: BBEvent, event_type: EventType, payload: dict[str, Any]) -> BBEvent:
        return BBEvent(
            session_id=parent.session_id,
            source_agent=self.name,
            type=event_type,
            payload=payload,
            parent_event_id=parent.event_id,
        )
