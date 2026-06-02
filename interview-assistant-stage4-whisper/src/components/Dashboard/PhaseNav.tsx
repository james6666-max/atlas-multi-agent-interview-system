import type { CSSProperties } from "react"
import { useI18n } from "../../i18n/LanguageProvider"

export type PhaseView = "prep" | "live" | "review"

interface PhaseNavProps {
  view: PhaseView
  onChange: (view: PhaseView) => void
  backendConnected: boolean | null
}

const PHASES: { key: PhaseView; step: string; titleKey: string; subKey: string }[] = [
  { key: "prep", step: "1", titleKey: "nav.prep", subKey: "nav.prepSub" },
  { key: "live", step: "2", titleKey: "nav.live", subKey: "nav.liveSub" },
  { key: "review", step: "3", titleKey: "nav.review", subKey: "nav.reviewSub" },
]

export function PhaseNav({ view, onChange, backendConnected }: PhaseNavProps) {
  const { t } = useI18n()

  const dot = backendConnected === true ? "#22c55e" : backendConnected === false ? "#ef4444" : "#94a3b8"

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
        padding: "16px 20px 4px",
        position: "relative",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 6,
          padding: 6,
          borderRadius: 14,
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
        }}
      >
        {PHASES.map((p, i) => {
          const active = view === p.key
          const btn: CSSProperties = {
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 18px",
            borderRadius: 10,
            border: "none",
            cursor: "pointer",
            background: active ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" : "transparent",
            color: active ? "#fff" : "rgba(255,255,255,0.6)",
            transition: "all 0.18s ease",
          }
          return (
            <button key={p.key} style={btn} onClick={() => onChange(p.key)}>
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 999,
                  display: "grid",
                  placeItems: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  background: active ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.08)",
                  flexShrink: 0,
                }}
              >
                {p.step}
              </span>
              <span style={{ textAlign: "left", lineHeight: 1.2 }}>
                <span style={{ display: "block", fontSize: 13, fontWeight: 700 }}>{t(p.titleKey)}</span>
                <span style={{ display: "block", fontSize: 10, opacity: 0.75 }}>{t(p.subKey)}</span>
              </span>
              {i < PHASES.length - 1 && (
                <span style={{ marginLeft: 6, opacity: 0.4, fontSize: 13 }}>→</span>
              )}
            </button>
          )
        })}
      </div>

      <span
        title={backendConnected ? "Backend connected" : "Backend disconnected"}
        style={{
          position: "absolute",
          right: 24,
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: 11,
          color: "rgba(255,255,255,0.55)",
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: 999, background: dot }} />
        {t("nav.backend")}
      </span>
    </div>
  )
}
