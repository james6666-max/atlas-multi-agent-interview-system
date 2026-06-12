import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { UpdateNotification } from "../components/UpdateNotification"
import {
  Toast,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport
} from "../components/ui/toast"
import { DashboardHeader } from "../components/Dashboard/DashboardHeader"
import { PhaseNav, type PhaseView } from "../components/Dashboard/PhaseNav"
import { WindowDragBar } from "../components/Dashboard/WindowDragBar"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog"
import { CandidatePrep } from "../components/Phase2/CandidatePrep"
import { PracticePanel } from "../components/Phase2/PracticePanel"
import { StatusCard } from "../components/Phase2/StatusCard"
import { useI18n } from "../i18n/LanguageProvider"
import { ToastContext } from "../contexts/toast"
import { useAudioAsk } from "../hooks/useAudioAsk"
import { useBlackboard } from "../hooks/useBlackboard"
import { useImageAsk } from "../hooks/useImageAsk"
import { useReportActions } from "../hooks/useReportActions"
import BlackboardPage from "./BlackboardPage"
import InputWorkspacePage from "./InputWorkspacePage"
import ReportPage from "./ReportPage"

const SettingsDialog = lazy(() =>
  import("../components/Settings/SettingsDialog").then((module) => ({
    default: module.SettingsDialog
  }))
)
type WindowMode = "normal" | "stealth"
type WindowModeResult = {
  success: boolean
  mode?: WindowMode
  error?: string
}
const STEALTH_GUIDE_STORAGE_KEY = "atlas_seen_stealth_guide"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0,
      gcTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
      experimental_prefetchInRender: true
    } as any,
    mutations: {
      retry: 1
    }
  }
})

function fallbackTone(label: string) {
  return {
    label,
    color: "rgba(255,255,255,0.55)",
    background: "rgba(255,255,255,0.055)",
    border: "rgba(255,255,255,0.12)"
  }
}

function getLlmStatusTone(llmStatus: any) {
  if (llmStatus.fallback === true) {
    return { label: "Fallback", color: "#f97316", background: "rgba(249,115,22,0.12)", border: "rgba(249,115,22,0.35)" }
  }
  if (llmStatus.fallback === false) {
    return { label: "Live LLM", color: "#22c55e", background: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.3)" }
  }
  return fallbackTone("Unknown")
}

