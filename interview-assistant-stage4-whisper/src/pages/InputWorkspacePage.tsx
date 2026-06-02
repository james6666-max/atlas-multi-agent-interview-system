import Phase2ManualDemoPage from "./Phase2ManualDemoPage"
import { useI18n } from "../i18n/LanguageProvider"

type TabId = "ocr" | "voice" | "manual"

interface Tone {
  label: string
  color: string
  background: string
  border: string
}

interface InputWorkspacePageProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  llmTone: Tone
  resumeTone: Tone
  jdTone: Tone
  matchTone: Tone
  knowledgeTone: Tone
  ragTone: Tone
  llmStatus: any
  resumeStatus: any
  jdStatus: any
  matchStatus: any
  knowledgeStatus: any
  ragStatus: any
  localAskLoading: boolean
  onAskImage: () => void
  voiceLanguage: "Unknown" | "Chinese" | "English"
  onVoiceLanguageChange: (value: "Unknown" | "Chinese" | "English") => void
  voiceRecording: boolean
  voiceChunksLength: number
  voiceSendLoading: boolean
  voiceResult: string
  onStartRecording: () => void
  onStopRecording: () => void
  onSendAudio: () => void
  onCompleted?: () => void
}

function StatusBlock({
  title,
  tone,
  rows
}: {
  title: string
  tone: Tone
  rows: Array<[string, unknown]>
}) {
  return (
    <div className="legacy-status-block" style={{ background: tone.background, borderColor: tone.border }}>
      <div className="legacy-status-head">
        <strong>{title}</strong>
        <span style={{ color: tone.color }}>{tone.label}</span>
      </div>
      <div className="legacy-status-rows">
        {rows.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value === null || value === undefined || value === "" ? "unknown" : String(value)}</strong>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function InputWorkspacePage({
  activeTab,
  onTabChange,
  llmTone,
  resumeTone,
  jdTone,
  matchTone,
  knowledgeTone,
  ragTone,
  llmStatus,
  resumeStatus,
  jdStatus,
  matchStatus,
  knowledgeStatus,
  ragStatus,
  localAskLoading,
  onAskImage,
  voiceLanguage,
  onVoiceLanguageChange,
  voiceRecording,
  voiceChunksLength,
  voiceSendLoading,
  voiceResult,
  onStartRecording,
  onStopRecording,
  onSendAudio,
  onCompleted
}: InputWorkspacePageProps) {
  const { t } = useI18n()
  return (
    <section className="legacy-panel">
      <h2 className="legacy-panel-title">{t("input.title")}</h2>

      <StatusBlock
        title={t("status.llm")}
        tone={llmTone}
        rows={[
          [t("row.source"), llmStatus.answerSource],
          [t("row.model"), llmStatus.model],
          [t("row.fallback"), llmStatus.fallback === null ? t("common.unknown") : String(llmStatus.fallback)],
          [t("common.error"), llmStatus.llmError || t("common.none")]
        ]}
      />
      <StatusBlock
        title={t("status.rag")}
        tone={ragTone}
        rows={[
          [t("row.rag"), ragTone.label],
          [t("row.snippets"), ragStatus.snippetsCount === null ? t("common.unknown") : ragStatus.snippetsCount],
          [t("row.keywords"), ragStatus.keywords?.length ? ragStatus.keywords.join(", ") : t("common.none")]
        ]}
      />

      <div className="legacy-tabs">
        {[
          { id: "ocr" as const, label: t("tabs.ocr") },
          { id: "voice" as const, label: t("tabs.voice") },
          { id: "manual" as const, label: t("tabs.manual") }
        ].map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "legacy-tab legacy-tab-active" : "legacy-tab"}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "ocr" && (
        <button className="legacy-primary-button" onClick={onAskImage} disabled={localAskLoading}>
          {localAskLoading ? t("common.processing") : t("ocr.capture")}
        </button>
      )}

      {activeTab === "voice" && (
        <div>
          <select
            className="legacy-select"
            value={voiceLanguage}
            onChange={(event) => onVoiceLanguageChange(event.target.value as "Unknown" | "Chinese" | "English")}
          >
            <option value="Unknown">{t("voice.autoDetect")}</option>
            <option value="Chinese">{t("voice.chinese")}</option>
            <option value="English">{t("voice.english")}</option>
          </select>

          <div className="legacy-button-row">
            <button className="legacy-danger-button" onClick={onStartRecording} disabled={voiceRecording}>
              {voiceRecording ? t("voice.recording") : t("voice.start")}
            </button>
            <button className="legacy-secondary-button" onClick={onStopRecording} disabled={!voiceRecording}>
              {t("voice.stop")}
            </button>
          </div>

          <button
            className="legacy-primary-button"
            onClick={onSendAudio}
            disabled={voiceRecording || !voiceChunksLength || voiceSendLoading}
          >
            {voiceSendLoading ? t("voice.sending") : t("voice.send")}
          </button>
        </div>
      )}

      {activeTab === "manual" && <Phase2ManualDemoPage onCompleted={onCompleted} />}

      {voiceResult && (
        <pre className="legacy-result-box">{voiceResult}</pre>
      )}
    </section>
  )
}
