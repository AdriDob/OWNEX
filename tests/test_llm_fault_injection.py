"""AI fault-injection tests for CodeGenerator._llm_complete (P3/P5).

Injects provider failures into the OAR-first → provider-router fallback chain
and verifies graceful degradation: fallback is attempted, and total AI outage
yields None (callers fall back to heuristics) instead of raising or inventing.
No network, no real providers: fakes only.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from cores.autonomy.code_generator import CodeGenerator


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class _FakeOAR:
    """Fake OAR with programmable chat behavior."""

    def __init__(self, behavior: str = "ok", content: str = "fixed-code"):
        self.behavior = behavior
        self.content = content
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        self.calls.append(messages)
        if self.behavior == "raise":
            raise ConnectionError("FCC down")
        if self.behavior == "empty":
            return SimpleNamespace(content="")
        if self.behavior == "malformed":
            return SimpleNamespace()
        return SimpleNamespace(content=self.content)


class _FakeRouter:
    """Fake copilot provider router with programmable route behavior."""

    def __init__(self, behavior: str = "ok", content: str = "router-code"):
        self.behavior = behavior
        self.content = content
        self.calls = 0

    async def route(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self.behavior == "raise":
            raise TimeoutError("all providers timed out")
        if self.behavior == "error":
            return SimpleNamespace(content="", error="quota exhausted")
        return SimpleNamespace(content=self.content, error=None)


def _patched(oar: _FakeOAR | None, router: _FakeRouter | None):
    """Patch both lazy imports used inside _llm_complete."""
    oar_patcher = patch("cores.ai.runtime.get_oar", return_value=oar)
    router_patcher = patch("cores.copilot.providers.router.get_provider_router", return_value=router)
    return oar_patcher, router_patcher


class TestOARFallbackChain:
    def test_oar_success_never_touches_router(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("ok"), _FakeRouter("ok")
        po, pr = _patched(oar, router)
        with po, pr:
            assert _run(gen._llm_complete("sys", "user")) == "fixed-code"
        assert router.calls == 0

    def test_oar_outage_falls_back_to_router(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("raise"), _FakeRouter("ok")
        po, pr = _patched(oar, router)
        with po, pr:
            assert _run(gen._llm_complete("sys", "user")) == "router-code"
        assert router.calls == 1

    def test_oar_empty_content_falls_back_to_router(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("empty"), _FakeRouter("ok")
        po, pr = _patched(oar, router)
        with po, pr:
            assert _run(gen._llm_complete("sys", "user")) == "router-code"

    def test_oar_malformed_response_falls_back_to_router(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("malformed"), _FakeRouter("ok")
        po, pr = _patched(oar, router)
        with po, pr:
            assert _run(gen._llm_complete("sys", "user")) == "router-code"

    def test_total_outage_returns_none_for_heuristics(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("raise"), _FakeRouter("raise")
        po, pr = _patched(oar, router)
        with po, pr:
            assert _run(gen._llm_complete("sys", "user")) is None

    def test_router_error_yields_none_not_invention(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("raise"), _FakeRouter("error")
        po, pr = _patched(oar, router)
        with po, pr:
            assert _run(gen._llm_complete("sys", "user")) is None

    def test_oar_import_failure_still_falls_back(self):
        gen = CodeGenerator()
        router = _FakeRouter("ok")
        with (
            patch("cores.ai.runtime.get_oar", side_effect=ImportError("no OAR")),
            patch("cores.copilot.providers.router.get_provider_router", return_value=router),
        ):
            assert _run(gen._llm_complete("sys", "user")) == "router-code"

    def test_secrets_never_reach_oar(self):
        gen = CodeGenerator()
        oar, router = _FakeOAR("ok"), _FakeRouter("ok")
        po, pr = _patched(oar, router)
        with po, pr:
            _run(gen._llm_complete("api_key=sk-live-abc123XYZ", "password=hunter2hunter"))
        sent = str(oar.calls)
        assert "sk-live-abc123XYZ" not in sent
        assert "hunter2hunter" not in sent
        assert "[REDACTED]" in sent
