from __future__ import annotations

"""LLM providers for Atlas.

Two providers, one interface:
  - OllamaProvider: local-first, private, uses /api/generate.
  - OpenAICompatProvider: any OpenAI-compatible chat-completions endpoint
    (Groq / DeepSeek / Qwen / OpenRouter / ...).

Both expose blocking `generate()` and streaming `stream()` returning text deltas.
"""

import json
import os
from typing import Iterator, Protocol

import requests

# Cap on establishing the connection (TCP + TLS), separate from the read
# timeout: an unreachable endpoint then fails in seconds and the router can
# fall back to the next provider, instead of hanging for the full read timeout.
CONNECT_TIMEOUT = 5.0

# Keep the Ollama model loaded between requests; the default unload after
# 5 idle minutes makes the next question pay a multi-second model reload.
OLLAMA_KEEP_ALIVE = "30m"


def _max_output_tokens() -> int:
    """Cap generation length so total latency and cloud cost stay bounded.
    Interview answers fit comfortably; override with ATLAS_LLM_MAX_TOKENS."""
    try:
        return max(1, int(os.getenv("ATLAS_LLM_MAX_TOKENS", "2048")))
    except ValueError:
        return 2048


class LLMProvider(Protocol):
    name: str
    is_local: bool
    model: str

    def configured(self) -> bool: ...

    def generate(self, prompt: str, *, timeout: int = 60) -> str: ...

    def stream(self, prompt: str, *, timeout: int = 120) -> Iterator[str]: ...


class OllamaProvider:
    name = "ollama"
    is_local = True

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session = requests.Session()  # reuse connections across requests

    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _payload(self, prompt: str, stream: bool) -> dict:
        return {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {"num_predict": _max_output_tokens()},
        }

    def generate(self, prompt: str, *, timeout: int = 60) -> str:
        response = self._session.post(
            f"{self.base_url}/api/generate",
            json=self._payload(prompt, stream=False),
            timeout=(CONNECT_TIMEOUT, timeout),
        )
        response.raise_for_status()
        return str(response.json().get("response", "")).strip()

    def stream(self, prompt: str, *, timeout: int = 120) -> Iterator[str]:
        with self._session.post(
            f"{self.base_url}/api/generate",
            json=self._payload(prompt, stream=True),
            timeout=(CONNECT_TIMEOUT, timeout),
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                piece = chunk.get("response")
                if piece:
                    yield piece
                if chunk.get("done"):
                    break


class OpenAICompatProvider:
    name = "cloud"
    is_local = False

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._session = requests.Session()  # reuse connections: skips TCP+TLS handshake per call

    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, prompt: str, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "temperature": 0.4,
            "max_tokens": _max_output_tokens(),
        }

    def generate(self, prompt: str, *, timeout: int = 60) -> str:
        response = self._session.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(prompt, stream=False),
            timeout=(CONNECT_TIMEOUT, timeout),
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        return str(choices[0].get("message", {}).get("content", "")).strip()

    def stream(self, prompt: str, *, timeout: int = 120) -> Iterator[str]:
        with self._session.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=self._payload(prompt, stream=True),
            timeout=(CONNECT_TIMEOUT, timeout),
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[len("data:"):].strip()
                if line == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                piece = delta.get("content")
                if piece:
                    yield piece
