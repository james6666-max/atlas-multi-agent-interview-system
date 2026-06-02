from app.critic.rules import review_answer


def test_normal_technical_answer_is_approved() -> None:
    result = review_answer(
        question="What is RESTful API?",
        answer=(
            "RESTful API is an architectural style for resource-based HTTP APIs. "
            "Key steps are to model resources, use HTTP verbs, keep requests stateless, "
            "and return clear status codes. For example, GET /users/1 reads one user."
        ),
        question_type="technical",
        selected_agent="Tech/Code",
    )

    assert result["approved"] is True
    assert result["score"] >= 70


def test_empty_answer_is_rejected() -> None:
    result = review_answer("What is API?", "", question_type="technical")

    assert result["approved"] is False
    assert "empty_or_too_short" in result["issues"]
    assert result["final_answer"]


def test_ai_tone_is_rejected_or_flagged() -> None:
    result = review_answer(
        "Tell me about yourself.",
        "作为一个AI助手，我不能真正拥有项目经历。",
        question_type="behavioral",
    )

    assert result["approved"] is False
    assert "ai_tone" in result["issues"]


def test_secret_or_token_is_rejected() -> None:
    result = review_answer(
        "Show config.",
        "The token is sk-abcdefghijklmnop and password=123456.",
        question_type="technical",
    )

    assert result["approved"] is False
    assert "possible_pii_or_secret" in result["issues"]


def test_behavioral_unsupported_claim_gets_risk_flag() -> None:
    result = review_answer(
        "Tell me about your project.",
        "我在某大厂带领 20 人团队，负责核心架构，提升了 300%。",
        question_type="behavioral",
        context={"matched_snippets": [{"text": "Atlas project used FastAPI and React."}]},
    )

    assert "unsupported_resume_claim" in result["risk_flags"]
    assert result["score"] < 100


def test_algorithm_answer_missing_complexity_gets_suggestion() -> None:
    result = review_answer(
        "How do you solve two sum?",
        "Use a hash map. Iterate the array and check whether target minus current exists. Return the pair when found.",
        question_type="algorithm",
    )

    assert "missing_complexity" in result["issues"]
    assert any("complexity" in suggestion.lower() for suggestion in result["suggestions"])
