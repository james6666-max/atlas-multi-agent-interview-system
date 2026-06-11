from __future__ import annotations

"""Deterministic, offline question planning for the practice (Coaching) loop.

Builds a role-relevant interview plan from the candidate's resume + JD by
detecting known tech topics and mixing behavioral / resume / technical /
system-design questions. An optional LLM can enrich the plan, but the bank
always works without any model so the loop is robust and testable offline.
"""

import re
from typing import Callable, Dict, List, Optional

from app.agents.perception_agent import classify_interview_input

# topic-key -> human-friendly display topic
TECH_TOPICS: Dict[str, str] = {
    "fastapi": "FastAPI 后端",
    "react": "React 前端",
    "electron": "Electron 桌面应用",
    "typescript": "TypeScript",
    "python": "Python 工程",
    "ollama": "本地大模型 Ollama",
    "llm": "大模型应用",
    "whisper": "语音识别 Whisper",
    "ocr": "OCR 截图识别",
    "rag": "RAG 检索增强",
    "agent": "多 Agent 架构",
    "blackboard": "黑板 / 事件总线",
    "orchestrator": "编排器调度",
    "docker": "Docker 部署",
    "redis": "Redis 缓存",
    "postgres": "数据库设计",
    "sql": "数据库设计",
    "kafka": "消息队列",
    "microservice": "微服务架构",
    "微服务": "微服务架构",
    "并发": "高并发",
    "分布式": "分布式系统",
}

# English display names for the same topic keys (used when language == en).
TECH_TOPICS_EN: Dict[str, str] = {
    "fastapi": "FastAPI backend",
    "react": "React frontend",
    "electron": "Electron desktop apps",
    "typescript": "TypeScript",
    "python": "Python engineering",
    "ollama": "local LLMs (Ollama)",
    "llm": "LLM applications",
    "whisper": "speech recognition (Whisper)",
    "ocr": "OCR",
    "rag": "RAG retrieval",
    "agent": "multi-agent architecture",
    "blackboard": "blackboard / event bus",
    "orchestrator": "orchestration",
    "docker": "Docker deployment",
    "redis": "Redis caching",
    "postgres": "database design",
    "sql": "database design",
    "kafka": "message queues",
    "microservice": "microservice architecture",
    "微服务": "microservice architecture",
    "并发": "high concurrency",
    "分布式": "distributed systems",
}

BEHAVIORAL_BANK: List[str] = [
    "请做个自我介绍,重点讲和这个岗位最相关的经历。",
    "讲一个你最有成就感的项目,你具体负责了什么?",
    "讲一次你遇到的最大技术难题,你是怎么定位和解决的?",
    "讲一次团队里的意见分歧或冲突,你是怎么推动达成一致的?",
    "你觉得自己最大的不足是什么?为改进它做过什么?",
]

GENERIC_TECH_BANK: List[str] = [
    "请解释一下进程和线程的区别,以及各自的适用场景。",
    "HTTP 和 HTTPS 的主要区别是什么?TLS 握手大致流程?",
    "数据库索引的原理是什么?什么情况下索引会失效?",
]

GENERIC_ALGO_BANK: List[str] = [
    "请描述你会怎么解决两数之和这类问题,并分析时间和空间复杂度。",
    "如何在有序数组里高效查找一个目标值?复杂度是多少?",
]

GENERIC_SYSTEM_BANK: List[str] = [
    "如果让你设计一个短链接系统,你会怎么做?",
    "如果让你设计一个 API 限流器,核心思路是什么?",
]

FOLLOWUP_BY_TYPE: Dict[str, List[str]] = {
    "behavioral": [
        "这件事里最难的部分具体是什么?",
        "如果重来一次,你会怎么改进?",
        "这个结果是怎么衡量的,有量化指标吗?",
    ],
    "resume_followup": [
        "在这个项目里你具体负责哪一块?哪些是你独立完成的?",
        "这个技术方案有什么权衡和不足?当时为什么这么选?",
    ],
    "technical": [
        "能举一个具体的使用场景或例子吗?",
        "它的边界情况和复杂度大概是什么样的?",
    ],
    "system_design": [
        "如果流量再涨十倍,瓶颈会在哪、怎么扩展?",
        "这个设计有哪些失败模式?你会怎么做降级和容错?",
    ],
    "algorithm": [
        "这个解法的时间和空间复杂度是多少?有没有更优解?",
        "有哪些边界情况需要特别处理?",
    ],
}

