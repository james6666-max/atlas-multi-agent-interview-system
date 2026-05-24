import { lazy, Suspense, useState, useCallback, useEffect, useRef } from "react"
import { UpdateNotification } from "./components/UpdateNotification"
import {
  QueryClient,
  QueryClientProvider
} from "@tanstack/react-query"
import {
  Toast,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport
} from "./components/ui/toast"
import { ToastContext } from "./contexts/toast"
import { WelcomeScreen } from "./components/WelcomeScreen"

const SubscribedApp = lazy(() => import("./_pages/SubscribedApp"))
const SettingsDialog = lazy(() => 
  import("./components/Settings/SettingsDialog").then(module => ({ 
    default: module.SettingsDialog 
  }))
)

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

interface PanelPosition {
  x: number
  y: number
}

function App() {
  const [localAskLoading, setLocalAskLoading] = useState(false)
  const [localAskResult, setLocalAskResult] = useState("")
  const [blackboardHistory, setBlackboardHistory] = useState<any[]>([])
  const [llmStatus, setLlmStatus] = useState<{
    answerSource: string
    model: string
    fallback: boolean | null
    llmError: string | null
  }>({
    answerSource: "unknown",
    model: "unknown",
    fallback: null,
    llmError: null
  })
  const [resumeStatus, setResumeStatus] = useState<{
    loaded: boolean | null
    path: string
    error: string | null
  }>({
    loaded: null,
    path: "unknown",
    error: null
  })
  const [jdStatus, setJdStatus] = useState<{
    loaded: boolean | null
    path: string
    error: string | null
  }>({
    loaded: null,
    path: "unknown",
    error: null
  })
  const [matchStatus, setMatchStatus] = useState<{
    score: number | null
    strongMatches: string[]
    gaps: string[]
    interviewFocus: string[]
  }>({
    score: null,
    strongMatches: [],
    gaps: [],
    interviewFocus: []
  })
  const [knowledgeStatus, setKnowledgeStatus] = useState<{
    loaded: boolean | null
    path: string
    error: string | null
  }>({
    loaded: null,
    path: "unknown",
    error: null
  })
  const [ragStatus, setRagStatus] = useState<{
    used: boolean | null
    snippetsCount: number | null
    keywords: string[]
  }>({
    used: null,
    snippetsCount: null,
    keywords: []
  })
  const [backendStatus, setBackendStatus] = useState<{
    connected: boolean | null
    error: string | null
  }>({
    connected: null,
    error: null
  })
  const [configStatus, setConfigStatus] = useState<any>(null)
  const [mockState, setMockState] = useState<any>(null)
  const [mockAnswer, setMockAnswer] = useState("")
  const [report, setReport] = useState<any>(null)
  const [exportedMarkdown, setExportedMarkdown] = useState("")
  const [voiceRecording, setVoiceRecording] = useState(false)
  const [voiceRecorder, setVoiceRecorder] = useState<MediaRecorder | null>(null)
  const [voiceChunks, setVoiceChunks] = useState<BlobPart[]>([])
  const [voiceMimeType, setVoiceMimeType] = useState("audio/webm")
  const [voiceResult, setVoiceResult] = useState("")
  const [voiceLanguage, setVoiceLanguage] = useState<"Unknown" | "Chinese" | "English">("Unknown")
  const [voiceSendLoading, setVoiceSendLoading] = useState(false)
  const [manualInput, setManualInput] = useState("")
  const [manualLoading, setManualLoading] = useState(false)
  const [mockLoading, setMockLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)
  const [pageNotice, setPageNotice] = useState("")
  const [activeTab, setActiveTab] = useState<"ocr" | "voice" | "manual">("ocr")
  const [rightPanelPos, setRightPanelPos] = useState<PanelPosition>({ x: 0, y: 0 })
  const [leftPanelPos, setLeftPanelPos] = useState<PanelPosition>({ x: 0, y: 0 })
  const [isDraggingRight, setIsDraggingRight] = useState(false)
  const [isDraggingLeft, setIsDraggingLeft] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [showHistory, setShowHistory] = useState(true)
  const rightPanelRef = useRef<HTMLDivElement>(null)
  const leftPanelRef = useRef<HTMLDivElement>(null)

  const [toastState, setToastState] = useState({
    open: false,
    title: "",
    description: "",
    variant: "neutral" as "neutral" | "success" | "error"
  })
  const [credits, setCredits] = useState<number>(999)

  const getPreferredAudioMimeType = () => {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus"
    ]

    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ""
  }

  const dataUrlToFile = async (dataUrl: string, filename: string) => {
    const response = await fetch(dataUrl)
    const blob = await response.blob()
    const type = blob.type || "image/png"
    return new File([blob], filename, { type })
  }

  const postImageFileToAtlas = async (image: Blob, filename = "screenshot.png") => {
    const formData = new FormData()
    formData.append("image", image, filename)
    formData.append("language", "Unknown")
    formData.append("source", "ocr")

    const res = await fetch("http://127.0.0.1:8000/ask_image_file", {
      method: "POST",
      body: formData
    })

    const text = await res.text()
    let json: any = {}
    try {
      json = text ? JSON.parse(text) : {}
    } catch {
      json = {}
    }
    if (!res.ok || json?.detail) {
      throw new Error(json?.detail ?? text ?? `HTTP ${res.status}`)
    }

    return json
  }

  const getLlmStatusTone = () => {
    if (llmStatus.fallback === true) {
      return {
        label: "Fallback",
        color: "#f97316",
        background: "rgba(249,115,22,0.12)",
        border: "rgba(249,115,22,0.35)"
      }
    }

    if (llmStatus.fallback === false) {
      return {
        label: "Live LLM",
        color: "#22c55e",
        background: "rgba(34,197,94,0.12)",
        border: "rgba(34,197,94,0.3)"
      }
    }

    return {
      label: "Unknown",
      color: "rgba(255,255,255,0.55)",
      background: "rgba(255,255,255,0.06)",
      border: "rgba(255,255,255,0.12)"
    }
  }

  const formatLlmValue = (value: unknown) => {
    if (value === null || value === undefined || value === "") return "none"
    return String(value)
  }

  const getResumeStatusTone = () => {
    if (resumeStatus.loaded === true) {
      return {
        label: "loaded",
        color: "#22c55e",
        background: "rgba(34,197,94,0.1)",
        border: "rgba(34,197,94,0.28)"
      }
    }

    if (resumeStatus.loaded === false) {
      return {
        label: "missing",
        color: "#f97316",
        background: "rgba(249,115,22,0.1)",
        border: "rgba(249,115,22,0.32)"
      }
    }

    return {
      label: "unknown",
      color: "rgba(255,255,255,0.55)",
      background: "rgba(255,255,255,0.055)",
      border: "rgba(255,255,255,0.12)"
    }
  }

  const getJdStatusTone = () => {
    if (jdStatus.loaded === true) {
      return {
        label: "loaded",
        color: "#22c55e",
        background: "rgba(34,197,94,0.1)",
        border: "rgba(34,197,94,0.28)"
      }
    }

    if (jdStatus.loaded === false) {
      return {
        label: "missing",
        color: "#f97316",
        background: "rgba(249,115,22,0.1)",
        border: "rgba(249,115,22,0.32)"
      }
    }

    return {
      label: "unknown",
      color: "rgba(255,255,255,0.55)",
      background: "rgba(255,255,255,0.055)",
      border: "rgba(255,255,255,0.12)"
    }
  }

  const getKnowledgeStatusTone = () => {
    if (knowledgeStatus.loaded === true) {
      return { label: "loaded", color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
    }
    if (knowledgeStatus.loaded === false) {
      return { label: "missing", color: "#f97316", background: "rgba(249,115,22,0.1)", border: "rgba(249,115,22,0.32)" }
    }
    return { label: "unknown", color: "rgba(255,255,255,0.55)", background: "rgba(255,255,255,0.055)", border: "rgba(255,255,255,0.12)" }
  }

  const getRagTone = () => {
    if (ragStatus.used === true) {
      return { label: "used", color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
    }
    if (ragStatus.used === false) {
      return { label: "unused", color: "#94a3b8", background: "rgba(255,255,255,0.055)", border: "rgba(255,255,255,0.12)" }
    }
    return { label: "unknown", color: "rgba(255,255,255,0.55)", background: "rgba(255,255,255,0.055)", border: "rgba(255,255,255,0.12)" }
  }

  const getBackendTone = () => {
    if (backendStatus.connected === true) {
      return { label: "Connected", color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
    }
    if (backendStatus.connected === false) {
      return { label: "Disconnected", color: "#ef4444", background: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.32)" }
    }
    return { label: "Unknown", color: "rgba(255,255,255,0.55)", background: "rgba(255,255,255,0.055)", border: "rgba(255,255,255,0.12)" }
  }

  const getMemoryTone = () => {
    const used = blackboardHistory.length > 1
    return used
      ? { label: "used", color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.28)" }
      : { label: "unused", color: "#94a3b8", background: "rgba(255,255,255,0.055)", border: "rgba(255,255,255,0.12)" }
  }

  const getMatchTone = () => {
    if (matchStatus.score === null) {
      return {
        label: "unknown",
        color: "rgba(255,255,255,0.55)",
        background: "rgba(255,255,255,0.055)",
        border: "rgba(255,255,255,0.12)"
      }
    }

    if (matchStatus.score >= 0.7) {
      return {
        label: `${Math.round(matchStatus.score * 100)}%`,
        color: "#22c55e",
        background: "rgba(34,197,94,0.1)",
        border: "rgba(34,197,94,0.28)"
      }
    }

    if (matchStatus.score >= 0.4) {
      return {
        label: `${Math.round(matchStatus.score * 100)}%`,
        color: "#f97316",
        background: "rgba(249,115,22,0.1)",
        border: "rgba(249,115,22,0.32)"
      }
    }

    return {
      label: `${Math.round(matchStatus.score * 100)}%`,
      color: "#ef4444",
      background: "rgba(239,68,68,0.1)",
      border: "rgba(239,68,68,0.3)"
    }
  }

  const getScoreColor = (score: unknown) => {
    if (typeof score !== "number") return "rgba(255,255,255,0.55)"
    if (score >= 0.7) return "#22c55e"
    if (score >= 0.4) return "#f97316"
    return "#ef4444"
  }

  const [currentLanguage, setCurrentLanguage] = useState<string>("python")
  const [isInitialized, setIsInitialized] = useState(true)
  const [hasApiKey, setHasApiKey] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  const showToast = useCallback(
    (title: string, description: string, variant: "neutral" | "success" | "error") => {
      setToastState({ open: true, title, description, variant })
    },
    []
  )

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

  const fetchBlackboard = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/blackboard")
      if (!response.ok) {
        setBackendStatus({ connected: false, error: `HTTP ${response.status}` })
        setPageNotice("后端未连接，请先启动 FastAPI 服务。")
        return
      }
      const data = await response.json()
      setBackendStatus({ connected: true, error: null })
      setPageNotice("")
      if (data.history) {
        setBlackboardHistory(data.history.slice().reverse())
      }

      const agentState = data.agent_state || {}
      const currentType = data.current_question?.type || data.current_question?.question_type
      const preferredAgent = currentType === "Behavioral" ? "Behavioral" : "Tech/Code"
      const selectedState = agentState[preferredAgent] || agentState["Tech/Code"] || agentState["Behavioral"]
      const meta = selectedState?.meta || selectedState?.metadata || {}

      setLlmStatus({
        answerSource: meta.answer_source || "unknown",
        model: meta.model || "unknown",
        fallback: typeof meta.fallback === "boolean" ? meta.fallback : null,
        llmError: meta.llm_error || meta.error || null
      })

      setResumeStatus({
        loaded: typeof meta.resume_context_loaded === "boolean" ? meta.resume_context_loaded : null,
        path: meta.resume_path || "unknown",
        error: meta.resume_error || null
      })

      setJdStatus({
        loaded: typeof meta.jd_context_loaded === "boolean" ? meta.jd_context_loaded : null,
        path: meta.jd_path || "unknown",
        error: meta.jd_error || null
      })

      const match = meta.resume_jd_match || {}
      setMatchStatus({
        score: typeof match.match_score === "number" ? match.match_score : null,
        strongMatches: Array.isArray(match.strong_matches) ? match.strong_matches : [],
        gaps: Array.isArray(match.gaps) ? match.gaps : [],
        interviewFocus: Array.isArray(match.interview_focus) ? match.interview_focus : []
      })

      setKnowledgeStatus({
        loaded: typeof meta.knowledge_context_loaded === "boolean" ? meta.knowledge_context_loaded : null,
        path: meta.knowledge_path || "unknown",
        error: meta.knowledge_error || null
      })

      setRagStatus({
        used: typeof meta.rag_used === "boolean" ? meta.rag_used : null,
        snippetsCount: typeof meta.rag_snippets_count === "number" ? meta.rag_snippets_count : null,
        keywords: Array.isArray(meta.rag_query_keywords) ? meta.rag_query_keywords : []
      })
    } catch (err) {
      console.error("Failed to fetch blackboard:", err)
      setBackendStatus({ connected: false, error: "Backend not connected" })
      setPageNotice("后端未连接，请先启动 FastAPI 服务。")
    }
  }

  const fetchConfigStatus = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/config/status")
      if (!response.ok) {
        setConfigStatus(null)
        return
      }
      setConfigStatus(await response.json())
    } catch (err) {
      console.error("Failed to fetch config status:", err)
      setConfigStatus(null)
    }
  }

  useEffect(() => {
    fetchBlackboard()
    fetchConfigStatus()
    const interval = setInterval(() => {
      fetchBlackboard()
      fetchConfigStatus()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleMouseDown = (e: React.MouseEvent, panel: "right" | "left") => {
    e.preventDefault()
    const rect = panel === "right" 
      ? rightPanelRef.current?.getBoundingClientRect()
      : leftPanelRef.current?.getBoundingClientRect()
    if (rect) {
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      })
      if (panel === "right") {
        setIsDraggingRight(true)
      } else {
        setIsDraggingLeft(true)
      }
    }
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingRight) {
        setRightPanelPos({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        })
      }
      if (isDraggingLeft) {
        setLeftPanelPos({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        })
      }
    }

    const handleMouseUp = () => {
      setIsDraggingRight(false)
      setIsDraggingLeft(false)
    }

    if (isDraggingRight || isDraggingLeft) {
      document.addEventListener("mousemove", handleMouseMove)
      document.addEventListener("mouseup", handleMouseUp)
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
    }
  }, [isDraggingRight, isDraggingLeft, dragOffset])

  const handleLocalAskImage = async () => {
    try {
      setLocalAskLoading(true)

      if (window.electronAPI?.triggerScreenshot) {
        setLocalAskResult("正在截图...")
        const result = await new Promise<any>((resolve, reject) => {
          let finished = false
          const unsubscribe = window.electronAPI.onScreenshotTaken(async (data: { path: string; preview: string }) => {
            if (finished) return
            finished = true
            try {
              setLocalAskResult("姝ｅ湪涓婁紶鎴浘鍒?OCR...")
              const imageFile = await dataUrlToFile(data.preview, "screenshot.png")
              const json = await postImageFileToAtlas(imageFile, imageFile.name)
              if (typeof unsubscribe === "function") unsubscribe()
              resolve(json)
            } catch (error) {
              if (typeof unsubscribe === "function") unsubscribe()
              reject(error)
            }
          })
          window.electronAPI.triggerScreenshot()
            .then((screenshotResult: any) => {
              if (screenshotResult?.error) {
                if (typeof unsubscribe === "function") unsubscribe()
                reject(new Error(screenshotResult.error))
              }
            })
            .catch((error: any) => {
              if (typeof unsubscribe === "function") unsubscribe()
              reject(error)
            })

          window.setTimeout(() => {
            if (finished) return
            finished = true
            if (typeof unsubscribe === "function") unsubscribe()
            reject(new Error("Screenshot timed out. Please try again."))
          }, 15000)
        })

        if (result?.detail) {
          setLocalAskResult(`请求失败：${result.detail}`)
          return
        }

        const critic = result.critic || {}
        const criticSection = critic.clarity_score ? [
          "",
          "【Critic Review】",
          `清晰度：${(critic.clarity_score * 100).toFixed(0)}%`,
          `正确性：${(critic.correctness_score * 100).toFixed(0)}%`,
          `人类口吻：${(critic.human_like_score * 100).toFixed(0)}%`,
          `隐私风险：${(critic.privacy_score * 100).toFixed(0)}%`,
          `JD Alignment：${typeof critic.jd_alignment_score === "number" ? `${(critic.jd_alignment_score * 100).toFixed(0)}%` : "unknown"}`,
          `JD Notes：${Array.isArray(critic.jd_alignment_notes) && critic.jd_alignment_notes.length ? critic.jd_alignment_notes.join("；") : "none"}`,
          "",
          `改进建议：${critic.improved_answer_suggestion ?? ""}`
        ].join("\n") : ""
        
        setLocalAskResult([
          `✓ 成功`,
          `类型：${result.question_type ?? ""} | Agent：${result.selected_agent ?? ""}`,
          "",
          `回答：${result.answer ?? ""}`,
          criticSection
        ].join("\n"))

        fetchBlackboard()
      } else {
        setLocalAskResult("请选择图片文件...")
        const input = document.createElement("input")
        input.type = "file"
        input.accept = "image/*"
        
        const file = await new Promise<File | null>((resolve) => {
          input.onchange = () => resolve(input.files?.[0] || null)
          input.click()
        })
        
        if (!file) {
          setLocalAskResult("已取消选择")
          return
        }
        
        setLocalAskResult("正在上传图片...")
        const result = await postImageFileToAtlas(file, file.name)
        
        if (result?.detail) {
          setLocalAskResult(`请求失败：${result.detail}`)
          return
        }

        const critic = result.critic || {}
        const criticSection = critic.clarity_score ? [
          "",
          "【Critic Review】",
          `清晰度：${(critic.clarity_score * 100).toFixed(0)}%`,
          `正确性：${(critic.correctness_score * 100).toFixed(0)}%`,
          `人类口吻：${(critic.human_like_score * 100).toFixed(0)}%`,
          `隐私风险：${(critic.privacy_score * 100).toFixed(0)}%`,
          `JD Alignment：${typeof critic.jd_alignment_score === "number" ? `${(critic.jd_alignment_score * 100).toFixed(0)}%` : "unknown"}`,
          `JD Notes：${Array.isArray(critic.jd_alignment_notes) && critic.jd_alignment_notes.length ? critic.jd_alignment_notes.join("；") : "none"}`,
          "",
          `改进建议：${critic.improved_answer_suggestion ?? ""}`
        ].join("\n") : ""
        
        setLocalAskResult([
          `✓ 成功`,
          `类型：${result.question_type ?? ""} | Agent：${result.selected_agent ?? ""}`,
          "",
          `回答：${result.answer ?? ""}`,
          criticSection
        ].join("\n"))

        fetchBlackboard()
      }
    } catch (error: any) {
      console.error("Local ask image failed:", error)
      setLocalAskResult([
        "✗ 截图问答失败",
        "",
        "请检查 FastAPI 后端是否已启动",
        `错误：${error?.message ?? String(error)}`
      ].join("\n"))
    } finally {
      setLocalAskLoading(false)
    }
  }

  const handleManualSubmit = async () => {
    if (!manualInput.trim()) {
      setLocalAskResult("请输入问题")
      return
    }
    try {
      setManualLoading(true)
      setLocalAskResult("正在处理...")

      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: manualInput, language: "Unknown", source: "manual_input" })
      })
      const result = await res.json()

      if (!res.ok || result?.detail) {
        setLocalAskResult(`请求失败：${result?.detail ?? res.statusText}`)
        return
      }

      const critic = result.critic || {}
      const criticSection = critic.clarity_score ? [
        "",
        "【Critic Review】",
        `清晰度：${(critic.clarity_score * 100).toFixed(0)}%`,
        `正确性：${(critic.correctness_score * 100).toFixed(0)}%`,
        `人类口吻：${(critic.human_like_score * 100).toFixed(0)}%`,
        `隐私风险：${(critic.privacy_score * 100).toFixed(0)}%`,
        `JD Alignment：${typeof critic.jd_alignment_score === "number" ? `${(critic.jd_alignment_score * 100).toFixed(0)}%` : "unknown"}`,
        `JD Notes：${Array.isArray(critic.jd_alignment_notes) && critic.jd_alignment_notes.length ? critic.jd_alignment_notes.join("；") : "none"}`,
        "",
        `改进建议：${critic.improved_answer_suggestion ?? ""}`
      ].join("\n") : ""

      setLocalAskResult([
        `✓ 成功`,
        `类型：${result.question_type ?? ""} | Agent：${result.selected_agent ?? ""}`,
        "",
        `回答：${result.answer ?? ""}`,
        criticSection
      ].join("\n"))

      setManualInput("")
      fetchBlackboard()
    } catch (error: any) {
      console.error("Manual ask failed:", error)
      setLocalAskResult([
        "✗ 请求失败",
        "",
        "请检查 FastAPI 后端是否已启动",
        `错误：${error?.message ?? String(error)}`
      ].join("\n"))
    } finally {
      setManualLoading(false)
    }
  }

  const handleStartWhisperRecording = async () => {
    try {
      setVoiceResult("正在请求麦克风权限...")
      setVoiceChunks([])
      setVoiceMimeType("audio/webm")
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      const preferredMimeType = getPreferredAudioMimeType()
      const recorder = preferredMimeType
        ? new MediaRecorder(stream, { mimeType: preferredMimeType })
        : new MediaRecorder(stream)
      setVoiceMimeType(recorder.mimeType || preferredMimeType || "audio/webm")
      const chunks: BlobPart[] = []

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunks.push(event.data)
      }
      recorder.onstart = () => {
        setVoiceRecording(true)
        setVoiceResult("🔴 录音中，请开始说话...")
      }
      recorder.onerror = (event: any) => {
        setVoiceResult(`录音错误：${event?.error?.message ?? "unknown error"}`)
        setVoiceRecording(false)
      }
      recorder.onstop = () => {
        setVoiceChunks(chunks)
        setVoiceRecording(false)
        setVoiceRecorder(null)
        stream.getTracks().forEach((track) => track.stop())
        setVoiceResult("⏹ 录音已停止，可以发送到 Whisper")
      }

      recorder.start(1000)
      setVoiceRecorder(recorder)
    } catch (error: any) {
      console.error("Start recording failed:", error)
      setVoiceResult([
        "✗ 启动录音失败",
        "",
        "请检查麦克风权限",
        `错误：${error?.message ?? String(error)}`
      ].join("\n"))
      setVoiceRecording(false)
    }
  }

  const handleStopWhisperRecording = () => {
    if (!voiceRecorder) {
      setVoiceResult("当前没有正在运行的录音")
      return
    }
    if (voiceRecorder.state === "recording") {
      try {
        voiceRecorder.requestData()
      } catch (error) {
        console.warn("Failed to flush recorder data before stopping:", error)
      }
    }
    voiceRecorder.stop()
  }

  const handleSendAudioToWhisper = async () => {
    setVoiceSendLoading(true)
    if (!voiceChunks.length) {
      setVoiceResult("没有可发送的录音数据，请先录音")
      return
    }
    try {
      setVoiceResult("正在上传音频到本地 Whisper...")
      const audioBlob = new Blob(voiceChunks, { type: voiceMimeType || "audio/webm" })
      if (audioBlob.size === 0) {
        setVoiceResult("褰曢煶鏁版嵁涓虹┖锛岃閲嶆柊褰曢煶")
        return
      }
      const audioExt = voiceMimeType.includes("mp4")
        ? "m4a"
        : voiceMimeType.includes("ogg")
          ? "ogg"
          : "webm"
      const formData = new FormData()
      formData.append("audio", audioBlob, `interview-audio.${audioExt}`)
      formData.append("language", voiceLanguage)
      formData.append("source", "stt")

      const res = await fetch("http://127.0.0.1:8000/ask_audio", { method: "POST", body: formData })
      const json = await res.json()

      if (!res.ok || json?.detail) {
        setVoiceResult(`请求失败：${json?.detail ?? res.statusText}`)
        return
      }

      const critic = json.critic || {}
      const criticSection = critic.clarity_score ? [
        "",
        "【Critic Review】",
        `清晰度：${(critic.clarity_score * 100).toFixed(0)}%`,
        `正确性：${(critic.correctness_score * 100).toFixed(0)}%`,
        `人类口吻：${(critic.human_like_score * 100).toFixed(0)}%`,
        `隐私风险：${(critic.privacy_score * 100).toFixed(0)}%`,
        `JD Alignment：${typeof critic.jd_alignment_score === "number" ? `${(critic.jd_alignment_score * 100).toFixed(0)}%` : "unknown"}`,
        `JD Notes：${Array.isArray(critic.jd_alignment_notes) && critic.jd_alignment_notes.length ? critic.jd_alignment_notes.join("；") : "none"}`,
        "",
        `改进建议：${critic.improved_answer_suggestion ?? ""}`
      ].join("\n") : ""

      setVoiceResult([
        `✓ 识别成功`,
        `类型：${json.question_type ?? ""} | Agent：${json.selected_agent ?? ""}`,
        "",
        `问题：${json.question ?? ""}`,
        "",
        `回答：${json.answer ?? ""}`,
        criticSection
      ].join("\n"))

      fetchBlackboard()
      setVoiceSendLoading(false)
    } catch (error: any) {
      console.error("Send audio to Whisper failed:", error)
      setVoiceSendLoading(false)
      setVoiceResult([
        "✗ 语音模拟面试失败",
        "",
        "请检查后端和 Whisper 服务",
        `错误：${error?.message ?? String(error)}`
      ].join("\n"))
    }
  }

  useEffect(() => {
    const checkApiKey = async () => {
      try {
        if (window.electronAPI?.checkApiKey) {
          const hasKey = await window.electronAPI.checkApiKey()
          setHasApiKey(hasKey)
          if (!hasKey) {
            setTimeout(() => setIsSettingsOpen(true), 1000)
          }
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
          if (config?.language) {
            updateLanguage(config.language)
          } else {
            updateLanguage("python")
          }
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

  const handleOpenSettings = useCallback(() => setIsSettingsOpen(true), [])
  const handleCloseSettings = useCallback((open: boolean) => setIsSettingsOpen(open), [])

  const startMockInterview = async () => {
    try {
      setMockLoading(true)
      const res = await fetch("http://127.0.0.1:8000/mock/start", { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setMockState(await res.json())
      setMockAnswer("")
    } catch (error: any) {
      setPageNotice(`Mock Interview 启动失败：${error?.message ?? String(error)}`)
    } finally {
      setMockLoading(false)
    }
  }

  const submitMockAnswer = async () => {
    try {
      setMockLoading(true)
      const res = await fetch("http://127.0.0.1:8000/mock/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: mockAnswer })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setMockState(await res.json())
      setMockAnswer("")
    } catch (error: any) {
      setPageNotice(`Mock Interview 提交失败：${error?.message ?? String(error)}`)
    } finally {
      setMockLoading(false)
    }
  }

  const generateReport = async () => {
    try {
      setReportLoading(true)
      const res = await fetch("http://127.0.0.1:8000/report/session")
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setReport(await res.json())
    } catch (error: any) {
      setPageNotice(`生成报告失败：${error?.message ?? String(error)}`)
    } finally {
      setReportLoading(false)
    }
  }

  const exportReport = async () => {
    try {
      setExportLoading(true)
      const res = await fetch("http://127.0.0.1:8000/report/export_markdown")
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setExportedMarkdown(await res.text())
    } catch (error: any) {
      setPageNotice(`导出报告失败：${error?.message ?? String(error)}`)
    } finally {
      setExportLoading(false)
    }
  }

  const clearHistory = async () => {
    if (!window.confirm("Clear Blackboard history?")) return
    try {
      setClearLoading(true)
      const res = await fetch("http://127.0.0.1:8000/blackboard/clear_history", { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      fetchBlackboard()
    } catch (error: any) {
      setPageNotice(`清空历史失败：${error?.message ?? String(error)}`)
    } finally {
      setClearLoading(false)
    }
  }

  const resetSession = async () => {
    if (!window.confirm("Reset current Atlas session?")) return
    try {
      setResetLoading(true)
      const res = await fetch("http://127.0.0.1:8000/blackboard/reset_session", { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setReport(null)
      setExportedMarkdown("")
      fetchBlackboard()
    } catch (error: any) {
      setPageNotice(`重置 Session 失败：${error?.message ?? String(error)}`)
    } finally {
      setResetLoading(false)
    }
  }

  const llmTone = getLlmStatusTone()
  const resumeTone = getResumeStatusTone()
  const jdTone = getJdStatusTone()
  const matchTone = getMatchTone()
  const knowledgeTone = getKnowledgeStatusTone()
  const ragTone = getRagTone()
  const backendTone = getBackendTone()
  const memoryTone = getMemoryTone()

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

            {/* Header */}
            <header style={{
              height: 48,
              background: "rgba(0,0,0,0.3)",
              backdropFilter: "blur(20px)",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 20px",
              WebkitAppRegion: "drag"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: 14
                }}>A</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>Atlas Interview</div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>Multi-Agent AI Interview System</div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, WebkitAppRegion: "no-drag" }}>
                <button
                  onClick={() => window.open("http://127.0.0.1:8000/blackboard", "_blank")}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 6,
                    border: "1px solid rgba(255,255,255,0.15)",
                    background: "rgba(255,255,255,0.05)",
                    color: "white",
                    fontSize: 12,
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                >
                  📋 Blackboard
                </button>
                <button
                  onClick={handleOpenSettings}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 6,
                    border: "1px solid rgba(255,255,255,0.15)",
                    background: "rgba(255,255,255,0.05)",
                    color: "white",
                    fontSize: 12,
                    cursor: "pointer",
                    transition: "all 0.2s"
                  }}
                >
                  ⚙️ 设置
                </button>
              </div>
            </header>

            {/* Main Content */}
            <main style={{
              padding: "24px",
              display: "grid",
              gridTemplateColumns: "minmax(300px, 1fr) minmax(320px, 400px) minmax(320px, 400px)",
              gap: 20,
              maxWidth: 1600,
              margin: "0 auto",
              width: "100%",
              minHeight: "calc(100vh - 80px)"
            }}>
              {/* History Panel - Left */}
              <div style={{
                background: "rgba(255,255,255,0.03)",
                borderRadius: 16,
                border: "1px solid rgba(255,255,255,0.08)",
                padding: 20,
                backdropFilter: "blur(10px)"
              }}>
                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 16
                }}>
                  <h2 style={{ fontSize: 16, fontWeight: 600 }}>📜 历史记录</h2>
                  <button
                    onClick={() => setShowHistory(!showHistory)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "rgba(255,255,255,0.6)",
                      cursor: "pointer",
                      fontSize: 14
                    }}
                  >
                    {showHistory ? "▲ 收起" : "▼ 展开"}
                  </button>
                </div>

                {showHistory && (
                  <div style={{ maxHeight: 500, overflowY: "auto" }}>
                    {blackboardHistory.length === 0 && (
                      <div style={{
                        textAlign: "center",
                        padding: 40,
                        color: "rgba(255,255,255,0.4)",
                        fontSize: 13
                      }}>
                        暂无历史记录
                      </div>
                    )}
                    {blackboardHistory.slice(0, 10).map((item, index) => (
                      <div key={index} style={{
                        marginBottom: 12,
                        padding: 14,
                        borderRadius: 10,
                        background: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.06)",
                        transition: "all 0.2s"
                      }}>
                        <div style={{
                          display: "flex",
                          gap: 8,
                          marginBottom: 8,
                          flexWrap: "wrap"
                        }}>
                          <span style={{
                            padding: "2px 8px",
                            borderRadius: 4,
                            background: "rgba(102,126,234,0.2)",
                            color: "#a5b4fc",
                            fontSize: 11,
                            fontWeight: 500
                          }}>{item.question_type || "Unknown"}</span>
                          <span style={{
                            padding: "2px 8px",
                            borderRadius: 4,
                            background: "rgba(34,197,94,0.2)",
                            color: "#86efac",
                            fontSize: 11,
                            fontWeight: 500
                          }}>{item.agent || "Unknown"}</span>
                          <span style={{
                            padding: "2px 8px",
                            borderRadius: 4,
                            background: "rgba(255,255,255,0.08)",
                            color: "rgba(255,255,255,0.5)",
                            fontSize: 10
                          }}>{item.source || "unknown"}</span>
                        </div>
                        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.85)", lineHeight: 1.5, marginBottom: 8 }}>
                          {item.question}
                        </div>
                        {item.critic && (
                          <div style={{
                            marginTop: 10,
                            padding: 10,
                            borderRadius: 8,
                            background: "rgba(239,68,68,0.08)",
                            border: "1px solid rgba(239,68,68,0.15)"
                          }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: "#f87171", marginBottom: 8 }}>
                              🔍 Critic Review
                            </div>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                              <div style={{ fontSize: 11 }}>
                                <span style={{ color: "rgba(255,255,255,0.5)" }}>Final Score</span>
                                <div style={{ color: getScoreColor(typeof item.critic.final_score === "number" ? item.critic.final_score / 100 : null), fontWeight: 600 }}>{typeof item.critic.final_score === "number" ? item.critic.final_score : "unknown"}</div>
                              </div>
                              <div style={{ fontSize: 11 }}>
                                <span style={{ color: "rgba(255,255,255,0.5)" }}>清晰度</span>
                                <div style={{ color: "#fbbf24", fontWeight: 600 }}>{(item.critic.clarity_score * 100).toFixed(0)}%</div>
                              </div>
                              <div style={{ fontSize: 11 }}>
                                <span style={{ color: "rgba(255,255,255,0.5)" }}>正确性</span>
                                <div style={{ color: "#22c55e", fontWeight: 600 }}>{(item.critic.correctness_score * 100).toFixed(0)}%</div>
                              </div>
                              <div style={{ fontSize: 11 }}>
                                <span style={{ color: "rgba(255,255,255,0.5)" }}>人类口吻</span>
                                <div style={{ color: "#38bdf8", fontWeight: 600 }}>{(item.critic.human_like_score * 100).toFixed(0)}%</div>
                              </div>
                              <div style={{ fontSize: 11 }}>
                                <span style={{ color: "rgba(255,255,255,0.5)" }}>隐私风险</span>
                                <div style={{ color: "#a855f7", fontWeight: 600 }}>{(item.critic.privacy_score * 100).toFixed(0)}%</div>
                              </div>
                              <div style={{ fontSize: 11 }}>
                                <span style={{ color: "rgba(255,255,255,0.5)" }}>JD Alignment</span>
                                <div style={{ color: getScoreColor(item.critic.jd_alignment_score), fontWeight: 600 }}>
                                  {typeof item.critic.jd_alignment_score === "number"
                                    ? `${(item.critic.jd_alignment_score * 100).toFixed(0)}%`
                                    : "unknown"}
                                </div>
                              </div>
                            </div>
                            {Array.isArray(item.critic.jd_alignment_notes) && item.critic.jd_alignment_notes.length > 0 && (
                              <div style={{
                                marginTop: 8,
                                fontSize: 10,
                                color: "rgba(255,255,255,0.62)",
                                lineHeight: 1.45
                              }}>
                                <div style={{ color: "rgba(255,255,255,0.72)", fontWeight: 600, marginBottom: 4 }}>JD Notes</div>
                                {item.critic.jd_alignment_notes.slice(0, 3).map((note: string, noteIndex: number) => (
                                  <div key={`${note}-${noteIndex}`} style={{ overflowWrap: "anywhere" }}>- {note}</div>
                                ))}
                              </div>
                            )}
                            <div style={{ marginTop: 8, fontSize: 10, color: "rgba(255,255,255,0.62)", lineHeight: 1.45 }}>
                              <div>Main Weakness: {item.critic.main_weakness || "unknown"}</div>
                              <div>Should Rewrite: {typeof item.critic.should_rewrite === "boolean" ? String(item.critic.should_rewrite) : "unknown"}</div>
                              <div>Rewrite Strategy: {item.critic.rewrite_strategy || "none"}</div>
                              {Array.isArray(item.critic.specific_issues) && item.critic.specific_issues.length > 0 && (
                                <div style={{ marginTop: 4 }}>Issues: {item.critic.specific_issues.slice(0, 3).join(" / ")}</div>
                              )}
                              {item.critic.human_like_rewrite?.speaking_version && (
                                <div style={{ marginTop: 6 }}>Human-like Rewrite: {item.critic.human_like_rewrite.speaking_version.slice(0, 140)}...</div>
                              )}
                              {item.critic.followup_questions?.followups?.length > 0 && (
                                <div style={{ marginTop: 6 }}>Likely Follow-ups: {item.critic.followup_questions.followups.slice(0, 3).join(" / ")}</div>
                              )}
                            </div>
                            {item.critic.improved_answer_suggestion && (
                              <div style={{
                                marginTop: 8,
                                fontSize: 10,
                                color: "rgba(255,255,255,0.5)",
                                fontStyle: "italic"
                              }}>
                                💡 {item.critic.improved_answer_suggestion.substring(0, 80)}...
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Input Panel - Middle */}
              <div style={{
                background: "rgba(255,255,255,0.03)",
                borderRadius: 16,
                border: "1px solid rgba(255,255,255,0.08)",
                padding: 20,
                backdropFilter: "blur(10px)"
              }}>
                <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>💬 输入问题</h2>
                
                {/* LLM Status */}
                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 16,
                  padding: 14,
                  borderRadius: 10,
                  background: llmTone.background,
                  border: `1px solid ${llmTone.border}`
                }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    marginBottom: 10
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>
                      LLM Status
                    </div>
                    <div style={{
                      padding: "3px 8px",
                      borderRadius: 999,
                      background: "rgba(0,0,0,0.18)",
                      color: llmTone.color,
                      fontSize: 11,
                      fontWeight: 700
                    }}>
                      {llmTone.label}
                    </div>
                  </div>
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr",
                    gap: "6px 10px",
                    fontSize: 12,
                    lineHeight: 1.35
                  }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Source</span>
                    <span style={{ color: llmTone.color, fontWeight: 650 }}>{formatLlmValue(llmStatus.answerSource)}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Model</span>
                    <span style={{ color: "rgba(255,255,255,0.86)", overflowWrap: "anywhere" }}>{formatLlmValue(llmStatus.model)}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Fallback</span>
                    <span style={{ color: "rgba(255,255,255,0.86)" }}>
                      {llmStatus.fallback === null ? "unknown" : String(llmStatus.fallback)}
                    </span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Error</span>
                    <span style={{ color: llmStatus.llmError ? "#fca5a5" : "rgba(255,255,255,0.72)", overflowWrap: "anywhere" }}>
                      {llmStatus.llmError || "none"}
                    </span>
                  </div>
                </div>

                {/* Resume Status */}
                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 16,
                  padding: 14,
                  borderRadius: 10,
                  background: resumeTone.background,
                  border: `1px solid ${resumeTone.border}`
                }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    marginBottom: 10
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>
                      Resume Status
                    </div>
                    <div style={{
                      padding: "3px 8px",
                      borderRadius: 999,
                      background: "rgba(0,0,0,0.18)",
                      color: resumeTone.color,
                      fontSize: 11,
                      fontWeight: 700
                    }}>
                      {resumeTone.label}
                    </div>
                  </div>
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr",
                    gap: "6px 10px",
                    fontSize: 12,
                    lineHeight: 1.35
                  }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Context</span>
                    <span style={{ color: resumeTone.color, fontWeight: 650 }}>{resumeTone.label}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Path</span>
                    <span style={{ color: "rgba(255,255,255,0.86)", overflowWrap: "anywhere" }}>
                      {resumeStatus.path || "unknown"}
                    </span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Error</span>
                    <span style={{ color: resumeStatus.error ? "#fca5a5" : "rgba(255,255,255,0.72)", overflowWrap: "anywhere" }}>
                      {resumeStatus.error || "none"}
                    </span>
                  </div>
                </div>

                {/* JD Status */}
                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 16,
                  padding: 14,
                  borderRadius: 10,
                  background: jdTone.background,
                  border: `1px solid ${jdTone.border}`
                }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    marginBottom: 10
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>
                      JD Status
                    </div>
                    <div style={{
                      padding: "3px 8px",
                      borderRadius: 999,
                      background: "rgba(0,0,0,0.18)",
                      color: jdTone.color,
                      fontSize: 11,
                      fontWeight: 700
                    }}>
                      {jdTone.label}
                    </div>
                  </div>
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "auto 1fr",
                    gap: "6px 10px",
                    fontSize: 12,
                    lineHeight: 1.35
                  }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Context</span>
                    <span style={{ color: jdTone.color, fontWeight: 650 }}>{jdTone.label}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Path</span>
                    <span style={{ color: "rgba(255,255,255,0.86)", overflowWrap: "anywhere", wordBreak: "break-all" }}>
                      {jdStatus.path || "unknown"}
                    </span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Error</span>
                    <span style={{ color: jdStatus.error ? "#fca5a5" : "rgba(255,255,255,0.72)", overflowWrap: "anywhere", wordBreak: "break-all" }}>
                      {jdStatus.error || "none"}
                    </span>
                  </div>
                </div>

                {/* Resume-JD Match */}
                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 16,
                  padding: 14,
                  borderRadius: 10,
                  background: matchTone.background,
                  border: `1px solid ${matchTone.border}`
                }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    marginBottom: 10
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>
                      Resume-JD Match
                    </div>
                    <div style={{
                      padding: "3px 8px",
                      borderRadius: 999,
                      background: "rgba(0,0,0,0.18)",
                      color: matchTone.color,
                      fontSize: 11,
                      fontWeight: 700
                    }}>
                      {matchTone.label}
                    </div>
                  </div>
                  <div style={{ fontSize: 12, lineHeight: 1.45, color: "rgba(255,255,255,0.82)" }}>
                    <div>
                      <span style={{ color: "rgba(255,255,255,0.52)" }}>Score: </span>
                      <span style={{ color: matchTone.color, fontWeight: 650 }}>
                        {matchStatus.score === null ? "unknown" : `${Math.round(matchStatus.score * 100)}%`}
                      </span>
                    </div>
                    <div style={{ marginTop: 6, overflowWrap: "anywhere" }}>
                      <span style={{ color: "rgba(255,255,255,0.52)" }}>Strong Matches: </span>
                      {matchStatus.strongMatches.length ? matchStatus.strongMatches.join(", ") : "none"}
                    </div>
                    <div style={{ marginTop: 6, overflowWrap: "anywhere" }}>
                      <span style={{ color: "rgba(255,255,255,0.52)" }}>Gaps: </span>
                      {matchStatus.gaps.length ? matchStatus.gaps.join(", ") : "none"}
                    </div>
                    <div style={{ marginTop: 6 }}>
                      <span style={{ color: "rgba(255,255,255,0.52)" }}>Interview Focus: </span>
                      {matchStatus.interviewFocus.length ? (
                        <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                          {matchStatus.interviewFocus.slice(0, 3).map((focus, index) => (
                            <li key={`${focus}-${index}`} style={{ marginBottom: 4, overflowWrap: "anywhere" }}>{focus}</li>
                          ))}
                        </ul>
                      ) : "none"}
                    </div>
                  </div>
                </div>

                {/* Knowledge Status */}
                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 16,
                  padding: 14,
                  borderRadius: 10,
                  background: knowledgeTone.background,
                  border: `1px solid ${knowledgeTone.border}`
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>Knowledge Status</div>
                    <div style={{ padding: "3px 8px", borderRadius: 999, background: "rgba(0,0,0,0.18)", color: knowledgeTone.color, fontSize: 11, fontWeight: 700 }}>{knowledgeTone.label}</div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 10px", fontSize: 12, lineHeight: 1.35 }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Context</span>
                    <span style={{ color: knowledgeTone.color, fontWeight: 650 }}>{knowledgeTone.label}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Path</span>
                    <span style={{ color: "rgba(255,255,255,0.86)", overflowWrap: "anywhere", wordBreak: "break-all" }}>{knowledgeStatus.path || "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Error</span>
                    <span style={{ color: knowledgeStatus.error ? "#fca5a5" : "rgba(255,255,255,0.72)", overflowWrap: "anywhere", wordBreak: "break-all" }}>{knowledgeStatus.error || "none"}</span>
                  </div>
                </div>

                {/* RAG Status */}
                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 16,
                  padding: 14,
                  borderRadius: 10,
                  background: ragTone.background,
                  border: `1px solid ${ragTone.border}`
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 10 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>RAG Status</div>
                    <div style={{ padding: "3px 8px", borderRadius: 999, background: "rgba(0,0,0,0.18)", color: ragTone.color, fontSize: 11, fontWeight: 700 }}>{ragTone.label}</div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 10px", fontSize: 12, lineHeight: 1.35 }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>RAG</span>
                    <span style={{ color: ragTone.color, fontWeight: 650 }}>{ragTone.label}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Snippets</span>
                    <span>{ragStatus.snippetsCount === null ? "unknown" : ragStatus.snippetsCount}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Keywords</span>
                    <span style={{ overflowWrap: "anywhere" }}>{ragStatus.keywords.length ? ragStatus.keywords.join(", ") : "none"}</span>
                  </div>
                </div>

                {/* Tabs */}
                <div style={{
                  display: "flex",
                  gap: 4,
                  marginBottom: 16,
                  background: "rgba(255,255,255,0.05)",
                  padding: 4,
                  borderRadius: 10
                }}>
                  {[
                    { id: "ocr", label: "📷 截图" },
                    { id: "voice", label: "🎤 语音" },
                    { id: "manual", label: "⌨️ 文本" }
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      style={{
                        flex: 1,
                        padding: "10px 12px",
                        borderRadius: 8,
                        border: "none",
                        background: activeTab === tab.id ? "rgba(102,126,234,0.8)" : "transparent",
                        color: "white",
                        fontSize: 13,
                        fontWeight: 500,
                        cursor: "pointer",
                        transition: "all 0.2s"
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* OCR Tab */}
                {activeTab === "ocr" && (
                  <div>
                    <button
                      onClick={handleLocalAskImage}
                      disabled={localAskLoading}
                      style={{
                        width: "100%",
                        padding: "14px",
                        borderRadius: 10,
                        border: "none",
                        background: localAskLoading 
                          ? "rgba(102,126,234,0.5)" 
                          : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                        color: "white",
                        fontSize: 14,
                        fontWeight: 600,
                        cursor: localAskLoading ? "not-allowed" : "pointer",
                        transition: "all 0.2s",
                        boxShadow: localAskLoading ? "none" : "0 4px 15px rgba(102,126,234,0.3)"
                      }}
                    >
                      {localAskLoading ? "⏳ 处理中..." : "📷 截图并分析"}
                    </button>
                  </div>
                )}

                {/* Voice Tab */}
                {activeTab === "voice" && (
                  <div>
                    <select
                      value={voiceLanguage}
                      onChange={(e) => setVoiceLanguage(e.target.value as any)}
                      style={{
                        width: "100%",
                        marginBottom: 12,
                        padding: "10px 12px",
                        borderRadius: 8,
                        border: "1px solid rgba(255,255,255,0.15)",
                        background: "rgba(255,255,255,0.08)",
                        color: "white",
                        fontSize: 13
                      }}
                    >
                      <option value="Unknown">🌐 自动识别语言</option>
                      <option value="Chinese">🇨🇳 中文</option>
                      <option value="English">🇺🇸 English</option>
                    </select>

                    <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                      <button
                        onClick={handleStartWhisperRecording}
                        disabled={voiceRecording}
                        style={{
                          flex: 1,
                          padding: "12px",
                          borderRadius: 8,
                          border: "none",
                          background: voiceRecording ? "rgba(239,68,68,0.5)" : "rgba(239,68,68,0.8)",
                          color: "white",
                          fontSize: 13,
                          fontWeight: 600,
                          cursor: voiceRecording ? "not-allowed" : "pointer"
                        }}
                      >
                        {voiceRecording ? "🔴 录音中..." : "🔴 开始录音"}
                      </button>
                      <button
                        onClick={handleStopWhisperRecording}
                        disabled={!voiceRecording}
                        style={{
                          flex: 1,
                          padding: "12px",
                          borderRadius: 8,
                          border: "none",
                          background: !voiceRecording ? "rgba(255,255,255,0.1)" : "rgba(249,115,22,0.8)",
                          color: "white",
                          fontSize: 13,
                          fontWeight: 600,
                          cursor: !voiceRecording ? "not-allowed" : "pointer"
                        }}
                      >
                        ⏹ 停止
                      </button>
                    </div>

                    <button
                      onClick={handleSendAudioToWhisper}
                      disabled={voiceRecording || !voiceChunks.length || voiceSendLoading}
                      style={{
                        width: "100%",
                        padding: "12px",
                        borderRadius: 8,
                        border: "none",
                        background: voiceRecording || !voiceChunks.length || voiceSendLoading
                          ? "rgba(255,255,255,0.1)" 
                          : "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)",
                        color: "white",
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: voiceRecording || !voiceChunks.length || voiceSendLoading ? "not-allowed" : "pointer"
                      }}
                    >
                      📤 发送到 Whisper
                    </button>
                  </div>
                )}

                {/* Manual Tab */}
                {activeTab === "manual" && (
                  <div>
                    <textarea
                      value={manualInput}
                      onChange={(e) => setManualInput(e.target.value)}
                      placeholder="在这里输入你的面试问题..."
                      disabled={manualLoading}
                      style={{
                        width: "100%",
                        height: 100,
                        padding: "12px",
                        borderRadius: 10,
                        border: "1px solid rgba(255,255,255,0.15)",
                        background: "rgba(255,255,255,0.08)",
                        color: "white",
                        fontSize: 13,
                        resize: "none",
                        outline: "none",
                        marginBottom: 12,
                        fontFamily: "inherit"
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && e.ctrlKey) {
                          handleManualSubmit()
                        }
                      }}
                    />
                    <button
                      onClick={handleManualSubmit}
                      disabled={manualLoading || !manualInput.trim()}
                      style={{
                        width: "100%",
                        padding: "14px",
                        borderRadius: 10,
                        border: "none",
                        background: manualLoading || !manualInput.trim()
                          ? "rgba(102,126,234,0.5)"
                          : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                        color: "white",
                        fontSize: 14,
                        fontWeight: 600,
                        cursor: manualLoading || !manualInput.trim() ? "not-allowed" : "pointer",
                        boxShadow: manualLoading || !manualInput.trim() ? "none" : "0 4px 15px rgba(102,126,234,0.3)"
                      }}
                    >
                      {manualLoading ? "⏳ 处理中..." : "🚀 提交问题 (Ctrl+Enter)"}
                    </button>
                  </div>
                )}

                {/* Result Display */}
                {localAskResult && (
                  <div style={{
                    marginTop: 16,
                    padding: 14,
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    maxHeight: 300,
                    overflowY: "auto"
                  }}>
                    <pre style={{
                      fontSize: 12,
                      lineHeight: 1.6,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      color: "rgba(255,255,255,0.85)"
                    }}>
                      {localAskResult}
                    </pre>
                  </div>
                )}

                {/* Voice Result */}
                {voiceResult && (
                  <div style={{
                    marginTop: 16,
                    padding: 14,
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    maxHeight: 300,
                    overflowY: "auto"
                  }}>
                    <pre style={{
                      fontSize: 12,
                      lineHeight: 1.6,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      color: "rgba(255,255,255,0.85)"
                    }}>
                      {voiceResult}
                    </pre>
                  </div>
                )}
              </div>

              {/* Quick Actions Panel - Right */}
              <div style={{
                background: "rgba(255,255,255,0.03)",
                borderRadius: 16,
                border: "1px solid rgba(255,255,255,0.08)",
                padding: 20,
                backdropFilter: "blur(10px)"
              }}>
                <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>⚡ 快速操作</h2>
                
                {pageNotice && (
                  <div style={{
                    WebkitAppRegion: "no-drag",
                    marginBottom: 14,
                    padding: 12,
                    borderRadius: 10,
                    background: "rgba(239,68,68,0.12)",
                    border: "1px solid rgba(239,68,68,0.3)",
                    color: "#fecaca",
                    fontSize: 12,
                    lineHeight: 1.5,
                    overflowWrap: "anywhere"
                  }}>
                    {pageNotice}
                  </div>
                )}

                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 14,
                  padding: 14,
                  borderRadius: 10,
                  background: backendTone.background,
                  border: `1px solid ${backendTone.border}`
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 8 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>Backend Status</div>
                    <div style={{ padding: "3px 8px", borderRadius: 999, background: "rgba(0,0,0,0.18)", color: backendTone.color, fontSize: 11, fontWeight: 700 }}>{backendTone.label}</div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 10px", fontSize: 12, lineHeight: 1.35 }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>URL</span>
                    <span style={{ overflowWrap: "anywhere" }}>http://127.0.0.1:8000</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Error</span>
                    <span style={{ color: backendStatus.error ? "#fca5a5" : "rgba(255,255,255,0.72)", overflowWrap: "anywhere" }}>{backendStatus.error || "none"}</span>
                  </div>
                </div>

                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 14,
                  padding: 14,
                  borderRadius: 10,
                  background: memoryTone.background,
                  border: `1px solid ${memoryTone.border}`
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 8 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)" }}>Memory Status</div>
                    <div style={{ padding: "3px 8px", borderRadius: 999, background: "rgba(0,0,0,0.18)", color: memoryTone.color, fontSize: 11, fontWeight: 700 }}>{memoryTone.label}</div>
                  </div>
                  <div style={{ fontSize: 12, color: "rgba(255,255,255,0.72)" }}>Recent History: {blackboardHistory.length}</div>
                </div>

                <div style={{
                  WebkitAppRegion: "no-drag",
                  marginBottom: 14,
                  padding: 14,
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.055)",
                  border: "1px solid rgba(255,255,255,0.12)"
                }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "rgba(255,255,255,0.92)", marginBottom: 8 }}>Config Status</div>
                  <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 10px", fontSize: 12, lineHeight: 1.35 }}>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Model</span>
                    <span style={{ overflowWrap: "anywhere" }}>{configStatus?.ollama_model || "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Use Ollama</span>
                    <span>{typeof configStatus?.use_ollama === "boolean" ? String(configStatus.use_ollama) : "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Resume</span>
                    <span>{typeof configStatus?.use_resume_context === "boolean" ? String(configStatus.use_resume_context) : "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>JD</span>
                    <span>{typeof configStatus?.use_jd_context === "boolean" ? String(configStatus.use_jd_context) : "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Knowledge</span>
                    <span>{typeof configStatus?.use_knowledge_context === "boolean" ? String(configStatus.use_knowledge_context) : "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Memory Limit</span>
                    <span>{configStatus?.memory_limit ?? "unknown"}</span>
                    <span style={{ color: "rgba(255,255,255,0.52)" }}>Ollama URL</span>
                    <span style={{ overflowWrap: "anywhere" }}>{configStatus?.ollama_base_url || "unknown"}</span>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <button
                    onClick={handleLocalAskImage}
                    disabled={localAskLoading}
                    style={{
                      padding: "14px",
                      borderRadius: 10,
                      border: "none",
                      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                      color: "white",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 8
                    }}
                  >
                    📷 截图问答
                  </button>

                  <button
                    onClick={handleStartWhisperRecording}
                    disabled={voiceRecording}
                    style={{
                      padding: "14px",
                      borderRadius: 10,
                      border: "none",
                      background: voiceRecording ? "rgba(239,68,68,0.5)" : "rgba(239,68,68,0.8)",
                      color: "white",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: voiceRecording ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 8
                    }}
                  >
                    🎤 {voiceRecording ? "录音中..." : "语音输入"}
                  </button>

                  <button
                    onClick={() => window.open("http://127.0.0.1:8000/docs", "_blank")}
                    style={{
                      padding: "14px",
                      borderRadius: 10,
                      border: "1px solid rgba(255,255,255,0.15)",
                      background: "rgba(255,255,255,0.05)",
                      color: "white",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 8
                    }}
                  >
                    📖 API 文档
                  </button>

                  <button
                    onClick={() => window.open("http://127.0.0.1:8000/blackboard", "_blank")}
                    style={{
                      padding: "14px",
                      borderRadius: 10,
                      border: "1px solid rgba(255,255,255,0.15)",
                      background: "rgba(255,255,255,0.05)",
                      color: "white",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 8
                    }}
                  >
                    📋 查看 Blackboard
                  </button>
                </div>

                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10, WebkitAppRegion: "no-drag" }}>
                  <button onClick={startMockInterview} disabled={mockLoading} style={{ padding: "12px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.05)", color: "white", fontSize: 13, fontWeight: 600, cursor: mockLoading ? "not-allowed" : "pointer" }}>{mockLoading ? "Starting..." : "Mock Interview"}</button>
                  <button onClick={generateReport} disabled={reportLoading} style={{ padding: "12px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.05)", color: "white", fontSize: 13, fontWeight: 600, cursor: reportLoading ? "not-allowed" : "pointer" }}>{reportLoading ? "Generating..." : "Generate Report"}</button>
                  <button onClick={exportReport} disabled={exportLoading} style={{ padding: "12px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.05)", color: "white", fontSize: 13, fontWeight: 600, cursor: exportLoading ? "not-allowed" : "pointer" }}>{exportLoading ? "Exporting..." : "Export Report"}</button>
                  <button onClick={clearHistory} disabled={clearLoading} style={{ padding: "12px", borderRadius: 10, border: "1px solid rgba(249,115,22,0.35)", background: "rgba(249,115,22,0.08)", color: "#fed7aa", fontSize: 13, fontWeight: 600, cursor: clearLoading ? "not-allowed" : "pointer" }}>{clearLoading ? "Clearing..." : "Clear History"}</button>
                  <button onClick={resetSession} disabled={resetLoading} style={{ padding: "12px", borderRadius: 10, border: "1px solid rgba(239,68,68,0.35)", background: "rgba(239,68,68,0.08)", color: "#fecaca", fontSize: 13, fontWeight: 600, cursor: resetLoading ? "not-allowed" : "pointer" }}>{resetLoading ? "Resetting..." : "Reset Session"}</button>
                </div>

                {mockState && (
                  <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", WebkitAppRegion: "no-drag" }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Mock Interview</div>
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.75)", marginBottom: 8, overflowWrap: "anywhere" }}>{mockState.current_question || mockState.next_question || (mockState.completed ? "completed" : "ready")}</div>
                    {!mockState.completed && (
                      <>
                        <textarea value={mockAnswer} onChange={(e) => setMockAnswer(e.target.value)} style={{ width: "100%", height: 80, borderRadius: 8, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.08)", color: "white", padding: 8, resize: "vertical" }} />
                        <button onClick={submitMockAnswer} disabled={!mockAnswer.trim() || mockLoading} style={{ marginTop: 8, width: "100%", padding: 10, borderRadius: 8, border: "none", background: "rgba(34,197,94,0.75)", color: "white", cursor: mockAnswer.trim() && !mockLoading ? "pointer" : "not-allowed" }}>{mockLoading ? "Processing..." : "Submit Answer"}</button>
                      </>
                    )}
                    {mockState.feedback && <div style={{ marginTop: 8, fontSize: 12, color: "rgba(255,255,255,0.72)" }}>Score: {mockState.feedback.final_score ?? "unknown"} | {mockState.feedback.main_weakness ?? ""}</div>}
                  </div>
                )}

                {report && (
                  <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", maxHeight: 260, overflowY: "auto", WebkitAppRegion: "no-drag" }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Interview Report</div>
                    <div style={{ color: getScoreColor((report.overall_score ?? 0) / 100), fontWeight: 700 }}>Overall Score: {report.overall_score ?? "unknown"}</div>
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.72)", marginTop: 8 }}>{report.summary}</div>
                    <div style={{ fontSize: 12, marginTop: 8 }}><strong>Strengths</strong><ul style={{ margin: "4px 0 0 16px", padding: 0 }}>{(report.strengths || []).slice(0, 3).map((item: string, index: number) => <li key={`s-${index}`}>{item}</li>)}</ul></div>
                    <div style={{ fontSize: 12, marginTop: 8 }}><strong>Recommended Practice</strong><ul style={{ margin: "4px 0 0 16px", padding: 0 }}>{(report.recommended_practice || []).slice(0, 3).map((item: string, index: number) => <li key={`p-${index}`}>{item}</li>)}</ul></div>
                  </div>
                )}

                {exportedMarkdown && <textarea readOnly value={exportedMarkdown} style={{ marginTop: 16, width: "100%", minHeight: 160, borderRadius: 10, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(0,0,0,0.22)", color: "rgba(255,255,255,0.82)", padding: 10, fontSize: 11, resize: "vertical", WebkitAppRegion: "no-drag" }} />}

                {/* Status */}
                <div style={{
                  marginTop: 20,
                  padding: 12,
                  borderRadius: 10,
                  background: "rgba(34,197,94,0.1)",
                  border: "1px solid rgba(34,197,94,0.2)"
                }}>
                  <div style={{ fontSize: 12, color: "#86efac", fontWeight: 600, marginBottom: 8 }}>
                    ✅ 系统状态
                  </div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.6)", display: "flex", flexDirection: "column", gap: 4 }}>
                    <div>• 后端服务: <span style={{ color: "#22c55e" }}>已连接</span></div>
                    <div>• OCR 服务: <span style={{ color: "#22c55e" }}>就绪</span></div>
                    <div>• Whisper: <span style={{ color: "#22c55e" }}>就绪</span></div>
                    <div>• Critic Agent: <span style={{ color: "#22c55e" }}>已启用</span></div>
                  </div>
                </div>
              </div>
            </main>



            <UpdateNotification />

            {isSettingsOpen && (
              <Suspense fallback={null}>
                <SettingsDialog open={isSettingsOpen} onOpenChange={handleCloseSettings} />
              </Suspense>
            )}

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
              
              ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
              }
              
              ::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 3px;
              }
              
              ::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
              }
              
              ::-webkit-scrollbar-thumb:hover {
                background: rgba(255, 255, 255, 0.3);
              }
            `}</style>
          </div>
        </ToastContext.Provider>
      </ToastProvider>
    </QueryClientProvider>
  )
}

export default App
