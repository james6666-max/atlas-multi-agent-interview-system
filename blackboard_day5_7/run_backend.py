"""Frozen-app entry point for the Atlas backend (PyInstaller target).

Builds into `atlas-backend(.exe)` and is launched by the Electron app in the
packaged build. In dev you normally use `uvicorn orchestrator_v0:app` instead.
"""
from __future__ import annotations

import os
import sys


def _log(msg: str) -> None:
    print(f"[atlas-backend] {msg}", flush=True)


def main() -> None:
    # Frozen onedir cold start can take a while to load the bundled modules,
    # so emit visible progress (unbuffered) instead of a silent blank console.
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass

    _log("starting — loading modules (first run can take 10–60s)…")
    import uvicorn
    from orchestrator_v0 import app

    host = os.getenv("ATLAS_HOST", "127.0.0.1")
    port = int(os.getenv("ATLAS_PORT", "8000"))
    _log(f"modules loaded — serving on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
