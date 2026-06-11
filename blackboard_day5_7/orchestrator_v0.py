from __future__ import annotations

import threading
import time
import tempfile
import os
import re
import json
import requests
import asyncio

from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from uuid import uuid4
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
# NOTE: rapidocr_onnxruntime / faster_whisper are imported lazily inside their
# getters (get_ocr_engine / get_whisper_model) so the heavy onnxruntime /
# ctranslate2 / cv2 DLLs do NOT load at startup — the server boots in seconds.
from pydantic import BaseModel

from app.adapters.phase1_pipeline import configure_phase1_pipeline
from app.agents.perception_agent import classify_interview_input
from app.blackboard.events import BBEvent, EventType
from app.coaching.models import AnswerRequest, StartRequest
from app.coaching.service import CoachingService
from app.critic.rules import review_answer
from app.llm.config import LLMConfig, load_config, save_settings
from app.llm.router import LLMRouter, build_router
from app.orchestrator.factory import create_phase2_runtime
from app.paths import data_dir, ensure_seed_files, resource_dir
from app.rag.local_rag import load_knowledge_text, retrieve_local_knowledge
from app.resume.context_loader import build_candidate_context
from blackboard_store import BlackboardStore

app = FastAPI(title="Orchestrator v0 - Blackboard Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Seed writable data dir with bundled defaults on first launch (no-op in dev).
ensure_seed_files([
    "blackboard_instance.json",
    "blackboard_schema.json",
    "resume.txt",
    "jd.txt",
    "knowledge.txt",
])
store = BlackboardStore(
    data_path=str(data_dir() / "blackboard_instance.json"),
    schema_path=str(resource_dir() / "blackboard_schema.json"),
)
phase2_bus, phase2_orchestrator = create_phase2_runtime()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
RESUME_PATH = os.getenv("RESUME_PATH", "resume.txt")
USE_RESUME_CONTEXT = os.getenv("USE_RESUME_CONTEXT", "true").lower() == "true"
JD_PATH = os.getenv("JD_PATH", "jd.txt")
USE_JD_CONTEXT = os.getenv("USE_JD_CONTEXT", "true").lower() == "true"
KNOWLEDGE_PATH = os.getenv("KNOWLEDGE_PATH", "knowledge.txt")
USE_KNOWLEDGE_CONTEXT = os.getenv("USE_KNOWLEDGE_CONTEXT", "true").lower() == "true"

# Tiered LLM runtime (M1): local Ollama + optional cloud (OpenAI-compatible),
# hot-reloadable from the Settings UI via /config.
_llm_config: LLMConfig = load_config()
_llm_router: LLMRouter = build_router(_llm_config)


def get_llm_config() -> LLMConfig:
    return _llm_config


def get_llm_router() -> LLMRouter:
    return _llm_router


def reload_llm() -> LLMConfig:
    global _llm_config, _llm_router
    _llm_config = load_config()
    _llm_router = build_router(_llm_config)
    return _llm_config


def _coaching_llm_generate(prompt: str) -> str:
    """LLM generator for practice question generation.

    Respects the current runtime config: when no LLM is enabled/configured this
    raises, and the question bank deterministically falls back to its template
    plan (keeps eval/smoke and key-less setups fast and offline).
    """
    cfg = get_llm_config()
    if not (cfg.use_ollama or cfg.cloud_configured):
        raise RuntimeError("LLM disabled; using deterministic question bank")
    text, _ = get_llm_router().generate(prompt)
    return text


# Coaching / practice loop (M2): turn-based mock interview driven by resume/JD,
# scored by the same rule-based critic as the live path.
_coaching_service = CoachingService(llm_generate=_coaching_llm_generate)


_whisper_model = None
_mock_state = {
    "active": False,
    "round_index": 0,
    "completed": False,
    "questions": [],
    "answers": []
}


def get_whisper_model():
    global _whisper_model

    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel  # lazy: avoid loading ctranslate2 at startup
        except ImportError as exc:
            # Lite delivery build ships without the STT stack; degrade gracefully.
            raise HTTPException(
                status_code=503,
                detail="此交付版本未包含语音转写功能,请使用文字 / 截图提问 (Voice STT not bundled in this build).",
            ) from exc
        model_name = os.getenv("ATLAS_WHISPER_MODEL", "small")
        # Set ATLAS_WHISPER_MODEL=tiny for faster local startup on weaker CPUs.
        _whisper_model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8"
        )

    return _whisper_model


def transcribe_audio_file(audio_path: str, language: str = "auto") -> str:
    model = get_whisper_model()

    whisper_language = None
    if language == "Chinese":
        whisper_language = "zh"
    elif language == "English":
        whisper_language = "en"

    segments, info = model.transcribe(
    audio_path,
    language=whisper_language,
    vad_filter=True,
    beam_size=5,
    best_of=5,
    temperature=0,
    initial_prompt="这是一段中文或英文的面试问题语音，请准确转写技术面试、系统设计、算法、行为面试相关内容。常见词包括：系统设计、短链接、限流器、API、算法、二分查找、面向对象、多态、缓存、数据库、队列、并发。"
)
    

    texts = []
    for segment in segments:
        if segment.text and segment.text.strip():
            texts.append(segment.text.strip())

    return " ".join(texts).strip()




_ocr_engine = None
_ocr_lock = threading.Lock()


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        with _ocr_lock:  # pre-warm thread and first request may race here
            if _ocr_engine is None:
                from rapidocr_onnxruntime import RapidOCR  # lazy: avoid loading onnxruntime/cv2 at startup
                _ocr_engine = RapidOCR()
    return _ocr_engine


@app.on_event("startup")
def _prewarm_ocr_in_background() -> None:
    """Load the OCR model shortly after boot so the first screenshot ask
    (Ctrl+Shift+A) doesn't pay the multi-second model load. Startup itself
    stays fast (the load runs in a daemon thread) and this is a no-op when
    the OCR stack isn't bundled. Disable with ATLAS_PREWARM_OCR=0."""
    if os.getenv("ATLAS_PREWARM_OCR", "1").lower() in {"0", "false"}:
        return

    def _load() -> None:
        time.sleep(2)  # let the server finish booting before the heavy import
        try:
            get_ocr_engine()
            print("[startup] OCR engine pre-warmed")
        except Exception as exc:  # e.g. OCR not bundled in a minimal build
            print(f"[startup] OCR pre-warm skipped: {exc}")

    threading.Thread(target=_load, name="ocr-prewarm", daemon=True).start()


def extract_text_from_image(image_path: str) -> str:
    path = Path(image_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Image file not found: {image_path}"
        )

    engine = get_ocr_engine()
    result, _ = engine(str(path))

    if not result:
        return ""

    lines = []
    for item in result:
        # RapidOCR item format usually:
        # [box, text, confidence]
        if len(item) >= 2:
            text = item[1]
            if isinstance(text, str) and text.strip():
                lines.append(text.strip())

    return "\n".join(lines)

