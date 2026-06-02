import asyncio

from app.agents.perception_agent import PerceptionAgent, classify_interview_input
from app.blackboard.bus import InMemoryBlackboardBus
from app.blackboard.events import BBEvent, EventType


def event(event_type: EventType, payload: dict) -> BBEvent:
    return BBEvent(
        session_id="session-1",
        source_agent="test",
        type=event_type,
        payload=payload,
    )


def test_classifies_technical_question() -> None:
    result = classify_interview_input("解释一下 Python 的 GIL。")

    assert result["should_answer"] is True
    assert result["question_type"] == "technical"


def test_classifies_algorithm_question() -> None:
    result = classify_interview_input("请写一个二分查找，并分析时间复杂度。")

    assert result["should_answer"] is True
    assert result["question_type"] == "algorithm"


def test_classifies_behavioral_question() -> None:
    result = classify_interview_input("请用 STAR 法介绍一次你解决困难的经历。")

    assert result["should_answer"] is True
    assert result["question_type"] == "behavioral"


def test_classifies_system_design_question() -> None:
    result = classify_interview_input("如果让你设计一个秒杀系统，你会怎么做？")

    assert result["should_answer"] is True
    assert result["question_type"] == "system_design"


def test_classifies_resume_followup_question() -> None:
    result = classify_interview_input("你简历里的这个项目具体做了什么？")

    assert result["should_answer"] is True
    assert result["question_type"] == "resume_followup"


def test_chitchat_is_skipped() -> None:
    result = classify_interview_input("你好")

    assert result["should_answer"] is False
    assert result["question_type"] == "chitchat"


def test_partial_input_is_skipped() -> None:
    result = classify_interview_input("如果让你")

    assert result["should_answer"] is False


def test_empty_input_is_skipped() -> None:
    result = classify_interview_input("")

    assert result["should_answer"] is False
    assert result["reason"] == "empty_input"


def test_transcript_from_user_is_skipped() -> None:
    bus = InMemoryBlackboardBus()
    agent = PerceptionAgent(bus)

    outputs = asyncio.run(
        agent.run_once(
            event(
                EventType.TRANSCRIPT_FINAL,
                {"transcript": "解释一下数据库索引。", "speaker": "user"},
            )
        )
    )

    assert outputs == []


def test_manual_input_from_user_can_emit_question_detected() -> None:
    bus = InMemoryBlackboardBus()
    agent = PerceptionAgent(bus)

    outputs = asyncio.run(
        agent.run_once(
            event(
                EventType.MANUAL_INPUT,
                {"question": "解释一下数据库索引为什么能加速查询。", "speaker": "user"},
            )
        )
    )

    assert len(outputs) == 1
    assert outputs[0].type == EventType.QUESTION_DETECTED
    assert outputs[0].payload["question_type"] == "technical"
