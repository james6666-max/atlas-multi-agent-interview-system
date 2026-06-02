from app.blackboard.events import BBEvent, EventType
from app.rag.local_rag import (
    load_knowledge_text,
    retrieve_local_knowledge,
    retrieve_session_history,
    split_passages,
)


def test_load_knowledge_text_reads_existing_file(tmp_path) -> None:
    (tmp_path / "knowledge.txt").write_text("RESTful API uses HTTP resources.", encoding="utf-8")

    assert "RESTful API" in load_knowledge_text(base_dir=tmp_path)


def test_load_knowledge_text_missing_file_returns_empty(tmp_path) -> None:
    assert load_knowledge_text(base_dir=tmp_path) == ""


def test_retrieve_local_knowledge_returns_top_k_chunks() -> None:
    text = """
RESTful API uses resources, HTTP methods, and stateless requests.

React components manage frontend UI state.

FastAPI can expose backend API endpoints.
"""

    chunks = retrieve_local_knowledge("What is RESTful API?", text, top_k=2)

    assert len(chunks) == 2
    assert chunks[0]["source"] == "knowledge.txt"
    assert chunks[0]["score"] >= chunks[1]["score"]
    assert "RESTful" in chunks[0]["text"]


def test_retrieve_local_knowledge_no_keyword_hit_is_stable() -> None:
    chunks = retrieve_local_knowledge("binary tree traversal", "Only unrelated deployment notes.", top_k=3)

    assert chunks == []


def test_retrieve_session_history_finds_answer_and_context_events() -> None:
    events = [
        BBEvent(
            session_id="session-1",
            source_agent="test",
            type=EventType.ANSWER_FINAL,
            payload={"question": "old", "answer": "RESTful API is stateless and uses HTTP methods."},
        ),
        BBEvent(
            session_id="session-1",
            source_agent="test",
            type=EventType.CONTEXT_LOADED,
            payload={"knowledge_summary": "FastAPI exposes API routes for backend services."},
        ),
    ]

    chunks = retrieve_session_history("What is RESTful API?", events, top_k=3)

    assert len(chunks) == 2
    assert {chunk["source"] for chunk in chunks} == {"session_replay"}
    assert all(chunk["event_type"] in {"answer_final", "context_loaded"} for chunk in chunks)


def test_chinese_query_retrieves_chinese_passage() -> None:
    text = """
短链接系统通过哈希和发号器生成唯一短码,并用缓存和数据库分层存储。

React 组件管理前端界面状态。

限流器常用令牌桶或滑动窗口算法实现。
"""
    chunks = retrieve_local_knowledge("如何设计一个高并发的短链接系统?", text, top_k=2)
    assert chunks, "Chinese query should now hit the Chinese knowledge passage"
    assert "短链接" in chunks[0]["text"]


def test_chinese_bigram_terms() -> None:
    from app.rag.local_rag import extract_query_terms

    terms = extract_query_terms("短链接系统设计")
    assert "短链" in terms and "链接" in terms and "系统" in terms
    # common function-word bigrams are filtered out
    assert "如何" not in extract_query_terms("如何设计一个系统")


def test_split_passages_limits_chunk_length() -> None:
    text = "a" * 1200

    chunks = split_passages(text, max_chars=600)

    assert chunks
    assert all(len(chunk) <= 600 for chunk in chunks)
