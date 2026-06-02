# Phase 2 W18 Frontend Page Refactor

## Scope

W18 only changed the Electron/React frontend presentation layer and documentation. The backend Phase2 Agent chain and API semantics were not changed.

Backend chain remains:

```text
Perception -> Resume -> RAG -> Tech/Behavioral Draft -> Critic -> Final
```

## App.tsx Responsibility

`interview-assistant-stage4-whisper/src/App.tsx` is now a thin lazy entrypoint. It only imports React `lazy` / `Suspense`, lazy-loads `AtlasDashboardPage`, and renders a loading fallback.

Line count changed from approximately 1942 lines after W17 to 13 lines after W18.

## New Page Components

- `src/pages/AtlasDashboardPage.tsx`
  - Owns the existing desktop dashboard state and legacy handlers.
  - Keeps current OCR, voice, blackboard, mock interview, report, settings, and Phase2 demo behavior.

- `src/pages/BlackboardPage.tsx`
  - Renders recent blackboard history and critic summary.

- `src/pages/InputWorkspacePage.tsx`
  - Renders LLM/resume/JD/knowledge/RAG status and the screenshot, voice, and manual input tabs.

- `src/pages/Phase2ManualDemoPage.tsx`
  - Thin page wrapper around the W17 `Phase2ManualDemo` component.

- `src/pages/ActionCenterPage.tsx`
  - Renders backend status, config status, quick actions, mock interview controls, and report controls.

- `src/pages/ReportPage.tsx`
  - Renders the generated report and exported Markdown.

## Lazy Import

`App.tsx` now uses:

```tsx
const AtlasDashboardPage = lazy(() => import("./pages/AtlasDashboardPage"))
```

The Suspense fallback is:

```tsx
<div className="loading-panel">Loading page...</div>
```

No React Router was introduced.

## API And Hooks

The API client was not split in W18 because `src/api/client.ts` is still small and stable.

No new OCR/voice/blackboard hooks were added. The state and handlers stayed in `AtlasDashboardPage` to avoid changing screenshot, recorder, or blackboard side effects during a page-level refactor.

## Vite Chunking

The existing Vite manual chunks were left unchanged. Page-level lazy loading created a separate `AtlasDashboardPage` chunk, but the large chunk warning still remains because the main bundle still includes existing large vendor/runtime assets.

Build output highlights:

- `AtlasDashboardPage-*.js`: about 70.50 kB
- large renderer chunk: about 1,626.25 kB
- large Electron main chunk: about 1,012.56 kB

## Validation

Frontend:

```powershell
npm run build
```

Result: passed. Vite large chunk warning remains.

Backend:

```powershell
conda run -n chuangxin python scripts\smoke_phase2.py
conda run -n chuangxin python evals\run_phase2_eval.py
conda run -n chuangxin python scripts\check_phase2.py
```

Results:

- smoke: passed
- eval: 250/250, accuracy 1.0
- check: 81 tests passed, Phase2 check passed

## Remaining Issues

- `AtlasDashboardPage.tsx` still contains legacy OCR/voice/mock/report state and can be reduced in a future W19 by extracting dedicated hooks.
- Vite large chunk warning remains. A future pass can inspect syntax-highlighter and Electron main-process dependencies before changing chunk strategy.
- Agent Trace is still inferred from response fields; no real trace API was added.