function getLoadedTone(loaded: boolean | null, loadedLabel = "loaded", missingLabel = "missing") {
  if (loaded === true) {
    return { label: loadedLabel, color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
  }
  if (loaded === false) {
    return { label: missingLabel, color: "#f97316", background: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.32)" }
  }
  return fallbackTone("unknown")
}

function getRagTone(ragStatus: any) {
  if (ragStatus.used === true) {
    return { label: "used", color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
  }
  if (ragStatus.used === false) {
    return { label: "unused", color: "#94a3b8", background: "rgba(255,255,255,0.055)", border: "rgba(255,255,255,0.12)" }
  }
  return fallbackTone("unknown")
}

function getMatchTone(matchStatus: any) {
  if (matchStatus.score === null) return fallbackTone("unknown")
  if (matchStatus.score >= 0.7) {
    return { label: `${Math.round(matchStatus.score * 100)}%`, color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
  }
  if (matchStatus.score >= 0.4) {
    return { label: `${Math.round(matchStatus.score * 100)}%`, color: "#f97316", background: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.32)" }
  }
  return { label: `${Math.round(matchStatus.score * 100)}%`, color: "#ef4444", background: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.3)" }
}

function getScoreColor(score: unknown) {
  if (typeof score !== "number") return "rgba(255,255,255,0.55)"
  if (score >= 0.7) return "#22c55e"
  if (score >= 0.4) return "#f97316"
  return "#ef4444"
}

function AtlasDashboardPage() {
  const { t } = useI18n()
  const [view, setView] = useState<PhaseView>("live")
  const blackboard = useBlackboard()
  const imageAsk = useImageAsk(blackboard.fetchBlackboard)
  const audioAsk = useAudioAsk(blackboard.fetchBlackboard)
  const reportActions = useReportActions({
    refreshBlackboard: blackboard.fetchBlackboard,
    setPageNotice: blackboard.setPageNotice
  })

  const [activeTab, setActiveTab] = useState<"ocr" | "voice" | "manual">("ocr")
  const [showHistory, setShowHistory] = useState(true)
  const [currentLanguage, setCurrentLanguage] = useState("python")
  const [isInitialized, setIsInitialized] = useState(true)
  const [hasApiKey, setHasApiKey] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [windowMode, setWindowModeState] = useState<WindowMode>("normal")
  const [showStealthGuide, setShowStealthGuide] = useState(false)
  const [credits, setCredits] = useState(999)
  const [toastState, setToastState] = useState({
    open: false,
    title: "",
    description: "",
    variant: "neutral" as "neutral" | "success" | "error"
  })

  const showToast = useCallback(
    (title: string, description: string, variant: "neutral" | "success" | "error") => {
      setToastState({ open: true, title, description, variant })
    },
    []
  )

  const openCommandSearch = useCallback(() => {
    setIsSettingsOpen(true)
    showToast("搜索", "已打开设置和模型搜索入口", "neutral")
  }, [showToast])

  const startDownload = useCallback(async () => {
    if (!window.electronAPI?.startUpdate) {
      showToast("下载", "当前环境不支持自动更新下载", "error")
      return
    }

    try {
      showToast("下载", "正在检查并下载可用更新", "neutral")
      const result = await window.electronAPI.startUpdate()
      if (!result?.success) {
        showToast("下载失败", result?.error || "没有可下载的更新，或当前为开发模式", "error")
      }
    } catch (error) {
      showToast("下载失败", error instanceof Error ? error.message : "下载入口暂不可用", "error")
    }
  }, [showToast])

  const enterStealthMode = useCallback(async () => {
    const result = await window.electronAPI?.setWindowMode?.("stealth")
    if (result?.success) {
      setWindowModeState("stealth")
      showToast("Stealth mode", "Shortcut-driven window mode is active.", "neutral")
    } else if (result?.error) {
      showToast("Stealth mode", result.error, "error")
    }
  }, [showToast])

  const requestStealthMode = useCallback(() => {
    if (windowMode === "stealth") {
      void window.electronAPI?.setWindowMode?.("normal").then((result: WindowModeResult | undefined) => {
        if (result?.success) {
          setWindowModeState("normal")
          showToast("Normal mode", "Mouse-first window mode is active.", "neutral")
        } else if (result?.error) {
          showToast("Normal mode", result.error, "error")
        }
      })
      return
    }

    if (localStorage.getItem(STEALTH_GUIDE_STORAGE_KEY) === "true") {
      void enterStealthMode()
      return
    }

    setShowStealthGuide(true)
  }, [enterStealthMode, showToast, windowMode])

  const confirmStealthGuide = useCallback(() => {
    localStorage.setItem(STEALTH_GUIDE_STORAGE_KEY, "true")
    setShowStealthGuide(false)
    void enterStealthMode()
  }, [enterStealthMode])

  const updateCredits = useCallback(() => {
    setCredits(999)
    window.__CREDITS__ = 999
  }, [])

  const updateLanguage = useCallback((newLanguage: string) => {
    setCurrentLanguage(newLanguage)
    window.__LANGUAGE__ = newLanguage
  }, [])

  const markInitialized = useCallback(() => {
    setIsInitialized(true)
    window.__IS_INITIALIZED__ = true
  }, [])

  useEffect(() => {
    const checkApiKey = async () => {
      try {
        if (window.electronAPI?.checkApiKey) {
          const hasKey = await window.electronAPI.checkApiKey()
          setHasApiKey(hasKey)
          if (!hasKey) setTimeout(() => setIsSettingsOpen(true), 1000)
        } else {
          setHasApiKey(true)
        }
      } catch (error) {
        console.error("Failed to check API key:", error)
        setHasApiKey(true)
      }
    }

    const initializeApp = async () => {
      try {
        updateCredits()
        if (window.electronAPI?.getConfig) {
          const config = await window.electronAPI.getConfig()
          updateLanguage(config?.language || "python")
        } else {
          updateLanguage("python")
        }
        markInitialized()
      } catch (error) {
        updateLanguage("python")
        markInitialized()
      }
    }

    checkApiKey()
    initializeApp()

    if (window.electronAPI?.onApiKeyInvalid) {
      const onApiKeyInvalid = () => {
        showToast("API Key Invalid", "Your API key appears invalid", "error")
        setIsSettingsOpen(true)
      }
      window.electronAPI.onApiKeyInvalid(onApiKeyInvalid)
    }

    return () => {
      window.__IS_INITIALIZED__ = false
      setIsInitialized(false)
    }
  }, [updateCredits, updateLanguage, markInitialized, showToast])

  useEffect(() => {
    let unsubscribe: (() => void) | undefined

    void window.electronAPI?.getWindowMode?.().then((result: WindowModeResult | undefined) => {
      if (result?.mode) setWindowModeState(result.mode)
    })

    if (window.electronAPI?.onWindowModeChanged) {
      unsubscribe = window.electronAPI.onWindowModeChanged(setWindowModeState)
    }

    return () => {
      unsubscribe?.()
    }
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        openCommandSearch()
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [openCommandSearch])

  // Atlas live-assist hotkeys (M3): Ctrl+Shift+A screenshot ask, Ctrl+Shift+V clipboard ask.
  const imageAskRef = useRef(imageAsk)
  imageAskRef.current = imageAsk
  useEffect(() => {
    const onScreenshot = () => {
      setActiveTab("ocr")
      void imageAskRef.current.submitImage()
    }
    const onRegionScreenshot = () => {
      setActiveTab("ocr")
      void imageAskRef.current.submitRegionImage()
    }
    const onClipboardAsk = (event: Event) => {
      const text = (event as CustomEvent<{ text?: string }>).detail?.text
      setActiveTab("manual")
      if (typeof text === "string" && text.trim()) {
        // let the manual tab mount, then prefill + auto-submit
        window.setTimeout(
          () => window.dispatchEvent(new CustomEvent("atlas-prefill-ask", { detail: { text } })),
          80
        )
      }
    }
    window.addEventListener("atlas-live-screenshot", onScreenshot)
    window.addEventListener("atlas-live-region-screenshot", onRegionScreenshot)
    window.addEventListener("atlas-live-ask", onClipboardAsk as EventListener)
    return () => {
      window.removeEventListener("atlas-live-screenshot", onScreenshot)
      window.removeEventListener("atlas-live-region-screenshot", onRegionScreenshot)
      window.removeEventListener("atlas-live-ask", onClipboardAsk as EventListener)
    }
  }, [])

  const llmTone = getLlmStatusTone(blackboard.llmStatus)
  const resumeTone = getLoadedTone(blackboard.resumeStatus.loaded)
  const jdTone = getLoadedTone(blackboard.jdStatus.loaded)
  const matchTone = getMatchTone(blackboard.matchStatus)
  const knowledgeTone = getLoadedTone(blackboard.knowledgeStatus.loaded)
  const ragTone = getRagTone(blackboard.ragStatus)

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ToastContext.Provider value={{ showToast }}>
          <div style={{
            minHeight: "100vh",
            background: "linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%)",
            color: "white",
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
          }}>
            <style>{`
              @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
              * { box-sizing: border-box; margin: 0; padding: 0; }
              ::-webkit-scrollbar { width: 6px; }
              ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 3px; }
              ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
              ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }
            `}</style>

            <WindowDragBar
              onDownload={startDownload}
              onSearch={openCommandSearch}
              onOpenMenu={() => setIsSettingsOpen(true)}
              onToggleStealth={requestStealthMode}
              windowMode={windowMode}
            />
            <DashboardHeader onOpenSettings={() => setIsSettingsOpen(true)} />

            <PhaseNav view={view} onChange={setView} backendConnected={blackboard.backendStatus.connected} />

            {/* ① 面试前 · 准备 */}
            {view === "prep" && (
              <main style={{ padding: "8px 24px 36px", maxWidth: 980, margin: "0 auto", width: "100%" }}>
                <p style={{ color: "rgba(255,255,255,0.62)", fontSize: 13, margin: "6px 4px 16px", lineHeight: 1.6 }}>{t("prep.lead")}</p>
                <CandidatePrep onSaved={blackboard.fetchBlackboard} />
                <PracticePanel />
                <h3 style={{ margin: "22px 4px 12px", fontSize: 14, fontWeight: 700, color: "rgba(255,255,255,0.85)" }}>{t("prep.readiness")}</h3>
                <div className="phase2-status-grid">
                  <StatusCard
                    label={t("status.resume")}
                    value={resumeTone.label}
                    detail={blackboard.resumeStatus.path || "resume.txt"}
                    tone={blackboard.resumeStatus.loaded === true ? "online" : blackboard.resumeStatus.loaded === false ? "warning" : "neutral"}
                  />
                  <StatusCard
                    label={t("status.jd")}
                    value={jdTone.label}
                    detail={blackboard.jdStatus.path || "jd.txt"}
                    tone={blackboard.jdStatus.loaded === true ? "online" : blackboard.jdStatus.loaded === false ? "warning" : "neutral"}
                  />
                  <StatusCard
                    label={t("status.match")}
                    value={matchTone.label}
                    detail={blackboard.matchStatus.gaps?.length ? `gaps: ${blackboard.matchStatus.gaps.join(", ")}` : t("common.none")}
                    tone={blackboard.matchStatus.score === null ? "neutral" : blackboard.matchStatus.score >= 0.7 ? "online" : blackboard.matchStatus.score >= 0.4 ? "warning" : "offline"}
                  />
                  <StatusCard
                    label={t("status.knowledge")}
                    value={knowledgeTone.label}
                    detail={blackboard.knowledgeStatus.path || "knowledge.txt"}
                    tone={blackboard.knowledgeStatus.loaded === true ? "online" : blackboard.knowledgeStatus.loaded === false ? "warning" : "neutral"}
                  />
                </div>
              </main>
            )}

            {/* ② 面试中 · 实战 */}
            {view === "live" && (
              <main style={{ padding: "8px 24px 36px", maxWidth: 1080, margin: "0 auto", width: "100%" }}>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.62)", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10, padding: "8px 12px", margin: "6px 0 14px" }}>
                  {t("live.hotkeys")}
                </div>
                <InputWorkspacePage
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  llmTone={llmTone}
                  resumeTone={resumeTone}
                  jdTone={jdTone}
                  matchTone={matchTone}
                  knowledgeTone={knowledgeTone}
                  ragTone={ragTone}
                  llmStatus={blackboard.llmStatus}
                  resumeStatus={blackboard.resumeStatus}
                  jdStatus={blackboard.jdStatus}
                  matchStatus={blackboard.matchStatus}
                  knowledgeStatus={blackboard.knowledgeStatus}
                  ragStatus={blackboard.ragStatus}
                  localAskLoading={imageAsk.loading}
                  ocrResult={imageAsk.result}
                  onAskImage={imageAsk.submitImage}
                  onAskRegionImage={imageAsk.submitRegionImage}
                  voiceLanguage={audioAsk.language}
                  onVoiceLanguageChange={audioAsk.setLanguage}
                  voiceRecording={audioAsk.recording}
                  voiceChunksLength={audioAsk.chunks.length}
                  voiceSendLoading={audioAsk.sendLoading}
                  voiceResult={audioAsk.result}
                  onStartRecording={audioAsk.startRecording}
                  onStopRecording={audioAsk.stopRecording}
                  onSendAudio={audioAsk.submitAudio}
                  onCompleted={blackboard.fetchBlackboard}
                />
              </main>
            )}

            {/* ③ 面试后 · 复盘 */}
            {view === "review" && (
              <main style={{ padding: "8px 24px 36px", maxWidth: 1280, margin: "0 auto", width: "100%", display: "grid", gridTemplateColumns: "minmax(320px,1fr) minmax(320px,460px)", gap: 20 }}>
                <BlackboardPage
                  history={blackboard.blackboardHistory}
                  showHistory={showHistory}
                  onToggleHistory={() => setShowHistory(!showHistory)}
                  getScoreColor={getScoreColor}
                />
                <section className="legacy-panel">
                  <h2 className="legacy-panel-title">{t("review.title")}</h2>
                  <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, lineHeight: 1.6, marginBottom: 14 }}>{t("review.lead")}</p>
                  {blackboard.pageNotice && <div className="legacy-error-box">{blackboard.pageNotice}</div>}
                  <div className="legacy-action-stack">
                    <button className="legacy-primary-button" onClick={reportActions.generateReport} disabled={reportActions.reportLoading}>
                      {reportActions.reportLoading ? t("common.loading") : t("report.generate")}
                    </button>
                    <button className="legacy-secondary-button" onClick={reportActions.exportReport} disabled={reportActions.exportLoading}>
                      {reportActions.exportLoading ? t("common.loading") : t("report.export")}
                    </button>
                    <button className="legacy-warn-button" onClick={reportActions.clearHistory} disabled={reportActions.clearLoading}>
                      {reportActions.clearLoading ? t("common.loading") : t("report.clear")}
                    </button>
                    <button className="legacy-danger-outline-button" onClick={reportActions.resetSession} disabled={reportActions.resetLoading}>
                      {reportActions.resetLoading ? t("common.loading") : t("report.reset")}
                    </button>
                  </div>
                  <ReportPage report={reportActions.report} exportedMarkdown={reportActions.exportedMarkdown} getScoreColor={getScoreColor} />
                </section>
              </main>
            )}

            <UpdateNotification />

            {isSettingsOpen && (
              <Suspense fallback={null}>
                <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
              </Suspense>
            )}

            <Dialog open={showStealthGuide} onOpenChange={setShowStealthGuide}>
              <DialogContent className="bg-black/92 text-white border border-white/15">
                <DialogHeader>
                  <DialogTitle>即将进入隐形模式</DialogTitle>
                  <DialogDescription>
                    隐形模式适合面试或屏幕共享场景。进入后窗口会更偏向快捷键控制，并保持当前大小和位置不变。
                  </DialogDescription>
                </DialogHeader>
                <div className="stealth-guide-body">
                  <p>进入后请优先使用这些快捷键：</p>
                  <ul>
                    <li><strong>Ctrl + Shift + A</strong>：截图问答</li>
                    <li><strong>Ctrl + Shift + S</strong>：区域截图问答</li>
                    <li><strong>Ctrl + Shift + V</strong>：剪贴板题目问答</li>
                    <li><strong>Ctrl + B</strong>：显示 / 隐藏窗口</li>
                    <li><strong>Ctrl + Q</strong>：退出程序</li>
                    <li><strong>Ctrl + [ / ]</strong>：调整窗口透明度</li>
                    <li><strong>Ctrl + 方向键</strong>：移动窗口</li>
                  </ul>
                </div>
                <DialogFooter>
                  <button className="legacy-secondary-button" type="button" onClick={() => setShowStealthGuide(false)}>
                    取消
                  </button>
                  <button className="legacy-primary-button" type="button" onClick={confirmStealthGuide}>
                    我知道了，进入隐形模式
                  </button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Toast
              open={toastState.open}
              onOpenChange={(open) => setToastState((current) => ({ ...current, open }))}
              variant={toastState.variant}
            >
              <ToastTitle>{toastState.title}</ToastTitle>
              <ToastDescription>{toastState.description}</ToastDescription>
            </Toast>
            <ToastViewport />

            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }

              @media (max-width: 1200px) {
                main {
                  grid-template-columns: 1fr 380px !important;
                }
              }

              @media (max-width: 900px) {
                main {
                  grid-template-columns: 1fr !important;
                }
              }
            `}</style>
          </div>
        </ToastContext.Provider>
      </ToastProvider>
    </QueryClientProvider>
  )
}

export default AtlasDashboardPage
