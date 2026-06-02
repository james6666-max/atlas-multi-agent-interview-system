import { useI18n } from "../../i18n/LanguageProvider"

interface QuestionInputProps {
  value: string
  loading?: boolean
  error?: string | null
  onChange: (value: string) => void
  onSubmit: () => void
  onClear: () => void
}

export function QuestionInput({
  value,
  loading = false,
  error,
  onChange,
  onSubmit,
  onClear
}: QuestionInputProps) {
  const { t } = useI18n()
  return (
    <div>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("manual.placeholder")}
        disabled={loading}
        className="phase2-question-input"
        onKeyDown={(event) => {
          if (event.key === "Enter" && event.ctrlKey) {
            onSubmit()
          }
        }}
      />
      {error && <div className="phase2-error-text">{error}</div>}
      <div className="phase2-input-actions">
        <button
          type="button"
          className="phase2-primary-button"
          onClick={onSubmit}
          disabled={loading || !value.trim()}
        >
          {loading ? t("answer.streaming") : `${t("manual.submit")} (Ctrl+Enter)`}
        </button>
        <button type="button" className="phase2-secondary-button" onClick={onClear} disabled={loading}>
          {t("manual.clear")}
        </button>
      </div>
    </div>
  )
}
