import type {
  BackendStatusResponse,
  LlmConfig,
  Phase2AskResponse,
  PracticeAnswerResult,
  PracticeReport,
  PracticeState,
  StreamEvent,
  StreamHandlers,
  TraceResponse,
} from "../types/phase2"

const API_BASE_URL = "http://127.0.0.1:8000"

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text()
  const payload = text ? JSON.parse(text) : {}

  if (!response.ok || payload?.detail) {
    throw new Error(payload?.detail ?? response.statusText ?? `HTTP ${response.status}`)
  }

  return payload as T
}

export async function askPhase2Question(
  question: string,
  language = "Unknown"
): Promise<Phase2AskResponse> {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      language,
      source: "manual_input"
    })
  })

  return parseJsonResponse<Phase2AskResponse>(response)
}

export async function getBackendConfigStatus(): Promise<BackendStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/config/status`)
  return parseJsonResponse<BackendStatusResponse>(response)
}

/**
 * Stream an answer from POST /ask_stream (SSE). Returns the final event (or the
 * ignored event) once the stream completes. `signal` allows cancellation.
 */
export async function askPhase2Stream(
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
  language = "Unknown"
): Promise<StreamEvent | null> {
  const response = await fetch(`${API_BASE_URL}/ask_stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, language, source: "manual_input" }),
    signal,
  })

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "")
    throw new Error(text || response.statusText || `HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let result: StreamEvent | null = null

  const dispatch = (event: StreamEvent) => {
    switch (event.type) {
      case "meta":
        handlers.onMeta?.(event)
        break
      case "delta":
        handlers.onDelta?.(event.text ?? "", event)
        break
      case "final":
        result = event
        handlers.onFinal?.(event)
        break
      case "ignored":
        result = event
        handlers.onIgnored?.(event)
        break
      case "done":
        handlers.onDone?.(event)
        break
    }
  }

  const flush = () => {
    let index = buffer.indexOf("\n\n")
    while (index !== -1) {
      const chunk = buffer.slice(0, index)
      buffer = buffer.slice(index + 2)
      for (const line of chunk.split("\n")) {
        const trimmed = line.trim()
        if (!trimmed.startsWith("data:")) continue
        const payload = trimmed.slice(5).trim()
        if (!payload || payload === "[DONE]") continue
        try {
          dispatch(JSON.parse(payload) as StreamEvent)
        } catch {
          // ignore malformed chunk
        }
      }
      index = buffer.indexOf("\n\n")
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    flush()
  }
  buffer += decoder.decode()
  buffer += "\n\n"
  flush()

  return result
}

export async function getTrace(sessionId: string): Promise<TraceResponse> {
  const response = await fetch(`${API_BASE_URL}/trace/${encodeURIComponent(sessionId)}`)
  return parseJsonResponse<TraceResponse>(response)
}

// ---- Practice / Coaching loop (M2) ----

export async function practiceStart(
  options: { num_questions?: number; role?: string; focus?: string; session_id?: string; language?: string } = {}
): Promise<PracticeState> {
  const response = await fetch(`${API_BASE_URL}/practice/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: "default", num_questions: 5, ...options }),
  })
  return parseJsonResponse<PracticeState>(response)
}

export async function practiceAnswer(answer: string, sessionId = "default"): Promise<PracticeAnswerResult> {
  const response = await fetch(`${API_BASE_URL}/practice/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer, session_id: sessionId }),
  })
  return parseJsonResponse<PracticeAnswerResult>(response)
}

export async function practiceReport(sessionId = "default"): Promise<PracticeReport> {
  const response = await fetch(`${API_BASE_URL}/practice/report?session_id=${encodeURIComponent(sessionId)}`)
  return parseJsonResponse<PracticeReport>(response)
}

export async function getLlmConfig(): Promise<LlmConfig> {
  const response = await fetch(`${API_BASE_URL}/config/llm`)
  return parseJsonResponse<LlmConfig>(response)
}

export async function updateLlmConfig(update: Partial<LlmConfig>): Promise<LlmConfig> {
  const response = await fetch(`${API_BASE_URL}/config/llm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  })
  return parseJsonResponse<LlmConfig>(response)
}

export interface LlmTestResult {
  ok: boolean
  provider?: string
  model?: string
  is_local?: boolean
  fallback_used?: boolean
  latency_ms?: number
  sample?: string
  error?: string
}

export async function testLlmConnection(): Promise<LlmTestResult> {
  const response = await fetch(`${API_BASE_URL}/config/llm/test`, { method: "POST" })
  return parseJsonResponse<LlmTestResult>(response)
}

export interface CandidateProfile {
  resume: string
  jd: string
  knowledge: string
  company: string
  position: string
  focus: string
}

export async function getProfile(): Promise<CandidateProfile> {
  const response = await fetch(`${API_BASE_URL}/profile`)
  return parseJsonResponse<CandidateProfile>(response)
}

export async function saveProfile(update: Partial<CandidateProfile>): Promise<CandidateProfile> {
  const response = await fetch(`${API_BASE_URL}/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  })
  return parseJsonResponse<CandidateProfile>(response)
}

export async function parseProfileFile(file: File): Promise<{ text: string; chars: number; filename: string }> {
  const formData = new FormData()
  formData.append("file", file, file.name)
  const response = await fetch(`${API_BASE_URL}/profile/parse_file`, { method: "POST", body: formData })
  return parseJsonResponse<{ text: string; chars: number; filename: string }>(response)
}
