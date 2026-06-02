# Phase 2 W13 Notes

## Scope

W13 adds a lightweight local `RAGAgent`.

It does not add web search, Tavily, Redis, PostgreSQL, pgvector, embeddings, document upload, or frontend UI changes.

## RAGAgent

`RAGAgent` lives at:

```text
blackboard_day5_7\app\agents\rag_agent.py
```

It subscribes to:

```text
QUESTION_DETECTED
```

It emits:

```text
RAG_CHUNK
ERROR
```

It never emits final answers. TechAgent and BehavioralAgent keep answer ownership.

## RAG_CHUNK Payload

The event payload includes:

```text
question
question_type
chunks
sources
has_rag
retrieval_mode
```

`retrieval_mode` is currently:

```text
local_keyword
```

If no useful chunks are found, RAGAgent still emits `RAG_CHUNK` with:

```text
chunks=[]
sources=[]
has_rag=false
```

## Local Retrieval

The retrieval helpers live at:

```text
blackboard_day5_7\app\rag\local_rag.py
```

The strategy is deliberately simple:

- load `blackboard_day5_7\knowledge.txt`
- extract English and Chinese query terms
- split text into short passages
- score passages by keyword hits
- keep top local chunks
- search current-session blackboard replay for related previous events

Each chunk is capped at about 600 characters.

## Session Replay

RAGAgent reads:

```text
self.bus.replay(session_id)
```

It can use relevant `ANSWER_FINAL`, `ANSWER_DRAFT`, `CONTEXT_LOADED`, `RAG_CHUNK`, and `QUESTION_DETECTED` events as local session context.

## Agent Usage

`TechAgent` reads:

```text
bus.latest(session_id, EventType.RAG_CHUNK)
```

and passes it to the Phase 1 pipeline adapter as `rag`.

`BehavioralAgent` also reads RAG, but keeps this priority rule:

```text
Resume/JD facts have higher priority than RAG chunks for experience-specific claims.
Do not invent candidate experience from RAG chunks.
Prefer STAR structure.
```

## Factory Registration

The default Phase 2 runtime now registers:

```text
PerceptionAgent
ResumeAgent
RAGAgent
TechAgent
BehavioralAgent
```

`MainAgent` remains as a legacy adapter and is not part of the default runtime.

## Current `/ask` Flow

```text
/ask
-> MANUAL_INPUT
-> PerceptionAgent
-> QUESTION_DETECTED
-> ResumeAgent
-> CONTEXT_LOADED
-> RAGAgent
-> RAG_CHUNK
-> TechAgent or BehavioralAgent
-> Phase 1 pipeline adapter
-> ANSWER_DRAFT / CRITIQUE_NOTE / ANSWER_FINAL
-> AskResponse
```

`AskResponse` exposes:

```text
context_used
context_sources
rag_used
rag_sources
```

It does not return full RAG chunks or full resume/JD/knowledge context.

## Branch Semantics

Ignored:

```text
No QUESTION_DETECTED
-> ResumeAgent is not triggered
-> RAGAgent is not triggered
-> answer agents are not triggered
-> no Phase 1 fallback
```

Empty RAG:

```text
RAG_CHUNK has has_rag=false
-> answer agents still run
-> rag_used=false
```

RAGAgent error:

```text
RAGAgent emits ERROR
-> answer agents can still continue without RAG
-> no automatic fallback unless the main Phase 2 path raises before ANSWER_FINAL
```

Exception:

```text
Phase 2 execution error
-> fallback to Phase 1
```

## Validation

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\rag\local_rag.py app\agents\rag_agent.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py tests\test_resume_agent.py tests\test_phase2_context_flow.py tests\test_local_rag.py tests\test_rag_agent.py tests\test_phase2_rag_flow.py -q
```

Result:

```text
65 passed
```

Smoke used `USE_OLLAMA=false`.

Technical:

```text
What is RESTful API?
selected_agent=Tech/Code
answer non-empty
context_used=true
rag_used=true
rag_sources=session_replay,knowledge.txt
```

Behavioral:

```text
Tell me about a project you are most proud of.
selected_agent=Behavioral
answer non-empty
context_used=true
rag_used=true
rag_sources=session_replay,knowledge.txt
```

Chitchat:

```text
hello, nice weather.
question_type=ignored
selected_agent=Perception
answer=""
context_used=false
rag_used=false
```

## W14 Next

W14 should extract and harden CriticAgent so final answers pass through a standard critic event step before returning to the API.
