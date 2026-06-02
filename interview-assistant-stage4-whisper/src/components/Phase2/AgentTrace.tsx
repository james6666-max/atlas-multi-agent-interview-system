import type { Phase2AskResponse, TraceStep } from "../../types/phase2"
import { useI18n } from "../../i18n/LanguageProvider"

interface AgentTraceProps {
  response: Phase2AskResponse | null
  loading?: boolean
  trace?: TraceStep[] | null
}

const steps = ["Perception", "Resume", "RAG", "Tech Draft", "Behavioral Draft", "Critic", "Final"]

/** Inferred fallback (no trace yet): derive from response fields. */
function inferStepState(step: string, response: Phase2AskResponse | null, loading: boolean) {
  if (loading && !response) return "running"
  if (!response) return "idle"

  const agent = String(response.selected_agent ?? "").toLowerCase()
  const questionType = String(response.question_type ?? "").toLowerCase()
  const hasCritic = Boolean(response.critic)
  const hasAnswer = Boolean(response.answer)

  if (questionType === "ignored") {
    return step === "Perception" ? "done" : "skipped"
  }

  if (step === "Perception") return "done"
  if (step === "Resume") return response.context_used ? "done" : "skipped"
  if (step === "RAG") return response.rag_used ? "done" : "skipped"
  if (step === "Tech Draft") return agent.includes("tech") || agent.includes("code") ? "done" : "skipped"
  if (step === "Behavioral Draft") return agent.includes("behavioral") ? "done" : "skipped"
  if (step === "Critic") return hasCritic ? "done" : loading ? "running" : "idle"
  if (step === "Final") return hasAnswer ? "done" : loading ? "running" : "idle"
  return "idle"
}

/** Real trace: derive from the actual event stream returned by /trace. */
function traceStepState(step: string, types: Set<string>, response: Phase2AskResponse | null) {
  const agent = String(response?.selected_agent ?? "").toLowerCase()

  // Question detected? If only manual_input arrived, Perception skipped the rest.
  if (!types.has("question_detected")) {
    return step === "Perception" ? "done" : "skipped"
  }

  if (step === "Perception") return "done"
  if (step === "Resume") return types.has("context_loaded") ? "done" : "skipped"
  if (step === "RAG") return types.has("rag_chunk") ? "done" : "skipped"
  if (step === "Tech Draft") {
    return types.has("answer_draft") && (agent.includes("tech") || agent.includes("code")) ? "done" : "skipped"
  }
  if (step === "Behavioral Draft") {
    return types.has("answer_draft") && agent.includes("behavioral") ? "done" : "skipped"
  }
  if (step === "Critic") return types.has("answer_final") ? "done" : "idle"
  if (step === "Final") return types.has("answer_final") ? "done" : "idle"
  return "idle"
}

export function AgentTrace({ response, loading = false, trace = null }: AgentTraceProps) {
  const { t } = useI18n()
  const hasTrace = Array.isArray(trace) && trace.length > 0
  const traceTypes = hasTrace ? new Set(trace!.map((step) => String(step.type ?? ""))) : null

  return (
    <section className="phase2-card">
      <div className="phase2-section-heading">
        <div>
          <div className="phase2-muted-label">{t("trace.title")}</div>
          <h3>Phase2 standard chain</h3>
        </div>
        <span className={`phase2-badge ${hasTrace ? "phase2-badge-approved" : "phase2-badge-neutral"}`}>
          {hasTrace ? "real trace" : loading ? "streaming…" : "inferred"}
        </span>
      </div>

      <div className="phase2-trace">
        {steps.map((step) => {
          const state = traceTypes
            ? traceStepState(step, traceTypes, response)
            : inferStepState(step, response, loading)
          return (
            <span key={step} className={`phase2-trace-step phase2-trace-${state}`}>
              {step}
              <small>{state}</small>
            </span>
          )
        })}
      </div>
    </section>
  )
}
