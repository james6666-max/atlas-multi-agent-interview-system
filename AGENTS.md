# Atlas Interview - AGENTS.md

## Project Identity

This is a Windows-first local AI interview assistant.

It is not a new project. Do not recreate the repository. Do not scaffold a new backend or frontend unless explicitly requested.

The current real project root is:

`D:\atlas-multi-agent-interview-system`

## Current Repository Layout

```text
D:\atlas-multi-agent-interview-system
|-- blackboard_day5_7/                  # Python FastAPI backend
|-- interview-assistant-stage4-whisper/ # Electron + React + Vite desktop frontend
|-- docs/                               # documentation, runbooks, demo scripts, validation notes
|-- start-all.bat                       # one-click startup script
`-- README_Phase1.txt                   # Phase 1 project description
```

## Backend

The backend lives in:

`blackboard_day5_7/`

It contains the FastAPI service and the current multi-agent / blackboard-style implementation.

Core backend responsibilities:

- receive screenshot / audio / manual input
- run OCR or Whisper/STT where available
- classify interview questions
- route to Tech/Code or Behavioral style answer generation
- load resume / JD / knowledge context
- call a local Ollama model such as `qwen2.5:7b`
- use fallback logic when model generation fails
- run Critic scoring / revision suggestions
- write blackboard-style state, including `blackboard_instance.json`

The actual FastAPI entrypoint is:

`orchestrator_v0:app`

The backend Python environment is the existing conda environment:

`chuangxin`

Do not move backend code to a new `backend/` folder unless explicitly requested.

## Frontend

The frontend lives in:

`interview-assistant-stage4-whisper/`

It is an Electron + React + Vite desktop application.

Core frontend responsibilities:

- provide local desktop UI
- connect to the FastAPI backend at `http://127.0.0.1:8000`
- display recognized question text
- display generated answers
- show critic / review information where implemented

The active Vite renderer uses top-level `src/`. The `renderer/` directory appears to be an older or secondary scaffold; do not move active code there unless explicitly requested.

Do not move frontend code to a new `frontend/`, `renderer/`, or `desktop/` folder unless explicitly requested.

## Startup

The one-click startup script is:

`start-all.bat`

This script must use the current project root:

`D:\atlas-multi-agent-interview-system`

It must not contain old hardcoded paths such as:

`C:\Users\hp\Desktop\...`

When editing startup scripts, prefer paths relative to `%~dp0`.

## Development Rules

- Preserve the current project structure.
- Prefer minimal, surgical fixes over large rewrites.
- Do not introduce new production dependencies without asking first.
- Do not hardcode API keys.
- Do not remove existing fallback behavior.
- Do not remove local Ollama support.
- Do not remove manual input mode; it is important for demos and debugging.
- Keep Windows PowerShell and `.bat` compatibility.
- After changing scripts, test them from the project root.
- After changing backend code, run backend smoke checks.
- After changing frontend code, run the frontend build check.
- Any path must use the current real repository path, not `C:\Users\hp\Desktop\...`.

## Suggested Commands

From project root:

```powershell
cd D:\atlas-multi-agent-interview-system
```

Backend:

```powershell
cd blackboard_day5_7
conda run -n chuangxin python -m pip install -r requirements.txt
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000 --reload
```

Backend syntax check:

```powershell
cd blackboard_day5_7
conda run -n chuangxin python -m py_compile orchestrator_v0.py blackboard_store.py
```

Frontend:

```powershell
cd interview-assistant-stage4-whisper
npm install
npm run dev
```

Frontend build check:

```powershell
cd interview-assistant-stage4-whisper
npm run build
```

Backend status checks:

```powershell
curl http://127.0.0.1:8000/config/status
curl http://127.0.0.1:8000/blackboard
```

There is no `/api/health` endpoint in the current backend. Use `/config/status` or `/blackboard` for smoke checks unless a health route is added later.

## Current Phase

Current phase: Phase 1 stabilization.

Primary goals:

1. Make the existing project easy to start.
2. Fix stale paths in startup scripts and documentation.
3. Document the current architecture accurately.
4. Add simple smoke-test instructions.
5. Avoid large Phase 2 refactors until the current MVP is reproducibly runnable.

## Validation Requirement

For every change, report:

- files changed
- why each change was made
- commands run
- whether the command passed or failed
- remaining risks or manual steps

Do not claim something works unless the relevant command was actually run.
