import { useState } from "react"
import type { Phase2AskResponse } from "../../types/phase2"
import { useI18n } from "../../i18n/LanguageProvider"
import { Markdown } from "./Markdown"

interface AnswerPanelProps {
  response: Phase2AskResponse | null
  loading?: boolean
  streaming?: boolean
  latencyMs?: number | null
  firstTokenMs?: number | null
}

function getAgentTone(result: Phase2AskResponse | null) {
  const questionType = String(result?.question_type ?? "").toLowerCase()
  const selectedAgent = String(result?.selected_agent ?? "").toLowerCase()

  if (questionType === "ignored") return "ignored"
  if (selectedAgent.includes("behavioral")) return "behavioral"
  if (selectedAgent.includes("tech") || selectedAgent.includes("code")) return "tech"
  return "neutral"
}

export function AnswerPanel({
  response,
  loading = false,
  streaming = false,
  latencyMs = null,
  firstTokenMs = null,
}: AnswerPanelProps) {
  const { t } = useI18n()
  const answer = typeof response?.answer === "string" ? response.answer : ""
  const tone = getAgentTone(response)
  const provider = (response?.llm?.provider as string) || ""
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle")

  const copyAnswer = async () => {
    if (!answer) return
    try {
      await navigator.clipboard.writeText(answer)
      setCopyState("copied")
      window.setTimeout(() => setCopyState("idle"), 1600)
    } catch (err) {
      console.warn("Copy answer failed:", err)
      setCopyState("failed")
      window.setTimeout(() => setCopyState("idle"), 1600)
    }
  }

  return (
    <section className="phase2-card phase2-answer-panel">
      <div className="phase2-section-heading">
        <div>
          <div className="phase2-muted-label">{t("answer.title")}</div>
          <h3>{t("manual.title")}</h3>
        </div>
        <div className="phase2-badge-row">
          <span className={`phase2-badge phase2-badge-${tone}`}>
            {response?.selected_agent || t("answer.agent")}
          </span>
          <span className={`phase2-badge phase2-badge-${tone}`}>
            {response?.question_type || "idle"}
          </span>
          {provider && <span className="phase2-badge">{provider}</span>}
          {firstTokenMs !== null && <span className="phase2-badge">{t("answer.firstToken")} {firstTokenMs}ms</span>}
          {latencyMs !== null && <span className="phase2-badge">{t("answer.total")} {latencyMs}ms</span>}
        </div>
      </div>

      <div className="phase2-answer-body">
        {answer ? (
          <>
            <Markdown>{answer}</Markdown>
            {streaming && <span className="phase2-stream-cursor">▌</span>}
          </>
        ) : streaming || loading ? (
          t("answer.streaming")
        ) : (
          t("answer.empty")
        )}
      </div>
      <button type="button" className="phase2-copy-button" onClick={copyAnswer} disabled={!answer || streaming}>
        {copyState === "copied" ? t("common.copied") : copyState === "failed" ? "✕" : t("common.copy")}
      </button>
    </section>
  )
}
