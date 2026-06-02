import { useI18n } from "../i18n/LanguageProvider"
import { localizeReport } from "../utils/localizeReport"

interface ReportPageProps {
  report: any
  exportedMarkdown: string
  getScoreColor: (score: unknown) => string
}

export default function ReportPage({ report, exportedMarkdown, getScoreColor }: ReportPageProps) {
  const { lang, t } = useI18n()
  const localizedReport = localizeReport(report, lang)
  const metricSummaries = [
    localizedReport?.jd_alignment_summary,
    localizedReport?.resume_alignment_summary,
    localizedReport?.privacy_risk_summary,
  ].filter(Boolean)

  return (
    <>
      {localizedReport && (
        <div className="legacy-report-box">
          <div className="legacy-critic-title">{t("report.title")}</div>
          <div style={{ color: getScoreColor((localizedReport.overall_score ?? 0) / 100), fontWeight: 700 }}>
            {t("report.overall")}: {localizedReport.overall_score ?? t("common.unknown")}
          </div>
          <div className="legacy-note-line">{localizedReport.summary}</div>

          {metricSummaries.length > 0 && (
            <ReportList items={metricSummaries as string[]} />
          )}

          <ReportList title={t("practice.strengths")} items={(localizedReport.strengths || []).slice(0, 3)} />
          <ReportList title={t("practice.weaknesses")} items={(localizedReport.weaknesses || []).slice(0, 3)} />
          <ReportList title={t("practice.recommended")} items={(localizedReport.recommended_practice || []).slice(0, 3)} />

          {Array.isArray(localizedReport.question_reviews) && localizedReport.question_reviews.length > 0 && (
            <ReportList
              title={t("practice.perQuestion")}
              items={localizedReport.question_reviews.slice(0, 5).map((item: any) => (
                `${item.question || t("common.unknown")} / ${t("common.score")}: ${item.final_score ?? t("common.unknown")}`
              ))}
            />
          )}
        </div>
      )}

      {exportedMarkdown && (
        <textarea className="legacy-markdown-output" readOnly value={exportedMarkdown} />
      )}
    </>
  )
}

function ReportList({ title, items }: { title?: string; items: string[] }) {
  if (!items.length) return null
  return (
    <div className="legacy-note-line">
      {title && <strong>{title}</strong>}
      <ul>
        {items.map((item, index) => (
          <li key={`${title ?? "report"}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  )
}