def clean_ocr_question(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    keywords = [
        "design",
        "explain",
        "implement",
        "how would you",
        "what is",
        "rate limiter",
        "api",
        "system",
        "algorithm",
        "binary search",
        "leetcode",
        "请设计",
        "解释",
        "实现",
        "系统",
        "算法",
        "面试题",
        "设计一个",
    ]

    noise_keywords = [
        "cmd.exe",
        "windows",
        "microsoft",
        "chrome",
        "chatgpt",
        "powershell",
        "uvicorn",
        "vite",
        "electron",
        "console",
        "localhost",
        "127.0.0.1",
        "app.tsx",
        "dist-electron",
        "node_modules",
        "error",
        "warning",
    ]

    candidates = []

    for line in lines:
        lower = line.lower()

        if any(noise in lower for noise in noise_keywords):
            continue

        if any(keyword in lower for keyword in keywords):
            candidates.append(line)

    if candidates:
        return "\n".join(candidates[:5])

    cleaned_lines = []
    for line in lines:
        lower = line.lower()

        if any(noise in lower for noise in noise_keywords):
            continue

        if len(line) >= 8:
            cleaned_lines.append(line)

    if cleaned_lines:
        return "\n".join(cleaned_lines[:10])

    return "\n".join(lines[:10])

class AskRequest(BaseModel):
    question: str
    language: Literal["Chinese", "English", "Mixed", "Unknown"] = "Unknown"
    source: Literal["manual_input", "ocr", "stt", "imported"] = "manual_input"

class AskImageRequest(BaseModel):
    image_path: str
    language: str = "Unknown"
    source: str = "ocr"


class MockAnswerRequest(BaseModel):
    answer: str


class CriticResult(BaseModel):
    approved: bool = True
    score: int = 100
    issues: list[str] = []
    suggestions: list[str] = []
    risk_flags: list[str] = []
    clarity_score: float
    correctness_score: float
    human_like_score: float
    resume_alignment_score: float
    privacy_score: float
    jd_alignment_score: float
    jd_alignment_notes: list[str]
    final_score: int
    main_weakness: str
    specific_issues: list[str]
    rewrite_strategy: str
    should_rewrite: bool
    critic_notes: list[str]
    improved_answer_suggestion: str
    human_like_rewrite: dict = {}
    followup_questions: dict = {}


class AskResponse(BaseModel):
    question: str
    question_type: str
    selected_agent: str
    answer: str
    critic: CriticResult
    blackboard_version: int
    context_used: bool = False
    context_sources: list[str] = []
    rag_used: bool = False
    rag_sources: list[str] = []
    session_id: str = ""
    # Which engine produced the answer ("ollama"/"cloud"/"stub") and whether it
    # was a fallback — lets the UI warn when no real LLM is configured.
    answer_source: str = ""
    llm_fallback: bool = False


class LLMConfigUpdate(BaseModel):
    mode: str | None = None
    use_ollama: bool | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    cloud_base_url: str | None = None
    cloud_api_key: str | None = None
    cloud_model: str | None = None


def classify_question(question: str) -> str:
    q = question.lower()
    behavioral_keywords = [
        "tell me about a time",
        "tell me about a project",
        "project you are proud",
        "proud of",
        "describe a time",
        "describe a project",
        "conflict",
        "feedback",
        "strength",
        "weakness",
        "good fit",
        "fit for this role",
        "why are you",
        "experience",
        "background",
        "项目",
        "困难",
        "冲突",
        "优点",
        "不足",
        "为什么",
        "经历"
    ]
    system_design_keywords = ["design", "architecture", "scalable", "rate limiter", "url shortener", "设计", "架构", "高并发", "系统", "短链接", "秒杀", "推荐"]
    if any(k in q for k in behavioral_keywords):
        return "Behavioral"
    if any(k in q for k in system_design_keywords):
        return "System Design"
    return "Technical/Algorithm"


def select_agent(question_type: str) -> str:
    if question_type == "Behavioral":
        return "Behavioral"
    return "Tech/Code"

def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    answer = data.get("response", "")

    return answer.strip()


def load_resume_context() -> tuple[str, dict]:
    if not USE_RESUME_CONTEXT:
        return "", {
            "resume_context_loaded": False,
            "resume_path": RESUME_PATH,
            "resume_error": "USE_RESUME_CONTEXT is false"
        }

    try:
        path = Path(RESUME_PATH)

        if not path.is_absolute():
            path = data_dir() / path

        if not path.exists():
            return "", {
                "resume_context_loaded": False,
                "resume_path": str(path),
                "resume_error": "resume.txt not found"
            }

        text = path.read_text(encoding="utf-8").strip()

        if not text:
            return "", {
                "resume_context_loaded": False,
                "resume_path": str(path),
                "resume_error": "resume.txt is empty"
            }

        max_chars = 3500
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[简历内容过长，已截断]"

        return text, {
            "resume_context_loaded": True,
            "resume_path": str(path),
            "resume_error": None
        }

    except Exception as error:
        return "", {
            "resume_context_loaded": False,
            "resume_path": RESUME_PATH,
            "resume_error": str(error)
        }


def load_jd_context() -> tuple[str, dict]:
    if not USE_JD_CONTEXT:
        return "", {
            "jd_context_loaded": False,
            "jd_path": JD_PATH,
            "jd_error": "USE_JD_CONTEXT is false"
        }

    try:
        path = Path(JD_PATH)

        if not path.is_absolute():
            path = data_dir() / path

        if not path.exists():
            return "", {
                "jd_context_loaded": False,
                "jd_path": str(path),
                "jd_error": "jd.txt not found"
            }

        text = path.read_text(encoding="utf-8").strip()

        if not text:
            return "", {
                "jd_context_loaded": False,
                "jd_path": str(path),
                "jd_error": "jd.txt is empty"
            }

        max_chars = 3500
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[JD context truncated]"

        return text, {
            "jd_context_loaded": True,
            "jd_path": str(path),
            "jd_error": None
        }

    except Exception as error:
        return "", {
            "jd_context_loaded": False,
            "jd_path": JD_PATH,
            "jd_error": str(error)
        }


def compute_resume_jd_match(resume_context: str, jd_context: str) -> dict:
    if not resume_context:
        return {
            "match_score": 0.0,
            "strong_matches": [],
            "gaps": ["resume_context_missing"],
            "interview_focus": []
        }

    if not jd_context:
        return {
            "match_score": 0.0,
            "strong_matches": [],
            "gaps": ["jd_context_missing"],
            "interview_focus": []
        }

    keyword_groups = {
        "python_fastapi": ["python", "fastapi", "api", "后端", "接口"],
        "frontend_electron": ["react", "typescript", "electron", "前端", "桌面"],
        "local_llm": ["ollama", "llm", "大模型", "本地模型", "qwen"],
        "speech_ocr": ["whisper", "ocr", "rapidocr", "语音识别", "截图"],
        "agent_system": ["agent", "multi-agent", "多智能体", "orchestrator", "blackboard"],
        "debugging": ["debug", "调试", "排错", "联调", "稳定性"],
        "privacy": ["privacy", "隐私", "本地优先", "local-first"]
    }
    focus_map = {
        "python_fastapi": "重点讲 FastAPI 后端接口设计、/ask、/ask_image、/ask_audio 等 API 链路。",
        "frontend_electron": "重点讲 Electron + React 前端面板、截图按钮、Whisper 面板和状态可视化。",
        "local_llm": "重点讲 Ollama qwen2.5:7b 本地模型接入、fallback 机制和 LLM Status。",
        "speech_ocr": "重点讲 Whisper 语音识别和 RapidOCR 截图识别两条输入链路。",
        "agent_system": "重点讲 Orchestrator + Blackboard + Critic Agent 的多 Agent 雏形。",
        "debugging": "重点讲复杂链路调试、日志排查、接口联调和稳定性修复。",
        "privacy": "重点讲本地优先、隐私保护和避免云端泄露的设计取舍。"
    }

    resume_lower = resume_context.lower()
    jd_lower = jd_context.lower()
    strong_matches = []
    gaps = []

    for group, keywords in keyword_groups.items():
        jd_has_group = any(keyword.lower() in jd_lower for keyword in keywords)
        resume_has_group = any(keyword.lower() in resume_lower for keyword in keywords)

        if jd_has_group and resume_has_group:
            strong_matches.append(group)
        elif jd_has_group:
            gaps.append(group)

    total_count = len(strong_matches) + len(gaps)
    match_score = round(len(strong_matches) / total_count, 2) if total_count else 0.0

    return {
        "match_score": match_score,
        "strong_matches": strong_matches,
        "gaps": gaps,
        "interview_focus": [focus_map[group] for group in strong_matches if group in focus_map]
    }


def load_knowledge_context() -> tuple[str, dict]:
    if not USE_KNOWLEDGE_CONTEXT:
        return "", {
            "knowledge_context_loaded": False,
            "knowledge_path": KNOWLEDGE_PATH,
            "knowledge_error": "USE_KNOWLEDGE_CONTEXT is false"
        }

    try:
        path = Path(KNOWLEDGE_PATH)
        if not path.is_absolute():
            path = data_dir() / path

        if not path.exists():
            return "", {
                "knowledge_context_loaded": False,
                "knowledge_path": str(path),
                "knowledge_error": "knowledge.txt not found"
            }

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return "", {
                "knowledge_context_loaded": False,
                "knowledge_path": str(path),
                "knowledge_error": "knowledge.txt is empty"
            }

        max_chars = 4500
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Knowledge context truncated]"

        return text, {
            "knowledge_context_loaded": True,
            "knowledge_path": str(path),
            "knowledge_error": None
        }
    except Exception as error:
        return "", {
            "knowledge_context_loaded": False,
            "knowledge_path": KNOWLEDGE_PATH,
            "knowledge_error": str(error)
        }


def retrieve_knowledge_snippets(question: str, knowledge_context: str, limit: int = 5) -> dict:
    if not knowledge_context:
        return {"rag_used": False, "snippets": [], "query_keywords": []}

    raw_keywords = re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,}|[\u4e00-\u9fff]{2,}", question.lower())
    stop_words = {"the", "and", "for", "with", "how", "what", "why", "your", "you", "are", "does", "this"}
    query_keywords = []
    for keyword in raw_keywords:
        if keyword not in stop_words and keyword not in query_keywords:
            query_keywords.append(keyword)

    paragraphs = [
        chunk.strip()
        for chunk in re.split(r"\n\s*\n|\n", knowledge_context)
        if chunk.strip()
    ]
    scored = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        score = sum(1 for keyword in query_keywords if keyword in lower)
        if score > 0:
            scored.append((score, paragraph))

    scored.sort(key=lambda item: item[0], reverse=True)
    snippets = [paragraph for _, paragraph in scored[:limit]]
    return {
        "rag_used": bool(snippets),
        "snippets": snippets,
        "query_keywords": query_keywords
    }


def build_recent_context(limit: int = 3) -> str:
    try:
        data = store.read()
        history = data.get("history", [])
        if not isinstance(history, list) or not history:
            return ""

        recent = history[-limit:]
        lines = ["Recent Interview Context:"]
        for index, item in enumerate(recent, start=1):
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if len(answer) > 800:
                answer = answer[:800] + "...[truncated]"
            if question or answer:
                lines.append(f"Q{index}: {question}")
                lines.append(f"A{index}: {answer}")
        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception as error:
        print("Failed to build recent context:", error)
        return ""

def build_interview_prompt(question: str, question_type: str, agent: str, resume_context: str = "") -> str:
    base_rules = (
        "你是一个实时 AI 面试辅助系统 Atlas 的回答 Agent。\n"
        "请根据用户的问题生成面试中可以直接参考的回答。\n"
        "要求：\n"
        "1. 回答要自然，像真人候选人的口吻。\n"
        "2. 不要说“作为一个 AI”。\n"
        "3. 不要机械使用“首先、其次、最后”。\n"
        "4. 内容要具体，避免空泛。\n"
        "5. 不要编造用户简历中不存在的具体公司、学校或项目经历。\n"
        "6. 回答长度适中，适合面试中快速参考。\n\n"
    )
    resume_section = ""
    if resume_context:
        resume_section = (
            "以下是候选人的简历/项目上下文。回答时只能参考其中已经出现的经历，不要编造不存在的公司、实习、项目、论文或获奖经历。\n"
            "如果问题适合结合个人经历，可以优先使用这些素材；如果不适合，不要强行套简历。\n\n"
            "【候选人上下文】\n"
            f"{resume_context}\n\n"
        )
        
    if question_type == "System Design":
        return (
            base_rules
            + resume_section
            + "题型：系统设计题。\n"
            + "请按以下结构回答：\n"
            + "1. 需求澄清\n"
            + "2. 核心 API\n"
            + "3. 数据模型\n"
            + "4. 高层架构\n"
            + "5. 关键流程\n"
            + "6. 扩展性\n"
            + "7. 容错与降级\n"
            + "8. 面试口语版总结\n\n"
            + f"用户问题：{question}\n"
        )

    if question_type == "Behavioral":
        return (
            base_rules
            + resume_section
            + "题型：行为面试题。\n"
            + "请使用 STAR 结构回答：\n"
            + "Situation：背景\n"
            + "Task：任务\n"
            + "Action：行动\n"
            + "Result：结果\n\n"
            "注意：如果有候选人上下文，必须优先使用其中真实出现的项目或经历。\n"
            "不要编造不存在的公司、实习、商业上线、获奖、论文或具体数字。\n"
            "如果上下文不足，请明确使用可替换模板，而不是虚构经历。\n\n"
            + f"用户问题：{question}\n"
        )

    return (
        base_rules
        + resume_section
        + "题型：技术/算法题。\n"
        + "请按以下结构回答：\n"
        + "1. 核心概念\n"
        + "2. 解题思路\n"
        + "3. 关键步骤\n"
        + "4. 复杂度分析\n"
        + "5. 边界情况\n"
        + "6. 面试口语版总结\n\n"
        + f"用户问题：{question}\n"
    )

