import type { Phase2AskResponse } from "../../types/phase2"
import { useI18n } from "../../i18n/LanguageProvider"

interface ContextRagPanelProps {
  response: Phase2AskResponse | null
}

const sourceLabels: Record<string, string> = {
  resume: "Resume",
  jd: "Job Description",
  knowledge: "Knowledge",
  "knowledge.txt": "Local knowledge.txt",
  session_replay: "Session replay"
}

function labelSources(value: unknown) {
  if (!Array.isArray(value) || value.length === 0) return []
  return value.map((source) => sourceLabels[String(source)] || String(source))
}

export function ContextRagPanel({ response }: ContextRagPanelProps) {
  const { t } = useI18n()
  const ignored = response?.question_type === "ignored"
  const contextSources = labelSources(response?.context_sources)
  const ragSources = labelSources(response?.rag_sources)
  const dash = "—"

  return (
    <section className="phase2-card">
      <div className="phase2-section-heading">
        <div>
          <div className="phase2-muted-label">{t("context.eyebrow")}</div>
          <h3>{t("context.title")}</h3>
        </div>
      </div>

      <div className="phase2-context-grid">
        <div>
          <span>{t("context.contextUsed")}</span>
          <strong>{ignored ? dash : response?.context_used ? "✓" : "—"}</strong>
          <p>
            {ignored
              ? dash
              : response?.context_used
                ? contextSources.join(", ") || t("context.sources")
                : dash}
          </p>
        </div>
        <div>
          <span>{t("context.ragUsed")}</span>
          <strong>{ignored ? dash : response?.rag_used ? "✓" : "—"}</strong>
          <p>
            {ignored
              ? dash
              : response?.rag_used
                ? ragSources.join(", ") || t("context.sources")
                : dash}
          </p>
        </div>
      </div>
    </section>
  )
}
