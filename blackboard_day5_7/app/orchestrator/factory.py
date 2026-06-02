from __future__ import annotations

from app.agents.behavioral_agent import BehavioralAgent
from app.agents.critic_agent import CriticAgent
from app.agents.perception_agent import PerceptionAgent
from app.agents.rag_agent import RAGAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.tech_agent import TechAgent
from app.blackboard.bus import InMemoryBlackboardBus
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.registry import AgentRegistry


def create_phase2_orchestrator() -> Orchestrator:
    bus = InMemoryBlackboardBus()
    registry = AgentRegistry()
    registry.register(PerceptionAgent(bus))
    registry.register(ResumeAgent(bus))
    registry.register(RAGAgent(bus))
    registry.register(TechAgent(bus))
    registry.register(BehavioralAgent(bus))
    registry.register(CriticAgent(bus))
    # MainAgent is kept as a legacy fallback adapter after W11, but is no
    # longer registered in the default Phase 2 runtime.
    return Orchestrator(bus, registry)


def create_phase2_runtime() -> tuple[InMemoryBlackboardBus, Orchestrator]:
    bus = InMemoryBlackboardBus()
    registry = AgentRegistry()
    registry.register(PerceptionAgent(bus))
    registry.register(ResumeAgent(bus))
    registry.register(RAGAgent(bus))
    registry.register(TechAgent(bus))
    registry.register(BehavioralAgent(bus))
    registry.register(CriticAgent(bus))
    # MainAgent remains available in app.agents.main_agent for explicit legacy
    # fallback wiring, but is not part of the default runtime.
    orchestrator = Orchestrator(bus, registry)
    return bus, orchestrator
