import { useCallback, useEffect, useState } from "react"
import { getBackendConfigStatus } from "../api/client"

export function useBlackboard() {
  const [blackboardHistory, setBlackboardHistory] = useState<any[]>([])
  const [llmStatus, setLlmStatus] = useState({
    answerSource: "unknown",
    model: "unknown",
    fallback: null as boolean | null,
    llmError: null as string | null
  })
  const [resumeStatus, setResumeStatus] = useState({
    loaded: null as boolean | null,
    path: "unknown",
    error: null as string | null
  })
  const [jdStatus, setJdStatus] = useState({
    loaded: null as boolean | null,
    path: "unknown",
    error: null as string | null
  })
  const [matchStatus, setMatchStatus] = useState({
    score: null as number | null,
    strongMatches: [] as string[],
    gaps: [] as string[],
    interviewFocus: [] as string[]
  })
  const [knowledgeStatus, setKnowledgeStatus] = useState({
    loaded: null as boolean | null,
    path: "unknown",
    error: null as string | null
  })
  const [ragStatus, setRagStatus] = useState({
    used: null as boolean | null,
    snippetsCount: null as number | null,
    keywords: [] as string[]
  })
  const [backendStatus, setBackendStatus] = useState({
    connected: null as boolean | null,
    error: null as string | null
  })
  const [configStatus, setConfigStatus] = useState<any>(null)
  const [pageNotice, setPageNotice] = useState("")

  const fetchBlackboard = useCallback(async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/blackboard")
      if (!response.ok) {
        setBackendStatus({ connected: false, error: `HTTP ${response.status}` })
        setPageNotice("Backend is not connected. Please start the FastAPI service first.")
        return
      }

      const data = await response.json()
      setBackendStatus({ connected: true, error: null })
      setPageNotice("")
      if (data.history) setBlackboardHistory(data.history.slice().reverse())

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
      setPageNotice("Backend is not connected. Please start the FastAPI service first.")
    }
  }, [])

  const fetchConfigStatus = useCallback(async () => {
    try {
      setConfigStatus(await getBackendConfigStatus())
    } catch (err) {
      console.error("Failed to fetch config status:", err)
      setConfigStatus(null)
    }
  }, [])

  useEffect(() => {
    fetchBlackboard()
    fetchConfigStatus()
    const interval = setInterval(() => {
      fetchBlackboard()
      fetchConfigStatus()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchBlackboard, fetchConfigStatus])

  return {
    blackboardHistory,
    llmStatus,
    resumeStatus,
    jdStatus,
    matchStatus,
    knowledgeStatus,
    ragStatus,
    backendStatus,
    configStatus,
    pageNotice,
    setPageNotice,
    fetchBlackboard,
    fetchConfigStatus
  }
}
