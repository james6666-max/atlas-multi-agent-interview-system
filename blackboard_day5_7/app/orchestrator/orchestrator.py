from __future__ import annotations

import logging
from collections import deque
from typing import List

from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType
from app.orchestrator.registry import AgentRegistry


class Orchestrator:
    max_events: int = 30

    def __init__(self, bus: InMemoryBlackboardBus, registry: AgentRegistry):
        self.bus = bus
        self.registry = registry
        self.logger = logging.getLogger(self.__class__.__name__)

    async def dispatch(self, event: BBEvent) -> List[BBEvent]:
        self.bus.publish(event)
        all_outputs: List[BBEvent] = []
        queue = deque([event])
        seen_event_ids = set()
        processed_count = 0

        while queue:
            current = queue.popleft()
            if current.event_id in seen_event_ids:
                continue
            seen_event_ids.add(current.event_id)
            processed_count += 1

            if processed_count > self.max_events:
                self.logger.error("Orchestrator event limit exceeded")
                error_event = BBEvent(
                    session_id=current.session_id,
                    source_agent="orchestrator",
                    type=EventType.ERROR,
                    payload={"error": "orchestrator_event_limit_exceeded"},
                    parent_event_id=current.event_id,
                )
                self.bus.publish(error_event)
                all_outputs.append(error_event)
                break

            for agent in self.registry.get_agents_for(current.type):
                agent_outputs = await agent.run_once(current)
                for output in agent_outputs:
                    all_outputs.append(output)
                    queue.append(output)

        return all_outputs
