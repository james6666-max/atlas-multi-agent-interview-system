import { useRef, useState } from "react"
import { askPhase2Stream, getTrace } from "../api/client"
import type { Phase2AskResponse, StreamEvent, TraceStep } from "../types/phase2"
import { useI18n } from "../i18n/LanguageProvider"

export function useAskPhase2() {
  const { apiLanguage } = useI18n()
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [response, setResponse] = useState<Phase2AskResponse | null>(null)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [firstTokenMs, setFirstTokenMs] = useState<number | null>(null)
  const [trace, setTrace] = useState<TraceStep[] | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  // Batches streaming deltas into one render per animation frame instead of
  // one render per token, which keeps long answers smooth.
  const flushFrameRef = useRef<number | null>(null)

  const cancelPendingFlush = () => {
    if (flushFrameRef.current !== null) {
      cancelAnimationFrame(flushFrameRef.current)
      flushFrameRef.current = null
    }
  }

  const submit = async (override?: string) => {
    const trimmed = (override ?? question).trim()
    if (!trimmed) {
      setError("Please enter an interview question.")
      return
    }
    if (override !== undefined) setQuestion(override)

    abortRef.current?.abort()
    cancelPendingFlush() // drop any stale flush from a previous run
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setStreaming(true)
    setError(null)
    setLatencyMs(null)
    setFirstTokenMs(null)
    setTrace(null)
    setResponse(null)

    const start = performance.now()
    let acc = ""
    let firstToken = false
    let meta: Partial<Phase2AskResponse> = {}

    const mergePartial = () => {
      setResponse({ ...meta, answer: acc } as Phase2AskResponse)
    }

    const scheduleFlush = () => {
      if (flushFrameRef.current !== null) return
      flushFrameRef.current = requestAnimationFrame(() => {
        flushFrameRef.current = null
        mergePartial()
      })
    }

    try {
      const final = await askPhase2Stream(
        trimmed,
        {
          onMeta: (event: StreamEvent) => {
            meta = {
              question: event.question,
              question_type: event.question_type,
              selected_agent: event.selected_agent,
            }
            mergePartial()
          },
          onDelta: (text: string) => {
            if (!firstToken) {
              firstToken = true
              setFirstTokenMs(Math.round(performance.now() - start))
            }
            acc += text
            scheduleFlush()
          },
          onFinal: (event: StreamEvent) => {
            cancelPendingFlush() // a stale partial flush must not overwrite the final payload
            setResponse({
              question: event.question,
              question_type: event.question_type,
              selected_agent: event.selected_agent,
              answer: event.answer ?? acc,
              critic: event.critic,
              context_used: event.context_used,
              rag_used: event.rag_used,
              session_id: event.session_id,
              llm: event.llm,
            })
          },
          onIgnored: (event: StreamEvent) => {
            cancelPendingFlush()
            setResponse({
              question: trimmed,
              question_type: "ignored",
              selected_agent: "Perception",
              answer: "",
              session_id: event.session_id,
            })
          },
        },
        controller.signal,
        apiLanguage
      )

      setLatencyMs(Math.round(performance.now() - start))

      const sessionId = final?.session_id
      if (sessionId) {
        try {
          const traceResponse = await getTrace(sessionId)
          setTrace(traceResponse.steps ?? [])
        } catch (traceErr) {
          console.warn("Trace fetch failed:", traceErr)
        }
      }
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return
      cancelPendingFlush() // a stale partial flush must not overwrite the error state
      setResponse(null)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      cancelPendingFlush()
      setLoading(false)
      setStreaming(false)
    }
  }

  const clear = () => {
    abortRef.current?.abort()
    setQuestion("")
    setError(null)
    setResponse(null)
    setLatencyMs(null)
    setFirstTokenMs(null)
    setTrace(null)
  }

  return {
    question,
    loading,
    streaming,
    error,
    response,
    latencyMs,
    firstTokenMs,
    trace,
    setQuestion,
    submit,
    clear,
  }
}