def build_interview_prompt(
    question: str,
    question_type: str,
    agent: str,
    resume_context: str = "",
    jd_context: str = "",
    recent_context: str = "",
    knowledge_context: str = "",
    rag_snippets: list[str] = []
) -> str:
    base_rules = (
        "You are the answer agent for Atlas, a real-time AI interview assistant.\n"
        "Generate an answer the candidate can use directly in an interview.\n"
        "Rules:\n"
        "1. Use a natural candidate voice, not an AI-assistant voice.\n"
        "2. Do not say 'as an AI'.\n"
        "3. Be specific and avoid generic filler.\n"
        "4. Do not invent companies, schools, internships, awards, papers, or project facts that are not in the resume context.\n"
        "5. Match the user's requested language when possible.\n"
        "6. Keep the answer concise enough for interview reference.\n\n"
    )
    resume_section = ""
    if resume_context:
        resume_section = (
            "Candidate resume/project context follows. Use only facts that appear here.\n"
            "For project, system-design, or behavioral questions, prefer relevant material from this context.\n"
            "Strong reusable signals include Atlas, multi-agent interview system, local-first AI, FastAPI, Electron, React, Whisper, RapidOCR/OCR, Ollama, Blackboard, Critic Agent, History, and observability when they appear in the context.\n\n"
            "[Candidate Context]\n"
            f"{resume_context}\n\n"
        )
    jd_section = ""
    if jd_context:
        jd_section = (
            "Job description context follows. Use it to understand what the role values.\n"
            "Prioritize relevant role requirements when they naturally fit the question, but do not force JD language into unrelated answers.\n"
            "Do not invent resume experience that is not present in the candidate context.\n"
            "For behavioral questions, explain why the candidate is a good fit for this role.\n"
            "For system design or technical questions, emphasize matching points from the role's technical stack when appropriate.\n\n"
            "[Job Description Context]\n"
            f"{jd_context}\n\n"
        )
    recent_section = ""
    if recent_context:
        recent_section = (
            "Recent interview context follows. If the current question is clearly a follow-up, use this context to resolve references like 'it', 'that project', or 'the hardest part'. If the question is independent, do not force history into the answer.\n\n"
            "[Recent Interview Context]\n"
            f"{recent_context}\n\n"
        )
    knowledge_section = ""
    if knowledge_context:
        knowledge_section = (
            "Local knowledge-base context follows. Use it only when relevant, and do not invent facts outside the provided contexts.\n\n"
            "[Local Knowledge Context]\n"
            f"{knowledge_context}\n\n"
        )
    rag_section = ""
    if rag_snippets:
        rag_section = (
            "Retrieved knowledge snippets:\n"
            + "\n".join(f"- {snippet}" for snippet in rag_snippets[:5])
            + "\n\n"
        )

    if question_type == "System Design":
        return (
            base_rules
            + resume_section
            + jd_section
            + recent_section
            + knowledge_section
            + rag_section
            + "Question type: System Design.\n"
            + "If the resume context contains the Atlas stack, explicitly reuse it as an example architecture: Electron/React frontend, FastAPI backend, Blackboard state, Whisper audio, RapidOCR/OCR screenshots, Ollama local LLM, Critic Agent review, History, and observability.\n"
            + "Answer with this structure:\n"
            + "1. Requirements\n"
            + "2. Core APIs\n"
            + "3. Data model\n"
            + "4. High-level architecture\n"
            + "5. Key flow\n"
            + "6. Scalability\n"
            + "7. Fault tolerance and fallback\n"
            + "8. Interview-style summary\n\n"
            + f"User question: {question}\n"
        )

    if question_type == "Behavioral":
        return (
            base_rules
            + resume_section
            + jd_section
            + recent_section
            + knowledge_section
            + rag_section
            + "Question type: Behavioral.\n"
            + "Use STAR structure:\n"
            + "Situation: background\n"
            + "Task: responsibility\n"
            + "Action: concrete actions\n"
            + "Result: outcome\n\n"
            + "If candidate context exists, you must prioritize real projects and experiences from it. Do not invent missing details or metrics.\n\n"
            + f"User question: {question}\n"
        )

    return (
        base_rules
        + resume_section
        + jd_section
        + recent_section
        + knowledge_section
        + rag_section
        + "Question type: Technical/Algorithm.\n"
        + "Answer with this structure:\n"
        + "1. Core concept\n"
        + "2. Approach\n"
        + "3. Key steps\n"
        + "4. Complexity analysis\n"
        + "5. Edge cases\n"
        + "6. Interview-style summary\n\n"
        + f"User question: {question}\n"
    )


def reinforce_resume_context_signals(answer: str, question: str, question_type: str, resume_meta: dict, resume_context: str = "") -> str:
    if not resume_meta.get("resume_context_loaded"):
        return answer

    # Only ground answers in the Atlas stack when the resume is actually about
    # Atlas — otherwise this would inject FastAPI/backend content that has
    # nothing to do with the candidate's real background.
    if "atlas" not in (resume_context or "").lower():
        return answer

    q = question.lower()
    is_project_question = "project" in q or "proud" in q
    is_system_design = question_type == "System Design"
    if not (is_project_question or is_system_design):
        return answer

    expected_terms = [
        "Atlas",
        "FastAPI",
        "Electron",
        "React",
        "Whisper",
        "RapidOCR",
        "Ollama",
        "Blackboard",
        "Critic Agent",
        "History",
        "observability",
        "local-first",
        "multi-agent",
    ]
    missing_terms = [term for term in expected_terms if term.lower() not in answer.lower()]
    required_system_terms = ["local-first", "multi-agent", "observability"]
    missing_required_system_terms = [
        term for term in required_system_terms if term.lower() not in answer.lower()
    ]
    if len(missing_terms) < 4 and not (is_system_design and missing_required_system_terms):
        return answer

    context_note = (
        "\n\nIn my Atlas implementation, I would ground this design in a local-first, multi-agent architecture: "
        "an Electron and React desktop frontend, a FastAPI orchestrator backend, Blackboard state management, "
        "Whisper for audio input, RapidOCR/OCR for screenshot input, Ollama as the local LLM, a Critic Agent for review, "
        "and History plus observability metadata so each answer source, fallback, and resume-context status can be debugged."
    )
    return answer.rstrip() + context_note


def parse_two_section_rewrite(text: str) -> dict:
    speaking = text.strip()
    short = ""
    speaking_match = re.search(r"speaking[_\s-]*version\s*[:：]\s*(.+?)(?:\n\s*(?:short|30s)|$)", text, re.IGNORECASE | re.DOTALL)
    short_match = re.search(r"(?:short[_\s-]*version|30s(?:\s+short)?(?:\s+version)?)\s*[:：]\s*(.+)$", text, re.IGNORECASE | re.DOTALL)
    if speaking_match:
        speaking = speaking_match.group(1).strip()
    if short_match:
        short = short_match.group(1).strip()
    return {
        "speaking_version": speaking.strip(),
        "short_version": short.strip() or speaking.strip()[:260]
    }


def fallback_human_like_rewrite(question: str, answer: str, question_type: str, critic: dict) -> dict:
    cleaned = re.sub(r"\*\*|#+|`", "", answer).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if len(cleaned) > 900:
        cleaned = cleaned[:900].rstrip() + "..."

    if question_type == "Behavioral":
        prefix = "I would answer it around my Atlas project: "
    elif question_type == "System Design":
        prefix = "I would start by framing the design like this: "
    else:
        prefix = "I would explain it to the interviewer this way: "

    speaking = prefix + cleaned
    short = speaking[:320].rstrip() + ("..." if len(speaking) > 320 else "")
    notes = ["Used rule-based fallback rewrite."]
    if critic.get("should_rewrite"):
        notes.append(str(critic.get("rewrite_strategy") or "Make the answer more concise and natural."))
    return {
        "rewrite_available": True,
        "speaking_version": speaking,
        "short_version": short,
        "rewrite_notes": notes
    }


def generate_human_like_rewrite(
    question: str,
    answer: str,
    question_type: str,
    critic: dict,
    resume_context: str = "",
    jd_context: str = ""
) -> dict:
    prompt = (
        "Rewrite the answer into a natural interview speaking style.\n"
        "Rules: do not sound like a paper, do not use 'first/second/finally' mechanically, do not invent resume facts, keep core technical points.\n"
        "Return exactly two labeled sections:\n"
        "Speaking Version: <one natural complete answer>\n"
        "Short Version: <30 second answer>\n\n"
        f"Question type: {question_type}\n"
        f"Question: {question}\n"
        f"Critic strategy: {critic.get('rewrite_strategy', '')}\n"
        f"Resume context excerpt: {resume_context[:1200]}\n"
        f"JD context excerpt: {jd_context[:1200]}\n"
        f"Original answer:\n{answer[:2500]}\n"
    )
    try:
        if not get_llm_config().use_ollama:
            raise RuntimeError("LLM disabled")
        rewritten, _ = get_llm_router().generate(prompt)
        parsed = parse_two_section_rewrite(rewritten)
        return {
            "rewrite_available": True,
            "speaking_version": parsed["speaking_version"],
            "short_version": parsed["short_version"],
            "rewrite_notes": ["Generated by LLM rewrite prompt."]
        }
    except Exception as error:
        rewrite = fallback_human_like_rewrite(question, answer, question_type, critic)
        rewrite["rewrite_notes"].append(f"LLM rewrite fallback: {error}")
        return rewrite


def generate_followup_questions(
    question: str,
    answer: str,
    question_type: str,
    resume_context: str = "",
    jd_context: str = ""
) -> dict:
    combined = f"{question}\n{answer}".lower()
    followups = []
    focus = "technical"

    if question_type == "Behavioral":
        focus = "behavioral"
        followups.extend([
            "What was the hardest part of that project?",
            "What exactly was your responsibility?",
            "If you did it again, what would you improve?"
        ])
    if question_type == "System Design":
        focus = "system_design"
        followups.extend([
            "How would this system scale under higher traffic?",
            "What are the failure modes and fallback paths?",
            "How would you monitor quality and latency?"
        ])
    if "fastapi" in combined:
        followups.extend([
            "Why did you choose FastAPI instead of Flask?",
            "How would you design API error handling?",
            "How would you scale the API under concurrency?"
        ])
    if "electron" in combined:
        followups.extend([
            "How does the Electron window communicate with the backend?",
            "How do you handle desktop permissions and security?"
        ])
    if "whisper" in combined or "ocr" in combined or "rapidocr" in combined:
        followups.extend([
            "How do you handle inaccurate speech recognition?",
            "How do you clean noisy OCR output?"
        ])
    if "blackboard" in combined or "agent" in combined or "orchestrator" in combined:
        focus = "resume_deep_dive"
        followups.extend([
            "How does Blackboard keep state consistent?",
            "How do multiple agents avoid conflicting outputs?"
        ])
    if "role" in question.lower() or jd_context:
        focus = "jd_alignment" if question_type == "Behavioral" else focus

    if not followups:
        followups = [
            "Can you give a concrete example?",
            "What trade-off did you consider?",
            "How would you improve this next?"
        ]

    unique_followups = []
    for item in followups:
        if item not in unique_followups:
            unique_followups.append(item)
    return {
        "followups": unique_followups[:5],
        "followup_focus": focus
    }


