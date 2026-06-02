from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from app.agents.base import Agent
from app.blackboard.events import EventType


class AgentRegistry:
    def __init__(self):
        self._agents: List[Agent] = []
        self._by_event: Dict[EventType, List[Agent]] = defaultdict(list)

    def register(self, agent: Agent) -> None:
        self._agents.append(agent)
        for event_type in agent.subscribes_to:
            self._by_event[event_type].append(agent)

    def get_agents_for(self, event_type: EventType) -> List[Agent]:
        return list(self._by_event.get(event_type, []))

    def all_agents(self) -> List[Agent]:
        return list(self._agents)
