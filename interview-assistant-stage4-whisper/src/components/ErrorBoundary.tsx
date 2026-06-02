import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/** Top-level safety net: a render error shows a message instead of a blank screen. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Atlas ErrorBoundary caught:", error, info)
  }

  private reset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 16,
            background: "#0f0f23",
            color: "white",
            fontFamily: "'Inter', -apple-system, sans-serif",
            padding: 24,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 600 }}>Something went wrong</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", maxWidth: 520, wordBreak: "break-word" }}>
            {this.state.error.message}
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={this.reset}
              style={{ padding: "8px 16px", borderRadius: 10, border: "none", background: "white", color: "black", fontWeight: 600, cursor: "pointer" }}
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{ padding: "8px 16px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.2)", background: "transparent", color: "white", cursor: "pointer" }}
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