def generate_llm_answer(question: str, question_type: str, agent: str):
    resume_context, resume_meta = load_resume_context()
    jd_context, jd_meta = load_jd_context()
    knowledge_context, knowledge_meta = load_knowledge_context()
    recent_context = build_recent_context(limit=3)
    rag_meta = retrieve_knowledge_snippets(question, knowledge_context, limit=5)
    match_meta = compute_resume_jd_match(resume_context, jd_context)
    context_meta = {
        **resume_meta,
        **jd_meta,
        **knowledge_meta,
        "resume_jd_match": match_meta,
        "resume_context": resume_context,
        "jd_context": jd_context,
        "knowledge_context": knowledge_context,
        "recent_context_used": bool(recent_context),
        "rag_used": rag_meta.get("rag_used", False),
        "rag_snippets_count": len(rag_meta.get("snippets", [])),
        "rag_query_keywords": rag_meta.get("query_keywords", [])
    }

    if not get_llm_config().use_ollama:
        fallback_answer = generate_stub_answer(question, question_type, agent)
        return fallback_answer, {
            "answer_source": "stub",
            "model": "none",
            "fallback": True,
            "error": "LLM disabled (use_ollama is false)",
            **context_meta
        }

    try:
        prompt = build_interview_prompt(
            question,
            question_type,
            agent,
            resume_context=resume_context,
            jd_context=jd_context,
            recent_context=recent_context,
            knowledge_context=knowledge_context,
            rag_snippets=rag_meta.get("snippets", [])
        )
        answer, llm_meta = get_llm_router().generate(prompt)
        answer = reinforce_resume_context_signals(answer, question, question_type, resume_meta, resume_context)
        return answer, {
            "answer_source": llm_meta.get("provider", "llm"),
            "model": llm_meta.get("model"),
            "provider": llm_meta.get("provider"),
            "is_local": llm_meta.get("is_local"),
            "fallback": bool(llm_meta.get("fallback_used")),
            "redactions": llm_meta.get("redactions", {}),
            "error": None,
            **context_meta
        }

    except Exception as error:
        print("LLM failed, fallback to stub:", error)

        fallback_answer = generate_stub_answer(question, question_type, agent)
        return fallback_answer, {
            "answer_source": "stub",
            "model": "none",
            "fallback": True,
            "error": str(error),
            **context_meta
        }

def generate_stub_answer(question: str, question_type: str, agent: str) -> str:
    q = question.lower()

    if question_type == "Behavioral":
        return (
            "这是一个行为面试题，可以用 STAR 结构回答：\n\n"
            "1. Situation：先交代背景，说明当时的团队、项目或冲突场景。\n"
            "2. Task：明确你当时承担的责任，以及问题为什么重要。\n"
            "3. Action：重点讲你采取了什么具体行动，例如沟通、拆解问题、推动协作、复盘改进。\n"
            "4. Result：最后用结果收尾，尽量包含可量化成果，例如效率提升、风险降低、项目按时交付。\n\n"
            f"针对这个问题：{question}\n"
            "回答时不要只讲态度，要突出你的判断、行动和复盘能力。"
        )

    if question_type == "System Design":
        if "rate limiter" in q or "限流" in q or "限流器" in q:
            return (
                "可以这样设计一个 API 限流系统：\n\n"
                "1. 需求澄清：先确认限流维度，例如按用户、IP、API Key、接口路径，还是全局限流。\n"
                "2. 核心算法：常见方案有固定窗口、滑动窗口、漏桶和令牌桶。实际系统中令牌桶更适合允许一定突发流量。\n"
                "3. 核心 API：请求进入网关后，根据 user_id 或 api_key 生成限流 key，然后查询当前配额。\n"
                "4. 存储设计：单机可以用内存计数；分布式环境建议使用 Redis，配合 Lua 脚本保证计数和过期操作的原子性。\n"
                "5. 高并发处理：限流逻辑应放在 API Gateway 或边车层，避免请求打到后端服务后才被拒绝。\n"
                "6. 返回策略：超过限制时返回 HTTP 429，并在 Header 中返回 Retry-After、RateLimit-Remaining 等信息。\n"
                "7. 扩展性：可以支持多级限流，例如用户级、租户级、接口级和全局保护级。\n"
                "8. 容错：如果 Redis 不可用，可以选择 fail-open 保证可用性，或 fail-closed 保护核心系统，具体取决于业务场景。\n\n"
                "面试中可以总结：我会把限流放在网关层，用令牌桶算法处理突发流量，用 Redis + Lua 保证分布式一致性，并通过 429 和监控告警形成完整闭环。"
            )

        if "url shortener" in q or "short link" in q or "短链接" in q:
            return (
                "可以这样设计一个短链接系统：\n\n"
                "1. 需求澄清：确认是否需要自定义短码、过期时间、访问统计、防刷、二维码和权限控制。\n"
                "2. 核心 API：\n"
                "   - POST /shorten：提交长链接，返回短链接。\n"
                "   - GET /{code}：根据短码重定向到原始长链接。\n"
                "3. 短码生成：可以使用自增 ID 转 Base62，也可以用哈希。自增 ID + Base62 更容易避免冲突。\n"
                "4. 数据模型：保存 code、long_url、user_id、created_at、expired_at、status、click_count。\n"
                "5. 读写路径：创建短链是低频写入，访问跳转是高频读取，因此要重点优化读路径。\n"
                "6. 缓存设计：热门短链可以放入 Redis，减少数据库查询。缓存 miss 后查数据库并回填。\n"
                "7. 重定向：通常使用 302，方便统计点击；如果是永久链接可考虑 301。\n"
                "8. 可扩展性：短码生成服务、跳转服务、统计服务可以拆分；访问日志异步写入消息队列。\n"
                "9. 风控：需要防止恶意链接、钓鱼链接、批量刷接口和短码枚举。\n\n"
                "面试中可以强调：短链接系统的核心不是生成短码，而是高并发跳转、缓存、统计和安全治理。"
            )

        return (
            f"这是一个系统设计题：{question}\n\n"
            "可以按下面结构回答：\n\n"
            "1. 需求澄清：确认用户规模、读写比例、延迟要求、一致性要求和核心功能边界。\n"
            "2. 核心 API：列出主要接口，包括创建、查询、更新、删除或访问类接口。\n"
            "3. 数据模型：说明核心实体、字段、索引和主键设计。\n"
            "4. 高层架构：客户端、API Gateway、业务服务、数据库、缓存、消息队列、对象存储等模块如何协作。\n"
            "5. 关键流程：分别讲写路径和读路径，说明请求如何流转。\n"
            "6. 扩展性：通过水平扩容、分库分表、缓存、异步化和限流提升系统容量。\n"
            "7. 可靠性：考虑重试、幂等、降级、熔断、监控和告警。\n"
            "8. 权衡：说明一致性与性能、成本与可用性之间的取舍。\n\n"
            "回答时不要只背架构名词，要围绕题目的核心瓶颈展开。"
        )

    if "binary search" in q or "二分" in q:
        return (
            "二分查找适用于有序数组或具有单调性的搜索空间。\n\n"
            "核心思路：\n"
            "1. 定义左右边界 left 和 right。\n"
            "2. 每次取 mid = left + (right - left) // 2，避免整数溢出。\n"
            "3. 比较 nums[mid] 和 target。\n"
            "4. 如果相等则返回 mid；如果 nums[mid] 小于 target，说明目标在右半边；否则在左半边。\n"
            "5. 循环直到 left > right。\n\n"
            "复杂度：\n"
            "- 时间复杂度：O(log n)\n"
            "- 空间复杂度：O(1)\n\n"
            "面试中要注意边界条件，比如空数组、单元素数组、target 不存在，以及 left/right 更新是否会死循环。"
        )

    if "polymorphism" in q or "多态" in q:
        return (
            "多态是面向对象编程中的一个核心特性，意思是同一个接口或方法调用，在不同对象上可以表现出不同的行为。\n\n"
            "可以这样回答：\n"
            "1. 定义：多态允许父类引用指向子类对象，并在运行时调用子类重写的方法。\n"
            "2. 作用：它可以降低代码耦合，提高扩展性。\n"
            "3. 例子：Animal 有 makeSound() 方法，Dog 和 Cat 都继承 Animal，但各自实现不同声音。\n"
            "4. 好处：调用方只依赖 Animal 接口，不需要关心具体是 Dog 还是 Cat。\n"
            "5. 面试补充：多态通常和继承、接口、方法重写、动态绑定有关。\n\n"
            "一句话总结：多态让代码面向抽象编程，而不是面向具体实现编程。"
        )

    return (
        f"这是一个技术题：{question}\n\n"
        "可以按下面结构回答：\n\n"
        "1. 先解释核心概念，说明它解决什么问题。\n"
        "2. 给出基本思路或实现步骤。\n"
        "3. 如果涉及代码，说明关键数据结构和算法流程。\n"
        "4. 分析时间复杂度和空间复杂度。\n"
        "5. 补充边界情况，例如空输入、重复数据、异常输入和大规模数据。\n"
        "6. 最后给一句面试总结，体现你理解了原理和适用场景。"
    )


