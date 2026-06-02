# Phase 2 Runbook

## 1. Start Backend

From the backend directory:

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000
```

For smoke/demo without local model latency:

```powershell
$env:USE_OLLAMA="false"
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000
```

## 2. Start Frontend

From the frontend directory:

```powershell
cd D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
npm run dev
```

The current Electron/Vite dev server expects:

```text
http://localhost:54321
```

For a Phase2 frontend demo, open the manual input tab and use one of the sample questions:

```text
What is RESTful API?
Tell me about a project you are most proud of.
hello, nice weather.
```

Expected behavior:

- technical questions route to `Tech/Code`
- behavioral questions route to `Behavioral`
- chitchat returns `ignored`
- normal answers show Critic, context, RAG, and Agent Trace panels

For W17 and later frontend demos:

1. Click the Technical example and submit it.
2. Confirm Agent Trace highlights the Tech Draft path.
3. Confirm Critic, Context/RAG, latency, and Copy Answer are visible.
4. Click the Behavioral example and submit it.
5. Confirm Agent Trace highlights the Behavioral Draft path.
6. Click the ignored example and submit it.
7. Confirm the UI shows Perception skip and no generated answer.
8. Expand Raw response when a technical reviewer wants to inspect the full `/ask` payload.

For W18 and later frontend demos:

1. The app shell lazy-loads the dashboard page, so a short `Loading page...` fallback may appear on cold start.
2. Use the same top-level tabs for Screenshot, Voice, and Text input.
3. Use the right-side Quick Actions panel for Blackboard, API docs, mock interview, and report controls.
4. The Phase2 manual demo behavior remains unchanged from W17.

## 3. One-Click Startup

From the project root:

```powershell
cd D:\atlas-multi-agent-interview-system
.\start-all.bat
```

The script uses `%~dp0`, starts the backend from `blackboard_day5_7`, and starts the frontend from `interview-assistant-stage4-whisper`.

## 4. Run Smoke

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python scripts\smoke_phase2.py
```

Smoke covers:

```text
/config/status
/ask technical
/ask behavioral
/ask ignored
/blackboard
```

## 5. Run Eval

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python evals\run_phase2_eval.py
```

Results are written to:

```text
blackboard_day5_7\evals\results\phase2_eval_latest.json
blackboard_day5_7\evals\results\phase2_eval_YYYYMMDD_HHMMSS.json
```

## 6. Run Full Phase2 Check

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python scripts\check_phase2.py
```

This runs:

```text
py_compile
pytest
smoke
eval
```

## 7. Test Real Ollama

Check model availability:

```powershell
ollama list
ollama run qwen2.5:7b
```

Run backend with Ollama enabled:

```powershell
$env:USE_OLLAMA="true"
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000
```

## 8. Common Issues

### Port 8000 Is Occupied

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Stop the owning process or run the backend on a different port.

### Port 54321 Is Occupied

The frontend dev script expects Vite on port `54321`. Stop the process using that port before `npm run dev`.

### Ollama Is Not Running

Start Ollama, then check:

```powershell
ollama list
```

### `qwen2.5:7b` Is Missing

Pull it or switch `OLLAMA_MODEL`:

```powershell
ollama pull qwen2.5:7b
$env:OLLAMA_MODEL="your-local-model"
```

### `conda run` Reports Temporary File Occupied

This can happen when multiple `conda run` commands are launched in parallel. Re-run the failed command by itself.

### PowerShell Chinese JSON Looks Garbled

The backend stores UTF-8 JSON. If console output looks garbled, set:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8="1"
```

Then rerun the command.

## 9. Current Phase2 Chain

```text
Perception -> Resume -> RAG -> Tech/Behavioral Draft -> Critic -> Final
```
