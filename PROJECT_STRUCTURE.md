# Atlas Interview Project Structure

## Real Repository Root

`D:\atlas-multi-agent-interview-system`

## Directory Tree

```text
D:\atlas-multi-agent-interview-system
|-- blackboard_day5_7/
|   |-- blackboard_instance.json
|   |-- blackboard_schema.json
|   |-- blackboard_store.py
|   |-- jd.txt
|   |-- knowledge.txt
|   |-- orchestrator_v0.py
|   |-- README.md
|   |-- requirements.txt
|   |-- resume.txt
|   |-- start_server.py
|   |-- test_blackboard.py
|   `-- test_server.py
|-- docs/
|   |-- Atlas_Stage8_release_*.bat
|   |-- Atlas_Stage8_*.bat
|   |-- Atlas_Stage8_*.txt
|   |-- Atlas_启动说明.txt
|   `-- Atlas_演示脚本.txt
|-- interview-assistant-stage4-whisper/
|   |-- electron/
|   |-- src/
|   |-- shared/
|   |-- assets/
|   |-- build/
|   |-- scripts/
|   |-- renderer/
|   |-- package.json
|   |-- package-lock.json
|   |-- vite.config.ts
|   |-- tsconfig.json
|   `-- tsconfig.electron.json
|-- AGENTS.md
|-- PROJECT_STRUCTURE.md
|-- README_Phase1.txt
`-- start-all.bat
```

## First-Level Directory Purpose

- `blackboard_day5_7/`: Python FastAPI backend. It contains the current orchestrator, multi-agent routing logic, file-backed blackboard state, OCR/STT handlers, local Ollama calls, fallback answers, critic scoring, mock interview routes, and report routes.
- `interview-assistant-stage4-whisper/`: Electron + React + Vite desktop frontend. It contains the active Vite renderer in `src/`, Electron main/preload/IPC code in `electron/`, shared AI provider metadata in `shared/`, and packaging resources.
- `docs/`: project runbooks, demo scripts, final validation notes, and backup helper scripts from Phase 1 / Stage 8.
- `start-all.bat`: Windows one-click launcher for the backend and frontend.
- `_ANALYSIS/`: local analysis notes generated during repository review.

## Core Call Chain

```text
screenshot / audio / manual input
  -> FastAPI backend
  -> OCR or Whisper/STT when needed
  -> question classification
  -> Tech/Code or Behavioral agent selection
  -> resume / JD / knowledge / recent-history context loading
  -> Ollama qwen2.5:7b answer generation when available
  -> fallback answer when model generation fails
  -> Critic scoring and rewrite/follow-up suggestions
  -> blackboard_instance.json update
  -> Electron frontend reads and displays status/results
```

## Backend Routes Found

- `GET /blackboard`
- `GET /config/status`
- `POST /ask`
- `POST /ask_image`
- `POST /ask_image_file`
- `POST /ask_audio`
- `POST /mock/start`
- `POST /mock/answer`
- `GET /mock/state`
- `GET /report/session`
- `GET /report/export_markdown`
- `POST /blackboard/clear_history`
- `POST /blackboard/reset_session`

There is no `/api/health` route in the current backend.

## How To Start

From the repository root:

```powershell
cd D:\atlas-multi-agent-interview-system
.\start-all.bat
```

Backend only:

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python -m pip install -r requirements.txt
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000 --reload
```

Frontend only:

```powershell
cd D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
npm install
npm run dev
```

The frontend Vite dev server is configured for port `54321`.

## Common Issues

### Backend port 8000 is occupied

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Frontend port is occupied

The actual configured frontend port is `54321`, not Vite's default `5173`.

```powershell
netstat -ano | findstr :54321
taskkill /PID <PID> /F
```

### Ollama is not running

Start Ollama, then check:

```powershell
ollama list
```

### `qwen2.5:7b` model does not exist

```powershell
ollama pull qwen2.5:7b
```

Or set `OLLAMA_MODEL` to an existing local model before starting the backend.

### npm dependencies are not installed

```powershell
cd D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
npm install
```

If `npm install` fails while downloading Electron with `read ECONNRESET`, retry on a stable network or configure a working Electron mirror before running the frontend build:

```powershell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
npm install --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000
```

### Python dependencies are not installed

If backend startup fails with missing modules such as `rapidocr_onnxruntime`, install backend requirements:

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python -m pip install -r requirements.txt
```

### `start-all.bat` path errors

`start-all.bat` should derive paths from `%~dp0`. It must not reference old paths such as `C:\Users\hp\Desktop\...`.
