from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

CORE_FILES = [
    "app/blackboard/events.py",
    "app/blackboard/bus.py",
    "app/agents/base.py",
    "app/agents/perception_agent.py",
    "app/agents/resume_agent.py",
    "app/agents/rag_agent.py",
    "app/agents/tech_agent.py",
    "app/agents/behavioral_agent.py",
    "app/agents/critic_agent.py",
    "app/orchestrator/registry.py",
    "app/orchestrator/orchestrator.py",
    "app/orchestrator/factory.py",
    "app/adapters/phase1_pipeline.py",
    "app/resume/context_loader.py",
    "app/rag/local_rag.py",
    "app/critic/rules.py",
    "app/llm/config.py",
    "app/llm/providers.py",
    "app/llm/router.py",
    "app/privacy/outbound_guard.py",
    "orchestrator_v0.py",
]


def main() -> int:
    steps = [
        ("py_compile", [sys.executable, "-m", "py_compile", *CORE_FILES]),
        ("pytest", [sys.executable, "-m", "pytest", "tests", "-q"]),
        ("smoke_phase2", [sys.executable, "scripts/smoke_phase2.py"]),
        ("phase2_eval", [sys.executable, "evals/run_phase2_eval.py"]),
    ]
    for name, command in steps:
        print(f"[Phase2 check] Running {name}...")
        result = subprocess.run(command, cwd=BACKEND_ROOT)
        if result.returncode != 0:
            print(f"[Phase2 check] {name} failed with exit code {result.returncode}.")
            return result.returncode

    print("Phase2 check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
