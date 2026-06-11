import type { Lang } from "../i18n/translations"

const LABELS = {
  zh: {
    success: "完成",
    type: "类型",
    agent: "Agent",
    question: "识别到的问题",
    answer: "回答",
    critic: "[评审]",
    clarity: "清晰度",
    correctness: "正确性",
    humanLike: "自然度",
    privacy: "隐私",
    jdAlignment: "JD 匹配",
    jdNotes: "JD 备注",
    suggestion: "改进建议",
    unknown: "未知",
    none: "无",
    ignored: "未检测到完整的面试问题，已跳过回答。",
    ignoredHint: "提示：截图/语音中需要包含一个可识别的面试问题（OCR 只提取文字，不做图像理解）。",
    fallbackWarning: "⚠ 未配置可用 AI 模型，以下为离线模板回答。请在「设置」中配置云端 API Key，或启动本地 Ollama。",
  },
  en: {
    success: "Success",
    type: "Type",
    agent: "Agent",
    question: "Detected question",
    answer: "Answer",
    critic: "[Critic Review]",
    clarity: "Clarity",
    correctness: "Correctness",
    humanLike: "Human-like",
    privacy: "Privacy",
    jdAlignment: "JD Alignment",
    jdNotes: "JD Notes",
    suggestion: "Suggestion",
    unknown: "unknown",
    none: "none",
    ignored: "No complete interview question detected; answering was skipped.",
    ignoredHint: "Hint: the screenshot/audio needs to contain a recognizable interview question (OCR extracts text only, it does not understand images).",
    fallbackWarning: "⚠ No AI model is configured — this is an offline template answer. Set a cloud API key in Settings, or start local Ollama.",
  },
} as const

export function formatCriticSection(critic: any, lang: Lang = "zh") {
  if (!critic?.clarity_score) return ""
  const L = LABELS[lang] ?? LABELS.zh

  return [
    "",
    L.critic,
    `${L.clarity}: ${(critic.clarity_score * 100).toFixed(0)}%`,
    `${L.correctness}: ${(critic.correctness_score * 100).toFixed(0)}%`,
    `${L.humanLike}: ${(critic.human_like_score * 100).toFixed(0)}%`,
    `${L.privacy}: ${(critic.privacy_score * 100).toFixed(0)}%`,
    `${L.jdAlignment}: ${typeof critic.jd_alignment_score === "number" ? `${(critic.jd_alignment_score * 100).toFixed(0)}%` : L.unknown}`,
    `${L.jdNotes}: ${Array.isArray(critic.jd_alignment_notes) && critic.jd_alignment_notes.length ? critic.jd_alignment_notes.join(" / ") : L.none}`,
    "",
    `${L.suggestion}: ${critic.improved_answer_suggestion ?? ""}`
  ].join("\n")
}

export function formatAskResult(result: any, lang: Lang = "zh") {
  const L = LABELS[lang] ?? LABELS.zh

  if (String(result?.question_type ?? "") === "ignored") {
    return [
      L.ignored,
      result?.question ? `${L.question}: ${result.question}` : "",
      L.ignoredHint,
    ].filter(Boolean).join("\n\n")
  }

  const isFallback = Boolean(result?.llm_fallback) || result?.answer_source === "stub"
  const criticSection = formatCriticSection(result?.critic || {}, lang)

  return [
    isFallback ? L.fallbackWarning : L.success,
    `${L.type}: ${result?.question_type ?? ""} | ${L.agent}: ${result?.selected_agent ?? ""}`,
    "",
    result?.question ? `${L.question}: ${result.question}` : "",
    result?.question ? "" : "",
    `${L.answer}: ${result?.answer ?? ""}`,
    criticSection
  ].filter(Boolean).join("\n")
}
