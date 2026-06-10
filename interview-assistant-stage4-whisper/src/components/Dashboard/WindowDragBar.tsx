import { useEffect, useState } from "react"
import { Download, EyeOff, GripHorizontal, MoreVertical, Search } from "lucide-react"

type WindowAction = "minimize" | "toggle-maximize" | "close"
type WindowMode = "normal" | "stealth"
type WindowControlResult = {
  success: boolean
  isMaximized?: boolean
  error?: string
}

interface WindowDragBarProps {
  onDownload?: () => void
  onSearch?: () => void
  onOpenMenu?: () => void
  onToggleStealth?: () => void
  windowMode?: WindowMode
}

export function WindowDragBar({
  onDownload,
  onSearch,
  onOpenMenu,
  onToggleStealth,
  windowMode = "normal"
}: WindowDragBarProps) {
  const [isMaximized, setIsMaximized] = useState(false)

  useEffect(() => {
    return window.electronAPI?.onWindowMaximizedChange?.(setIsMaximized)
  }, [])

  const controlWindow = (action: WindowAction) => {
    void window.electronAPI?.windowControl?.(action).then((result: WindowControlResult) => {
      if (typeof result?.isMaximized === "boolean") {
        setIsMaximized(result.isMaximized)
      }
    })
  }

  return (
    <div className="window-drag-bar">
      <div className="browser-toolbar-actions" aria-label="Browser tools">
        <button type="button" title="Download" aria-label="Download" onClick={onDownload}>
          <Download size={14} />
        </button>
        <button type="button" title="Search (Ctrl+K)" aria-label="Search (Ctrl+K)" onClick={onSearch}>
          <Search size={14} />
          <span>Ctrl+K</span>
        </button>
        <button type="button" title="More" aria-label="More" onClick={onOpenMenu}>
          <MoreVertical size={14} />
        </button>
        <button
          type="button"
          title={windowMode === "stealth" ? "Exit stealth mode" : "Enter stealth mode"}
          aria-label={windowMode === "stealth" ? "Exit stealth mode" : "Enter stealth mode"}
          onClick={onToggleStealth}
        >
          <EyeOff size={14} />
        </button>
      </div>

      <GripHorizontal size={14} className="window-drag-grip" aria-hidden="true" />

      <div className="window-control-actions" aria-label="Window controls">
        <button type="button" title="Minimize" aria-label="Minimize" onClick={() => controlWindow("minimize")}>
          <span aria-hidden="true">−</span>
        </button>
        <button
          type="button"
          title={isMaximized ? "Restore" : "Maximize"}
          aria-label={isMaximized ? "Restore" : "Maximize"}
          onClick={() => controlWindow("toggle-maximize")}
        >
          <span aria-hidden="true">□</span>
        </button>
        <button type="button" title="Close" aria-label="Close" className="window-close-button" onClick={() => controlWindow("close")}>
          <span aria-hidden="true">×</span>
        </button>
      </div>
    </div>
  )
}
