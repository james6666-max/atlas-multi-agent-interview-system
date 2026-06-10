from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from jsonschema import Draft202012Validator

# Bounded growth keeps every read/parse/validate O(1) instead of O(all turns):
# the session report only uses the last 10 turns and recent context the last 3,
# so trimming old turns does not change any feature behaviour.
MAX_HISTORY_ITEMS = 300
MAX_TRANSCRIPT_ITEMS = 50


class BlackboardStore:
    """MVP file-based blackboard. Later replace with Redis/PostgreSQL."""

    def __init__(self, data_path: str = "blackboard_instance.json", schema_path: str = "blackboard_schema.json") -> None:
        self.data_path = Path(data_path)
        self.schema_path = Path(schema_path)
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)
        # (st_mtime_ns, st_size) of the file content we last validated, plus its
        # version. Lets us skip re-validating a file only we have written, and
        # answer CAS version checks without re-reading the whole document.
        self._validated_stat: Optional[Tuple[int, int]] = None
        self._cached_version: Optional[int] = None

    def _stat_signature(self) -> Tuple[int, int]:
        stat = self.data_path.stat()
        return (stat.st_mtime_ns, stat.st_size)

    def read(self) -> Dict[str, Any]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Blackboard data file not found: {self.data_path}")
        signature = self._stat_signature()
        data = json.loads(self.data_path.read_text(encoding="utf-8"))
        if signature != self._validated_stat:
            self.validate(data)
            self._validated_stat = signature
        self._cached_version = data.get("version")
        return data

    def _current_version(self) -> Optional[int]:
        if self._validated_stat is not None and self._stat_signature() == self._validated_stat:
            return self._cached_version
        return self.read().get("version")

    def write(self, data: Dict[str, Any], expected_version: Optional[int] = None) -> Dict[str, Any]:
        if self.data_path.exists() and expected_version is not None:
            current_version = self._current_version()
            if current_version != expected_version:
                raise ValueError(f"Version conflict: current={current_version}, expected={expected_version}")
        data["version"] = int(data.get("version", 0)) + 1
        data["updated_at"] = int(time.time())
        self._trim(data)
        self.validate(data)
        self.data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self._validated_stat = self._stat_signature()
        self._cached_version = data["version"]
        return data

    @staticmethod
    def _trim(data: Dict[str, Any]) -> None:
        history = data.get("history")
        if isinstance(history, list) and len(history) > MAX_HISTORY_ITEMS:
            del history[:-MAX_HISTORY_ITEMS]
        transcript = (data.get("rolling_context") or {}).get("recent_transcript")
        if isinstance(transcript, list) and len(transcript) > MAX_TRANSCRIPT_ITEMS:
            del transcript[:-MAX_TRANSCRIPT_ITEMS]

    def validate(self, data: Dict[str, Any]) -> None:
        errors = sorted(self.validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            msg = "\n".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors)
            raise ValueError(f"Blackboard schema validation failed:\n{msg}")

    def update_current_question(self, text: str, question_type: str = "Unknown", language: str = "Unknown", source: str = "manual_input", confidence: float = 0.8) -> Dict[str, Any]:
        data = self.read()
        expected_version = data["version"]
        now = int(time.time())
        data["current_question"] = {"text": text, "type": question_type, "language": language, "timestamp": now, "source": source, "confidence": confidence}
        data.setdefault("rolling_context", {}).setdefault("recent_transcript", []).append({"speaker": "interviewer", "text": text, "timestamp": now})
        return self.write(data, expected_version=expected_version)

    def update_agent_state(self, agent_name: str, status: str, last_response: str, metadata: Optional[Dict[str, Any]] = None, last_error: str = "") -> Dict[str, Any]:
        data = self.read()
        expected_version = data["version"]
        metadata = metadata or {}
        data.setdefault("agent_state", {})[agent_name] = {
            "status": status,
            "last_response": last_response,
            "last_error": last_error,
            "last_updated": int(time.time()),
            "metadata": metadata,
            "meta": metadata,
        }
        return self.write(data, expected_version=expected_version)

    def append_history(self, question: str, answer: str, agent: str, question_type: str = "Unknown", critic: Optional[Dict[str, Any]] = None, source: str = "manual_input") -> Dict[str, Any]:
        data = self.read()
        expected_version = data["version"]
        history = data.setdefault("history", [])
        history_item: Dict[str, Any] = {
            "turn_id": f"turn-{_next_turn_number(history):03d}",
            "question": question,
            "question_type": question_type,
            "answer": answer,
            "agent": agent,
            "timestamp": int(time.time()),
            "source": source,
        }
        if critic:
            history_item["critic"] = critic
        history.append(history_item)
        return self.write(data, expected_version=expected_version)


def _next_turn_number(history: list) -> int:
    """Monotonic turn number that stays unique even after old turns are trimmed."""
    if not history:
        return 1
    match = re.search(r"(\d+)$", str(history[-1].get("turn_id", "")))
    return int(match.group(1)) + 1 if match else len(history) + 1
