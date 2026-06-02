# Phase 2 Acceptance

## Acceptance Criteria

Phase 2 is accepted when all of the following pass:

1. `/config/status` returns HTTP 200.
2. `/ask` technical questions route to `Tech/Code`.
3. `/ask` behavioral questions route to `Behavioral`.
4. `/ask` chitchat returns `question_type=ignored` and `answer=""`.
5. Normal answers include a `critic` object.
6. Normal answers include `context_used` and `rag_used` fields.
7. `pytest` passes.
8. `scripts\smoke_phase2.py` passes.
9. `evals\run_phase2_eval.py` produces a score report.
10. The frontend still starts with `npm run dev`.

## Current Acceptance Result

Backend checks:

```text
py_compile: passed
pytest: 81 passed
smoke_phase2.py: passed
run_phase2_eval.py: 250/250, accuracy=1.0
check_phase2.py: passed
```

Current standard Phase 2 chain:

```text
Perception -> Resume -> RAG -> Tech/Behavioral Draft -> Critic -> Final
```

Frontend build:

```text
npm run build: passed, with Vite large chunk warning
```

## Commands

From:

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
```

Run all backend checks:

```powershell
conda run -n chuangxin python scripts\check_phase2.py
```

Run smoke only:

```powershell
conda run -n chuangxin python scripts\smoke_phase2.py
```

Run eval only:

```powershell
conda run -n chuangxin python evals\run_phase2_eval.py
```

Frontend build:

```powershell
cd D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
npm run build
```
