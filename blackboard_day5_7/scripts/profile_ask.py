# -*- coding: utf-8 -*-
"""Profile the /ask pipeline overhead in stub mode (USE_OLLAMA=false).

Calls _ask_phase2_impl directly (no HTTP layer) so cProfile sees the real work.
Usage: python scripts/profile_ask.py
"""
import cProfile
import io
import json
import os
import pstats
import sys
import time
from pathlib import Path

os.environ["USE_OLLAMA"] = "false"
os.environ.setdefault("ATLAS_PREWARM_OCR", "0")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import orchestrator_v0 as o  # noqa: E402


def main() -> None:
    questions = json.loads((ROOT / "evals" / "phase2_questions.json").read_text(encoding="utf-8"))
    o._ask_phase2_impl(o.AskRequest(question=questions[0]["question"]))  # warmup

    runs = questions[1:21]
    started = time.perf_counter()
    pr = cProfile.Profile()
    pr.enable()
    for item in runs:
        o._ask_phase2_impl(o.AskRequest(question=item["question"]))
    pr.disable()
    elapsed_ms = (time.perf_counter() - started) * 1000

    print(f"avg per request: {elapsed_ms / len(runs):.1f} ms over {len(runs)} runs")
    stream = io.StringIO()
    pstats.Stats(pr, stream=stream).sort_stats("tottime").print_stats(25)
    print(stream.getvalue())


if __name__ == "__main__":
    main()