def critic_review(
    question: str,
    answer: str,
    question_type: str,
    resume_context: str = "",
    jd_context: str = ""
) -> dict:
    q = question.lower()
    a = answer.lower()
    
    clarity_score = 0.8
    correctness_score = 0.8
    human_like_score = 0.75
    resume_alignment_score = 0.6
    privacy_score = 0.95
    jd_alignment_score = 0.5
    jd_alignment_notes = []
    
    critic_notes = []
    improved_answer_suggestion = ""
    
    # 清晰度评分
    if len(answer) < 100:
        clarity_score = 0.4
        critic_notes.append("回答过于简短，建议增加细节说明")
    elif len(answer) > 800:
        clarity_score = 0.6
        critic_notes.append("回答过于冗长，建议精简要点")
    elif "\n\n" not in answer:
        clarity_score = 0.7
        critic_notes.append("建议使用分段和列表结构提高可读性")
    
    # 人类口吻评分
    structured_phrases = ["首先", "其次", "最后", "综上所述", "总而言之"]
    if sum(1 for phrase in structured_phrases if phrase in a) > 3:
        human_like_score = 0.5
        critic_notes.append("结构化短语使用过多，显得生硬，建议更自然的表达方式")
    
    # 正确性评分 - 系统设计题检查
    if question_type == "System Design":
        if "api" not in a and "接口" not in a:
            correctness_score -= 0.15
            critic_notes.append("系统设计回答中缺少 API 设计部分")
        if "数据模型" not in a and "database" not in a and "存储" not in a:
            correctness_score -= 0.15
            critic_notes.append("系统设计回答中缺少数据模型或存储设计")
        if "扩展" not in a and "scalable" not in a and "高可用" not in a:
            correctness_score -= 0.1
            critic_notes.append("系统设计回答中缺少扩展性考虑")
    
    # 正确性评分 - 行为面试题检查
    if question_type == "Behavioral":
        star_elements = ["situation", "task", "action", "result", "背景", "任务", "行动", "结果"]
        found_elements = sum(1 for element in star_elements if element in a)
        if found_elements < 2:
            correctness_score = 0.5
            critic_notes.append("行为面试回答缺少 STAR 结构，建议按情境-任务-行动-结果组织")
        elif found_elements < 3:
            correctness_score = 0.7
            critic_notes.append("建议完善 STAR 结构的完整性")
    
    # 隐私风险检测
    privacy_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # email
        r'\b1[3-9]\d{9}\b',  # 手机号
        r'\b\d{17}[\dXx]\b',  # 身份证号
        r'\b\d{18}\b',
        r'\bsecret\b',
        r'\bpassword\b',
        r'\bapi[_-]?key\b',
        r'\baccess[_-]?token\b'
    ]
    for pattern in privacy_patterns:
        if re.search(pattern, a, re.IGNORECASE):
            privacy_score = 0.3
            critic_notes.append("检测到潜在敏感信息，建议移除或脱敏处理")
            break
    
    # 生成改进建议
    if critic_notes:
        improved_answer_suggestion = "建议改进方向：\n" + "\n".join(f"- {note}" for note in critic_notes)
    else:
        improved_answer_suggestion = "回答质量良好，无需重大改进。可以考虑增加更多具体例子或量化成果。"
    
    jd_keyword_groups = {
        "backend": ["fastapi", "python", "api", "backend", "后端"],
        "frontend": ["react", "electron", "typescript", "前端"],
        "llm": ["ollama", "llm", "大模型", "agent"],
        "speech_ocr": ["whisper", "ocr", "rapidocr"],
        "system_design": ["architecture", "orchestrator", "blackboard", "设计"]
    }
    if jd_context:
        jd_lower = jd_context.lower()
        jd_groups = []
        matched_groups = []
        for group, keywords in jd_keyword_groups.items():
            jd_has_group = any(keyword.lower() in jd_lower for keyword in keywords)
            answer_has_group = any(keyword.lower() in a for keyword in keywords)
            if jd_has_group:
                jd_groups.append(group)
                if answer_has_group:
                    matched_groups.append(group)

        if jd_groups:
            jd_alignment_score = round(len(matched_groups) / len(jd_groups), 2)
            if "favorite movie" in q:
                jd_alignment_score = min(jd_alignment_score, 0.3)
        else:
            jd_alignment_score = 0.5
            jd_alignment_notes.append("岗位 JD 中未识别到明确技术关键词，岗位匹配度只能粗略判断。")

        if jd_alignment_score >= 0.7:
            jd_alignment_notes.append("回答较好体现岗位 JD 中要求的技术栈和能力。")
        elif jd_alignment_score >= 0.4:
            jd_alignment_notes.append("回答部分体现岗位要求，但还可以进一步强调 JD 相关经验。")
        else:
            jd_alignment_notes.append("回答与岗位 JD 的关联较弱，建议更多结合岗位技术要求。")

        if "fastapi" in a:
            jd_alignment_notes.append("回答体现了 FastAPI 后端开发经验。")
        if "electron" in a:
            jd_alignment_notes.append("回答体现了 Electron 桌面应用经验。")
        if "ollama" in a:
            jd_alignment_notes.append("回答体现了本地大模型接入能力。")
        if "whisper" in a or "ocr" in a or "rapidocr" in a:
            jd_alignment_notes.append("回答体现了多模态输入链路能力。")
        if "blackboard" in a or "orchestrator" in a:
            jd_alignment_notes.append("回答体现了多 Agent 编排与状态管理能力。")
    else:
        jd_alignment_score = 0.5
        jd_alignment_notes.append("未加载岗位 JD，无法准确判断岗位匹配度。")

    if resume_context:
        resume_signals = ["atlas", "fastapi", "electron", "react", "whisper", "rapidocr", "ollama", "blackboard"]
        matched_resume_signals = sum(1 for signal in resume_signals if signal in a and signal in resume_context.lower())
        resume_alignment_score = max(resume_alignment_score, min(1.0, matched_resume_signals / 4))
    else:
        resume_alignment_score = min(resume_alignment_score, 0.5)

    ai_tone_phrases = ["首先", "其次", "最后", "作为一个 ai", "作为ai", "综上所述", "在当今时代", "firstly", "secondly", "lastly", "as an ai", "in conclusion"]
    ai_tone_hits = [phrase for phrase in ai_tone_phrases if phrase in a]
    if ai_tone_hits:
        human_like_score = min(human_like_score, 0.55)
        critic_notes.append("回答存在明显 AI 腔或模板化表达，建议改成更自然的候选人口吻。")

    if len(answer) > 1200:
        human_like_score = min(human_like_score, 0.6)
        critic_notes.append("回答偏长，面试现场不容易完整说完。")

    specific_issues = list(dict.fromkeys(critic_notes + jd_alignment_notes))
    score_parts = {
        "clarity": clarity_score * 0.20,
        "correctness": correctness_score * 0.25,
        "human_like": human_like_score * 0.20,
        "resume_alignment": resume_alignment_score * 0.15,
        "jd_alignment": jd_alignment_score * 0.15,
        "privacy": privacy_score * 0.05
    }
    final_score = int(round(sum(score_parts.values()) * 100))
    weakness_candidates = [
        ("清晰度", clarity_score),
        ("正确性", correctness_score),
        ("口语自然度", human_like_score),
        ("简历结合度", resume_alignment_score),
        ("岗位匹配度", jd_alignment_score),
        ("隐私安全", privacy_score)
    ]
    main_weakness_label, main_weakness_score = min(weakness_candidates, key=lambda item: item[1])
    main_weakness = f"{main_weakness_label}偏弱" if main_weakness_score < 0.7 else "整体表现较均衡"

    if jd_alignment_score < 0.5:
        rewrite_strategy = "改写时优先补强岗位 JD 相关技术栈和职责匹配点。"
    elif human_like_score < 0.65:
        rewrite_strategy = "改写时减少模板化表达，改成真实候选人口吻。"
    elif clarity_score < 0.65:
        rewrite_strategy = "改写时压缩结构，保留关键事实和结论。"
    else:
        rewrite_strategy = "保留核心内容，略微增强具体例子和口语自然度。"

    should_rewrite = (
        final_score < 75
        or human_like_score < 0.65
        or clarity_score < 0.65
        or jd_alignment_score < 0.5
    )

    if specific_issues:
        improved_answer_suggestion = "建议改进方向：\n" + "\n".join(f"- {issue}" for issue in specific_issues[:6])
    else:
        improved_answer_suggestion = "回答质量良好，无需重大改进。可以考虑增加更多具体例子或量化成果。"

    return {
        "clarity_score": round(clarity_score, 2),
        "correctness_score": round(correctness_score, 2),
        "human_like_score": round(human_like_score, 2),
        "resume_alignment_score": round(resume_alignment_score, 2),
        "privacy_score": round(privacy_score, 2),
        "jd_alignment_score": round(jd_alignment_score, 2),
        "jd_alignment_notes": jd_alignment_notes,
        "final_score": final_score,
        "main_weakness": main_weakness,
        "specific_issues": specific_issues,
        "rewrite_strategy": rewrite_strategy,
        "should_rewrite": should_rewrite,
        "critic_notes": critic_notes,
        "improved_answer_suggestion": improved_answer_suggestion
    }


# Keys allowed by blackboard_schema.json -> history.items.critic (additionalProperties: false).
# review_answer() also returns gate-only keys (approved/score/issues/...) that are valid in the
# API response but must be stripped before persisting to the strictly-validated history entry.
_HISTORY_CRITIC_KEYS = {
    "clarity_score",
    "correctness_score",
    "human_like_score",
    "resume_alignment_score",
    "privacy_score",
    "jd_alignment_score",
    "jd_alignment_notes",
    "final_score",
    "main_weakness",
    "specific_issues",
    "rewrite_strategy",
    "should_rewrite",
    "human_like_rewrite",
    "followup_questions",
    "critic_notes",
    "improved_answer_suggestion",
}


def _critic_for_history(critic: dict) -> dict:
    return {key: value for key, value in critic.items() if key in _HISTORY_CRITIC_KEYS}


@app.get("/blackboard")
def read_blackboard():
    return store.read()


@app.get("/config/status")
def config_status():
    cfg = get_llm_config()
    return {
        "ollama_model": cfg.ollama_model,
        "ollama_base_url": cfg.ollama_base_url,
        "use_ollama": cfg.use_ollama,
        "llm": cfg.public_dict(),
        "use_resume_context": USE_RESUME_CONTEXT,
        "resume_path": str((data_dir() / RESUME_PATH).resolve()) if not Path(RESUME_PATH).is_absolute() else RESUME_PATH,
        "use_jd_context": USE_JD_CONTEXT,
        "jd_path": str((data_dir() / JD_PATH).resolve()) if not Path(JD_PATH).is_absolute() else JD_PATH,
        "use_knowledge_context": USE_KNOWLEDGE_CONTEXT,
        "knowledge_path": str((data_dir() / KNOWLEDGE_PATH).resolve()) if not Path(KNOWLEDGE_PATH).is_absolute() else KNOWLEDGE_PATH,
        "memory_limit": 3,
        "backend_url": "http://127.0.0.1:8000"
    }


@app.get("/config/llm")
def get_llm_settings():
    """Effective LLM config (api key never returned, only whether it is set)."""
    return get_llm_config().public_dict()


@app.post("/config/llm")
def update_llm_settings(update: LLMConfigUpdate):
    """Persist LLM settings (Settings UI) and hot-reload the router."""
    updates = {key: value for key, value in update.model_dump().items() if value is not None}
    save_settings(updates)
    cfg = reload_llm()
    return cfg.public_dict()


