# Phase 2 Plan

## Goal

Phase 2 upgrades the existing Phase 1 MVP into a clearer multi-agent architecture without rebuilding the repository.

The backend remains in:

```text
D:\atlas-multi-agent-interview-system\blackboard_day5_7
```

The frontend remains in:

```text
D:\atlas-multi-agent-interview-system\interview-assistant-stage4-whisper
```

Do not create new `backend/`, `frontend/`, or `native/` directories for Phase 2 work.

## Current Backend Shape

The current FastAPI backend entry is:

```text
blackboard_day5_7\orchestrator_v0.py
```

It currently owns the Phase 1 MVP chain:

```text
screenshot / audio / manual input
-> FastAPI API
-> OCR or Whisper/STT where applicable
-> question classification
-> Tech/Code or Behavioral selection
-> resume / JD / knowledge context loading
-> Ollama qwen2.5:7b answer generation, with fallback
-> Critic review and rewrite/follow-up metadata
-> blackboard_instance.json updates through blackboard_store.py
-> frontend display
```

`blackboard_day5_7\blackboard_store.py` is the current file-based blackboard adapter for `blackboard_instance.json`.

## Phase 2 Order

W8: Blackboard Event + Agent Base infrastructure.

W9: Orchestrator + migrate the existing MainAgent-style answer chain, while keeping a single agent wrapper.

W10: Perception Agent for complete-question detection and classification.

W11: Tech Agent + Behavioral Agent split.

W12: Resume Agent for structured resume, JD, and project context.

W13: RAG Agent for local knowledge and session replay first; web search remains optional.

W14: Critic Agent hardening before final answer.

W15: Evaluation, packaging, and documentation hardening.

## W8 Status

W8 adds only infrastructure. It does not migrate the existing API flow and does not change frontend behavior.

New backend modules:

```text
blackboard_day5_7\app\blackboard\events.py
blackboard_day5_7\app\blackboard\bus.py
blackboard_day5_7\app\agents\base.py
blackboard_day5_7\app\orchestrator\registry.py
blackboard_day5_7\app\orchestrator\orchestrator.py
```

Tests:

```text
blackboard_day5_7\tests\test_blackboard_bus.py
blackboard_day5_7\tests\test_agent_base.py
```

## W8 Design

`BBEvent` is the standard event object for later agent communication.

`InMemoryBlackboardBus` is append-only and session-aware. It supports publish, replay, latest, clear, and JSON dumping. It does not depend on Redis, PostgreSQL, or any database.

`Agent` is the abstract base class. Agents declare subscribed event types and emitted event types. If an agent emits an undeclared event type, `run_once` raises an error.

`AgentRegistry` maps event types to registered agent instances.

`Orchestrator` publishes an incoming event, finds subscribed agents, and dispatches the event to them.

## W9 Status

W9 wraps the existing answer-generation chain in a single MainAgent adapter and dispatches `/ask` through the Phase 2 Orchestrator.

New backend modules:

```text
blackboard_day5_7\app\adapters\phase1_pipeline.py
blackboard_day5_7\app\agents\main_agent.py
blackboard_day5_7\app\orchestrator\factory.py
```

Updated backend entry:

```text
blackboard_day5_7\orchestrator_v0.py
```

Current W9 behavior:

- `/ask` creates a `MANUAL_INPUT` event and dispatches it through the Phase 2 Orchestrator.
- `MainAgent` consumes `MANUAL_INPUT` and calls the configured Phase 1 pipeline adapter.
- The Phase 1 pipeline still performs classification, answer generation, Critic review, fallback handling, and `blackboard_instance.json` updates.
- `MainAgent` emits `ANSWER_DRAFT`, `CRITIQUE_NOTE`, and `ANSWER_FINAL` events.
- `/ask` returns the same `AskResponse` shape as Phase 1.
- If the Phase 2 path fails, `/ask` falls back to the Phase 1 implementation.
- `/ask_image`, `/ask_image_file`, and `/ask_audio` are not directly migrated in W9; they continue to reuse `ask(AskRequest)` as before.

W9 intentionally does not split Tech/Behavioral yet. It preserves:

- existing `/ask`, `/ask_image`, `/ask_image_file`, and `/ask_audio` behavior
- Ollama `qwen2.5:7b` support
- fallback answer generation
- manual input mode
- Critic execution before the API response
- `blackboard_instance.json` compatibility

W9 validation:

```text
conda run -n chuangxin python -m py_compile app\agents\main_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py -q
```

Result: 12 tests passed.

## W10 Next Step

W10 adds a Perception Agent for complete-question detection and classification.

New backend module:

```text
blackboard_day5_7\app\agents\perception_agent.py
```

Updated W10 behavior:

