import { useCallback, useState } from "react"
import { practiceAnswer, practiceReport, practiceStart } from "../api/client"
import type {
  CriticResult,
  PracticeQuestion,
  PracticeReport,
  PracticeState,
} from "../types/phase2"
import { useI18n } from "../i18n/LanguageProvider"

export function usePractice() {
  const { lang } = useI18n()
  const [state, setState] = useState<PracticeState | null>(null)
  const [current, setCurrent] = useState<PracticeQuestion | null>(null)
  const [feedback, setFeedback] = useState<CriticResult | null>(null)
  const [lastScore, setLastScore] = useState<number | null>(null)
  const [report, setReport] = useState<PracticeReport | null>(null)
  const [answer, setAnswer] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const start = useCallback(async (numQuestions = 5) => {
    setLoading(true)
    setError(null)
    setReport(null)
    setFeedback(null)
    setLastScore(null)
    try {
      const next = await practiceStart({ num_questions: numQuestions, language: lang })
      setState(next)
      setCurrent(next.current_question ?? null)
      setAnswer("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start practice")
    } finally {
      setLoading(false)
    }
  }, [lang])

  const submit = useCallback(async () => {
    if (!answer.trim() || !current) return
    setLoading(true)
    setError(null)
    try {
      const result = await practiceAnswer(answer.trim())
      setState(result.state)
      setFeedback(result.feedback ?? null)
      setLastScore(typeof result.score === "number" ? result.score : null)
      setCurrent(result.next_question ?? null)
      setAnswer("")
      if (result.completed) {
        const rep = await practiceReport()
        setReport(rep)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answer")
    } finally {
      setLoading(false)
    }
  }, [answer, current])

  const reset = useCallback(() => {
    setState(null)
    setCurrent(null)
    setFeedback(null)
    setLastScore(null)
    setReport(null)
    setAnswer("")
    setError(null)
  }, [])

  return {
    state,
    current,
    feedback,
    lastScore,
    report,
    answer,
    setAnswer,
    loading,
    error,
    start,
    submit,
    reset,
    completed: Boolean(state?.completed),
    active: Boolean(state?.active),
  }
}
