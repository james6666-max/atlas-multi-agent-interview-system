# Phase 2 W10 Notes

## Scope

W10 adds `PerceptionAgent` in front of `MainAgent`.

It decides whether an input should trigger an answer and classifies complete interview questions.

W10 does not split Tech Agent, Behavioral Agent, Resume Agent, RAG Agent, or Critic Agent.

## Input Events

`PerceptionAgent` subscribes to:

```text
MANUAL_INPUT
TRANSCRIPT_FINAL
OCR_TEXT
```

It extracts text from:

```text
question
text
input
transcript
ocr_text
```

## Output Events

If the input should be answered, `PerceptionAgent` emits:

```text
QUESTION_DETECTED
```

If the input should be skipped, it emits nothing.

## Classification

The initial classifier is rule-based and does not call Ollama or any remote service.

Supported categories:

```text
technical
algorithm
system_design
behavioral
resume_followup
chitchat
unknown
```

`should_answer=True` is used for complete interview questions in the technical, algorithm, system design, behavioral, and resume-followup categories.

`should_answer=False` is used for empty input, short filler, chitchat, incomplete phrases, and user microphone speech that is not manual input.

## Skip Rules

Examples that are skipped:

```text
你好
hello, nice weather.
如果让你
我想问一下这个
```

For non-manual input, these payloads are skipped:

```text
speaker=user
channel=mic
```

Manual input remains eligible for answering because it is the demo and debugging entry.

## Current `/ask` Flow

```text
/ask
-> MANUAL_INPUT
-> PerceptionAgent
-> QUESTION_DETECTED, only if complete interview question
-> MainAgent
-> Phase 1 pipeline adapter
-> ANSWER_DRAFT / CRITIQUE_NOTE / ANSWER_FINAL
-> AskResponse
```

If no `QUESTION_DETECTED` is produced, `/ask` returns a compatible ignored response:

```text
question_type=ignored
selected_agent=Perception
answer=""
```

Ignored input does not fall back to Phase 1. This preserves the Perception gate.

If Phase 2 itself raises an exception, `/ask` still falls back to Phase 1.

## Why No LLM Classifier Yet

W10 is a lightweight gate in front of the current MVP. A rule-based classifier keeps latency low, avoids model cost, and prevents the Perception layer from becoming another source of Ollama failures.

LLM-assisted classification can be considered later only if local rules are not accurate enough.

## Why Tech / Behavioral Are Not Split Yet

W10 only creates the gate and classification event. Splitting answer generation belongs to W11, after this event flow is stable.

## Validation

Commands run:

```powershell
conda run -n chuangxin python -m py_compile app\agents\perception_agent.py app\agents\main_agent.py app\orchestrator\factory.py app\orchestrator\orchestrator.py orchestrator_v0.py
conda run -n chuangxin python -m pytest tests\test_blackboard_bus.py tests\test_agent_base.py tests\test_main_agent_adapter.py tests\test_phase2_ask_flow.py tests\test_perception_agent.py tests\test_phase2_perception_flow.py -q
```

Result:

```text
26 passed
```

Smoke test used `USE_OLLAMA=false`.

Complete question:

```text
What is RESTful API?
```

Returned a normal answer with `question_type=Technical/Algorithm` and `selected_agent=Tech/Code`.

Chitchat:

```text
hello, nice weather.
```

Returned `question_type=ignored`, `selected_agent=Perception`, and an empty answer.