# ---- English banks (used when language resolves to English) ----
BEHAVIORAL_BANK_EN: List[str] = [
    "Give a brief self-introduction, focusing on the experience most relevant to this role.",
    "Tell me about a project you're most proud of. What exactly did you own?",
    "Tell me about the hardest technical problem you've faced and how you diagnosed and solved it.",
    "Tell me about a disagreement or conflict in your team and how you drove it to alignment.",
    "What's your biggest weakness, and what have you done to improve it?",
]

GENERIC_TECH_BANK_EN: List[str] = [
    "Explain the difference between a process and a thread, and when you'd use each.",
    "What are the main differences between HTTP and HTTPS? Outline the TLS handshake.",
    "How do database indexes work, and when can an index become ineffective?",
]

GENERIC_ALGO_BANK_EN: List[str] = [
    "Walk me through how you'd solve a Two Sum-style problem, including time and space complexity.",
    "How would you efficiently find a target value in a sorted array? What's the complexity?",
]

GENERIC_SYSTEM_BANK_EN: List[str] = [
    "How would you design a URL shortener?",
    "How would you design an API rate limiter? What's the core idea?",
]

FOLLOWUP_BY_TYPE_EN: Dict[str, List[str]] = {
    "behavioral": [
        "What was the hardest part of that, specifically?",
        "If you did it again, what would you improve?",
        "How was the outcome measured? Any quantified metrics?",
    ],
    "resume_followup": [
        "Which part did you personally own? What did you build independently?",
        "What were the trade-offs or weaknesses of that approach, and why did you choose it?",
    ],
    "technical": [
        "Can you give a concrete use case or example?",
        "What are the edge cases and the complexity?",
    ],
    "system_design": [
        "If traffic grew 10x, where's the bottleneck and how would you scale?",
        "What are the failure modes, and how would you do fallback and fault tolerance?",
    ],
    "algorithm": [
        "What's the time and space complexity? Is there a better solution?",
        "Which edge cases need special handling?",
    ],
}

_KNOWN_TYPES = {"technical", "algorithm", "system_design", "behavioral", "resume_followup"}


def _is_english(language: str | None) -> bool:
    return str(language or "").strip().lower() in {"en", "english"}


def detect_topics(resume: str, jd: str, knowledge: str = "", language: str = "zh") -> List[str]:
    """Return ordered, de-duplicated display topics found in resume/JD/knowledge."""
    haystack = f"{resume}\n{jd}\n{knowledge}".lower()
    display_map = TECH_TOPICS_EN if _is_english(language) else TECH_TOPICS
    topics: List[str] = []
    for key, display in display_map.items():
        if key in haystack and display not in topics:
            topics.append(display)
    return topics


def _q(index: int, qtype: str, question: str, topic: str = "", is_followup: bool = False) -> Dict:
    return {
        "id": f"q{index + 1}",
        "index": index,
        "type": qtype,
        "topic": topic,
        "question": question,
        "is_followup": is_followup,
    }


def build_plan(resume: str, jd: str, knowledge: str = "", num_questions: int = 5, language: str = "zh") -> List[Dict]:
    """Deterministic plan: self-intro + resume deep-dive + technical + system design + behavioral."""
    num_questions = max(3, min(8, int(num_questions or 5)))
    topics = detect_topics(resume, jd, knowledge, language)
    # Resume deep-dive questions claim "in your resume ..." — they must only
    # use topics that actually appear in the resume, not in the JD/knowledge.
    resume_topics = detect_topics(resume, "", "", language)
    has_resume = bool(resume.strip())
    en = _is_english(language)

    behavioral = BEHAVIORAL_BANK_EN if en else BEHAVIORAL_BANK
    tech_bank = GENERIC_TECH_BANK_EN if en else GENERIC_TECH_BANK
    algo_bank = GENERIC_ALGO_BANK_EN if en else GENERIC_ALGO_BANK
    system_bank = GENERIC_SYSTEM_BANK_EN if en else GENERIC_SYSTEM_BANK

    def resume_q(topic: str) -> str:
        return (
            f"For the work on “{topic}” in your resume, can you walk me through your specific contribution and the hard parts?"
            if en else
            f"你简历里和「{topic}」相关的工作,能展开讲讲你的具体贡献和遇到的难点吗?"
        )

    def technical_q(topic: str) -> str:
        return (
            f"Can you explain the core principles and use cases of “{topic}”?"
            if en else
            f"能解释一下「{topic}」的核心原理和适用场景吗?"
        )

    def system_q(topic: str) -> str:
        return (
            f"If you had to design a scalable system around “{topic}”, how would you approach it?"
            if en else
            f"如果让你基于「{topic}」设计一个可扩展的系统,你会怎么做?"
        )

    slots: List[Dict] = []
    # 1) self introduction (always first)
    slots.append({"type": "behavioral", "question": behavioral[0], "topic": ""})

    # 2) resume deep-dive on the first topic found in the resume itself
    #    (or a generic project question when the resume has no known tech topic)
    if has_resume:
        topic = resume_topics[0] if resume_topics else ""
        if topic:
            slots.append({"type": "resume_followup", "topic": topic, "question": resume_q(topic)})
        else:
            slots.append({"type": "behavioral", "question": behavioral[1], "topic": ""})

    # 3) technical on a tech topic
    if topics:
        topic = topics[min(1, len(topics) - 1)]
        slots.append({"type": "technical", "topic": topic, "question": technical_q(topic)})
    else:
        slots.append({"type": "technical", "topic": "", "question": tech_bank[0]})

    # 4) system design on a tech topic
    if topics:
        topic = topics[-1]
        slots.append({"type": "system_design", "topic": topic, "question": system_q(topic)})
    else:
        slots.append({"type": "system_design", "topic": "", "question": system_bank[0]})

    # 5+) behavioral depth, then rotate extra banks
    rotation = [
        {"type": "behavioral", "question": behavioral[2], "topic": ""},
        {"type": "behavioral", "question": behavioral[3], "topic": ""},
        {"type": "algorithm", "question": algo_bank[0], "topic": ""},
        {"type": "behavioral", "question": behavioral[4], "topic": ""},
        {"type": "system_design", "question": system_bank[1], "topic": ""},
    ]
    rot = 0
    while len(slots) < num_questions and rot < len(rotation):
        slots.append(rotation[rot])
        rot += 1

    plan = [_q(i, s["type"], s["question"], s.get("topic", "")) for i, s in enumerate(slots[:num_questions])]
    return plan


