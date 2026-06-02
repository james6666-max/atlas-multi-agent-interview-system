from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PracticeQuestion(BaseModel):
    id: str
    index: int
    type: str  # technical | algorithm | system_design | behavioral | resume_followup
    topic: str = ""
    question: str
    is_followup: bool = False


class PracticeTurn(BaseModel):
    question: PracticeQuestion
    answer: str
    score: int
    critic: Dict[str, Any] = Field(default_factory=dict)


class PracticeState(BaseModel):
    session_id: str
    active: bool = False
    completed: bool = False
    round_index: int = 0          # how many answers submitted
    total_planned: int = 0        # main questions planned
    queue_length: int = 0         # current queue length (incl. inserted follow-ups)
    followups_used: int = 0
    current_question: Optional[PracticeQuestion] = None
    answered: List[PracticeTurn] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class StartRequest(BaseModel):
    role: str = ""
    focus: str = ""
    num_questions: int = 5
    session_id: str = "default"
    # "zh" / "en" (also accepts "Chinese" / "English")
    language: str = "zh"


class AnswerRequest(BaseModel):
    answer: str
    session_id: str = "default"
