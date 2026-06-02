type StatusTone = "online" | "offline" | "neutral" | "warning"

interface StatusCardProps {
  label: string
  value: string
  detail?: string
  tone?: StatusTone
}

export function StatusCard({ label, value, detail, tone = "neutral" }: StatusCardProps) {
  return (
    <section className={`phase2-card phase2-status phase2-status-${tone}`}>
      <div className="phase2-muted-label">{label}</div>
      <div className="phase2-status-value">{value}</div>
      {detail && <div className="phase2-status-detail">{detail}</div>}
    </section>
  )
}
