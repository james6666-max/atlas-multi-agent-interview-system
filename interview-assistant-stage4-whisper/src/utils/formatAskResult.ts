export function formatCriticSection(critic: any) {
  if (!critic?.clarity_score) return ""

  return [
    "",
    "[Critic Review]",
    `Clarity: ${(critic.clarity_score * 100).toFixed(0)}%`,
    `Correctness: ${(critic.correctness_score * 100).toFixed(0)}%`,
    `Human-like: ${(critic.human_like_score * 100).toFixed(0)}%`,
    `Privacy: ${(critic.privacy_score * 100).toFixed(0)}%`,
    `JD Alignment: ${typeof critic.jd_alignment_score === "number" ? `${(critic.jd_alignment_score * 100).toFixed(0)}%` : "unknown"}`,
    `JD Notes: ${Array.isArray(critic.jd_alignment_notes) && critic.jd_alignment_notes.length ? critic.jd_alignment_notes.join(" / ") : "none"}`,
    "",
    `Suggestion: ${critic.improved_answer_suggestion ?? ""}`
  ].join("\n")
}

export function formatAskResult(result: any) {
  const criticSection = formatCriticSection(result?.critic || {})

  return [
    "Success",
    `Type: ${result?.question_type ?? ""} | Agent: ${result?.selected_agent ?? ""}`,
    "",
    result?.question ? `Question: ${result.question}` : "",
    result?.question ? "" : "",
    `Answer: ${result?.answer ?? ""}`,
    criticSection
  ].filter(Boolean).join("\n")
}
