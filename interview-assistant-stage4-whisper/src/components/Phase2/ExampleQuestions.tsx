import { useI18n } from "../../i18n/LanguageProvider"

interface ExampleQuestionsProps {
  onPick: (question: string) => void
  disabled?: boolean
}

const EXAMPLES = {
  zh: [
    { type: "technical", question: "请解释一下数据库索引为什么能加速查询。" },
    { type: "algorithm", question: "如何判断一个链表中是否存在环?" },
    { type: "behavioral", question: "请用 STAR 法介绍一次你解决技术难题的经历。" },
    { type: "ignored", question: "你好,今天天气不错。" },
  ],
  en: [
    { type: "technical", question: "What is a RESTful API?" },
    { type: "algorithm", question: "How would you detect a cycle in a linked list?" },
    { type: "behavioral", question: "Tell me about a project you are most proud of." },
    { type: "ignored", question: "hello, nice weather." },
  ],
}

export function ExampleQuestions({ onPick, disabled = false }: ExampleQuestionsProps) {
  const { lang, t } = useI18n()
  const examples = EXAMPLES[lang]
  return (
    <div className="phase2-example-row">
      {examples.map((example) => (
        <button
          key={`${example.type}-${example.question}`}
          type="button"
          className="phase2-example-button"
          onClick={() => onPick(example.question)}
          disabled={disabled}
        >
          <span>{t(`qtype.${example.type}`, example.type)}</span>
          {example.question}
        </button>
      ))}
    </div>
  )
}