@app.post("/config/llm/test")
def test_llm_connection():
    """Actually call the configured LLM once and report which provider answered.

    This is the ground truth for "is the cloud API really being used": with a
    valid cloud key it returns provider="cloud"; if cloud fails it falls back to
    local and reports fallback_used=true; if nothing works, ok=false.
    """
    start = time.perf_counter()
    try:
        text, meta = get_llm_router().generate("Reply with exactly: OK", timeout=20)
        return {
            "ok": True,
            "provider": meta.get("provider"),
            "model": meta.get("model"),
            "is_local": meta.get("is_local"),
            "fallback_used": bool(meta.get("fallback_used")),
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "sample": (text or "")[:80],
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }


class ProfileUpdate(BaseModel):
    resume: str | None = None
    jd: str | None = None
    knowledge: str | None = None
    company: str | None = None
    position: str | None = None
    focus: str | None = None


@app.get("/profile")
def get_profile():
    """Candidate prep: resume / JD / knowledge text + target company/position/focus."""
    from app.profile_store import read_all
    return read_all()


@app.post("/profile")
def save_profile(update: ProfileUpdate):
    from app.profile_store import save_all
    return save_all(update.model_dump())


def _extract_pdf_text(data: bytes) -> str:
    import io
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF parsing needs the 'pypdf' package (pip install pypdf)") from exc
    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(part for part in parts if part)


def _extract_docx_text(data: bytes) -> str:
    import io
    try:
        import docx  # python-docx
    except ImportError as exc:
        raise RuntimeError("DOCX parsing needs 'python-docx'; upload PDF/TXT or paste text instead") from exc
    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


@app.post("/profile/parse_file")
async def parse_profile_file(file: UploadFile = File(...)):
    """Extract plain text from an uploaded resume/JD file (txt/md/pdf/docx)."""
    name = (file.filename or "").lower()
    content = await file.read()
    try:
        if name.endswith(".pdf"):
            text = _extract_pdf_text(content)
        elif name.endswith(".docx"):
            text = _extract_docx_text(content)
        else:
            text = content.decode("utf-8", errors="replace")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text could be extracted from the file.")
    return {"text": text, "chars": len(text), "filename": file.filename}


@app.get("/trace/{session_id}")
def get_trace(session_id: str):
    """Real per-request agent trace: the ordered event stream from the bus.

    The /ask response returns its session_id; the UI fetches the trace here
    instead of inferring agent steps from response fields.
    """
    events = phase2_bus.dump_session_json(session_id)
    steps = [
        {
            "ts": event.get("ts"),
            "source_agent": event.get("source_agent"),
            "type": event.get("type"),
            "question_type": (event.get("payload") or {}).get("question_type"),
            "parent_event_id": event.get("parent_event_id"),
            "event_id": event.get("event_id"),
        }
        for event in events
    ]
    return {"session_id": session_id, "count": len(steps), "steps": steps, "events": events}


