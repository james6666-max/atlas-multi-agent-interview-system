import { useState } from "react"

interface RawJsonPanelProps {
  data: unknown
}

export function RawJsonPanel({ data }: RawJsonPanelProps) {
  const [open, setOpen] = useState(false)

  return (
    <section className="phase2-card">
      <button type="button" className="phase2-raw-toggle" onClick={() => setOpen((value) => !value)}>
        <span>Raw response</span>
        <strong>{open ? "Collapse" : "Expand"}</strong>
      </button>
      {open && (
        <pre className="phase2-raw-json">
          {data ? JSON.stringify(data, null, 2) : "No response yet."}
        </pre>
      )}
    </section>
  )
}
