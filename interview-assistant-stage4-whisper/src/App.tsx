import { lazy, Suspense } from "react"
import { LanguageProvider } from "./i18n/LanguageProvider"
import { ErrorBoundary } from "./components/ErrorBoundary"

const AtlasDashboardPage = lazy(() => import("./pages/AtlasDashboardPage"))

function App() {
  return (
    <ErrorBoundary>
      <LanguageProvider>
        <Suspense fallback={<div className="loading-panel">Loading page...</div>}>
          <AtlasDashboardPage />
        </Suspense>
      </LanguageProvider>
    </ErrorBoundary>
  )
}

export default App
