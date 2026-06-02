from __future__ import annotations

import shutil
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Runtime files that tests may touch via the real app (the /ask path writes the
# blackboard; LLM-config tests could write settings). Back them up for the whole
# session and restore afterwards so the working tree is never polluted.
GUARDED_FILES = ["blackboard_instance.json", "atlas_settings.json"]


@pytest.fixture(scope="session", autouse=True)
def _isolate_runtime_files():
    backups: dict[str, Path | None] = {}
    for name in GUARDED_FILES:
        path = BACKEND_ROOT / name
        if path.exists():
            backup = path.with_suffix(path.suffix + ".pytest.bak")
            shutil.copy2(path, backup)
            backups[name] = backup
        else:
            backups[name] = None

    try:
        yield
    finally:
        for name, backup in backups.items():
            path = BACKEND_ROOT / name
            if backup is not None:
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
            elif path.exists():
                # File did not exist before the test session; remove if created.
                path.unlink(missing_ok=True)
