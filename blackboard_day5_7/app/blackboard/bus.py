from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Dict, List, Optional

from app.blackboard.events import BBEvent, EventType


class InMemoryBlackboardBus:
    """Append-only in-memory event bus for Phase 2 W8 infrastructure."""

    def __init__(self) -> None:
        self._events_by_session: Dict[str, List[BBEvent]] = defaultdict(list)
        self._lock = RLock()

    def publish(self, event: BBEvent) -> BBEvent:
        with self._lock:
            self._events_by_session[event.session_id].append(event)
        return event

    def replay(self, session_id: str) -> List[BBEvent]:
        with self._lock:
            return list(self._events_by_session.get(session_id, []))

    def latest(
        self,
        session_id: str,
        event_type: Optional[EventType] = None,
    ) -> Optional[BBEvent]:
        events = self.replay(session_id)
        if event_type is None:
            return events[-1] if events else None

        for event in reversed(events):
            if event.type == event_type:
                return event
        return None

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._events_by_session.pop(session_id, None)

    def dump_session_json(self, session_id: str) -> List[dict]:
        return [self._event_to_dict(event) for event in self.replay(session_id)]

    def dump_all_json(self) -> Dict[str, List[dict]]:
        with self._lock:
            return {
                session_id: [self._event_to_dict(event) for event in events]
                for session_id, events in self._events_by_session.items()
            }

    @staticmethod
    def _event_to_dict(event: BBEvent) -> dict:
        if hasattr(event, "model_dump"):
            return event.model_dump(mode="json")
        return event.dict()
