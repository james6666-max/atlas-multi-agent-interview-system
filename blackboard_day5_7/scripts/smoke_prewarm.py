# -*- coding: utf-8 -*-
"""Smoke check: the startup hook pre-warms the OCR engine in the background."""
import os
import sys
import time
from pathlib import Path

os.environ["USE_OLLAMA"] = "false"
os.environ["ATLAS_PREWARM_OCR"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import orchestrator_v0 as o  # noqa: E402

with TestClient(o.app):  # context manager fires startup events
    boot = time.perf_counter()
    deadline = time.time() + 60
    while o._ocr_engine is None and time.time() < deadline:
        time.sleep(0.5)
    if o._ocr_engine is None:
        print("FAIL: OCR engine not pre-warmed within 60s")
        sys.exit(1)
    print(f"OK: OCR engine pre-warmed {time.perf_counter() - boot:.1f}s after startup")
