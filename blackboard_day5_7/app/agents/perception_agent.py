from __future__ import annotations

import re
from typing import Any, ClassVar, Dict, List, Set

from app.agents.base import Agent
from app.blackboard.events import BBEvent, EventType


QUESTION_MARKERS = ("?", "？", "how", "what", "why", "when", "where", "which")

TECHNICAL_KEYWORDS = {
    "python",
    "java",
    "c++",
    "golang",
    "操作系统",
    "数据库",
    "网络",
    "http",
    "tcp",
    "api",
    "restful",
    "react",
    "vue",
    "fastapi",
    "docker",
    "linux",
    "线程",
    "进程",
    "锁",
    "索引",
    "事务",
    "缓存",
    "分布式",
    "gil",
    "useeffect",
}

ALGORITHM_KEYWORDS = {
    "算法",
    "复杂度",
    "数组",
    "链表",
    "栈",
    "队列",
    "二叉树",
    "图",
    "动态规划",
    "贪心",
    "二分",
    "dfs",
    "bfs",
    "排序",
    "哈希",
    "滑动窗口",
    "两数之和",
}

SYSTEM_DESIGN_KEYWORDS = {
    "设计一个",
    "系统设计",
    "高并发",
    "秒杀",
    "短链接",
    "架构",
    "扩展性",
    "负载均衡",
    "消息队列",
    "限流",
    "熔断",
    "一致性",
    "design a",
    "system design",
    "scalable",
    "rate limiter",
}

BEHAVIORAL_KEYWORDS = {
    "介绍一下你自己",
    "自我介绍",
    "优点",
    "缺点",
    "困难",
    "挑战",
    "冲突",
    "合作",
    "团队",
    "压力",
    "失败",
    "成功",
    "经历",
    "star",
    "tell me about",
    "describe a time",
    "strength",
    "weakness",
}

RESUME_FOLLOWUP_KEYWORDS = {
    "简历",
    "项目",
    "负责",
    "实习",
    "论文",
    "比赛",
    "你做了什么",
    "你的贡献",
    "为什么用",
    "怎么实现",
    "resume",
    "project",
    "internship",
    "contribution",
}

CHITCHAT_PATTERNS = {
    "你好",
    "您好",
    "hello",
    "hi",
    "今天天气不错",
    "你能听到我吗",
    "能听到吗",
    "我们先等一下",
    "稍等一下",
    "等一下",
    "ok",
    "okay",
    "好的",
    "嗯",
    "啊",
}

PARTIAL_PATTERNS = {
    "我想问一下这个",
    "那你觉得",
    "如果让你",
    "关于这个项目",
    "我想问一下",
    "这个项目",
    "然后呢",
}


class PerceptionAgent(Agent):
    name: ClassVar[str] = "perception_agent"
    subscribes_to: ClassVar[Set[EventType]] = {
        EventType.MANUAL_INPUT,
        EventType.TRANSCRIPT_FINAL,
        EventType.OCR_TEXT,
    }
    emits: ClassVar[Set[EventType]] = {EventType.QUESTION_DETECTED}
    latency_budget_ms: ClassVar[int] = 50

    async def handle(self, event: BBEvent) -> List[BBEvent]:
        if self._should_skip_source(event):
            return []

        text = self._extract_text(event.payload)
        result = classify_interview_input(text)

        if not result["should_answer"]:
            return []

        return [
            BBEvent(
                session_id=event.session_id,
                source_agent=self.name,
                type=EventType.QUESTION_DETECTED,
                parent_event_id=event.event_id,
                payload={
                    "question": result["question"],
                    "question_type": result["question_type"],
                    "confidence": result["confidence"],
                    "reason": result["reason"],
                    "source_event_type": event.type.value,
                    "source": event.payload.get("source", "unknown"),
                    "language": event.payload.get("language", "Unknown"),
                },
            )
        ]

    def _extract_text(self, payload: Dict[str, Any]) -> str:
        for key in ("question", "text", "input", "transcript", "ocr_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _should_skip_source(event: BBEvent) -> bool:
        if event.type == EventType.MANUAL_INPUT:
            return False
        return event.payload.get("speaker") == "user" or event.payload.get("channel") == "mic"


def classify_interview_input(text: str) -> dict:
    cleaned = _clean_text(text)
    lowered = cleaned.lower()

    if not cleaned:
        return _result(False, cleaned, "unknown", 0.0, "empty_input")

    if len(cleaned) <= 2 or lowered in CHITCHAT_PATTERNS:
        return _result(False, cleaned, "chitchat", 0.95, "too_short_or_chitchat")

    if any(pattern in lowered for pattern in CHITCHAT_PATTERNS):
        return _result(False, cleaned, "chitchat", 0.9, "chitchat_phrase")

    if _is_partial(cleaned, lowered):
        return _result(False, cleaned, "unknown", 0.85, "partial_or_incomplete_input")

    category, reason, confidence = _classify_category(cleaned, lowered)
    if category != "unknown":
        return _result(True, cleaned, category, confidence, reason)

    if _looks_like_question(cleaned, lowered):
        return _result(True, cleaned, "technical", 0.55, "question_shape_without_specific_category")

    return _result(False, cleaned, "unknown", 0.45, "not_interview_question")


def _classify_category(cleaned: str, lowered: str) -> tuple[str, str, float]:
    if _contains_any(lowered, SYSTEM_DESIGN_KEYWORDS):
        return "system_design", "matched_system_design_keywords", 0.9
    if _contains_any(lowered, ALGORITHM_KEYWORDS):
        return "algorithm", "matched_algorithm_keywords", 0.88
    if _contains_any(lowered, BEHAVIORAL_KEYWORDS):
        return "behavioral", "matched_behavioral_keywords", 0.86
    if _contains_any(lowered, RESUME_FOLLOWUP_KEYWORDS):
        return "resume_followup", "matched_resume_followup_keywords", 0.84
    if _contains_any(lowered, TECHNICAL_KEYWORDS):
        return "technical", "matched_technical_keywords", 0.82
    return "unknown", "no_category_keywords", 0.0


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _contains_any(lowered: str, keywords: set[str]) -> bool:
    return any(keyword in lowered for keyword in keywords)


def _looks_like_question(cleaned: str, lowered: str) -> bool:
    return cleaned.endswith(("?", "？")) or any(marker in lowered for marker in QUESTION_MARKERS)


def _is_partial(cleaned: str, lowered: str) -> bool:
    if lowered in PARTIAL_PATTERNS:
        return True
    if any(lowered.endswith(pattern) for pattern in PARTIAL_PATTERNS):
        return True
    return len(cleaned) < 8 and not _looks_like_question(cleaned, lowered)


def _result(
    should_answer: bool,
    question: str,
    question_type: str,
    confidence: float,
    reason: str,
) -> dict:
    return {
        "should_answer": should_answer,
        "question": question,
        "question_type": question_type,
        "confidence": confidence,
        "reason": reason,
    }
