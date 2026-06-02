from typing import Iterator

import pytest

from app.llm.config import LLMConfig
from app.llm.router import LLMRouter


class FakeProvider:
    def __init__(self, name, is_local, *, text=None, deltas=None, fail=False):
        self.name = name
        self.is_local = is_local
        self.model = f"{name}-model"
        self._text = text
        self._deltas = deltas or []
        self._fail = fail
        self.seen_prompt = None

    def configured(self) -> bool:
        return True

    def generate(self, prompt: str, *, timeout: int = 60) -> str:
        self.seen_prompt = prompt
        if self._fail:
            raise RuntimeError(f"{self.name} boom")
        return self._text or ""

    def stream(self, prompt: str, *, timeout: int = 120) -> Iterator[str]:
        self.seen_prompt = prompt
        if self._fail:
            raise RuntimeError(f"{self.name} boom")
        for piece in self._deltas:
            yield piece


def _router(mode, cloud, local) -> LLMRouter:
    cfg = LLMConfig(mode=mode)
    router = LLMRouter(cfg)
    router.cloud = cloud
    router.ollama = local
    return router


def test_hybrid_prefers_cloud_when_available():
    cloud = FakeProvider("cloud", False, text="cloud answer")
    local = FakeProvider("ollama", True, text="local answer")
    text, meta = _router("hybrid", cloud, local).generate("hi")
    assert text == "cloud answer"
    assert meta["provider"] == "cloud"
    assert meta["fallback_used"] is False


def test_hybrid_falls_back_to_local_when_cloud_fails():
    cloud = FakeProvider("cloud", False, fail=True)
    local = FakeProvider("ollama", True, text="local answer")
    text, meta = _router("hybrid", cloud, local).generate("hi")
    assert text == "local answer"
    assert meta["provider"] == "ollama"
    assert meta["fallback_used"] is True


def test_local_mode_never_uses_cloud():
    cloud = FakeProvider("cloud", False, text="cloud answer")
    local = FakeProvider("ollama", True, text="local answer")
    router = _router("local", cloud, local)
    text, meta = router.generate("hi")
    assert text == "local answer"
    assert cloud.seen_prompt is None


def test_cloud_prompt_is_scrubbed_local_is_not():
    cloud = FakeProvider("cloud", False, text="ok")
    local = FakeProvider("ollama", True, text="ok")
    prompt = "email me at a@b.com"
    # hybrid -> cloud first, prompt must be scrubbed
    _router("hybrid", cloud, local).generate(prompt)
    assert "a@b.com" not in cloud.seen_prompt
    assert "[REDACTED]" in cloud.seen_prompt
    # local mode -> raw prompt
    local2 = FakeProvider("ollama", True, text="ok")
    _router("local", None, local2).generate(prompt)
    assert local2.seen_prompt == prompt


def test_stream_yields_deltas_and_meta():
    cloud = FakeProvider("cloud", False, deltas=["Hel", "lo"])
    local = FakeProvider("ollama", True, deltas=["x"])
    meta: dict = {}
    out = list(_router("hybrid", cloud, local).stream("hi", meta))
    assert "".join(out) == "Hello"
    assert meta["provider"] == "cloud"


def test_stream_falls_back_before_first_delta():
    cloud = FakeProvider("cloud", False, fail=True)
    local = FakeProvider("ollama", True, deltas=["lo", "cal"])
    meta: dict = {}
    out = list(_router("hybrid", cloud, local).stream("hi", meta))
    assert "".join(out) == "local"
    assert meta["provider"] == "ollama"
    assert meta["fallback_used"] is True


def test_generate_raises_when_all_fail():
    cloud = FakeProvider("cloud", False, fail=True)
    local = FakeProvider("ollama", True, fail=True)
    with pytest.raises(RuntimeError):
        _router("hybrid", cloud, local).generate("hi")