def _run_async_blocking(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()


def _phase2_question_type_to_phase1(question_type: str | None) -> str | None:
    mapping = {
        "technical": "Technical/Algorithm",
        "algorithm": "Technical/Algorithm",
        "system_design": "System Design",
        "behavioral": "Behavioral",
        "resume_followup": "Behavioral",
    }
    if not question_type:
        return None
    return mapping.get(str(question_type).lower())


def _agent_hint_to_selected_agent(agent_hint: str | None) -> str | None:
    mapping = {
        "tech": "Tech/Code",
        "technical": "Tech/Code",
        "code": "Tech/Code",
        "behavioral": "Behavioral",
        "resume": "Behavioral",
    }
    if not agent_hint:
        return None
    return mapping.get(str(agent_hint).lower())


def _run_phase1_answer_pipeline_sync(
    question: str,
    language: str = "Unknown",
    source: str = "manual_input",
    agent_hint: str | None = None,
    question_type: str | None = None,
    context: dict | None = None,
    rag: dict | None = None,
) -> dict:
    phase1_question_type = _phase2_question_type_to_phase1(question_type) or classify_question(question)
    selected_agent = _agent_hint_to_selected_agent(agent_hint) or select_agent(phase1_question_type)

    store.update_current_question(question, phase1_question_type, language, source, 0.85)
    store.update_agent_state("Perception", "done", f"Detected question type: {phase1_question_type}", {"selected_agent": selected_agent})
    store.update_agent_state(selected_agent, "running", "Generating answer...", {"started_at": int(time.time())})

    answer, answer_meta = generate_llm_answer(question, phase1_question_type, selected_agent)

    store.update_agent_state(
        selected_agent,
        "done",
        answer,
        {
            "question_type": phase1_question_type,
            "answer_source": answer_meta.get("answer_source"),
            "model": answer_meta.get("model"),
            "fallback": answer_meta.get("fallback"),
            "llm_error": answer_meta.get("error"),
            "resume_context_loaded": answer_meta.get("resume_context_loaded"),
            "resume_path": answer_meta.get("resume_path"),
            "resume_error": answer_meta.get("resume_error"),
            "jd_context_loaded": answer_meta.get("jd_context_loaded"),
            "jd_path": answer_meta.get("jd_path"),
            "jd_error": answer_meta.get("jd_error"),
            "resume_jd_match": answer_meta.get("resume_jd_match"),
            "knowledge_context_loaded": answer_meta.get("knowledge_context_loaded"),
            "knowledge_path": answer_meta.get("knowledge_path"),
            "knowledge_error": answer_meta.get("knowledge_error"),
            "recent_context_used": answer_meta.get("recent_context_used"),
            "rag_used": answer_meta.get("rag_used"),
            "rag_snippets_count": answer_meta.get("rag_snippets_count"),
            "rag_query_keywords": answer_meta.get("rag_query_keywords")
        }
    )

    # Phase 2 (a specialized agent invoked this pipeline via agent_hint): the standalone
    # CriticAgent (app.critic.rules.review_answer) is the single source of truth for the
    # critic that reaches the response. Reuse that same engine here only to persist a
    # consistent critic to history / agent_state, and skip the legacy critic_review() plus
    # the Ollama-backed human_like_rewrite and followup generation, whose output was
    # previously computed and then discarded by CriticAgent on every Phase 2 request.
    if agent_hint is not None:
        critic = review_answer(
            question=question,
            answer=answer,
            question_type=str(question_type or phase1_question_type or "").lower(),
            selected_agent=selected_agent,
            context=context or {},
            rag=rag or {},
        )
        store.update_agent_state("Critic", "done", "Review completed", critic)
        updated = store.append_history(
            question,
            answer,
            selected_agent,
            phase1_question_type,
            _critic_for_history(critic),
            source,
        )
    else:
        critic = critic_review(
            question,
            answer,
            phase1_question_type,
            resume_context=answer_meta.get("resume_context", ""),
            jd_context=answer_meta.get("jd_context", "")
        )
        critic["human_like_rewrite"] = generate_human_like_rewrite(
            question,
            answer,
            phase1_question_type,
            critic,
            resume_context=answer_meta.get("resume_context", ""),
            jd_context=answer_meta.get("jd_context", "")
        )
        critic["followup_questions"] = generate_followup_questions(
            question,
            answer,
            phase1_question_type,
            resume_context=answer_meta.get("resume_context", ""),
            jd_context=answer_meta.get("jd_context", "")
        )
        store.update_agent_state("Critic", "done", "Review completed", critic)

        updated = store.append_history(question, answer, selected_agent, phase1_question_type, critic, source)
    context = context or {}
    context_sources = [
        source_name
        for source_name, present in (
            ("resume", context.get("has_resume")),
            ("jd", context.get("has_jd")),
            ("knowledge", context.get("has_knowledge")),
        )
        if present
    ]
    rag = rag or {}

    return {
        "question": question,
        "question_type": phase1_question_type,
        "selected_agent": selected_agent,
        "answer": answer,
        "critic": critic,
        "blackboard_version": updated["version"],
        "context_used": bool(context),
        "context_sources": context_sources,
        "context": context,
        "rag_used": bool(rag.get("has_rag")),
        "rag_sources": rag.get("sources", []),
        "rag": rag,
        "answer_source": str(answer_meta.get("answer_source") or ""),
        "llm_fallback": bool(answer_meta.get("fallback")),
    }


configure_phase1_pipeline(_run_phase1_answer_pipeline_sync)


def _ask_phase1_impl(req: AskRequest) -> AskResponse:
    return AskResponse(
        **_run_phase1_answer_pipeline_sync(
            question=req.question,
            language=req.language,
            source=req.source,
        )
    )


def _ignored_ask_response(req: AskRequest) -> AskResponse:
    try:
        blackboard_version = int(store.read().get("version", 0))
    except Exception:
        blackboard_version = 0

    return AskResponse(
        question=req.question,
        question_type="ignored",
        selected_agent="Perception",
        answer="",
        critic={
            "clarity_score": 1.0,
            "correctness_score": 1.0,
            "human_like_score": 1.0,
            "resume_alignment_score": 1.0,
            "privacy_score": 1.0,
            "jd_alignment_score": 1.0,
            "jd_alignment_notes": [],
            "final_score": 100,
            "main_weakness": "none",
            "specific_issues": ["No complete interview question detected."],
            "rewrite_strategy": "No answer generated.",
            "should_rewrite": False,
            "critic_notes": ["PerceptionAgent skipped this input."],
            "improved_answer_suggestion": "No complete interview question detected.",
            "human_like_rewrite": {},
            "followup_questions": {},
        },
        blackboard_version=blackboard_version,
    )


def _unhandled_ask_response(req: AskRequest, question_type: str = "unknown") -> AskResponse:
    try:
        blackboard_version = int(store.read().get("version", 0))
    except Exception:
        blackboard_version = 0

    return AskResponse(
        question=req.question,
        question_type=question_type or "unknown",
        selected_agent="Perception",
        answer="",
        critic={
            "clarity_score": 0.8,
            "correctness_score": 0.8,
            "human_like_score": 1.0,
            "resume_alignment_score": 0.5,
            "privacy_score": 1.0,
            "jd_alignment_score": 0.5,
            "jd_alignment_notes": [],
            "final_score": 80,
            "main_weakness": "no_specialized_agent",
            "specific_issues": ["Question detected but no specialized agent handled it."],
            "rewrite_strategy": "Route this question type to a specialized agent before answering.",
            "should_rewrite": False,
            "critic_notes": ["Phase2 detected a question but no Tech/Behavioral agent accepted it."],
            "improved_answer_suggestion": "Question detected but no specialized agent handled it.",
            "human_like_rewrite": {},
            "followup_questions": {},
        },
        blackboard_version=blackboard_version,
    )


def _ask_phase2_impl(req: AskRequest) -> AskResponse:
    session_id = f"api.ask.{uuid4()}"
    event = BBEvent(
        session_id=session_id,
        source_agent="api.ask",
        type=EventType.MANUAL_INPUT,
        payload={
            "question": req.question,
            "language": req.language,
            "source": req.source,
        },
    )
    outputs = _run_async_blocking(phase2_orchestrator.dispatch(event))
    final_event = next(
        (event for event in reversed(outputs) if event.type == EventType.ANSWER_FINAL),
        None,
    )
    if final_event is None:
        question_detected = any(event.type == EventType.QUESTION_DETECTED for event in outputs)
        if not question_detected:
            response = _ignored_ask_response(req)
            response.session_id = session_id
            return response

        error_event = next(
            (event for event in reversed(outputs) if event.type == EventType.ERROR),
            None,
        )
        if error_event is not None:
            error = error_event.payload.get("error")
            raise RuntimeError(f"Phase2 answer agent failed before ANSWER_FINAL: {error}")

        detected_event = next(
            (event for event in reversed(outputs) if event.type == EventType.QUESTION_DETECTED),
            None,
        )
        detected_type = ""
        if detected_event is not None:
            detected_type = str(detected_event.payload.get("question_type", "unknown"))
        response = _unhandled_ask_response(req, detected_type)
        response.session_id = session_id
        return response

    raw_result = final_event.payload.get("raw_result")
    if not isinstance(raw_result, dict):
        raise RuntimeError("Phase2 MainAgent returned invalid raw_result")
    raw_result.setdefault("session_id", session_id)
    return AskResponse(**raw_result)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        return _ask_phase2_impl(req)
    except Exception as exc:
        print("[W9] Phase2 path failed, fallback to Phase1:", exc)
        return _ask_phase1_impl(req)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


TECH_TYPES = {"technical", "algorithm", "system_design"}


def _stream_answer(req: AskRequest):
    """SSE generator for /ask_stream (M1).

    Emits: meta -> delta* -> final (with critic) -> done. Falls back to a stub
    answer when the LLM is disabled/unavailable so the stream always completes.

    Publishes its stages to the in-memory event bus so /trace/{session_id}
    returns a real agent trace for streamed requests too (cheap; does not touch
    the JSON blackboard store, so latency stays low).
    """
    session_id = f"api.stream.{uuid4()}"

    def publish(event_type: EventType, payload: dict, parent: BBEvent | None) -> BBEvent:
        event = BBEvent(
            session_id=session_id,
            source_agent="api.ask_stream",
            type=event_type,
            payload=payload,
            parent_event_id=parent.event_id if parent else None,
        )
        phase2_bus.publish(event)
        return event

    root = publish(
        EventType.MANUAL_INPUT,
        {"question": req.question, "language": req.language, "source": req.source},
        None,
    )

    perception = classify_interview_input(req.question)
    if not perception["should_answer"]:
        yield _sse({
            "type": "ignored",
            "session_id": session_id,
            "question_type": perception["question_type"],
            "reason": perception["reason"],
        })
        yield _sse({"type": "done", "session_id": session_id})
        return

    phase2_type = perception["question_type"]
    phase1_type = _phase2_question_type_to_phase1(phase2_type) or classify_question(req.question)
    selected_agent = "Tech/Code" if phase2_type in TECH_TYPES else "Behavioral"
    detected = publish(
        EventType.QUESTION_DETECTED,
        {"question": req.question, "question_type": phase2_type, "selected_agent": selected_agent},
        root,
    )
    yield _sse({
        "type": "meta",
        "session_id": session_id,
        "question": req.question,
        "question_type": phase1_type,
        "phase2_type": phase2_type,
        "selected_agent": selected_agent,
    })

    resume_context, _ = load_resume_context()
    jd_context, _ = load_jd_context()
    knowledge_context, _ = load_knowledge_context()
    recent_context = build_recent_context(limit=3)
    rag_meta = retrieve_knowledge_snippets(req.question, knowledge_context, limit=5)
    prompt = build_interview_prompt(
        req.question,
        phase1_type,
        selected_agent,
        resume_context=resume_context,
        jd_context=jd_context,
        recent_context=recent_context,
        knowledge_context=knowledge_context,
        rag_snippets=rag_meta.get("snippets", []),
    )

    pieces: list[str] = []
    llm_meta: dict = {}
    cfg = get_llm_config()
    if not cfg.use_ollama:
        stub = generate_stub_answer(req.question, phase1_type, selected_agent)
        pieces.append(stub)
        llm_meta = {"provider": "stub", "model": "none", "fallback_used": True}
        yield _sse({"type": "delta", "text": stub})
    else:
        try:
            for piece in get_llm_router().stream(prompt, llm_meta):
                pieces.append(piece)
                yield _sse({"type": "delta", "text": piece})
        except Exception as error:
            stub = generate_stub_answer(req.question, phase1_type, selected_agent)
            pieces = [stub]
            llm_meta = {"provider": "stub", "model": "none", "fallback_used": True, "error": str(error)}
            yield _sse({"type": "delta", "text": stub, "fallback": True})

    answer = "".join(pieces)

    # Build the same context/rag the CriticAgent uses, then review once.
    candidate = build_candidate_context(req.question)
    context_payload = {
        "resume_summary": candidate["resume_summary"],
        "jd_summary": candidate["jd_summary"],
        "knowledge_summary": candidate["knowledge_summary"],
        "matched_snippets": candidate["matched_snippets"],
        "constraints": candidate["constraints"],
        "has_resume": bool(candidate["resume_raw"].strip()),
        "has_jd": bool(candidate["jd_raw"].strip()),
        "has_knowledge": bool(candidate["knowledge_raw"].strip()),
    }
    rag_chunks = retrieve_local_knowledge(req.question, load_knowledge_text(), top_k=3)
    rag_payload = {"chunks": rag_chunks, "has_rag": bool(rag_chunks)}
    context_used = bool(
        context_payload.get("has_resume")
        or context_payload.get("has_jd")
        or context_payload.get("has_knowledge")
    )
    publish(
        EventType.CONTEXT_LOADED,
        {"question": req.question, "question_type": phase2_type, "has_resume": context_payload["has_resume"],
         "has_jd": context_payload["has_jd"], "has_knowledge": context_payload["has_knowledge"]},
        detected,
    )
    publish(
        EventType.RAG_CHUNK,
        {"question": req.question, "question_type": phase2_type, "has_rag": rag_payload["has_rag"],
         "sources": ["knowledge.txt"] if rag_payload["has_rag"] else []},
        detected,
    )

    critic = review_answer(
        question=req.question,
        answer=answer,
        question_type=phase2_type,
        selected_agent=selected_agent,
        context=context_payload,
        rag=rag_payload,
    )
    final_answer = str(critic.get("final_answer") or answer)

    # Persist the turn so the post-interview report (/report/session) reflects
    # streamed Q&A too — previously only the non-stream /ask path wrote history,
    # so everything asked through the live UI was missing from the report.
    try:
        store.update_current_question(req.question, phase1_type, req.language, req.source)
        store.append_history(
            req.question,
            final_answer,
            selected_agent,
            phase1_type,
            _critic_for_history(critic),
            req.source,
        )
    except Exception as error:
        print("[ask_stream] failed to persist history:", error)

    draft = publish(
        EventType.ANSWER_DRAFT,
        {"question": req.question, "question_type": phase2_type, "selected_agent": selected_agent},
        detected,
    )
    publish(
        EventType.ANSWER_FINAL,
        {"question": req.question, "question_type": phase2_type, "selected_agent": selected_agent,
         "approved": bool(critic.get("approved"))},
        draft,
    )

    yield _sse({
        "type": "final",
        "session_id": session_id,
        "question": req.question,
        "question_type": phase1_type,
        "selected_agent": selected_agent,
        "answer": final_answer,
        "critic": critic,
        "context_used": context_used,
        "rag_used": bool(rag_payload.get("has_rag")),
        "llm": {
            "provider": llm_meta.get("provider"),
            "model": llm_meta.get("model"),
            "fallback": bool(llm_meta.get("fallback_used")),
            "redactions": llm_meta.get("redactions", {}),
        },
    })
    yield _sse({"type": "done", "session_id": session_id})


@app.post("/ask_stream")
def ask_stream(req: AskRequest):
    return StreamingResponse(
        _stream_answer(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Practice / Coaching loop (M2): 陪练 -> 作答 -> 评分+自适应追问 -> 复盘报告
# ---------------------------------------------------------------------------
@app.post("/practice/start")
def practice_start(req: StartRequest):
    state = _coaching_service.start(
        req.session_id,
        role=req.role,
        focus=req.focus,
        num_questions=req.num_questions,
        language=req.language,
    )
    return state.model_dump()


@app.post("/practice/answer")
def practice_answer(req: AnswerRequest):
    try:
        return _coaching_service.submit_answer(req.session_id, req.answer)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/practice/state")
def practice_state(session_id: str = "default"):
    return _coaching_service.state(session_id).model_dump()


@app.get("/practice/report")
def practice_report(session_id: str = "default", lang: str = "zh"):
    return _coaching_service.report(session_id, lang)


@app.post("/ask_image", response_model=AskResponse)
def ask_image(req: AskImageRequest):
    raw_text = extract_text_from_image(req.image_path)
    text = clean_ocr_question(raw_text)

    text = text.replace("APl", "API")
    text = text.replace("AP1", "API")
    text = text.replace("A P I", "API")

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="OCR did not extract any useful question text from the image."
        )

    ask_req = AskRequest(
        question=text,
        language=req.language,
        source="ocr"
    )

    return ask(ask_req)

@app.post("/ask_image_file", response_model=AskResponse)
async def ask_image_file(
    image: UploadFile = File(...),
    language: str = Form("Unknown"),
    source: str = Form("ocr")
):
    suffix = ".png"
    if image.filename:
        _, ext = os.path.splitext(image.filename)
        if ext:
            suffix = ext

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await image.read()
            tmp.write(content)
            temp_path = tmp.name

        raw_text = extract_text_from_image(temp_path)
        text = clean_ocr_question(raw_text)

        text = text.replace("APl", "API")
        text = text.replace("AP1", "API")
        text = text.replace("A P I", "API")

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="OCR did not extract any useful question text from the image."
            )

        ask_req = AskRequest(
            question=text,
            language=language,
            source=source
        )

        return ask(ask_req)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/ask_audio", response_model=AskResponse)
async def ask_audio(
    audio: UploadFile = File(...),
    language: str = Form("Unknown"),
    source: str = Form("stt")
):
    suffix = ".webm"

    if audio.filename:
        _, ext = os.path.splitext(audio.filename)
        if ext:
            suffix = ext

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            temp_path = tmp.name

        text = transcribe_audio_file(temp_path, language=language)
        print("Whisper transcript:", text)

        text = text.strip()
        text = text.replace("APl", "API")
        text = text.replace("AP1", "API")
        text = text.replace("二分差找", "二分查找")
        text = text.replace("短连接", "短链接")
        text = text.replace("限留器", "限流器")

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Whisper did not extract any speech text from the audio."
            )

        ask_req = AskRequest(
            question=text,
            language=language,
            source="stt"
        )

        return ask(ask_req)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def _report_lang(lang: str = "zh") -> str:
    value = (lang or "").strip().lower()
    if value in {"en", "english"}:
        return "en"
    return "zh"


