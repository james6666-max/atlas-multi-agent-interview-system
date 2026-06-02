from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    AUDIO_CHUNK = "audio_chunk"
    TRANSCRIPT_PARTIAL = "transcript_partial"
    TRANSCRIPT_FINAL = "transcript_final"
    OCR_TEXT = "ocr_text"
    MANUAL_INPUT = "manual_input"

    QUESTION_DETECTED = "question_detected"
    CONTEXT_LOADED = "context_loaded"

    ANSWER_DRAFT = "answer_draft"
    CRITIQUE_NOTE = "critique_note"
    ANSWER_APPROVED = "answer_approved"
    ANSWER_REJECTED = "answer_rejected"
    ANSWER_FINAL = "answer_final"

    RAG_CHUNK = "rag_chunk"
    ERROR = "error"


class BBEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    ts: int = Field(default_factory=lambda: int(time.time() * 1000))
    source_agent: str
    type: EventType
    version: int = 1
    payload: Dict[str, Any] = Field(default_factory=dict)
    parent_event_id: Optional[str] = None
