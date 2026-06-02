# Atlas — Windows Packaging Runbook (M4)

Produces a double-click Windows installer that bundles the FastAPI backend as a
sidecar, so end users need **no Python install**. Run all steps **on Windows**.

## Architecture
- **Frontend**: Electron + React, packaged by `electron-builder` (NSIS installer).
- **Backend**: `orchestrator_v0:app`, frozen by **PyInstaller** into
  `blackboard_day5_7/dist/atlas-backend/` (onedir), then bundled into the app at
  `resources/backend/` (via `extraResources` in `package.json`).
- At runtime the Electron main process (`electron/backend-launcher.ts`) spawns
  `resources/backend/atlas-backend.exe` with:
  - `ATLAS_RESOURCE_DIR` = `resources/backend` (read-only bundled defaults)
  - `ATLAS_DATA_DIR` = `%APPDATA%/interview-assistant-v1/atlas_data` (writable:
    blackboard, settings, user-editable resume.txt / jd.txt / knowledge.txt)
- The renderer talks to `http://127.0.0.1:8000` and polls `/config/status`.

## Prerequisites (one-time)
```bat
:: backend env (conda "chuangxin" or any venv) with project deps + PyInstaller
conda activate chuangxin
pip install -r blackboard_day5_7\requirements.txt
pip install pyinstaller

:: frontend deps
cd interview-assistant-stage4-whisper
npm install
```

## Build steps

### One command (recommended)
```bat
:: from repo root — installs deps, freezes backend, builds installer
build-windows.bat
```

### Or manual
```bat
:: 1) Freeze the backend  ->  blackboard_day5_7\dist\atlas-backend\atlas-backend.exe
cd blackboard_day5_7
pyinstaller atlas_backend.spec --noconfirm

:: 2) (sanity) run the frozen backend directly, then hit http://127.0.0.1:8000/config/status
dist\atlas-backend\atlas-backend.exe

:: 3) Build the installer (electron-builder bundles dist/atlas-backend as resources/backend)
cd ..\interview-assistant-stage4-whisper
npm run package-win
:: -> installer in interview-assistant-stage4-whisper\release\
```

## LLM / models
- **LLM**: first run, open Settings → "Atlas 回答引擎 / Atlas Answer Engine":
  - Cloud (fast, streaming): pick a preset (Groq/DeepSeek/Qwen), paste the API key.
  - Local: install [Ollama](https://ollama.com) + `ollama pull qwen2.5:7b`, choose "Local only".
- **Whisper STT** (`faster-whisper`): the model (~460 MB for `small`) downloads on
  first voice transcription into the HF cache. Set `ATLAS_WHISPER_MODEL=tiny` for a
  smaller/faster first download. For fully offline installs, pre-bundle the model
  and point `HF_HOME` at it.
- **OCR** (`rapidocr-onnxruntime`): onnx models ship inside the package via the spec's
  `collect_all`.

## Troubleshooting
- **`ModuleNotFoundError` at sidecar startup**: add the missing module to
  `hiddenimports` in `atlas_backend.spec` and rebuild. Common culprits live under
  `onnxruntime`, `ctranslate2`, `tokenizers`, `uvicorn`.
- **Backend won't start in the packaged app**: launch
  `…\resources\backend\atlas-backend.exe` manually from a terminal to see the real
  error (the launcher runs it with `stdio: "ignore"`).
- **Big installer**: ML native libs are large; expect a few hundred MB. Consider
  `ATLAS_WHISPER_MODEL=tiny` and excluding unused providers.
- **SmartScreen warning**: unsigned builds trigger it. Add an EV code-signing cert
  to `package.json > build.win` when you have one.

## Notes
- `npm run dev` is unchanged (backend started separately via `start-all.bat`);
  `backend-launcher` is a no-op when `app.isPackaged` is false.
- The backend is cwd-independent and frozen-safe (`app/paths.py`); verified by the
  test suite + a simulated packaged run.
