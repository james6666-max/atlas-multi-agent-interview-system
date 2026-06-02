# Phase 2 W12 Notes

## Scope

W12 adds a lightweight `ResumeAgent` and `CONTEXT_LOADED` event.

It does not add Redis, PostgreSQL, pgvector, Web RAG, document upload, or frontend UI changes.

## ResumeAgent

`ResumeAgent` lives at:

```text
blackboard_day5_7\app\agents\resume_agent.py
```

It subscribes to:

```text
QUESTION_DETECTED
```

It emits:

```text
CONTEXT_LOADED
ERROR
```

On normal input, it loads the local text context and publishes a context event before TechAgent or BehavioralAgent answers.

## Context Loader

The context loader lives at:

```text
blackboard_day5_7\app\resume\context_loader.py
```

It reads:

```text
blackboard_day5_7\resume.txt
blackboard_day5_7\jd.txt
blackboard_day5_7\knowledge.txt
```

Missing files return empty strings instead of crashing.

## CONTEXT_LOADED Payload

The event payload includes:

```text
question
question_type
resume_summary
jd_summary
knowledge_summary
matched_snippets
constraints
has_resume
has_jd
has_knowledge
```

`matched_snippets` contains source-tagged snippets from resume, JD, and knowledge files. Matching is rule-based and uses simple keyword extraction, not embeddings or LLM calls.

## Agent Usage

`TechAgent` reads the latest `CONTEXT_LOADED` event from the bus and passes it into the Phase 1 pipeline adapter with:

```text
agent_hint=tech
```

`BehavioralAgent` reads the same context and passes it with:

```text
agent_hint=behavioral
```

Behavioral guidance includes:

```text
Use only existing resume/JD/knowledge facts.
If facts are missing, describe how to organize the answer without inventing details.
Prefer STAR structure.
```

## Factory Registration

The default Phase 2 runtime now registers:

```text
PerceptionAgent
ResumeAgent
TechAgent
BehavioralAgent
```

`MainAgent` remains as a legacy adapter, but it is not part of the default runtime.

## Current `/ask` Flow

```text
/ask
-> MANUAL_INPUT
-> PerceptionAgent
-> QUESTION_DETECTED
-> ResumeAgent
-> CONTEXT_LOADED
-> TechAgent or BehavioralAgent
-> Phase 1 pipeline adapter
-> ANSWER_DRAFT / CRITIQUE_NOTE / ANSWER_FINAL
-> AskResponse
```

Each `/ask` request uses a unique Phase 2 session id so answer agents do not read stale context from earlier requests.

`AskResponse` exposes:

```text
context_used
context_sources
```

It does not return the full loaded resume/JD/knowledge context.

## Branch Semantics

Ignored:

```text
No QUESTION_DETECTED
-> ResumeAgent is not triggered
-> answer agents are not triggered
-> no Phase 1 fallback
```

ResumeAgent error:

```text
ResumeAgent emits ERROR
-> answer agents can still continue with empty context
-> no automatic fallback unless the main Phase 2 path raises
```

Exception:

```text
Phase 2 execution error
-> fallback to Phase 1
```

## Validation

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\agents\resume_agent.py app\resume\context_loader.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
D:\miniconda\envs\chuangxin\python.exe -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py tests\test_resume_agent.py tests\test_phase2_context_flow.py -q
```

Result:

```text
50 passed
```

`conda run` hit a Windows GBK output encoding issue while printing pytest output, so pytest was rerun through the conda environment's Python executable directly.

## W13 Next

W13 can add a lightweight RAGAgent for local knowledge and session replay. It should not introduce Redis, PostgreSQL, pgvector, or web search without explicit approval.
