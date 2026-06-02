from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import ClassVar, List, Set

from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType


class Agent(ABC):
    name: ClassVar[str] = "base"
    subscribes_to: ClassVar[Set[EventType]] = set()
    emits: ClassVar[Set[EventType]] = set()
    latency_budget_ms: ClassVar[int] = 500

    def __init__(self, bus: InMemoryBlackboardBus):
        self.bus = bus
        self.logger = logging.getLogger(self.name)

    async def run_once(self, event: BBEvent) -> List[BBEvent]:
        if event.type not in self.subscribes_to:
            return []

        start = time.perf_counter()
        outputs = await self.handle(event)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        self.logger.info(
            "%s handled %s in %sms, budget=%sms",
            self.name,
            event.type,
            elapsed_ms,
            self.latency_budget_ms,
        )

        for output in outputs:
            if output.type not in self.emits:
                raise ValueError(
                    f"{self.name} emitted undeclared event type: {output.type}"
                )
            self.bus.publish(output)

        return outputs

    @abstractmethod
    async def handle(self, event: BBEvent) -> List[BBEvent]:
        raise NotImplementedError
