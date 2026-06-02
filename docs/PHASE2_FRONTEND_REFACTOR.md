# Phase 2 W17 Frontend Componentization

## Scope

W17 refactored the frontend demo surface only. The backend Agent chain and API semantics were not changed.

Backend chain remains:

```text
Perception -> Resume -> RAG -> Tech/Behavioral Draft -> Critic -> Final
```

## App.tsx Changes

`src/App.tsx` now delegates the Phase2 manual demo to `Phase2ManualDemo`.

The old W16 manual demo state and inline Phase2 panels were removed from `App.tsx`, making the entry file thinner while preserving the existing OCR, voice, blackboard, and report surfaces.

## New Hooks

- `src/hooks/useAskPhase2.ts`
  - owns the manual question
  - calls `/ask` through the existing API client
  - tracks loading, error, response, and latency
  - exposes `setQuestion`, `submit`, and `clear`

- `src/hooks/useBackendStatus.ts`
  - calls `/config/status`
  - reports online/offline, model, Ollama mode, and context flags
  - handles missing fields and offline errors safely

## Components

- `AppShell`
- `SectionCard`
- `StatusCards`
- `QuestionInput`
- `ExampleQuestions`
- `AnswerPanel`
- `CriticPanel`
- `ContextRagPanel`
- `AgentTrace`
- `RawJsonPanel`
- `Phase2ManualDemo`

## Demo Enhancements

- Agent Trace now highlights done, running, skipped, and idle states.
- CriticPanel shows approved state, score, issues, suggestions, and risk flags.
- ContextRagPanel maps source ids to readable labels such as `Resume`, `Job Description`, `Local knowledge.txt`, and `Session replay`.
- AnswerPanel shows selected agent, question type, latency, and a Copy Answer button.
- RawJsonPanel is collapsed by default and expands to show the full response.
- Example questions now cover Technical, Algorithm, Behavioral, Ignored, and Chinese demo inputs.

## API Compatibility

The `/ask` request body remains:

```json
{
  "question": "...",
  "language": "Unknown",
  "source": "manual_input"
}
```

The `/config/status` request is unchanged.

## Validation

Run from the frontend directory:

```powershell
npm run build
```

Run from the backend directory:

```powershell
conda run -n chuangxin python scripts\smoke_phase2.py
conda run -n chuangxin python evals\run_phase2_eval.py
```

## Remaining Issues

- Vite still reports a large chunk warning.
- `App.tsx` still contains legacy OCR, voice, blackboard, mock interview, and reporting UI; those can be split in a later frontend-only pass.
- Agent Trace is inferred from response fields. A future backend trace endpoint could make it fully authoritative.
