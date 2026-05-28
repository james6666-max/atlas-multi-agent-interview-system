# Atlas Multi-Agent Interview System - Project Structure

## Overview

This repository contains a local multi-agent interview assistant prototype named Atlas. It is organized as a two-part system:

- `blackboard_day5_7`: Python FastAPI backend for orchestration, blackboard state, OCR/STT input, local LLM answering, critique, mock interview, and reports.
- `interview-assistant-stage4-whisper`: Electron + React + Vite desktop frontend, with screenshot capture, provider-based AI helpers, and Atlas backend integration.

The root also contains launcher scripts and project acceptance/demo documents.

## Top-Level Layout

```text
D:\atlas-multi-agent-interview-system
├── blackboard_day5_7/
├── docs/
├── interview-assistant-stage4-whisper/
├── start-all.bat
├── README_Phase1.txt
├── Atlas_启动说明.txt
├── Atlas_演示脚本.txt
├── Atlas_Stage8_最终验收记录.txt
├── Atlas_Stage8_备份命令.bat
└── Atlas_Stage8_release_备份命令.bat
```

## Backend: blackboard_day5_7

Purpose: local FastAPI service for the Atlas interview workflow.

Key files:

- `orchestrator_v0.py`: main FastAPI app. Handles question classification, agent selection, local LLM calls through Ollama, OCR, Whisper STT, critique, human-like rewrite, follow-up questions, mock interview, and report export.
- `blackboard_store.py`: file-backed blackboard store with JSON Schema validation and optimistic version checks.
- `blackboard_schema.json`: schema for session state, current question, history, resume/company context, RAG context, agent state, and privacy flags.
- `blackboard_instance.json`: current/sample persisted blackboard session.
- `resume.txt`, `jd.txt`, `knowledge.txt`: local context files used by answer generation and matching/RAG logic.
- `test_blackboard.py`, `test_server.py`: simple validation/API tests.
- `requirements.txt`: FastAPI, uvicorn, jsonschema, OCR, Pillow, faster-whisper, multipart upload dependencies.

Important backend routes:

- `GET /blackboard`: read current blackboard state.
- `GET /config/status`: show backend model/context configuration.
- `POST /ask`: manual question input.
- `POST /ask_image`: OCR from image path.
- `POST /ask_image_file`: OCR from uploaded image file.
- `POST /ask_audio`: speech-to-text from uploaded audio.
- `POST /mock/start`: start mock interview.
- `POST /mock/answer`: submit mock interview answer for critique.
- `GET /mock/state`: inspect mock interview state.
- `GET /report/session`: build session report.
- `GET /report/export_markdown`: export report as Markdown.
- `POST /blackboard/clear_history`: clear interview history.
- `POST /blackboard/reset_session`: reset session state.

Backend data flow:

```text
input question / screenshot / audio
  -> perception: OCR or Whisper if needed
  -> classify question type
  -> select agent: Tech/Code or Behavioral
  -> load resume, JD, knowledge, recent history
  -> generate answer with Ollama qwen2.5:7b when available
  -> fallback to rule/template answer on LLM error
  -> critic scores clarity, correctness, human-likeness, resume/JD fit, privacy
  -> optional rewrite and follow-up generation
  -> append to blackboard history
  -> frontend reads history/status/report
```

## Frontend: interview-assistant-stage4-whisper

Purpose: Electron desktop app with a React renderer. The original app supports screenshot-based coding interview help through multiple AI providers; this repo adds Atlas backend panels and workflows in `src/App.tsx`.

Key directories:

- `electron/`: Electron main process, IPC handlers, screenshots, AI provider clients, transcription, answer suggestions, updater, shortcuts, config.
- `src/`: active Vite React renderer.
- `src/_pages/`: main app views: queue, solutions, debug, subscribed app wrapper.
- `src/components/`: UI components for queue, solution commands, conversation, settings, header, toasts, primitive UI.
- `shared/`: shared AI model/provider definitions.
- `assets/`: app icons and build resources.
- `build/`: packaging entitlements.
- `scripts/`: packaging/notarization helper.
- `renderer/`: appears to be an older/secondary CRA-style renderer scaffold; the active Vite app uses top-level `src/`.

Important frontend files:

- `package.json`: scripts, dependencies, Electron Builder config.
- `vite.config.ts`: Vite + React + Electron plugin config; dev server port is `54321`.
- `electron/main.ts`: app lifecycle, BrowserWindow setup, state, helper initialization, protocol registration, window movement/visibility.
- `electron/preload.ts`: exposes safe renderer APIs through `contextBridge`.
- `electron/ipcHandlers.ts`: IPC endpoints for config, screenshots, processing, movement, transcription, conversation, suggestions.
- `electron/ProcessingHelper.ts`: screenshot-to-problem extraction, solution generation, debugging, and AI SDK calls.
- `electron/ProviderClientFactory.ts`: provider abstraction for OpenAI, Gemini, Anthropic, Azure OpenAI, OpenRouter.
- `electron/TranscriptionHelper.ts`: OpenAI/Azure Whisper and Gemini audio transcription.
- `electron/ConfigHelper.ts`: persistent local app config.
- `shared/aiModels.ts`: provider metadata, default models, model validation helpers.
- `src/App.tsx`: active Atlas UI integration; calls backend routes on `http://127.0.0.1:8000`.

Frontend-to-backend integration:

```text
React App
  -> fetch http://127.0.0.1:8000/blackboard
  -> fetch http://127.0.0.1:8000/config/status
  -> POST /ask for manual questions
  -> POST /ask_image_file for screenshot/image OCR
  -> POST /ask_audio for voice input
  -> POST /mock/start and /mock/answer for mock interview
  -> GET /report/session and /report/export_markdown
  -> POST /blackboard/clear_history and /blackboard/reset_session
```

## Launch And Runtime

`start-all.bat` starts:

- Backend: `python -m uvicorn orchestrator_v0:app --reload --host 127.0.0.1 --port 8000`
- Frontend: `npx vite --host 127.0.0.1 --port 54321 --strictPort`

Note: older launcher/docs previously referenced a stale desktop path. For this workspace, startup scripts should derive paths from the repository root:

- `D:\atlas-multi-agent-interview-system\blackboard_day5_7`
- `D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper`

## Documentation

Root and `docs/` contain duplicated project-facing documents:

- startup instructions
- demo script
- final acceptance record
- backup/release backup commands

Some Chinese text displays as mojibake in the PowerShell output, but that appears to be a terminal encoding/display issue rather than necessarily a logic issue.

## Architecture Summary

Atlas is a local-first interview copilot prototype. The backend is the source of truth for multi-agent state through a JSON blackboard. The frontend is a desktop shell that captures input, displays status and results, and calls the backend HTTP API. The system prefers local context and local Ollama inference, with fallback behavior when the LLM is unavailable. The Electron app also retains its own provider-based AI SDK path for screenshot solution generation and live conversation assistance.
