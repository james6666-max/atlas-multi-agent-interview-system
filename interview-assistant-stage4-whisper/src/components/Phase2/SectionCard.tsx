import type { ReactNode } from "react"

interface SectionCardProps {
  eyebrow?: string
  title?: string
  children: ReactNode
  actions?: ReactNode
}

export function SectionCard({ eyebrow, title, children, actions }: SectionCardProps) {
  return (
    <section className="phase2-card">
      {(eyebrow || title || actions) && (
        <div className="phase2-section-heading">
          <div>
            {eyebrow && <div className="phase2-muted-label">{eyebrow}</div>}
            {title && <h3>{title}</h3>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  )
}