- `/ask` still creates a `MANUAL_INPUT` event.
- `PerceptionAgent` consumes `MANUAL_INPUT`, `TRANSCRIPT_FINAL`, and `OCR_TEXT`.
- If the input is a complete interview question, it emits `QUESTION_DETECTED`.
- `MainAgent` now subscribes only to `QUESTION_DETECTED`.
- The Orchestrator now supports queue-based chained event dispatch.
- If Perception skips the input, `/ask` returns a compatible `AskResponse` with `question_type="ignored"`, `selected_agent="Perception"`, and an empty answer.
- Ignored inputs do not fall back to Phase 1.
- Phase 2 execution errors still fall back to Phase 1.

W10 intentionally does not split Tech/Behavioral yet. That remains W11.

W10 validation:

```text
conda run -n chuangxin python -m py_compile app\agents\perception_agent.py app\agents\main_agent.py app\orchestrator\factory.py app\orchestrator\orchestrator.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py -q
```

Result: 26 tests passed.

## W11 Next Step

W11 splits the current MainAgent behavior into Tech Agent and Behavioral Agent while keeping the Phase 2 event flow stable.

New backend modules:

```text
blackboard_day5_7\app\agents\tech_agent.py
blackboard_day5_7\app\agents\behavioral_agent.py
```

Updated W11 behavior:

- `PerceptionAgent` still emits `QUESTION_DETECTED`.
- `TechAgent` handles `technical`, `algorithm`, and `system_design`.
- `BehavioralAgent` handles `behavioral` and `resume_followup`.
- `MainAgent` remains in the repository as a legacy adapter, but it is no longer registered in the default Phase 2 runtime.
- Factory registration is now `PerceptionAgent`, `TechAgent`, `BehavioralAgent`.
- Ignored input still does not fall back to Phase 1.
- Detected-but-unhandled input returns a compatible empty response instead of 500.
- Phase 2 execution errors still fall back to Phase 1.

W11 validation:

```text
conda run -n chuangxin python -m py_compile app\agents\tech_agent.py app\agents\behavioral_agent.py app\agents\main_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py -q
```

Result: 39 tests passed.

## W12 Status

W12 adds ResumeAgent as the shared resume/JD/knowledge context entrypoint before the specialized answer agents run.

New backend modules:

```text
blackboard_day5_7\app\agents\resume_agent.py
blackboard_day5_7\app\resume\context_loader.py
blackboard_day5_7\app\resume\__init__.py
```

Updated W12 behavior:

- `PerceptionAgent` still emits `QUESTION_DETECTED`.
- `ResumeAgent` consumes `QUESTION_DETECTED` and emits `CONTEXT_LOADED`.
- `TechAgent` reads the latest `CONTEXT_LOADED` event from the in-memory bus before calling the Phase 1 pipeline adapter.
- `BehavioralAgent` reads the same context and includes constraints to avoid inventing resume facts and prefer STAR framing.
- Factory registration is now `PerceptionAgent`, `ResumeAgent`, `TechAgent`, `BehavioralAgent`.
- `/ask` uses a unique Phase 2 session id per request so stale context from a previous request is not reused.
- `AskResponse` now exposes lightweight `context_used` and `context_sources` fields for debugging without returning full resume text.
- Ignored input still does not trigger ResumeAgent or answer agents.
- Resume file loading errors emit `ERROR` from ResumeAgent but do not by themselves prevent the answer agents from continuing.
- Phase 2 execution errors still fall back to Phase 1.

W12 intentionally does not add database storage, pgvector, Redis, Web RAG, document upload, or frontend UI changes.

W12 validation:

```text
conda run -n chuangxin python -m py_compile app\agents\resume_agent.py app\resume\context_loader.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
D:\miniconda\envs\chuangxin\python.exe -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py tests\test_resume_agent.py tests\test_phase2_context_flow.py -q
```

Result: 50 tests passed.

## W13 Status

W13 adds a lightweight local RAGAgent for `knowledge.txt` and current-session blackboard replay.

New backend modules:

```text
blackboard_day5_7\app\agents\rag_agent.py
blackboard_day5_7\app\rag\local_rag.py
blackboard_day5_7\app\rag\__init__.py
```

Updated W13 behavior:

- `RAGAgent` consumes `QUESTION_DETECTED` and emits `RAG_CHUNK`.
- Retrieval is local keyword matching only. It does not use web search, Tavily, embeddings, Redis, PostgreSQL, or pgvector.
- `RAGAgent` searches `knowledge.txt` and relevant events from `InMemoryBlackboardBus.replay(session_id)`.
- Factory registration is now `PerceptionAgent`, `ResumeAgent`, `RAGAgent`, `TechAgent`, `BehavioralAgent`.
- `TechAgent` reads the latest `RAG_CHUNK` before calling the Phase 1 pipeline adapter.
- `BehavioralAgent` also reads RAG, but resume/JD facts remain higher priority for experience-specific claims.
- Empty RAG results still emit `RAG_CHUNK` with `has_rag=False` and do not block answers.
- `AskResponse` now exposes lightweight `rag_used` and `rag_sources` fields.
- Ignored input still does not trigger ResumeAgent, RAGAgent, or answer agents.
- Phase 2 execution errors still fall back to Phase 1.

