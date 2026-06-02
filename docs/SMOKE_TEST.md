# Smoke Test

## 1. Install Backend Dependencies

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python -m pip install -r requirements.txt
```

Expected: required FastAPI, OCR, and Whisper dependencies are available in the active Python environment.

## 2. Start Backend

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000 --reload
```

Expected: FastAPI starts on `http://127.0.0.1:8000`.

## 3. Check Backend Status

The current backend does not expose `/api/health`. Use `/config/status` or `/blackboard`.

```powershell
curl http://127.0.0.1:8000/config/status
curl http://127.0.0.1:8000/blackboard
```

Expected: backend returns normal JSON responses.

## 4. Start Frontend

```powershell
cd D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
npm install
npm run dev
```

Expected: Vite/Electron starts without build errors. The configured Vite port is `54321`.

If installation fails at the Electron download step with `read ECONNRESET`, retry with an Electron mirror:

```powershell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
npm install --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000
```

## 5. Manual Input Test

Use the frontend manual input box, or call the backend API directly:

```powershell
curl -X POST http://127.0.0.1:8000/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"请用 STAR 法介绍一次你解决技术难题的经历。\",\"language\":\"Chinese\",\"source\":\"manual_input\"}"
```

Expected:

- backend receives the question
- agent generates an answer
- critic/review information is returned
- frontend displays the result when using the UI

## 6. Ollama Check

```powershell
ollama list
ollama run qwen2.5:7b
```

If the model is missing, pull it or switch to an existing local model:

```powershell
ollama pull qwen2.5:7b
```

The backend has fallback logic when Ollama is unavailable, but live LLM quality depends on Ollama and the configured model.

## 7. Static Checks

Backend syntax:

```powershell
cd D:\atlas-multi-agent-interview-system\blackboard_day5_7
conda run -n chuangxin python -m py_compile orchestrator_v0.py blackboard_store.py
```

Frontend build:

```powershell
cd D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
npm run build
```
