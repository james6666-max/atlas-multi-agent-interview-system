# Phase 2 W11 Notes

## Scope

W11 splits the answer side into two specialized agents:

```text
TechAgent
BehavioralAgent
```

It does not change OCR, STT, frontend UI, ResumeAgent, RAGAgent, Redis, or PostgreSQL.

## Agents

`TechAgent` handles:

```text
technical
algorithm
system_design
```

`BehavioralAgent` handles:

```text
behavioral
resume_followup
```

Both agents subscribe to:

```text
QUESTION_DETECTED
```

They filter by `question_type` and return `[]` when the event belongs to the other agent.

## MainAgent Status

`MainAgent` is still present:

```text
blackboard_day5_7\app\agents\main_agent.py
```

It is kept as a legacy adapter, but it is no longer registered in the default Phase 2 runtime.

## Factory Registration

The default Phase 2 runtime now registers:

```text
PerceptionAgent
TechAgent
BehavioralAgent
```

## Current `/ask` Flow

```text
/ask
-> MANUAL_INPUT
-> PerceptionAgent
-> QUESTION_DETECTED
-> TechAgent or BehavioralAgent
-> Phase 1 pipeline adapter
-> ANSWER_DRAFT / CRITIQUE_NOTE / ANSWER_FINAL
-> AskResponse
```

## Branch Semantics

Ignored:

```text
No QUESTION_DETECTED
-> question_type=ignored
-> selected_agent=Perception
-> answer=""
-> no Phase 1 fallback
```

Detected but unhandled:

```text
QUESTION_DETECTED exists, but no answer agent emits ANSWER_FINAL
-> compatible empty AskResponse
-> no 500
-> no Phase 1 fallback
```

Exception:

```text
Phase 2 execution error
-> fallback to Phase 1
```

## Phase 1 Adapter

`phase1_pipeline.run_phase1_answer_pipeline` now accepts optional hints:

```text
agent_hint
question_type
```

`TechAgent` passes:

```text
agent_hint=tech
```

`BehavioralAgent` passes:

```text
agent_hint=behavioral
```

The existing Phase 1 generation, fallback, context loading, Critic, and blackboard writes are still reused.

## Validation

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\agents\tech_agent.py app\agents\behavioral_agent.py app\agents\main_agent.py app\orchestrator\factory.py app\adapters\phase1_pipeline.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py -q
```

Result:

```text
39 passed
```

Smoke used `USE_OLLAMA=false`.

Technical:

```text
What is RESTful API?
selected_agent=Tech/Code
answer non-empty
```

Behavioral:

```text
Tell me about a time you solved a difficult technical problem.
selected_agent=Behavioral
answer non-empty
```

Chitchat:

```text
hello, nice weather.
question_type=ignored
selected_agent=Perception
answer=""
```

## W12 Next

W12 should add `ResumeAgent` to structure resume, JD, and project context before BehavioralAgent relies on them more heavily.
