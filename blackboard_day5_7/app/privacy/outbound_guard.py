from __future__ import annotations

"""Outbound privacy guard.

Before any prompt leaves the machine for a *cloud* LLM, scrub likely PII /
secrets (emails, phone numbers, national IDs, API keys/tokens). Local Ollama
calls never go through this guard, since the data never leaves the device.

This is a deterministic, non-LLM line of defense (a lightweight version of the
plan's Stealth/Privacy Guardian) so cloud usage stays auditable and compliant.
"""

import re
from typing import Dict, List, Tuple

REDACTION = "[REDACTED]"

# (flag, compiled pattern). Order matters: more specific first.
_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b")),
    ("api_key", re.compile(r"\b(?:gsk|xai|ds)_[A-Za-z0-9_\-]{16,}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("national_id", re.compile(r"\b\d{17}[\dXx]\b")),
    ("phone", re.compile(r"\b1[3-9]\d{9}\b")),
    ("phone", re.compile(r"\b\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{4}\b")),
    ("credential", re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key)\b\s*[:=]\s*\S+")),
]


def scrub_outbound(text: str) -> Tuple[str, Dict[str, int]]:
    """Return (scrubbed_text, {flag: count}) for text destined for a cloud LLM."""
    if not text:
        return "", {}

    flags: Dict[str, int] = {}
    scrubbed = text
    for flag, pattern in _PATTERNS:
        matches = pattern.findall(scrubbed)
        if not matches:
            continue
        flags[flag] = flags.get(flag, 0) + len(matches)
        scrubbed = pattern.sub(REDACTION, scrubbed)
    return scrubbed, flags


def has_pii(text: str) -> bool:
    _, flags = scrub_outbound(text or "")
    return bool(flags)