def _parse_llm_questions(text: str) -> List[str]:
    questions: List[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        # strip bullets / numbering like "1." "1、" "- " "* "
        line = re.sub(r"^\s*(\d+[\.\、\)]|[-*•])\s*", "", line).strip()
        if len(line) < 6:
            continue
        questions.append(line)
    return questions


def build_plan_with_llm(
    resume: str,
    jd: str,
    knowledge: str,
    num_questions: int,
    llm_generate: Optional[Callable[[str], str]],
    language: str = "zh",
    profile_hint: str = "",
) -> List[Dict]:
    """Try LLM-tailored questions, fall back to / top up from the deterministic bank."""
    base = build_plan(resume, jd, knowledge, num_questions, language)
    if llm_generate is None:
        return base

    en = _is_english(language)
    if en:
        target = f"Tailor the questions to this target — {profile_hint}.\n" if profile_hint else ""
        prompt = (
            "You are a senior technical interviewer. Based on the candidate resume and job description below, "
            f"generate {num_questions} high-quality interview questions in English, covering self-introduction, "
            "project deep-dive, technical, system design, and behavioral.\n"
            f"{target}"
            "Rules: one question per line, no numbering, no explanations, do not invent experience not in the resume.\n\n"
            f"[Resume]\n{resume[:1500]}\n\n[JD]\n{jd[:1200]}\n"
        )
    else:
        target = f"请针对以下目标定制问题——{profile_hint}。\n" if profile_hint else ""
        prompt = (
            "你是资深技术面试官。基于以下候选人简历和岗位 JD,生成"
            f" {num_questions} 道高质量中文面试题,覆盖自我介绍/项目深挖/技术/系统设计/行为面。\n"
            f"{target}"
            "要求:每行一题,不要编号,不要解释,不要编造简历里没有的经历。\n\n"
            f"[简历]\n{resume[:1500]}\n\n[JD]\n{jd[:1200]}\n"
        )
    try:
        text = llm_generate(prompt)
    except Exception:
        return base

    raw_questions = _parse_llm_questions(text)
    if not raw_questions:
        return base

    plan: List[Dict] = []
    for question in raw_questions[:num_questions]:
        classification = classify_interview_input(question)
        qtype = classification.get("question_type", "behavioral")
        if qtype not in _KNOWN_TYPES:
            qtype = "behavioral"
        plan.append(_q(len(plan), qtype, question, ""))

    # top up from deterministic bank if the model returned too few
    if len(plan) < num_questions:
        for slot in base[len(plan):num_questions]:
            slot = dict(slot)
            slot["index"] = len(plan)
            slot["id"] = f"q{len(plan) + 1}"
            plan.append(slot)
    return plan


def make_followup(question_type: str, asked: set[str], language: str = "zh") -> Optional[str]:
    """Return a follow-up probe for the given type that hasn't been asked yet."""
    table = FOLLOWUP_BY_TYPE_EN if _is_english(language) else FOLLOWUP_BY_TYPE
    for candidate in table.get(question_type, table["behavioral"]):
        if candidate not in asked:
            return candidate
    return None
