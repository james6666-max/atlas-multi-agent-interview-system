from app.coaching import question_bank
from app.coaching.service import CoachingService

RESUME = (
    "在 Atlas 项目中负责 FastAPI 后端与多 Agent 架构,"
    "使用 React + Electron 做桌面端,接入 Ollama 本地大模型和 Whisper 语音识别。"
)
JD = "招聘后端工程师,要求熟悉 Python、FastAPI、RAG、Redis 与分布式系统。"


def fake_sources():
    return {"resume": RESUME, "jd": JD, "knowledge": ""}


def make_service(llm=None) -> CoachingService:
    return CoachingService(resume_provider=fake_sources, llm_generate=llm)


def test_plan_detects_topics_and_mixes_types():
    plan = question_bank.build_plan(RESUME, JD, "", num_questions=5)
    assert len(plan) == 5
    assert plan[0]["type"] == "behavioral"  # self-intro first
    types = {item["type"] for item in plan}
    # resume present + tech topics detected -> resume_followup + technical + system_design appear
    assert "resume_followup" in types
    assert "technical" in types
    assert "system_design" in types
    # at least one topic is a detected display topic
    assert any("FastAPI" in (item["topic"] or "") or "Agent" in (item["topic"] or "") for item in plan)


def test_start_returns_first_question():
    svc = make_service()
    state = svc.start("s1", num_questions=5)
    assert state.active is True
    assert state.total_planned == 5
    assert state.current_question is not None
    assert state.round_index == 0


def test_full_session_runs_to_completion_and_reports():
    svc = make_service()
    svc.start("s2", num_questions=4)
    answer = (
        "在 Atlas 项目里我负责 FastAPI 后端和多 Agent 编排。Situation 是需要把单体流程拆成多个 Agent,"
        "Task 是保证延迟和一致性,Action 是引入事件总线和 Critic 审稿,Result 是可演示可评测,"
        "时间复杂度和扩展性也都有考虑,trade-off 是用内存总线换简单性。"
    )
    guard = 0
    while True:
        result = svc.submit_answer("s2", answer)
        guard += 1
        assert guard < 20
        if result["completed"]:
            break
    state = svc.state("s2")
    assert state.completed is True
    assert state.round_index >= 4
    report = svc.report("s2")
    assert report["overall_score"] > 0
    assert len(report["question_reviews"]) == state.round_index
    assert "by_type" in report


def test_weak_answer_triggers_followup():
    svc = make_service()
    svc.start("s3", num_questions=4)
    # an empty/short answer scores low -> should trigger a follow-up insert
    result = svc.submit_answer("s3", "不知道")
    assert result["feedback"]["approved"] is False
    state = svc.state("s3")
    # follow-up inserted -> queue grew beyond the original plan
    assert state.followups_used >= 1
    assert state.queue_length > state.total_planned
    assert state.current_question.is_followup is True


def test_followups_are_capped():
    svc = make_service()
    svc.start("s4", num_questions=6)
    for _ in range(20):
        r = svc.submit_answer("s4", "")
        if r["completed"]:
            break
    assert svc.state("s4").followups_used <= 2


def test_english_language_produces_english_questions_and_followups():
    svc = make_service()
    state = svc.start("en1", num_questions=4, language="en")
    assert state.config["language"] == "en"
    # first question (self-intro) should be the English bank entry
    assert "self-introduction" in state.current_question.question.lower()
    # weak answer -> English follow-up probe
    result = svc.submit_answer("en1", "I don't know")
    nxt = result["next_question"]
    assert nxt and nxt["is_followup"] is True
    # English follow-up text (ASCII), not Chinese
    assert nxt["question"].isascii()


def test_submit_without_start_raises():
    svc = make_service()
    try:
        svc.submit_answer("missing", "hi")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_llm_questions_used_when_available():
    def fake_llm(prompt: str) -> str:
        return (
            "1. 请解释 FastAPI 的依赖注入是怎么工作的?\n"
            "2. 讲一个你最有成就感的项目。\n"
            "3. 如果让你设计一个高并发的限流系统,你会怎么做?\n"
            "4. 你在简历里提到的 RAG,具体是怎么实现的?\n"
        )

    svc = make_service(llm=fake_llm)
    state = svc.start("s5", num_questions=4)
    questions = [t.question for t in []]  # noqa: F841 - placeholder
    plan_questions = [state.current_question.question]
    # drain to inspect all
    seen = [state.current_question.question]
    while True:
        r = svc.submit_answer("s5", "一些回答内容,包含复杂度和例子。")
        nxt = r["next_question"]
        if nxt:
            seen.append(nxt["question"])
        if r["completed"]:
            break
    assert any("FastAPI" in q for q in seen)
