from app.coaching import question_bank
from app.profile_store import profile_hint, read_profile, read_all, save_all


def test_save_and_read(tmp_path):
    save_all(
        {
            "resume": "my resume",
            "jd": "the jd",
            "company": "Acme",
            "position": "Backend Engineer",
            "focus": "distributed systems",
        },
        base_dir=tmp_path,
    )
    data = read_all(base_dir=tmp_path)
    assert data["resume"] == "my resume"
    assert data["jd"] == "the jd"
    assert data["company"] == "Acme"
    assert data["position"] == "Backend Engineer"
    assert (tmp_path / "resume.txt").read_text(encoding="utf-8") == "my resume"
    assert (tmp_path / "profile.json").exists()


def test_partial_update_preserves_other_fields(tmp_path):
    save_all({"company": "Acme"}, base_dir=tmp_path)
    save_all({"position": "SRE"}, base_dir=tmp_path)
    p = read_profile(base_dir=tmp_path)
    assert p["company"] == "Acme"
    assert p["position"] == "SRE"


def test_profile_hint_formatting(tmp_path):
    save_all({"company": "字节跳动", "position": "后端工程师", "focus": "分布式"}, base_dir=tmp_path)
    h = profile_hint(base_dir=tmp_path)
    assert "字节跳动" in h and "后端工程师" in h and "分布式" in h


def test_profile_hint_flows_into_llm_question_prompt():
    captured = {}

    def fake_llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "请介绍一下你自己?\n讲讲你的项目?"

    question_bank.build_plan_with_llm(
        "resume text", "jd text", "", 4, fake_llm, "zh",
        profile_hint="目标公司: 字节跳动 | 目标职位: 后端工程师",
    )
    assert "字节跳动" in captured["prompt"]
    assert "后端工程师" in captured["prompt"]
