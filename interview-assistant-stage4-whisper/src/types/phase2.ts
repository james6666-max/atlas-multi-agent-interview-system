export interface CriticResult {
  approved?: boolean
  score?: number
  final_score?: number
  clarity_score?: number
  correctness_score?: number
  human_like_score?: number
  privacy_score?: number
  issues?: string[]
  suggestions?: string[]
  risk_flags?: string[]
  specific_issues?: string[]
  improved_answer_suggestion?: string
  [key: string]: unknown
}

export interface LlmMeta {
  provider?: string
  model?: string
  fallback?: boolean
  redactions?: Record<string, number>
}

export interface Phase2AskResponse {
  question?: string
  question_type?: string
  selected_agent?: string
  answer?: string
  critic?: CriticResult
  context_used?: boolean
  context_sources?: string[]
  rag_used?: boolean
  rag_sources?: string[]
  session_id?: string
  llm?: LlmMeta
  [key: string]: unknown
}

export type Phase2Critic = CriticResult

/** One event from POST /ask_stream (SSE). */
export interface StreamEvent {
  type: "meta" | "delta" | "final" | "ignored" | "done"
  session_id?: string
  text?: string
  question?: string
  question_type?: string
  phase2_type?: string
  selected_agent?: string
  answer?: string
  critic?: CriticResult
  context_used?: boolean
  rag_used?: boolean
  reason?: string
  llm?: LlmMeta
  fallback?: boolean
}

export interface StreamHandlers {
  onMeta?: (event: StreamEvent) => void
  onDelta?: (text: string, event: StreamEvent) => void
  onFinal?: (event: StreamEvent) => void
  onIgnored?: (event: StreamEvent) => void
  onDone?: (event: StreamEvent) => void
}

/** One step from GET /trace/{session_id}. */
export interface TraceStep {
  ts?: number
  source_agent?: string
  type?: string
  question_type?: string
  parent_event_id?: string | null
  event_id?: string
}

export interface TraceResponse {
  session_id: string
  count: number
  steps: TraceStep[]
  events?: unknown[]
}

export interface LlmConfig {
  mode?: "hybrid" | "local" | "cloud"
  use_ollama?: boolean
  ollama_base_url?: string
  ollama_model?: string
  cloud_base_url?: string
  cloud_api_key?: string
  cloud_api_key_set?: boolean
  cloud_model?: string
  cloud_configured?: boolean
  [key: string]: unknown
}

/** Practice / Coaching loop (M2). */
export interface PracticeQuestion {
  id: string
  index: number
  type: string
  topic?: string
  question: string
  is_followup?: boolean
}

export interface PracticeTurn {
  question: PracticeQuestion
  answer: string
  score: number
  critic?: CriticResult
}

export interface PracticeState {
  session_id: string
  active: boolean
  completed: boolean
  round_index: number
  total_planned: number
  queue_length: number
  followups_used: number
  current_question?: PracticeQuestion | null
  answered: PracticeTurn[]
  config?: Record<string, unknown>
}

export interface PracticeAnswerResult {
  completed: boolean
  feedback?: CriticResult | null
  score?: number
  next_question?: PracticeQuestion | null
  state: PracticeState
}

export interface PracticeReport {
  session_id: string
  overall_score: number
  summary: string
  strengths: string[]
  weaknesses: string[]
  by_type: Record<string, { count: number; avg_score: number; score_sum?: number }>
  recommended_practice: string[]
  best_question?: string
  weakest_question?: string
  question_reviews: Array<{
    question: string
    type: string
    is_followup?: boolean
    score: number
    main_weakness?: string
    issues?: string[]
  }>
  config?: Record<string, unknown>
}

export interface BackendStatusResponse {
  ollama_model?: string
  use_ollama?: boolean
  use_resume_context?: boolean
  use_jd_context?: boolean
  use_knowledge_context?: boolean
  memory_limit?: number
  ollama_base_url?: string
  llm?: LlmConfig
  [key: string]: unknown
}
