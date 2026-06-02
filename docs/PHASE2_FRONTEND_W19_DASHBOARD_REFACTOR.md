# Phase2 W19 Dashboard Refactor

## Scope

W19 focused on frontend-only internal refactoring. It did not change the backend Agent chain, backend API semantics, request bodies, or Electron startup flow.

The Phase2 backend chain remains:

```text
Perception -> Resume -> RAG -> Tech/Behavioral Draft -> Critic -> Final
```

## AtlasDashboardPage Refactor

`AtlasDashboardPage.tsx` was reduced from about 1122 lines to 348 lines.

It now primarily:

- owns the dashboard composition
- wires hooks into page-level components
- manages app-level settings/toast state
- keeps the existing three-column dashboard layout

## Added Hooks

```text
src/hooks/useBlackboard.ts
src/hooks/useImageAsk.ts
src/hooks/useAudioAsk.ts
src/hooks/useReportActions.ts
```

Responsibilities:

- `useBlackboard`: `/blackboard` refresh, `/config/status`, backend/config/LLM/resume/JD/knowledge/RAG status derivation
- `useImageAsk`: screenshot/file image flow and `/ask_image_file` submission
- `useAudioAsk`: MediaRecorder flow and `/ask_audio` submission
- `useReportActions`: mock interview, report generation/export, clear history, reset session

## Added Dashboard Components

```text
src/components/Dashboard/DashboardHeader.tsx
src/components/Dashboard/DashboardMainGrid.tsx
```

These keep dashboard layout code out of `AtlasDashboardPage.tsx` without changing visual behavior.

## API Semantics

No API file split was needed. `src/api/client.ts` is still small and remains unchanged.

Request semantics preserved:

- `/ask`
- `/ask_image_file`
- `/ask_audio`
- `/blackboard`
- `/blackboard/clear_history`
- `/blackboard/reset_session`
- `/mock/start`
- `/mock/answer`
- `/report/session`
- `/report/export_markdown`

## Build Result

`npm run build` passed.

Renderer chunks remain split through the existing lazy page structure. The dashboard chunk is still around 70 kB because this refactor moved code into hooks/components without deleting dashboard functionality.

The Electron main bundle remains around 1 MB; this is outside the W19 frontend dashboard scope.

## Backend Regression

Backend smoke/eval/check should remain unchanged because W19 did not modify backend files.

## Remaining Issues

- Further bundle optimization would likely need Electron main-process dependency analysis.
- Agent Trace is still inferred from response fields, not a real trace API.
- `AtlasDashboardPage.tsx` can be reduced further if the remaining app-level settings/toast provider wiring is moved into a dedicated shell component.
