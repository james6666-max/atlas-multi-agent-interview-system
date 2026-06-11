"""Questions/answers/report must follow the candidate's actual resume & JD,
not the bundled Atlas demo profile."""
import os

os.environ["USE_OLLAMA"] = "false"

from app.coaching import question_bank  # noqa: E402

import orchestrator_v0  # noqa: E402

NON_TECH_RESUME = "我平时喜欢摄影和写作，组织过校园社团活动，担任过志愿者队长。"
BACKEND_JD = "招聘后端工程师，要求熟悉 Python、FastAPI、Redis 与分布式系统。"


def test_resume_deep_dive_does_not_borrow_jd_topics():
    plan = question_bank.build_plan(NON_TECH_RESUME, BACKEND_JD, "", num_questions=5)
    # The resume has no known tech topic, so no question may claim
    # "你简历里和「FastAPI 后端」相关" based on JD-only topics.
    for item in plan:
        if "你简历里" in item["question"]:
            assert "FastAPI" not in item["question"]
            assert "分布式" not in item["question"]
    # JD-driven technical/system questions are still allowed (role-relevant).
    types = {item["type"] for item in plan}
    assert "technical" in types


def test_resume_deep_dive_uses_resume_topic_when_present():
    resume = "我主导过 React 前端项目，负责组件库和性能优化。"
    plan = question_bank.build_plan(resume, BACKEND_JD, "", num_questions=5)
    resume_questions = [q for q in plan if q["type"] == "resume_followup"]
    assert resume_questions and "React" in resume_questions[0]["question"]


def test_detect_topics_english_display():
    topics = question_bank.detect_topics("FastAPI and Redis services", "", "", language="en")
    assert "FastAPI backend" in topics
    assert all(not any("一" <= ch <= "鿿" for ch in t) for t in topics)


def test_reinforce_skips_non_atlas_resume():
    meta = {"resume_context_loaded": True}
    answer = "I would clarify requirements first and then design for scaling."
    kept = orchestrator_v0.reinforce_resume_context_signals(
        answer, "Design a URL shortener?", "System Design", meta, NON_TECH_RESUME
    )
    assert kept == answer  # no Atlas/FastAPI stack injected

    atlas_resume = "我开发了 Atlas 多智能体面试系统，FastAPI 后端。"
    enriched = orchestrator_v0.reinforce_resume_context_signals(
        answer, "Design a URL shortener?", "System Design", meta, atlas_resume
    )
    assert "Atlas" in enriched


def test_report_recommendations_follow_profile(monkeypatch):
    monkeypatch.setattr(orchestrator_v0, "load_resume_context", lambda: (NON_TECH_RESUME, {}))
    monkeypatch.setattr(orchestrator_v0, "load_jd_context", lambda: ("招聘市场营销专员，负责品牌推广与活动策划。", {}))
    report = orchestrator_v0.build_session_report("zh")
    joined = "\n".join(report["recommended_practice"])
    assert "Atlas" not in joined
    assert "FastAPI" not in joined