W13 validation:

```text
conda run -n chuangxin python -m py_compile app\rag\local_rag.py app\agents\rag_agent.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py tests\test_resume_agent.py tests\test_phase2_context_flow.py tests\test_local_rag.py tests\test_rag_agent.py tests\test_phase2_rag_flow.py -q
```

Result: 65 tests passed.

## W14 Status

W14 standardizes the final-answer critic step as a Phase 2 agent.

New backend modules:

```text
blackboard_day5_7\app\agents\critic_agent.py
blackboard_day5_7\app\critic\rules.py
blackboard_day5_7\app\critic\__init__.py
```

Updated W14 behavior:

- `TechAgent` and `BehavioralAgent` now emit `ANSWER_DRAFT` and `ERROR` only.
- `CriticAgent` consumes `ANSWER_DRAFT`.
- `CriticAgent` emits `CRITIQUE_NOTE`, then `ANSWER_APPROVED` or `ANSWER_REJECTED`, then `ANSWER_FINAL`.
- `ANSWER_FINAL` in the default Phase 2 chain now comes from `CriticAgent`.
- Rejected drafts still produce a safe degraded `ANSWER_FINAL`.
- Factory registration is now `PerceptionAgent`, `ResumeAgent`, `RAGAgent`, `TechAgent`, `BehavioralAgent`, `CriticAgent`.
- The existing Phase 1 critic logic remains inside the Phase 1 pipeline for compatibility, but the standard Phase 2 event-chain final gate is now `CriticAgent`.
- Ignored input still does not trigger ResumeAgent, RAGAgent, answer agents, or CriticAgent.
- Phase 2 execution errors still fall back to Phase 1.

W14 validation:

```text
conda run -n chuangxin python -m py_compile app\critic\rules.py app\agents\critic_agent.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\orchestrator\factory.py app\orchestrator\orchestrator.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py tests\test_resume_agent.py tests\test_phase2_context_flow.py tests\test_local_rag.py tests\test_rag_agent.py tests\test_phase2_rag_flow.py tests\test_critic_rules.py tests\test_critic_agent.py tests\test_phase2_critic_flow.py -q
```

Result: 81 tests passed.

## W15 Status

W15 turns Phase 2 into a reproducible acceptance build.

New validation assets:

```text
blackboard_day5_7\evals\phase2_questions.json
blackboard_day5_7\evals\run_phase2_eval.py
blackboard_day5_7\scripts\smoke_phase2.py
blackboard_day5_7\scripts\check_phase2.py
docs\PHASE2_W15_NOTES.md
docs\PHASE2_ACCEPTANCE.md
docs\RUNBOOK_PHASE2.md
```

Updated W15 behavior:

- The eval set covers 50 cases across technical, algorithm, system design, behavioral, resume follow-up, and ignored input.
- `smoke_phase2.py` checks `/config/status`, `/ask`, ignored input, and `/blackboard` with `USE_OLLAMA=false`.
- `check_phase2.py` runs py_compile, pytest, smoke, and eval in sequence.
- `start-all.bat` still uses `%~dp0`, `blackboard_day5_7`, `interview-assistant-stage4-whisper`, `chuangxin`, and `orchestrator_v0:app`.
- `start-all.bat` no longer starts uvicorn with `--reload`, which is steadier for demo startup.
- Phase 2 still does not add Redis, PostgreSQL, pgvector, Web RAG, new agents, frontend UI changes, signing, or installers.

W15 validation:

```text
conda run -n chuangxin python -m py_compile app\blackboard\events.py app\blackboard\bus.py app\agents\base.py app\agents\perception_agent.py app\agents\resume_agent.py app\agents\rag_agent.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\agents\critic_agent.py app\orchestrator\registry.py app\orchestrator\orchestrator.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py app\resume\context_loader.py app\rag\local_rag.py app\critic\rules.py orchestrator_v0.py scripts\smoke_phase2.py scripts\check_phase2.py evals\run_phase2_eval.py
conda run -n chuangxin python -m pytest tests -q
conda run -n chuangxin python scripts\smoke_phase2.py
conda run -n chuangxin python evals\run_phase2_eval.py
conda run -n chuangxin python scripts\check_phase2.py
```

Result:

```text
pytest: 81 passed
smoke_phase2.py: passed
run_phase2_eval.py: 250/250, accuracy=1.0
check_phase2.py: passed
```

Frontend build check:

```text
npm run build
```

Result is recorded in `PHASE2_W15_NOTES.md`.
