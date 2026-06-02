from __future__ import annotations

"""Tiered LLM router.

Routing by mode:
  - hybrid: try cloud first (low latency) when configured, else local; always
    fall back to local Ollama if cloud fails.
  - cloud:  cloud first, fall back to local on failure.
  - local:  local Ollama only.

Cloud-bound prompts are scrubbed by the outbound privacy guard first. The local
provider receives the raw prompt (data never leaves the device).
"""

import logging
from typing import Any, Callable, Dict, Iterator, List, Optional

from app.llm.config import LLMConfig
from app.llm.providers import LLMProvider, OllamaProvider, OpenAICompatProvider
from app.privacy.outbound_guard import scrub_outbound

logger = logging.getLogger("llm_router")


class LLMRouter:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.ollama = OllamaProvider(config.ollama_base_url, config.ollama_model)
        self.cloud: Optional[OpenAICompatProvider] = None
        if config.cloud_configured:
            self.cloud = OpenAICompatProvider(
                config.cloud_base_url, config.cloud_api_key, config.cloud_model
            )

    def _ordered(self) -> List[LLMProvider]:
        mode = self.config.mode
        if mode == "local":
            return [self.ollama]
        if mode == "cloud":
            return [p for p in (self.cloud, self.ollama) if p is not None]
        # hybrid: cloud first when available, local fallback
        return [p for p in (self.cloud, self.ollama) if p is not None]

    def _prepare(self, provider: LLMProvider, prompt: str) -> tuple[str, Dict[str, int]]:
        if provider.is_local:
            return prompt, {}
        return scrub_outbound(prompt)

    def generate(self, prompt: str, *, timeout: int = 60) -> tuple[str, Dict[str, Any]]:
        providers = self._ordered()
        if not providers:
            raise RuntimeError("No LLM provider configured")

        last_error: Optional[Exception] = None
        for index, provider in enumerate(providers):
            sent_prompt, redactions = self._prepare(provider, prompt)
            try:
                text = provider.generate(sent_prompt, timeout=timeout)
                if not text:
                    raise RuntimeError(f"{provider.name} returned empty response")
                return text, self._meta(provider, index, redactions, error=None)
            except Exception as exc:  # noqa: BLE001 - fall back to next provider
                last_error = exc
                logger.warning("LLM provider %s failed: %s", provider.name, exc)
                continue
        raise RuntimeError(f"All LLM providers failed: {last_error}")

    def stream(self, prompt: str, meta_sink: Dict[str, Any], *, timeout: int = 120) -> Iterator[str]:
        """Yield text deltas. Falls back to the next provider only before the
        first delta is produced; mid-stream failures simply end the stream.
        The chosen provider's metadata is written into `meta_sink`."""
        providers = self._ordered()
        if not providers:
            raise RuntimeError("No LLM provider configured")

        last_error: Optional[Exception] = None
        for index, provider in enumerate(providers):
            sent_prompt, redactions = self._prepare(provider, prompt)
            produced = False
            try:
                for piece in provider.stream(sent_prompt, timeout=timeout):
                    if not produced:
                        meta_sink.update(self._meta(provider, index, redactions, error=None))
                        produced = True
                    yield piece
                if produced:
                    return
                # provider yielded nothing -> try next
                last_error = RuntimeError(f"{provider.name} produced no output")
            except Exception as exc:  # noqa: BLE001
                if produced:
                    # already streamed partial output to the client; stop here
                    meta_sink.setdefault("error", str(exc))
                    return
                last_error = exc
                logger.warning("LLM stream provider %s failed: %s", provider.name, exc)
                continue
        raise RuntimeError(f"All LLM stream providers failed: {last_error}")

    def _meta(self, provider: LLMProvider, index: int, redactions: Dict[str, int], error) -> Dict[str, Any]:
        return {
            "provider": provider.name,
            "model": provider.model,
            "is_local": provider.is_local,
            "fallback_used": index > 0,
            "redactions": redactions,
            "error": error,
        }


def build_router(config: LLMConfig, factory: Optional[Callable[[LLMConfig], LLMRouter]] = None) -> LLMRouter:
    if factory is not None:
        return factory(config)
    return LLMRouter(config)
