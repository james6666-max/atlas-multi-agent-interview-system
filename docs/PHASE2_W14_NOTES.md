# Phase 2 W14 Notes

## Scope

W14 adds `CriticAgent` as the standard Phase 2 final-answer gate.

It does not remove the old Phase 1 critic logic, call a new LLM provider, add Redis/PostgreSQL/pgvector, build a web backend, change frontend UI, or do packaging/signing.

## CriticAgent

`CriticAgent` lives at:

```text
blackboard_day5_7\app\agents\critic_agent.py
```

It subscribes to:

```text
ANSWER_DRAFT
```

It emits:

```text
CRITIQUE_NOTE
ANSWER_APPROVED
ANSWER_REJECTED
ANSWER_FINAL
ERROR
```

## Critic Rules

Rule helpers live at:

```text
blackboard_day5_7\app\critic\rules.py
```

The first version checks:

- empty or too-short answers
- AI-assistant framing such as `As an AI` or `作为一个AI`
- possible PII or secrets such as email, phone numbers, `sk-...`, `password`, `token`, or `secret`
- answer length
- unsupported resume-experience claims for behavioral or resume-followup questions
- missing complexity for algorithm answers
- missing trade-off or bottleneck discussion for system design answers
- missing example or steps for technical answers

No LLM is called by CriticAgent.

## Event Payloads

`CRITIQUE_NOTE` includes:

```text
question
question_type
selected_agent
approved
score
issues
suggestions
risk_flags
```

`ANSWER_APPROVED` includes the final answer, critic result, raw result, context flags, and RAG flags.

`ANSWER_REJECTED` includes:

```text
question
question_type
selected_agent
rejected_answer
safe_answer
critic
raw_result
```

`ANSWER_FINAL` includes:

```text
question
question_type
selected_agent
answer
critic
raw_result
context_used
context_sources
rag_used
rag_sources
```

## Agent Responsibilities

`TechAgent` now emits only:

```text
ANSWER_DRAFT
ERROR
```

`BehavioralAgent` now emits only:

```text
ANSWER_DRAFT
ERROR
```

The final `ANSWER_FINAL` in the default Phase 2 path comes from `CriticAgent`.

Behavioral guidance is still preserved:

```text
Use only existing resume/JD/knowledge facts.
If facts are missing, describe how to organize the answer without inventing details.
Prefer STAR.
Resume/JD facts have higher priority than RAG chunks for experience-specific claims.
```

## Factory Registration

The default Phase 2 runtime now registers:

```text
PerceptionAgent
ResumeAgent
RAGAgent
TechAgent
BehavioralAgent
CriticAgent
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
-> ANSWER_DRAFT
-> CriticAgent
-> CRITIQUE_NOTE
-> ANSWER_APPROVED or ANSWER_REJECTED
-> ANSWER_FINAL
-> AskResponse
```

`AskResponse` continues to expose:

```text
context_used
context_sources
rag_used
rag_sources
```

It also now exposes critic fields such as:

```text
approved
score
issues
suggestions
risk_flags
```

## Branch Semantics

Ignored:

```text
No QUESTION_DETECTED
-> no ResumeAgent
-> no RAGAgent
-> no answer agent
-> no CriticAgent
-> no Phase 1 fallback
```

Detected but unhandled:

```text
QUESTION_DETECTED exists, but no answer draft exists
-> no CriticAgent
-> compatible empty AskResponse
-> no 500
-> no Phase 1 fallback
```

Rejected draft:

```text
CriticAgent emits ANSWER_REJECTED
-> CriticAgent still emits safe ANSWER_FINAL
```

Exception:

```text
Phase 2 execution error
-> fallback to Phase 1
```

## Validation

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\critic\rules.py app\agents\critic_agent.py app\agents\tech_agent.py app\agents\behavioral_agent.py app\orchestrator\factory.py app\orchestrator\orchestrator.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py tests\test_tech_agent.py tests\test_behavioral_agent.py tests\test_phase2_routing_flow.py tests\test_resume_agent.py tests\test_phase2_context_flow.py tests\test_local_rag.py tests\test_rag_agent.py tests\test_phase2_rag_flow.py tests\test_critic_rules.py tests\test_critic_agent.py tests\test_phase2_critic_flow.py -q
```

Result:

```text
81 passed
```

Smoke used `USE_OLLAMA=false`.

Technical:

```text
What is RESTful API?
selected_agent=Tech/Code
answer non-empty
critic.approved=true
critic.score=100
context_used=true
rag_used=true
```

Behavioral:

```text
Tell me about a project you are most proud of.
selected_agent=Behavioral
answer non-empty
critic.approved=true
critic.score=100
context_used=true
rag_used=true
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

## W15 Next

W15 should focus on evaluation cases, launch reliability, smoke-test scripts, documentation hardening, and packaging readiness.
