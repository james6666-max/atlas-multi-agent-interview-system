from __future__ import annotations

"""Candidate prep storage: resume / JD / knowledge text + target company/position/focus.

Text docs live as resume.txt / jd.txt / knowledge.txt in the writable data dir
(so the existing loaders pick them up); the structured fields live in profile.json.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.paths import data_dir

PROFILE_FIELDS = ("company", "position", "focus")
DOCS = {"resume": "resume.txt", "jd": "jd.txt", "knowledge": "knowledge.txt"}


def _root(base_dir: Optional[Path]) -> Path:
    return base_dir or data_dir()


def read_doc(key: str, base_dir: Optional[Path] = None) -> str:
    name = DOCS.get(key)
    if not name:
        return ""
    path = _root(base_dir) / name
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def write_doc(key: str, text: str, base_dir: Optional[Path] = None) -> None:
    name = DOCS.get(key)
    if not name:
        return
    (_root(base_dir) / name).write_text(text or "", encoding="utf-8")


def read_profile(base_dir: Optional[Path] = None) -> Dict[str, str]:
    path = _root(base_dir) / "profile.json"
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {field: str(data.get(field, "")) for field in PROFILE_FIELDS}
    except Exception:
        pass
    return {field: "" for field in PROFILE_FIELDS}


def write_profile(updates: Dict[str, Any], base_dir: Optional[Path] = None) -> Dict[str, str]:
    current = read_profile(base_dir)
    for field in PROFILE_FIELDS:
        value = updates.get(field)
        if value is not None:
            current[field] = str(value)
    (_root(base_dir) / "profile.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return current


def read_all(base_dir: Optional[Path] = None) -> Dict[str, str]:
    return {
        "resume": read_doc("resume", base_dir),
        "jd": read_doc("jd", base_dir),
        "knowledge": read_doc("knowledge", base_dir),
        **read_profile(base_dir),
    }


def save_all(update: Dict[str, Any], base_dir: Optional[Path] = None) -> Dict[str, str]:
    for key in DOCS:
        if update.get(key) is not None:
            write_doc(key, str(update[key]), base_dir)
    write_profile({field: update[field] for field in PROFILE_FIELDS if update.get(field) is not None}, base_dir)
    return read_all(base_dir)


def profile_hint(base_dir: Optional[Path] = None) -> str:
    """Short natural-language hint for question generation."""
    p = read_profile(base_dir)
    parts = []
    if p.get("company"):
        parts.append(f"目标公司: {p['company']}")
    if p.get("position"):
        parts.append(f"目标职位: {p['position']}")
    if p.get("focus"):
        parts.append(f"重点方向: {p['focus']}")
    return " | ".join(parts)
