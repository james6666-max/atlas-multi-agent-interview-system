import { useCallback, useEffect, useState } from "react"
import { getBackendConfigStatus } from "../api/client"
import type { BackendStatusResponse } from "../types/phase2"

export interface BackendStatusState {
  online: boolean
  loading: boolean
  error: string | null
  model: string
  useOllama: boolean | null
  useResumeContext: boolean | null
  useJdContext: boolean | null
  useKnowledgeContext: boolean | null
  raw: BackendStatusResponse | null
  refresh: () => Promise<void>
}

export function useBackendStatus(): BackendStatusState {
  const [online, setOnline] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [raw, setRaw] = useState<BackendStatusResponse | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const status = await getBackendConfigStatus()
      setRaw(status)
      setOnline(true)
      setError(null)
    } catch (err) {
      setRaw(null)
      setOnline(false)
      setError(err instanceof Error ? err.message : "Backend offline")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return {
    online,
    loading,
    error,
    model: raw?.ollama_model || "unknown",
    useOllama: typeof raw?.use_ollama === "boolean" ? raw.use_ollama : null,
    useResumeContext: typeof raw?.use_resume_context === "boolean" ? raw.use_resume_context : null,
    useJdContext: typeof raw?.use_jd_context === "boolean" ? raw.use_jd_context : null,
    useKnowledgeContext: typeof raw?.use_knowledge_context === "boolean" ? raw.use_knowledge_context : null,
    raw,
    refresh
  }
}
