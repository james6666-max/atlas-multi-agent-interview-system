import { useEffect, useState, type ChangeEvent } from "react"
import { getProfile, parseProfileFile, saveProfile, type CandidateProfile } from "../../api/client"
import { useI18n } from "../../i18n/LanguageProvider"
import { useToast } from "../../contexts/toast"

const EMPTY: CandidateProfile = { resume: "", jd: "", knowledge: "", company: "", position: "", focus: "" }
const REQUIRED: (keyof CandidateProfile)[] = ["company", "position", "resume"]

const INPUT =
  "w-full bg-black/40 border border-white/12 text-white text-xs rounded-md px-2.5 py-2 outline-none focus:border-white/30"

interface CandidatePrepProps {
  onSaved?: () => void
}

export function CandidatePrep({ onSaved }: CandidatePrepProps) {
  const { t } = useI18n()
  const { showToast } = useToast()
  const [form, setForm] = useState<CandidateProfile>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [parsing, setParsing] = useState<keyof CandidateProfile | null>(null)
  const [errors, setErrors] = useState<Set<keyof CandidateProfile>>(new Set())

  const missing = (key: keyof CandidateProfile) => errors.has(key)

  useEffect(() => {
    let cancelled = false
    getProfile()
      .then((p) => !cancelled && setForm({ ...EMPTY, ...p }))
      .catch(() => !cancelled && showToast(t("prep.profile"), t("prep.loadFail"), "error"))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [showToast, t])

  const set = (key: keyof CandidateProfile) => (value: string) => {
    setForm((f) => ({ ...f, [key]: value }))
    if (errors.has(key) && value.trim()) {
      setErrors((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  const uploadInto = (key: keyof CandidateProfile) => async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ""
    if (!file) return
    setParsing(key)
    try {
      const { text } = await parseProfileFile(file)
      set(key)(text)
    } catch (err) {
      showToast(t("prep.profile"), err instanceof Error ? err.message : t("prep.parseFail"), "error")
    } finally {
      setParsing(null)
    }
  }

  const save = async () => {
    const nextErrors = new Set<keyof CandidateProfile>(REQUIRED.filter((k) => !form[k]?.trim()))
    if (nextErrors.size > 0) {
      setErrors(nextErrors)
      showToast(t("prep.profile"), t("prep.fixRequired"), "error")
      return
    }
    setSaving(true)
    try {
      const result = await saveProfile(form)
      setForm({ ...EMPTY, ...result })
      showToast(t("prep.profile"), t("prep.saved"), "success")
      onSaved?.()
    } catch (err) {
      showToast(t("prep.profile"), err instanceof Error ? err.message : t("prep.saveFail"), "error")
    } finally {
      setSaving(false)
    }
  }

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
        marginBottom: 16,
      }}
    >
      <div>
        <div style={{ fontSize: 11, letterSpacing: 1, color: "rgba(255,255,255,0.5)", textTransform: "uppercase" }}>
          {t("prep.profileEyebrow")}
        </div>
        <h3 style={{ fontSize: 16, fontWeight: 600 }}>{t("prep.profile")}</h3>
      </div>

      {loading ? (
        <p style={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}>{t("common.loading")}</p>
      ) : (
        <>
          {/* Target company / position / focus */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <Field label={t("prep.company")} required error={missing("company") ? t("prep.requiredField") : undefined}>
              <input
                className={INPUT}
                style={{ borderColor: missing("company") ? "#f87171" : undefined }}
                value={form.company}
                onChange={(e) => set("company")(e.target.value)}
                placeholder={t("prep.companyPh")}
              />
            </Field>
            <Field label={t("prep.position")} required error={missing("position") ? t("prep.requiredField") : undefined}>
              <input
                className={INPUT}
                style={{ borderColor: missing("position") ? "#f87171" : undefined }}
                value={form.position}
                onChange={(e) => set("position")(e.target.value)}
                placeholder={t("prep.positionPh")}
              />
            </Field>
          </div>
          <Field label={t("prep.focus")}>
            <input className={INPUT} value={form.focus} onChange={(e) => set("focus")(e.target.value)} placeholder={t("prep.focusPh")} />
          </Field>

          {/* Resume */}
          <Field
            label={t("prep.resume")}
            required
            error={missing("resume") ? t("prep.requiredField") : undefined}
            upload={<UploadButton label={parsing === "resume" ? t("prep.parsing") : t("prep.upload")} busy={parsing === "resume"} accept=".txt,.md,.pdf,.docx" onChange={uploadInto("resume")} />}
          >
            <textarea
              className={INPUT}
              style={{ resize: "vertical", borderColor: missing("resume") ? "#f87171" : undefined }}
              rows={6}
              value={form.resume}
              onChange={(e) => set("resume")(e.target.value)}
              placeholder={t("prep.resumePh")}
            />
          </Field>

          {/* JD */}
          <Field
            label={t("prep.jd")}
            upload={<UploadButton label={parsing === "jd" ? t("prep.parsing") : t("prep.upload")} busy={parsing === "jd"} accept=".txt,.md,.pdf,.docx" onChange={uploadInto("jd")} />}
          >
            <textarea className={INPUT} style={{ resize: "vertical" }} rows={4} value={form.jd} onChange={(e) => set("jd")(e.target.value)} placeholder={t("prep.jdPh")} />
          </Field>

          <button
            type="button"
            onClick={save}
            disabled={saving}
            style={{
              alignSelf: "flex-start",
              padding: "8px 16px",
              borderRadius: 10,
              border: "none",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
              background: "white",
              color: "#111",
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? t("prep.saving") : t("prep.save")}
          </button>
        </>
      )}
    </section>
  )
}

function Field({
  label,
  required,
  error,
  upload,
  children,
}: {
  label: string
  required?: boolean
  error?: string
  upload?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>
          {label}
          {required && <span style={{ color: "#f87171", marginLeft: 4 }}>*</span>}
        </span>
        {upload}
      </div>
      {children}
      {error && <div style={{ fontSize: 11, color: "#fca5a5", marginTop: 4 }}>{error}</div>}
    </label>
  )
}

function UploadButton({
  label,
  busy,
  accept,
  onChange,
}: {
  label: string
  busy?: boolean
  accept: string
  onChange: (e: ChangeEvent<HTMLInputElement>) => void
}) {
  return (
    <label style={{ fontSize: 11, color: busy ? "rgba(255,255,255,0.5)" : "#a5b4fc", cursor: busy ? "default" : "pointer" }}>
      {label}
      <input type="file" accept={accept} onChange={onChange} disabled={busy} style={{ display: "none" }} />
    </label>
  )
}
