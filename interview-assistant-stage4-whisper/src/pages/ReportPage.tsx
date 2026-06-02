import { useI18n } from "../i18n/LanguageProvider"

interface ReportPageProps {
  report: any
  exportedMarkdown: string
  getScoreColor: (score: unknown) => string
}

export default function ReportPage({ report, exportedMarkdown, getScoreColor }: ReportPageProps) {
  const { t } = useI18n()
  return (
    <>
      {report && (
        <div className="legacy-report-box">
          <div className="legacy-critic-title">{t("report.title")}</div>
          <div style={{ color: getScoreColor((report.overall_score ?? 0) / 100), fontWeight: 700 }}>
            {t("report.overall")}: {report.overall_score ?? "—"}
          </div>
          <div className="legacy-note-line">{report.summary}</div>
          <div className="legacy-note-line">
            <strong>{t("practice.strengths")}</strong>
            <ul>
              {(report.strengths || []).slice(0, 3).map((item: string, index: number) => (
                <li key={`strength-${index}`}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="legacy-note-line">
            <strong>{t("practice.recommended")}</strong>
            <ul>
              {(report.recommended_practice || []).slice(0, 3).map((item: string, index: number) => (
                <li key={`practice-${index}`}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {exportedMarkdown && (
        <textarea className="legacy-markdown-output" readOnly value={exportedMarkdown} />
      )}
    </>
  )
}
