# Day 5-7 Blackboard JSON Schema Demo

## 1. Install dependencies
```bash
pip install -r requirements.txt
```

## 2. Validate read/write locally
```bash
python test_blackboard.py
```

## 3. Start Orchestrator v0
```bash
uvicorn orchestrator_v0:app --reload --port 8000
```

## 4. Test with curl
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"请设计一个短链接系统","language":"Chinese","source":"manual_input"}'
```

```bash
curl http://127.0.0.1:8000/blackboard
```

## Files
- `blackboard_schema.json`: JSON Schema
- `blackboard_instance.json`: sample blackboard data
- `blackboard_store.py`: read/write/validate module
- `orchestrator_v0.py`: FastAPI demo
- `test_blackboard.py`: local test script
