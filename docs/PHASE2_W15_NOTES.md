# Phase 2 W15 Notes

## Scope

W15 makes the current Phase 2 build easier to validate, demo, and reproduce.

It does not add new agents, change frontend UI, add Redis/PostgreSQL/pgvector, add web search, package an installer, or sign binaries.

## Added Files

```text
blackboard_day5_7\evals\phase2_questions.json
blackboard_day5_7\evals\run_phase2_eval.py
blackboard_day5_7\scripts\smoke_phase2.py
blackboard_day5_7\scripts\check_phase2.py
docs\PHASE2_W15_NOTES.md
docs\PHASE2_ACCEPTANCE.md
docs\RUNBOOK_PHASE2.md
```

## Eval Set

`phase2_questions.json` contains 50 cases:

```text
technical: 10
algorithm: 10
system_design: 8
behavioral: 10
resume_followup: 6
ignored/chitchat/incomplete: 6
```

The eval script runs through FastAPI `TestClient` with:

```text
USE_OLLAMA=false
```

It checks routing, selected agent, should-answer behavior, forbidden phrases, simple answer content, latency, and category-level score.

Latest result:

```text
total_score: 250
max_score: 250
accuracy: 1.0
avg_latency_ms: 130.82
p95_latency_ms: 216
failed_cases_count: 0
```

## Smoke Script

`scripts\smoke_phase2.py` checks:

```text
/config/status
/ask technical
/ask behavioral
/ask ignored
/blackboard
```

It backs up and restores `blackboard_instance.json`.

Result:

```text
Phase2 smoke passed.
```

## Check Script

`scripts\check_phase2.py` runs:

```text
py_compile
pytest
smoke_phase2.py
run_phase2_eval.py
```

Result:

```text
Phase2 check passed.
```

## Startup Script

`start-all.bat` still derives paths from:

```text
%~dp0
```

It starts:

```text
Backend: blackboard_day5_7, conda env chuangxin, orchestrator_v0:app, port 8000
Frontend: interview-assistant-stage4-whisper, npm run dev, port 54321
```

It does not contain old `C:\Users\hp\Desktop` project paths.

W15 removed backend `--reload` from `start-all.bat` for steadier demo startup.

## Validation Commands

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\blackboard\events.py app\blackboard\bus.py app\agents\base.py app\agents\perception_agent.py app\agents\resume_agent.py app\agents\rag_agent.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\agents\critic_agent.py app\orchestrator\registry.py app\orchestrator\orchestrator.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py app\resume\context_loader.py app\rag\local_rag.py app\critic\rules.py orchestrator_v0.py scripts\smoke_phase2.py scripts\check_phase2.py evals\run_phase2_eval.py
conda run -n chuangxin python -m pytest tests -q
conda run -n chuangxin python scripts\smoke_phase2.py
conda run -n chuangxin python evals\run_phase2_eval.py
conda run -n chuangxin python scripts\check_phase2.py
```

Results:

```text
py_compile: passed
pytest: 81 passed
smoke_phase2.py: passed
run_phase2_eval.py: 250/250, avg_latency_ms=141.44, p95_latency_ms=235
check_phase2.py: passed, eval inside check was 250/250, avg_latency_ms=130.82, p95_latency_ms=216
npm run build: passed, with Vite large chunk warning
```

Frontend build produced Vite's standard chunk-size warning for large generated bundles, but the command exited successfully.

## Current Phase 2 Chain

```text
Perception -> Resume -> RAG -> Tech/Behavioral Draft -> Critic -> Final
```

## Remaining Risk

The eval set validates routing and basic response health. It is not a semantic correctness benchmark for high-quality answers.

The frontend dependency files are still dirty from the earlier dependency safety cleanup and were not changed in W15.
