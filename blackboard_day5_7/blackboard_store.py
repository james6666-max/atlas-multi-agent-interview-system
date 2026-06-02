from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from jsonschema import Draft202012Validator


class BlackboardStore:
    """MVP file-based blackboard. Later replace with Redis/PostgreSQL."""

    def __init__(self, data_path: str = "blackboard_instance.json", schema_path: str = "blackboard_schema.json") -> None:
        self.data_path = Path(data_path)
        self.schema_path = Path(schema_path)
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)

    def read(self) -> Dict[str, Any]:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Blackboard data file not found: {self.data_path}")
        data = json.loads(self.data_path.read_text(encoding="utf-8"))
        self.validate(data)
        return data

    def write(self, data: Dict[str, Any], expected_version: Optional[int] = None) -> Dict[str, Any]:
        if self.data_path.exists() and expected_version is not None:
            current = self.read()
            if current.get("version") != expected_version:
                raise ValueError(f"Version conflict: current={current.get('version')}, expected={expected_version}")
        data["version"] = int(data.get("version", 0)) + 1
        data["updated_at"] = int(time.time())
        self.validate(data)
        self.data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

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
        turn_id = f"turn-{len(data.get('history', [])) + 1:03d}"
        history_item: Dict[str, Any] = {
            "turn_id": turn_id,
            "question": question,
            "question_type": question_type,
            "answer": answer,
            "agent": agent,
            "timestamp": int(time.time()),
            "source": source,
        }
        if critic:
            history_item["critic"] = critic
        data.setdefault("history", []).append(history_item)
        return self.write(data, expected_version=expected_version)
