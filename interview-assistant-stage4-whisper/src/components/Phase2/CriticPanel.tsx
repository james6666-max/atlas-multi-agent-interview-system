import type { CriticResult } from "../../types/phase2"
import { useI18n } from "../../i18n/LanguageProvider"
import { Markdown } from "./Markdown"

interface CriticPanelProps {
  critic?: CriticResult
  questionType?: string
}

function normalizeList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : []
}

function getCriticScore(critic?: CriticResult) {
  if (!critic) return "unknown"
  if (typeof critic.score === "number") return String(critic.score)
  if (typeof critic.final_score === "number") return String(critic.final_score)
  return "unknown"
}

export function CriticPanel({ critic, questionType }: CriticPanelProps) {
  const { t } = useI18n()
  const issues = normalizeList(critic?.issues).concat(normalizeList(critic?.specific_issues))
  const suggestions = normalizeList(critic?.suggestions)
  const riskFlags = normalizeList(critic?.risk_flags)
  const approved =
    typeof critic?.approved === "boolean"
      ? critic.approved
      : questionType === "ignored"
        ? false
        : undefined

  return (
    <section className="phase2-card">
      <div className="phase2-section-heading">
        <div>
          <div className="phase2-muted-label">{t("critic.eyebrow")}</div>
          <h3>{t("critic.title")}</h3>
        </div>
        <span className={`phase2-badge ${approved ? "phase2-badge-approved" : approved === false ? "phase2-badge-error" : "phase2-badge-neutral"}`}>
          {approved === undefined ? t("critic.pending") : approved ? t("critic.approved") : t("critic.notApproved")}
        </span>
      </div>

      {!critic && <p className="phase2-empty-text">{t("critic.empty")}</p>}

      <div className="phase2-metrics">
        <div>
          <span>{t("critic.score")}</span>
          <strong>{getCriticScore(critic)}</strong>
        </div>
        <div>
          <span>{t("critic.issues")}</span>
          <strong>{issues.length}</strong>
        </div>
        <div>
          <span>{t("critic.risks")}</span>
          <strong>{riskFlags.length}</strong>
        </div>
      </div>

      <div className="phase2-list-block">
        <span>{t("critic.issues")}</span>
        <p>{issues.length ? issues.slice(0, 4).join(" / ") : t("critic.noIssues")}</p>
      </div>
      <div className="phase2-list-block">
        <span>{t("critic.suggestions")}</span>
        {suggestions.length || critic?.improved_answer_suggestion ? (
          <Markdown>
            {suggestions.length
              ? suggestions.slice(0, 6).map((s) => `- ${s}`).join("\n")
              : String(critic?.improved_answer_suggestion ?? "")}
          </Markdown>
        ) : (
          <p>{t("critic.noSuggestion")}</p>
        )}
      </div>
      <div className="phase2-list-block">
        <span>{t("critic.risks")}</span>
        <p>{riskFlags.length ? riskFlags.slice(0, 4).join(" / ") : t("critic.noRisks")}</p>
      </div>
    </section>
  )
}
