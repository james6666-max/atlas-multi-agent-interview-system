import { useState } from "react"
import { usePractice } from "../../hooks/usePractice"
import { useI18n } from "../../i18n/LanguageProvider"
import { localizeReport } from "../../utils/localizeReport"
import { Markdown } from "./Markdown"

function scoreColor(score: number | null | undefined): string {
  if (typeof score !== "number") return "#94a3b8"
  if (score >= 75) return "#22c55e"
  if (score >= 50) return "#f97316"
  return "#ef4444"
}

export function PracticePanel() {
  const { lang, t } = useI18n()
  const typeLabel = (type: string) => t(`qtype.${type}`, type)
  const p = usePractice()
  const report = localizeReport(p.report, lang)
  const [count, setCount] = useState(5)
  const idle = !p.state
  const inSession = p.active && p.current

  return (
    <section
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 14,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 11, letterSpacing: 1, color: "rgba(255,255,255,0.5)", textTransform: "uppercase" }}>
            {t("practice.eyebrow")}
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>{t("practice.title")}</h3>
        </div>
        {p.state && (
          <span style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>
            {t("practice.round")} {p.state.round_index + (p.completed ? 0 : 1)} {t("practice.of")} {p.state.total_planned}
            {p.state.followups_used > 0 ? ` (+${p.state.followups_used})` : ""}
          </span>
        )}
      </div>

      {p.error && (
        <div style={{ fontSize: 12, color: "#fca5a5", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, padding: 8 }}>
          {p.error}
        </div>
      )}

      {/* Idle: start */}
      {idle && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.7)" }}>{t("practice.intro")}</p>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.6)" }}>{t("practice.count")}</span>
            <div style={{ display: "flex", border: "1px solid rgba(255,255,255,0.15)", borderRadius: 8, overflow: "hidden" }}>
              {[3, 5, 7].map((n) => (
                <button
                  key={n}
                  onClick={() => setCount(n)}
                  disabled={p.loading}
                  style={{
                    padding: "6px 16px",
                    fontSize: 13,
                    fontWeight: 600,
                    border: "none",
                    cursor: "pointer",
                    background: count === n ? "rgba(255,255,255,0.92)" : "transparent",
                    color: count === n ? "#111" : "rgba(255,255,255,0.7)",
                  }}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <button onClick={() => p.start(count)} disabled={p.loading} style={btnStyle(true)}>
            {p.loading ? t("practice.generating") : `${t("practice.start")} · ${count} ${t("practice.questions")}`}
          </button>
        </div>
      )}

      {/* In session: question + answer */}
      {inSession && p.current && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span style={chip()}>{typeLabel(p.current.type)}</span>
            {p.current.is_followup && <span style={chip("#a78bfa")}>{t("practice.followupTag")}</span>}
            {p.current.topic && <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}>{p.current.topic}</span>}
          </div>
          <div style={{ fontSize: 15, lineHeight: 1.5, color: "white" }}>{p.current.question}</div>

          {p.feedback && p.lastScore !== null && (
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", display: "flex", gap: 10, alignItems: "center" }}>
              <span>{t("practice.lastScore")}</span>
              <strong style={{ color: scoreColor(p.lastScore) }}>{p.lastScore} {t("practice.points")}</strong>
              {(p.feedback.suggestions ?? [])[0] && <span>· {(p.feedback.suggestions ?? [])[0]}</span>}
            </div>
          )}

          <textarea
            value={p.answer}
            onChange={(e) => p.setAnswer(e.target.value)}
            placeholder={t("practice.answerPlaceholder")}
            rows={5}
            style={{
              width: "100%",
              background: "rgba(0,0,0,0.4)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 8,
              color: "white",
              padding: 10,
              fontSize: 13,
              resize: "vertical",
            }}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={p.submit} disabled={p.loading || !p.answer.trim()} style={btnStyle(true)}>
              {p.loading ? t("practice.scoring") : t("practice.submit")}
            </button>
            <button onClick={p.reset} disabled={p.loading} style={btnStyle(false)}>
              {t("common.close")}
            </button>
          </div>
        </div>
      )}

      {/* Completed: report */}
      {p.completed && report && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>{t("practice.totalScore")}</span>
            <span style={{ fontSize: 30, fontWeight: 700, color: scoreColor(report.overall_score) }}>
              {report.overall_score}
            </span>
          </div>
          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.75)" }}>{report.summary}</p>

          <ReportBlock title={t("practice.strengths")} items={report.strengths} />
          <ReportBlock title={t("practice.weaknesses")} items={report.weaknesses} />
          <ReportBlock title={t("practice.recommended")} items={report.recommended_practice} />

          <div>
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginBottom: 6 }}>{t("practice.perQuestion")}</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {report.question_reviews.map((r, i) => (
                <div key={i} style={{ display: "flex", gap: 8, fontSize: 12, alignItems: "center" }}>
                  <strong style={{ color: scoreColor(r.score), minWidth: 34 }}>{r.score}</strong>
                  <span style={{ color: "rgba(255,255,255,0.5)", minWidth: 56 }}>
                    {typeLabel(r.type)}
                    {r.is_followup ? " ·" : ""}
                  </span>
                  <span style={{ color: "rgba(255,255,255,0.8)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {r.question}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <button onClick={() => p.start(count)} style={btnStyle(true)}>
            {t("practice.again")}
          </button>
        </div>
      )}
    </section>
  )
}

function ReportBlock({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null
  return (
    <div>
      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginBottom: 4 }}>{title}</div>
      <Markdown>{items.map((it) => `- ${it}`).join("\n")}</Markdown>
    </div>
  )
}

function btnStyle(primary: boolean): React.CSSProperties {
  return {
    padding: "8px 14px",
    borderRadius: 10,
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    border: primary ? "none" : "1px solid rgba(255,255,255,0.15)",
    background: primary ? "white" : "transparent",
    color: primary ? "black" : "rgba(255,255,255,0.85)",
  }
}

function chip(color = "#38bdf8"): React.CSSProperties {
  return {
    fontSize: 11,
    fontWeight: 600,
    color,
    background: "rgba(255,255,255,0.06)",
    border: `1px solid ${color}55`,
    borderRadius: 6,
    padding: "2px 8px",
  }
}
