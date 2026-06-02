import type { CSSProperties } from "react"
import { useI18n } from "../../i18n/LanguageProvider"

interface DashboardHeaderProps {
  onOpenSettings: () => void
}

export function DashboardHeader({ onOpenSettings }: DashboardHeaderProps) {
  const { t, lang, setLang } = useI18n()

  const segBtn = (active: boolean): CSSProperties => ({
    padding: "2px 10px",
    fontSize: 12,
    fontWeight: 600,
    border: "none",
    cursor: "pointer",
    background: active ? "rgba(255,255,255,0.9)" : "transparent",
    color: active ? "#111" : "rgba(255,255,255,0.7)"
  })

  return (
    <header
      style={{
        height: 48,
        background: "rgba(0,0,0,0.3)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        WebkitAppRegion: "drag"
      } as CSSProperties}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 14
          }}
        >
          A
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{t("header.title")}</div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>{t("header.subtitle")}</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", WebkitAppRegion: "no-drag" } as CSSProperties}>
        <div
          title={t("header.lang")}
          style={{
            display: "flex",
            borderRadius: 6,
            overflow: "hidden",
            border: "1px solid rgba(255,255,255,0.18)"
          }}
        >
          <button style={segBtn(lang === "zh")} onClick={() => setLang("zh")}>中</button>
          <button style={segBtn(lang === "en")} onClick={() => setLang("en")}>EN</button>
        </div>
        <button className="legacy-header-button" onClick={() => window.open("http://127.0.0.1:8000/blackboard", "_blank")}>
          Blackboard
        </button>
        <button className="legacy-header-button" onClick={onOpenSettings}>
          {t("common.settings")}
        </button>
      </div>
    </header>
  )
}
