from __future__ import annotations

"""Path resolution that works both in dev and as a packaged (frozen) app.

Two roots:
  - resource_dir(): read-only bundled assets (schema, default resume/jd/knowledge).
    In a PyInstaller bundle this is sys._MEIPASS; in dev it's the backend root.
  - data_dir(): writable user data (blackboard_instance.json, atlas_settings.json,
    and the user-editable resume.txt / jd.txt / knowledge.txt). In a frozen app
    this lives next to the executable (./atlas_data); in dev it's the backend root.

Both can be overridden by env vars (ATLAS_RESOURCE_DIR / ATLAS_DATA_DIR), which is
how the Electron launcher points the packaged backend at the right folders.

In dev (not frozen, no env) BOTH resolve to the backend root, so behaviour is
identical to before — tests, smoke and eval are unaffected.
"""

import os
import shutil
import sys
from pathlib import Path

# blackboard_day5_7/  (app/paths.py -> parents[1])
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    override = os.getenv("ATLAS_RESOURCE_DIR")
    if override:
        return Path(override)
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return BACKEND_ROOT


def data_dir() -> Path:
    override = os.getenv("ATLAS_DATA_DIR")
    if override:
        path = Path(override)
    elif is_frozen():
        path = Path(sys.executable).resolve().parent / "atlas_data"
    else:
        path = BACKEND_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(name: str) -> Path:
    return resource_dir() / name


def data_path(name: str) -> Path:
    return data_dir() / name


def ensure_seed_files(names: list[str]) -> None:
    """Copy bundled default files into the writable data dir if they're missing.

    No-op in dev (data_dir == resource_dir). In a packaged app this seeds the
    user data folder on first launch from the read-only bundle.
    """
    src_root = resource_dir()
    dst_root = data_dir()
    if src_root.resolve() == dst_root.resolve():
        return
    for name in names:
        dst = dst_root / name
        src = src_root / name
        if not dst.exists() and src.exists():
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
