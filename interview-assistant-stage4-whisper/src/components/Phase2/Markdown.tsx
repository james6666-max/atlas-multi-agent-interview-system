import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

/**
 * Lightweight markdown renderer for streamed answers.
 * GFM support (tables, lists, etc.); code blocks rendered as styled <pre>
 * (no heavy syntax-highlighter dependency — keeps the bundle small).
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="md-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  )
}
