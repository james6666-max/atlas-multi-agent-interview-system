import { useCallback, useState } from "react"
import { useI18n } from "../i18n/LanguageProvider"

export function useReportActions({
  refreshBlackboard,
  setPageNotice
}: {
  refreshBlackboard: () => void
  setPageNotice: (notice: string) => void
}) {
  const { lang } = useI18n()
  const [mockState, setMockState] = useState<any>(null)
  const [mockAnswer, setMockAnswer] = useState("")
  const [report, setReport] = useState<any>(null)
  const [exportedMarkdown, setExportedMarkdown] = useState("")
  const [mockLoading, setMockLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)

  const startMockInterview = useCallback(async () => {
    try {
      setMockLoading(true)
      const res = await fetch("http://127.0.0.1:8000/mock/start", { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setMockState(await res.json())
      setMockAnswer("")
    } catch (error: any) {
      setPageNotice(`Mock interview failed to start: ${error?.message ?? String(error)}`)
    } finally {
      setMockLoading(false)
    }
  }, [setPageNotice])

  const submitMockAnswer = useCallback(async () => {
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
      setPageNotice(`Mock answer submit failed: ${error?.message ?? String(error)}`)
    } finally {
      setMockLoading(false)
    }
  }, [mockAnswer, setPageNotice])

  const generateReport = useCallback(async () => {
    try {
      setReportLoading(true)
      const res = await fetch(`http://127.0.0.1:8000/report/session?lang=${encodeURIComponent(lang)}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setReport(await res.json())
    } catch (error: any) {
      setPageNotice(`Report generation failed: ${error?.message ?? String(error)}`)
    } finally {
      setReportLoading(false)
    }
  }, [lang, setPageNotice])

  const exportReport = useCallback(async () => {
    try {
      setExportLoading(true)
      const res = await fetch(`http://127.0.0.1:8000/report/export_markdown?lang=${encodeURIComponent(lang)}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setExportedMarkdown(await res.text())
    } catch (error: any) {
      setPageNotice(`Report export failed: ${error?.message ?? String(error)}`)
    } finally {
      setExportLoading(false)
    }
  }, [lang, setPageNotice])

  const clearHistory = useCallback(async () => {
    if (!window.confirm("Clear Blackboard history?")) return
    try {
      setClearLoading(true)
      const res = await fetch("http://127.0.0.1:8000/blackboard/clear_history", { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      refreshBlackboard()
    } catch (error: any) {
      setPageNotice(`Clear history failed: ${error?.message ?? String(error)}`)
    } finally {
      setClearLoading(false)
    }
  }, [refreshBlackboard, setPageNotice])

  const resetSession = useCallback(async () => {
    if (!window.confirm("Reset current Atlas session?")) return
    try {
      setResetLoading(true)
      const res = await fetch("http://127.0.0.1:8000/blackboard/reset_session", { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setReport(null)
      setExportedMarkdown("")
      refreshBlackboard()
    } catch (error: any) {
      setPageNotice(`Reset session failed: ${error?.message ?? String(error)}`)
    } finally {
      setResetLoading(false)
    }
  }, [refreshBlackboard, setPageNotice])

  return {
    mockState,
    mockAnswer,
    setMockAnswer,
    report,
    exportedMarkdown,
    mockLoading,
    reportLoading,
    exportLoading,
    clearLoading,
    resetLoading,
    startMockInterview,
    submitMockAnswer,
    generateReport,
    exportReport,
    clearHistory,
    resetSession
  }
}
