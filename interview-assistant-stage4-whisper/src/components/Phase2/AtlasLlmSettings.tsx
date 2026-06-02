import { useEffect, useState } from "react"
import { getLlmConfig, testLlmConnection, updateLlmConfig, type LlmTestResult } from "../../api/client"
import type { LlmConfig } from "../../types/phase2"
import { useToast } from "../../contexts/toast"
import { useI18n } from "../../i18n/LanguageProvider"

type Mode = "hybrid" | "local" | "cloud"

const MODE_KEYS: Mode[] = ["hybrid", "local", "cloud"]
const MODE_LABEL: Record<Mode, { title: string; desc: string }> = {
  hybrid: { title: "llm.modeHybrid", desc: "llm.modeHybridDesc" },
  local: { title: "llm.modeLocal", desc: "llm.modeLocalDesc" },
  cloud: { title: "llm.modeCloud", desc: "llm.modeCloudDesc" },
}

const PRESETS: { label: string; base: string; model: string }[] = [
  { label: "Groq", base: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile" },
  { label: "DeepSeek", base: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { label: "Qwen", base: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus" },
  { label: "OpenRouter", base: "https://openrouter.ai/api/v1", model: "meta-llama/llama-3.3-70b-instruct" },
]

const INPUT_CLASS =
  "w-full bg-black/50 border border-white/10 text-white text-xs rounded-md px-2 py-1.5 outline-none focus:border-white/30"

export function AtlasLlmSettings() {
  const { showToast } = useToast()
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<LlmTestResult | null>(null)
  const [mode, setMode] = useState<Mode>("hybrid")
  const [cloudBaseUrl, setCloudBaseUrl] = useState("")
  const [cloudModel, setCloudModel] = useState("")
  const [cloudApiKey, setCloudApiKey] = useState("")
  const [cloudKeySet, setCloudKeySet] = useState(false)
  const [ollamaBaseUrl, setOllamaBaseUrl] = useState("http://127.0.0.1:11434")
  const [ollamaModel, setOllamaModel] = useState("qwen2.5:7b")

  const applyConfig = (cfg: LlmConfig) => {
    setMode((cfg.mode as Mode) || "hybrid")
    setCloudBaseUrl(cfg.cloud_base_url || "")
    setCloudModel(cfg.cloud_model || "")
    setCloudKeySet(Boolean(cfg.cloud_api_key_set))
    setOllamaBaseUrl(cfg.ollama_base_url || "http://127.0.0.1:11434")
    setOllamaModel(cfg.ollama_model || "qwen2.5:7b")
  }

  useEffect(() => {
    let cancelled = false
    getLlmConfig()
      .then((cfg) => {
        if (!cancelled) applyConfig(cfg)
      })
      .catch((err) => {
        console.warn("Failed to load LLM config:", err)
        if (!cancelled) showToast("Atlas LLM", "Backend not reachable for LLM settings", "error")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [showToast])

  const usePreset = (preset: (typeof PRESETS)[number]) => {
    setCloudBaseUrl(preset.base)
    setCloudModel(preset.model)
    if (mode === "local") setMode("hybrid")
  }

  const runTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      setTestResult(await testLlmConnection())
    } catch (err) {
      setTestResult({ ok: false, error: err instanceof Error ? err.message : "request failed" })
    } finally {
      setTesting(false)
    }
  }

  const save = async () => {
    setSaving(true)
    try {
      const updates: Partial<LlmConfig> = {
        mode,
        cloud_base_url: cloudBaseUrl.trim(),
        cloud_model: cloudModel.trim(),
        ollama_base_url: ollamaBaseUrl.trim(),
        ollama_model: ollamaModel.trim(),
      }
      if (cloudApiKey.trim()) updates.cloud_api_key = cloudApiKey.trim()
      const result = await updateLlmConfig(updates)
      applyConfig(result)
      setCloudApiKey("")
      const cloudReady = Boolean(result.cloud_configured)
      showToast(
        "Atlas LLM saved",
        cloudReady ? `Cloud ready (${result.cloud_model}). Hot-reloaded.` : "Saved. Using local Ollama.",
        "success"
      )
    } catch (err) {
      showToast("Atlas LLM", err instanceof Error ? err.message : "Failed to save", "error")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h2 className="text-sm font-semibold text-white">{t("llm.title")}</h2>
        <p className="text-xs text-white/60">{t("llm.desc")}</p>
      </div>

      {loading ? (
        <p className="text-xs text-white/50">{t("common.loading")}</p>
      ) : (
        <>
          {/* Mode */}
          <div className="grid grid-cols-3 gap-2">
            {MODE_KEYS.map((key) => (
              <div
                key={key}
                onClick={() => setMode(key)}
                className={`p-2 rounded-lg cursor-pointer transition-colors ${
                  mode === key
                    ? "bg-white/10 border border-white/20"
                    : "bg-black/30 border border-white/5 hover:bg-white/5"
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full flex-shrink-0 ${mode === key ? "bg-white" : "bg-white/20"}`} />
                  <div className="min-w-0">
                    <p className="font-medium text-white text-xs truncate">{t(MODE_LABEL[key].title)}</p>
                    <p className="text-[10px] text-white/60 truncate">{t(MODE_LABEL[key].desc)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Cloud presets */}
          {mode !== "local" && (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => usePreset(p)}
                    className="text-[11px] px-2 py-1 rounded-md bg-black/30 border border-white/10 text-white/80 hover:bg-white/5"
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              <label className="text-xs font-medium text-white block">{t("llm.cloudBaseUrl")}</label>
              <input
                className={INPUT_CLASS}
                value={cloudBaseUrl}
                onChange={(e) => setCloudBaseUrl(e.target.value)}
                placeholder="https://api.groq.com/openai/v1"
              />

              <label className="text-xs font-medium text-white block">{t("llm.cloudModel")}</label>
              <input
                className={INPUT_CLASS}
                value={cloudModel}
                onChange={(e) => setCloudModel(e.target.value)}
                placeholder="llama-3.3-70b-versatile"
              />

              <label className="text-xs font-medium text-white block">
                {t("llm.cloudKey")} {cloudKeySet && <span className="text-green-400">{t("llm.keySet")}</span>}
              </label>
              <input
                className={INPUT_CLASS}
                type="password"
                value={cloudApiKey}
                onChange={(e) => setCloudApiKey(e.target.value)}
                placeholder={cloudKeySet ? t("llm.keepCurrent") : t("llm.pasteKey")}
              />
            </div>
          )}

          {/* Ollama */}
          <details className="text-white/80">
            <summary className="text-xs cursor-pointer text-white/70 select-none">{t("llm.ollamaAdvanced")}</summary>
            <div className="space-y-2 mt-2">
              <label className="text-xs font-medium text-white block">{t("llm.ollamaBaseUrl")}</label>
              <input className={INPUT_CLASS} value={ollamaBaseUrl} onChange={(e) => setOllamaBaseUrl(e.target.value)} />
              <label className="text-xs font-medium text-white block">{t("llm.ollamaModel")}</label>
              <input className={INPUT_CLASS} value={ollamaModel} onChange={(e) => setOllamaModel(e.target.value)} />
            </div>
          </details>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="px-3 py-2 bg-white text-black rounded-lg text-xs font-medium hover:bg-white/90 transition-colors disabled:opacity-60"
            >
              {saving ? t("llm.saving") : t("llm.save")}
            </button>
            <button
              type="button"
              onClick={runTest}
              disabled={testing}
              className="px-3 py-2 rounded-lg text-xs font-medium border border-white/15 text-white/85 hover:bg-white/5 transition-colors disabled:opacity-60"
            >
              {testing ? t("llm.testing") : t("llm.test")}
            </button>
          </div>

          {testResult && (
            <div
              className="text-xs rounded-md px-2 py-1.5 border"
              style={{
                color: testResult.ok ? "#86efac" : "#fca5a5",
                background: testResult.ok ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                borderColor: testResult.ok ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)",
              }}
            >
              {testResult.ok
                ? `✓ ${testResult.provider}${testResult.model ? ` · ${testResult.model}` : ""}${
                    testResult.fallback_used ? " (fallback→local)" : ""
                  } · ${testResult.latency_ms}ms`
                : `✗ ${testResult.error}`}
            </div>
          )}
        </>
      )}
    </div>
  )
}
