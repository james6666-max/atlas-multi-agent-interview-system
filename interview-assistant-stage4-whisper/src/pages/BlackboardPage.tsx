import { useI18n } from "../i18n/LanguageProvider"

interface BlackboardPageProps {
  history: any[]
  showHistory: boolean
  onToggleHistory: () => void
  getScoreColor: (score: unknown) => string
}

export default function BlackboardPage({
  history,
  showHistory,
  onToggleHistory,
  getScoreColor
}: BlackboardPageProps) {
  const { t } = useI18n()
  return (
    <section className="legacy-panel">
      <div className="legacy-panel-header">
        <h2>{t("review.history")}</h2>
        <button className="legacy-link-button" onClick={onToggleHistory}>
          {showHistory ? t("review.collapse") : t("review.expand")}
        </button>
      </div>

      {showHistory && (
        <div className="legacy-scroll-panel">
          {history.length === 0 && (
            <div className="legacy-empty-state">{t("review.empty")}</div>
          )}

          {history.slice(0, 10).map((item, index) => {
            const critic = item?.critic || {}
            const finalScore = typeof critic.final_score === "number" ? critic.final_score : null

            return (
              <article className="legacy-history-item" key={`${item?.turn_id || index}`}>
                <div className="legacy-badge-row">
                  <span className="legacy-badge legacy-badge-blue">{item?.question_type || t("common.unknown")}</span>
                  <span className="legacy-badge legacy-badge-green">{item?.agent || t("common.unknown")}</span>
                  <span className="legacy-badge">{item?.source || t("common.unknown")}</span>
                </div>

                <div className="legacy-question">{item?.question || t("review.noQuestion")}</div>

                {item?.answer && (
                  <div className="legacy-answer-preview">{String(item.answer).slice(0, 220)}</div>
                )}

                {item?.critic && (
                  <div className="legacy-critic-box">
                    <div className="legacy-critic-title">{t("review.criticReview")}</div>
                    <div className="legacy-metric-grid">
                      <div>
                        <span>{t("review.finalScore")}</span>
                        <strong style={{ color: getScoreColor(finalScore === null ? null : finalScore / 100) }}>
                          {finalScore ?? t("common.unknown")}
                        </strong>
                      </div>
                      <div>
                        <span>{t("review.clarity")}</span>
                        <strong>{typeof critic.clarity_score === "number" ? `${(critic.clarity_score * 100).toFixed(0)}%` : t("common.unknown")}</strong>
                      </div>
                      <div>
                        <span>{t("review.correctness")}</span>
                        <strong>{typeof critic.correctness_score === "number" ? `${(critic.correctness_score * 100).toFixed(0)}%` : t("common.unknown")}</strong>
                      </div>
                      <div>
                        <span>{t("review.privacy")}</span>
                        <strong>{typeof critic.privacy_score === "number" ? `${(critic.privacy_score * 100).toFixed(0)}%` : t("common.unknown")}</strong>
                      </div>
                    </div>

                    {Array.isArray(critic.specific_issues) && critic.specific_issues.length > 0 && (
                      <div className="legacy-note-line">
                        {t("review.issues")}: {critic.specific_issues.slice(0, 3).join(" / ")}
                      </div>
                    )}
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
