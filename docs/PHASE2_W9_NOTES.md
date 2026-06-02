# Phase 2 W9 Notes

## Scope

W9 connects the existing `/ask` main flow to the Phase 2 Orchestrator through one MainAgent adapter.

It does not split Tech Agent, Behavioral Agent, Resume Agent, RAG Agent, or Critic Agent yet.

## Adapter Shape

The adapter entry is:

```text
blackboard_day5_7\app\adapters\phase1_pipeline.py
```

`orchestrator_v0.py` configures the adapter with `_run_phase1_answer_pipeline_sync`.

`MainAgent` calls:

```text
phase1_pipeline.run_phase1_answer_pipeline(...)
```

This avoids:

```text
app\agents\main_agent.py -> orchestrator_v0.py
```

So `MainAgent` does not import the FastAPI module and does not create a circular import.

## MainAgent Input

`MainAgent` subscribes to:

```text
MANUAL_INPUT
QUESTION_DETECTED
```

It accepts question text from these payload keys:

```text
question
text
input
transcript
```

## MainAgent Output

On success, `MainAgent` emits:

```text
ANSWER_DRAFT
CRITIQUE_NOTE
ANSWER_FINAL
```

On failure, it emits:

```text
ERROR
```

## `/ask` Compatibility

`/ask` now attempts:

```text
AskRequest
-> BBEvent(type=MANUAL_INPUT)
-> Phase2 Orchestrator
-> MainAgent
-> Phase1 pipeline adapter
-> ANSWER_FINAL
-> AskResponse
```

If Phase 2 does not produce `ANSWER_FINAL`, `/ask` logs the error and falls back to the Phase 1 implementation.

The external response model remains `AskResponse`.

## Other APIs

W9 does not directly migrate:

```text
/ask_image
/ask_image_file
/ask_audio
```

They still build an `AskRequest` and call `ask(...)`, so they naturally use the same `/ask` compatibility path without changing their own OCR/STT code.

## Validation

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\agents\main_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py -q
```

Result:

```text
12 passed
```

Manual smoke:

```powershell
conda run -n chuangxin python -m uvicorn orchestrator_v0:app --host 127.0.0.1 --port 8000
```

Checked:

```text
/config/status
/ask
```

The manual smoke used `USE_OLLAMA=false` to avoid a real model call during validation.
