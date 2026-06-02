import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { translations, type Lang } from "./translations"

type ApiLanguage = "Chinese" | "English"

interface I18nContextValue {
  lang: Lang
  setLang: (lang: Lang) => void
  toggle: () => void
  t: (key: string, fallback?: string) => string
  /** Backend `language` value derived from the UI language (answer / STT hint). */
  apiLanguage: ApiLanguage
}

const STORAGE_KEY = "atlas_lang"

const I18nContext = createContext<I18nContextValue | null>(null)

function detectInitial(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === "zh" || saved === "en") return saved
  } catch {
    /* ignore */
  }
  if (typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("en")) {
    return "en"
  }
  return "zh"
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectInitial)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      /* ignore */
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = lang === "zh" ? "zh-CN" : "en"
    }
  }, [lang])

  const setLang = useCallback((next: Lang) => setLangState(next), [])
  const toggle = useCallback(() => setLangState((cur) => (cur === "zh" ? "en" : "zh")), [])

  const t = useCallback(
    (key: string, fallback?: string) => translations[lang][key] ?? fallback ?? key,
    [lang]
  )

  const value = useMemo<I18nContextValue>(
    () => ({ lang, setLang, toggle, t, apiLanguage: lang === "zh" ? "Chinese" : "English" }),
    [lang, setLang, toggle, t]
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) {
    // Safe fallback so components used outside the provider still render.
    return {
      lang: "zh",
      setLang: () => {},
      toggle: () => {},
      t: (key, fallback) => translations.zh[key] ?? fallback ?? key,
      apiLanguage: "Chinese",
    }
  }
  return ctx
}
