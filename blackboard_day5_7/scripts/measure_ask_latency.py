# -*- coding: utf-8 -*-
"""Measure per-request /ask latency exactly the way the eval does."""
import json
import os
import sys
import time
from pathlib import Path

os.environ["USE_OLLAMA"] = "false"
os.environ.setdefault("ATLAS_PREWARM_OCR", "0")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import orchestrator_v0 as o  # noqa: E402

questions = json.loads((ROOT / "evals" / "phase2_questions.json").read_text(encoding="utf-8"))
client = TestClient(o.app)

lat = []
for item in questions[:25]:
    started = time.perf_counter()
    client.post("/ask", json={"question": item["question"]})
    lat.append((time.perf_counter() - started) * 1000)

print("per-request ms:", [round(x) for x in lat])
print(f"avg={sum(lat)/len(lat):.1f} first={lat[0]:.1f} rest_avg={sum(lat[1:])/len(lat[1:]):.1f}")
