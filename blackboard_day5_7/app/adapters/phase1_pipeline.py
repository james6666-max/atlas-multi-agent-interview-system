from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Dict, Optional, Union

PipelineResult = Dict[str, Any]
PipelineCallable = Callable[..., Union[PipelineResult, Awaitable[PipelineResult]]]

_phase1_pipeline: Optional[PipelineCallable] = None


def configure_phase1_pipeline(pipeline: PipelineCallable) -> None:
    global _phase1_pipeline
    _phase1_pipeline = pipeline


async def run_phase1_answer_pipeline(
    question: str,
    language: str = "Unknown",
    source: str = "manual_input",
    agent_hint: Optional[str] = None,
    question_type: Optional[str] = None,
    context: Optional[dict] = None,
    rag: Optional[dict] = None,
) -> PipelineResult:
    if _phase1_pipeline is None:
        raise RuntimeError("Phase 1 answer pipeline has not been configured")

    kwargs = {
        "question": question,
        "language": language,
        "source": source,
        "agent_hint": agent_hint,
        "question_type": question_type,
        "context": context,
        "rag": rag,
    }
    result = _phase1_pipeline(**_compatible_kwargs(_phase1_pipeline, kwargs))
    if inspect.isawaitable(result):
        result = await result

    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    if not isinstance(result, dict):
        raise TypeError(f"Phase 1 pipeline returned unsupported type: {type(result)!r}")
    return result


def _compatible_kwargs(pipeline: PipelineCallable, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(pipeline)
    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in signature.parameters}