def _report_unknown(lang: str) -> str:
    return "未知" if _report_lang(lang) == "zh" else "unknown"


def _report_text(lang: str, zh: str, en: str) -> str:
    return zh if _report_lang(lang) == "zh" else en


def build_session_report(lang: str = "zh") -> dict:
    lang = _report_lang(lang)
    data = store.read()
    history = data.get("history", [])
    scored_items = []
    all_notes = []
    jd_scores = []
    resume_scores = []
    privacy_scores = []

    for item in history:
        critic = item.get("critic") or {}
        final_score = critic.get("final_score")
        if isinstance(final_score, (int, float)):
            scored_items.append((float(final_score), item))
        if isinstance(critic.get("jd_alignment_score"), (int, float)):
            jd_scores.append(float(critic["jd_alignment_score"]))
        if isinstance(critic.get("resume_alignment_score"), (int, float)):
            resume_scores.append(float(critic["resume_alignment_score"]))
        if isinstance(critic.get("privacy_score"), (int, float)):
            privacy_scores.append(float(critic["privacy_score"]))
        notes = critic.get("specific_issues") or critic.get("critic_notes") or []
        if isinstance(notes, list):
            all_notes.extend(str(note) for note in notes)

    if scored_items:
        overall_score = int(round(sum(score for score, _ in scored_items) / len(scored_items)))
        best = max(scored_items, key=lambda item: item[0])[1]
        worst = min(scored_items, key=lambda item: item[0])[1]
    else:
        overall_score = 0
        best = None
        worst = None

    common_notes = list(dict.fromkeys(all_notes))[:5]
    strengths = []
    if jd_scores and sum(jd_scores) / len(jd_scores) >= 0.7:
        strengths.append(_report_text(lang, "岗位 JD 贴合度较好。", "Good alignment with the target JD."))
    if resume_scores and sum(resume_scores) / len(resume_scores) >= 0.7:
        strengths.append(_report_text(lang, "回答能结合简历和项目经历。", "Answers connect well with resume and project experience."))
    if privacy_scores and min(privacy_scores) >= 0.8:
        strengths.append(_report_text(lang, "隐私风险较低。", "Privacy risk stayed low."))
    if not strengths:
        strengths.append(_report_text(lang, "已完成多轮问答记录，可继续积累样本。", "Multiple interview turns were recorded; keep collecting samples for better review."))

    weaknesses = common_notes or [_report_text(lang, "暂无明显共性问题。", "No obvious repeated issue yet.")]

    # Recommend practice based on what the candidate's resume/JD actually
    # mention — not a hardcoded stack.
    from app.coaching.question_bank import detect_topics

    profile_resume, _ = load_resume_context()
    profile_jd, _ = load_jd_context()
    profile_topics = detect_topics(profile_resume or "", profile_jd or "", "", lang)[:4]
    if lang == "zh":
        recommended_practice = ["继续练习把核心项目经历讲成 60 秒和 2 分钟两个版本。"]
        if profile_topics:
            recommended_practice.append("针对简历/JD 中的 " + "、".join(profile_topics) + " 准备更具体的例子。")
        else:
            recommended_practice.append("结合目标岗位的核心要求，为每类常见问题准备一个具体例子。")
        recommended_practice.append("回答后主动补充关键取舍和可量化的结果。")
    else:
        recommended_practice = ["Keep practicing 60-second and 2-minute versions of your core project story."]
        if profile_topics:
            recommended_practice.append("Prepare more concrete examples for " + ", ".join(profile_topics) + " from your resume/JD.")
        else:
            recommended_practice.append("Prepare one concrete example per common question type, matched to the role's key requirements.")
        recommended_practice.append("After each answer, proactively add key trade-offs and quantifiable results.")

    question_reviews = []
    for item in history[-10:]:
        critic = item.get("critic") or {}
        question_reviews.append({
            "question": item.get("question", ""),
            "source": item.get("source", _report_unknown(lang)),
            "agent": item.get("agent", _report_unknown(lang)),
            "final_score": critic.get("final_score"),
            "main_weakness": critic.get("main_weakness", _report_unknown(lang)),
            "jd_alignment_score": critic.get("jd_alignment_score"),
        })

    # Append % only when there is a real number — avoids "未知%" / "unknown%".
    jd_value = f"{round(sum(jd_scores) / len(jd_scores) * 100)}%" if jd_scores else _report_unknown(lang)
    resume_value = f"{round(sum(resume_scores) / len(resume_scores) * 100)}%" if resume_scores else _report_unknown(lang)
    privacy_value = f"{round(min(privacy_scores) * 100)}%" if privacy_scores else _report_unknown(lang)

    return {
        "overall_score": overall_score,
        "summary": _report_text(
            lang,
            f"本轮共记录 {len(history)} 条问答，平均分 {overall_score}。",
            f"This session recorded {len(history)} Q&A turns with an average score of {overall_score}.",
        ),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "jd_alignment_summary": _report_text(lang, f"平均 JD 匹配度：{jd_value}", f"Average JD Alignment: {jd_value}"),
        "resume_alignment_summary": _report_text(lang, f"平均简历匹配度：{resume_value}", f"Average Resume Alignment: {resume_value}"),
        "privacy_risk_summary": _report_text(lang, f"最低隐私安全分：{privacy_value}", f"Lowest Privacy Score: {privacy_value}"),
        "recommended_practice": recommended_practice,
        "question_reviews": question_reviews,
        "best_question": best.get("question") if best else "",
        "weakest_question": worst.get("question") if worst else "",
    }


def report_to_markdown(report: dict, lang: str = "zh") -> str:
    lang = _report_lang(lang)
    if lang == "zh":
        lines = [
            "# Atlas 面试复盘报告",
            "",
            f"总体得分：{report.get('overall_score', 0)}",
            "",
            f"总结：{report.get('summary', '')}",
            "",
            "## 亮点",
            *[f"- {item}" for item in report.get("strengths", [])],
            "",
            "## 待改进",
            *[f"- {item}" for item in report.get("weaknesses", [])],
            "",
            "## 推荐练习",
            *[f"- {item}" for item in report.get("recommended_practice", [])],
            "",
            "## 逐题复盘",
        ]
        for item in report.get("question_reviews", []):
            lines.append(
                f"- {item.get('question', '')} | 得分={item.get('final_score', '未知')} | JD匹配={item.get('jd_alignment_score', '未知')}"
            )
        return "\n".join(lines)

    lines = [
        "# Atlas Interview Report",
        "",
        f"Overall Score: {report.get('overall_score', 0)}",
        "",
        f"Summary: {report.get('summary', '')}",
        "",
        "## Strengths",
        *[f"- {item}" for item in report.get("strengths", [])],
        "",
        "## Weaknesses",
        *[f"- {item}" for item in report.get("weaknesses", [])],
        "",
        "## Recommended Practice",
        *[f"- {item}" for item in report.get("recommended_practice", [])],
        "",
        "## Question Reviews",
    ]
    for item in report.get("question_reviews", []):
        lines.append(f"- {item.get('question', '')} | score={item.get('final_score', 'unknown')} | jd={item.get('jd_alignment_score', 'unknown')}")
    return "\n".join(lines)


@app.post("/mock/start")
def mock_start():
    questions = [
        "Tell me about yourself and your main project.",
        "Tell me about a technical challenge in your project.",
        "Why are you a good fit for this role?"
    ]
    _mock_state.update({
        "active": True,
        "round_index": 0,
        "completed": False,
        "questions": questions,
        "answers": []
    })
    return {
        "active": True,
        "completed": False,
        "round_index": 0,
        "current_question": questions[0]
    }


@app.post("/mock/answer")
def mock_answer(req: MockAnswerRequest):
    if not _mock_state.get("active"):
        return mock_start()

    questions = _mock_state.get("questions", [])
    round_index = int(_mock_state.get("round_index", 0))
    current_question = questions[round_index] if round_index < len(questions) else ""
    resume_context, _ = load_resume_context()
    jd_context, _ = load_jd_context()
    question_type = classify_question(current_question)
    critic = critic_review(current_question, req.answer, question_type, resume_context=resume_context, jd_context=jd_context)
    _mock_state.setdefault("answers", []).append({
        "question": current_question,
        "answer": req.answer,
        "critic": critic
    })

    next_index = round_index + 1
    completed = next_index >= len(questions)
    _mock_state["round_index"] = next_index
    _mock_state["completed"] = completed
    _mock_state["active"] = not completed

    return {
        "round_index": next_index,
        "completed": completed,
        "feedback": critic,
        "next_question": "" if completed else questions[next_index]
    }


@app.get("/mock/state")
def mock_state():
    return _mock_state


@app.get("/report/session")
def report_session(lang: str = "zh"):
    return build_session_report(lang)


@app.get("/report/export_markdown")
def report_export_markdown(lang: str = "zh"):
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(report_to_markdown(build_session_report(lang), lang))


@app.post("/blackboard/clear_history")
def clear_history():
    data = store.read()
    expected_version = data["version"]
    data["history"] = []
    return store.write(data, expected_version=expected_version)


@app.post("/blackboard/reset_session")
def reset_session():
    data = store.read()
    expected_version = data["version"]
    data["current_question"] = {
        "text": "",
        "type": "Unknown",
        "language": "Unknown",
        "timestamp": int(time.time()),
        "source": "manual_input",
        "confidence": 0
    }
    data["agent_state"] = {}
    data["history"] = []
    data.setdefault("rolling_context", {})["recent_transcript"] = []
    return store.write(data, expected_version=expected_version)
