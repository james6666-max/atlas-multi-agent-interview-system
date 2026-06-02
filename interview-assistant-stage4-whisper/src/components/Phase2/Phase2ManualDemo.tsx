import { useEffect, useRef } from "react"
import { useAskPhase2 } from "../../hooks/useAskPhase2"
import { useBackendStatus } from "../../hooks/useBackendStatus"
import { useI18n } from "../../i18n/LanguageProvider"
import { AgentTrace } from "./AgentTrace"
import { AnswerPanel } from "./AnswerPanel"
import { AppShell } from "./AppShell"
import { ContextRagPanel } from "./ContextRagPanel"
import { CriticPanel } from "./CriticPanel"
import { ExampleQuestions } from "./ExampleQuestions"
import { QuestionInput } from "./QuestionInput"
import { RawJsonPanel } from "./RawJsonPanel"
import { SectionCard } from "./SectionCard"
import { StatusCards } from "./StatusCards"

interface Phase2ManualDemoProps {
  onCompleted?: () => void
}

export function Phase2ManualDemo({ onCompleted }: Phase2ManualDemoProps) {
  const { t } = useI18n()
  const backend = useBackendStatus()
  const ask = useAskPhase2()

  const submit = async () => {
    await ask.submit()
    onCompleted?.()
  }

  // Hotkey-driven prefill + auto-submit (Ctrl+Shift+V clipboard ask, M3).
  const askRef = useRef(ask)
  askRef.current = ask
  const onCompletedRef = useRef(onCompleted)
  onCompletedRef.current = onCompleted
  useEffect(() => {
    const handler = (event: Event) => {
      const text = (event as CustomEvent<{ text?: string }>).detail?.text
      if (typeof text === "string" && text.trim()) {
        askRef.current.setQuestion(text)
        void askRef.current.submit(text).then(() => onCompletedRef.current?.())
      }
    }
    window.addEventListener("atlas-prefill-ask", handler)
    return () => window.removeEventListener("atlas-prefill-ask", handler)
  }, [])

  return (
    <AppShell>
      <StatusCards backend={backend} />
      <SectionCard eyebrow={t("manual.eyebrow")} title={t("manual.title")}>
        <ExampleQuestions onPick={ask.setQuestion} disabled={ask.loading} />
        <QuestionInput
          value={ask.question}
          loading={ask.loading}
          error={ask.error}
          onChange={ask.setQuestion}
          onSubmit={submit}
          onClear={ask.clear}
        />
      </SectionCard>
      <AgentTrace response={ask.response} loading={ask.loading} trace={ask.trace} />
      <AnswerPanel
        response={ask.response}
        loading={ask.loading}
        streaming={ask.streaming}
        latencyMs={ask.latencyMs}
        firstTokenMs={ask.firstTokenMs}
      />
      <CriticPanel critic={ask.response?.critic} questionType={ask.response?.question_type} />
      <ContextRagPanel response={ask.response} />
      <RawJsonPanel data={ask.response} />
    </AppShell>
  )
}
