import type { BackendStatusState } from "../../hooks/useBackendStatus"
import { StatusCard } from "./StatusCard"

interface StatusCardsProps {
  backend: BackendStatusState
}

function formatBool(value: boolean | null) {
  if (value === null) return "unknown"
  return String(value)
}

export function StatusCards({ backend }: StatusCardsProps) {
  return (
    <div className="phase2-status-grid">
      <StatusCard
        label="Backend"
        value={backend.loading ? "Checking" : backend.online ? "Online" : "Offline"}
        detail={backend.error || "http://127.0.0.1:8000"}
        tone={backend.online ? "online" : backend.loading ? "neutral" : "offline"}
      />
      <StatusCard
        label="Agent chain"
        value="Phase2"
        detail="Perception -> Resume -> RAG -> Draft -> Critic"
        tone="online"
      />
      <StatusCard
        label="Ollama mode"
        value={formatBool(backend.useOllama)}
        detail={backend.model}
        tone={backend.useOllama === false ? "warning" : "neutral"}
      />
    </div>
  )
}
