from __future__ import annotations

from typing import ClassVar, List, Set

from app.agents.base import Agent
from app.blackboard.events import BBEvent, EventType
from app.rag.local_rag import (
    load_knowledge_text,
    retrieve_local_knowledge,
    retrieve_session_history,
)


class RAGAgent(Agent):
    name: ClassVar[str] = "rag_agent"
    subscribes_to: ClassVar[Set[EventType]] = {EventType.QUESTION_DETECTED}
    emits: ClassVar[Set[EventType]] = {EventType.RAG_CHUNK, EventType.ERROR}
    latency_budget_ms: ClassVar[int] = 100

    async def handle(self, event: BBEvent) -> List[BBEvent]:
        question = str(event.payload.get("question", "")).strip()
        question_type = str(event.payload.get("question_type", "unknown")).strip()
        if not question:
            return [self._error_event(event, "RAGAgent received empty question")]

        try:
            knowledge_text = load_knowledge_text()
            knowledge_chunks = retrieve_local_knowledge(question, knowledge_text, top_k=3)
            history_chunks = retrieve_session_history(
                question,
                self.bus.replay(event.session_id),
                top_k=3,
            )
            chunks = self._rank_chunks(knowledge_chunks + history_chunks)
            sources = self._sources(chunks)
            return [
                BBEvent(
                    session_id=event.session_id,
                    source_agent=self.name,
                    type=EventType.RAG_CHUNK,
                    parent_event_id=event.event_id,
                    payload={
                        "question": question,
                        "question_type": question_type,
                        "chunks": chunks,
                        "sources": sources,
                        "has_rag": bool(chunks),
                        "retrieval_mode": "local_keyword",
                    },
                )
            ]
        except Exception as exc:
            self.logger.exception("RAGAgent failed")
            return [self._error_event(event, str(exc))]

    def _rank_chunks(self, chunks: list[dict]) -> list[dict]:
        ranked = sorted(
            chunks,
            key=lambda chunk: (-int(chunk.get("score", 0)), str(chunk.get("source", ""))),
        )
        limited = ranked[:5]
        for index, chunk in enumerate(limited, start=1):
            chunk["rank"] = index
        return limited

    def _sources(self, chunks: list[dict]) -> list[str]:
        sources = []
        for chunk in chunks:
            source = str(chunk.get("source", "")).strip()
            if source and source not in sources:
                sources.append(source)
        return sources

    def _error_event(self, parent: BBEvent, error: str) -> BBEvent:
        return BBEvent(
            session_id=parent.session_id,
            source_agent=self.name,
            type=EventType.ERROR,
            parent_event_id=parent.event_id,
            payload={
                "question": parent.payload.get("question", ""),
                "error": error,
            },
        )
