from __future__ import annotations

"""LLM configuration for Atlas Phase 2 (M0/M1).

Resolves an effective LLM configuration from, in increasing priority:
  1. built-in defaults
  2. environment variables (back-compatible with the old OLLAMA_* / USE_OLLAMA names)
  3. a runtime settings file (atlas_settings.json) written by the Settings UI

The cloud provider is any OpenAI-compatible chat-completions endpoint
(Groq / DeepSeek / Qwen / OpenRouter / ...), so a single client covers them all.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field

from app.paths import data_dir

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = data_dir() / "atlas_settings.json"

LLMMode = Literal["hybrid", "local", "cloud"]

# Keys that may be persisted to / loaded from the settings file.
_SETTINGS_KEYS = {
    "mode",
    "use_ollama",
    "ollama_base_url",
    "ollama_model",
    "cloud_base_url",
    "cloud_api_key",
    "cloud_model",
}


class LLMConfig(BaseModel):
    mode: LLMMode = "hybrid"
    use_ollama: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    cloud_base_url: str = ""
    cloud_api_key: str = ""
    cloud_model: str = ""

    @property
    def cloud_configured(self) -> bool:
        return bool(self.cloud_base_url.strip() and self.cloud_api_key.strip() and self.cloud_model.strip())

    def public_dict(self) -> Dict[str, Any]:
        """Config safe to expose over the API (never leak the api key)."""
        data = self.model_dump()
        key = data.get("cloud_api_key") or ""
        data["cloud_api_key"] = ""
        data["cloud_api_key_set"] = bool(key.strip())
        data["cloud_configured"] = self.cloud_configured
        return data


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_config() -> LLMConfig:
    return LLMConfig(
        mode=os.getenv("ATLAS_LLM_MODE", "hybrid").strip().lower() or "hybrid",  # type: ignore[arg-type]
        use_ollama=_bool_env("USE_OLLAMA", True),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        cloud_base_url=os.getenv("ATLAS_CLOUD_BASE_URL", "").strip(),
        cloud_api_key=os.getenv("ATLAS_CLOUD_API_KEY", "").strip(),
        cloud_model=os.getenv("ATLAS_CLOUD_MODEL", "").strip(),
    )


def _read_settings_file(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {key: value for key, value in data.items() if key in _SETTINGS_KEYS}
    except Exception:
        return {}


def load_config(settings_path: Path | None = None) -> LLMConfig:
    base = _env_config().model_dump()
    overrides = _read_settings_file(settings_path or SETTINGS_PATH)
    # Treat empty strings in the settings file as "unset" so they don't clobber env.
    for key, value in overrides.items():
        if isinstance(value, str) and not value.strip() and key != "cloud_api_key":
            continue
        base[key] = value
    if isinstance(base.get("mode"), str):
        base["mode"] = base["mode"].strip().lower() or "hybrid"
        if base["mode"] not in {"hybrid", "local", "cloud"}:
            base["mode"] = "hybrid"
    return LLMConfig(**base)


def save_settings(updates: Dict[str, Any], settings_path: Path | None = None) -> LLMConfig:
    """Merge `updates` into the settings file and return the new effective config.

    Only known keys are persisted. An empty/omitted cloud_api_key is preserved
    (not overwritten) so the UI can update other fields without resending the key.
    """
    path = settings_path or SETTINGS_PATH
    current = _read_settings_file(path)
    for key, value in (updates or {}).items():
        if key not in _SETTINGS_KEYS:
            continue
        if key == "cloud_api_key" and isinstance(value, str) and not value.strip():
            # Don't wipe an existing key when the UI sends a blank value.
            continue
        current[key] = value
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return load_config(path)
