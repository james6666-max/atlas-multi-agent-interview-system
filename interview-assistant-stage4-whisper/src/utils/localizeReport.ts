import type { Lang } from "../i18n/translations"

const zhMap: Record<string, string> = {
  "Good alignment with the target JD.": "岗位 JD 贴合度较好。",
  "Answers connect well with resume and project experience.": "回答能结合简历和项目经历。",
  "Privacy risk stayed low.": "隐私风险较低。",
  "Multiple interview turns were recorded; keep collecting samples for better review.": "已完成多轮问答记录，可继续积累样本。",
  "No obvious repeated issue yet.": "暂无明显共性问题。",
  "Keep practicing 60-second and 2-minute versions of the Atlas project story.": "继续练习把 Atlas 项目讲成 60 秒和 2 分钟两个版本。",
  "Prepare more concrete examples for FastAPI, Electron, Ollama, and Whisper/OCR in the JD.": "针对 JD 中的 FastAPI、Electron、Ollama、Whisper/OCR 准备更具体的例子。",
  "After each answer, proactively add key trade-offs, fallback plans, and observability details.": "回答后主动补充关键取舍、兜底方案和可观测性设计。",
  "unknown": "未知",
  "none": "无明显短板",
}

const enMap: Record<string, string> = Object.fromEntries(
  Object.entries(zhMap).map(([en, zh]) => [zh, en])
)

function localizeText(value: unknown, lang: Lang): unknown {
  if (typeof value !== "string") return value
  if (lang === "en") return enMap[value] ?? value

  const mapped = zhMap[value]
  if (mapped) return mapped

  let match = value.match(/^This session recorded (\d+) Q&A turns with an average score of (\d+)\.$/)
  if (match) return `本轮共记录 ${match[1]} 条问答，平均分 ${match[2]}。`

  match = value.match(/^Average JD Alignment: (.+)%$/)
  if (match) return `平均 JD 匹配度：${match[1]}%`

  match = value.match(/^Average Resume Alignment: (.+)%$/)
  if (match) return `平均简历匹配度：${match[1]}%`

  match = value.match(/^Lowest Privacy Score: (.+)%$/)
  if (match) return `最低隐私安全分：${match[1]}%`

  return value
}

function localizeList(items: unknown, lang: Lang): unknown {
  if (!Array.isArray(items)) return items
  return items.map((item) => localizeText(item, lang))
}

export function localizeReport<T extends Record<string, any> | null | undefined>(report: T, lang: Lang): T {
  if (!report) return report
  return {
    ...report,
    summary: localizeText(report.summary, lang),
    strengths: localizeList(report.strengths, lang),
    weaknesses: localizeList(report.weaknesses, lang),
    recommended_practice: localizeList(report.recommended_practice, lang),
    jd_alignment_summary: localizeText(report.jd_alignment_summary, lang),
    resume_alignment_summary: localizeText(report.resume_alignment_summary, lang),
    privacy_risk_summary: localizeText(report.privacy_risk_summary, lang),
    question_reviews: Array.isArray(report.question_reviews)
      ? report.question_reviews.map((item: any) => ({
          ...item,
          main_weakness: localizeText(item?.main_weakness, lang),
          issues: localizeList(item?.issues, lang),
        }))
      : report.question_reviews,
  } as T
}
