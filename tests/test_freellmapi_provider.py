"""FreeLLMAPI como provider opt-in de OAR (no un motor paralelo).

Contrato que se pinea:
- Factory devuelve un OpenAICompatibleAdapter con costo $0 (free tiers) y /v1.
- El registry SOLO lo registra si FREELLMAPI_BASE_URL está definido
  (si no, cada health check pagaría un timeout contra un localhost vacío).
- No está en enabled_providers por default: agregarlo es decisión del owner.
- El router lo trata como free-tier (mismo bonus que omniroute).
"""

from __future__ import annotations

import pytest

from cores.ai.runtime.adapters import create_freellmapi_adapter
from cores.ai.runtime.interfaces import AIRequest, Capability
from cores.ai.runtime.registry import ProviderRegistry


class TestAdapter:
    def test_identity_and_defaults(self) -> None:
        ad = create_freellmapi_adapter()
        assert ad.provider_id == "freellmapi"
        assert "FreeLLMAPI" in ad.name
        assert ad.supported_models == ["auto"]  # nunca un model ID fijo

    def test_cost_is_zero(self) -> None:
        """Free tiers por diseño: estimate_cost debe dar 0 (no 'casi gratis')."""
        ad = create_freellmapi_adapter()
        cost = ad.estimate_cost(AIRequest(messages=[{"role": "user", "content": "hola"}], max_tokens=1000))
        assert cost == 0.0

    def test_capabilities_cover_the_lane(self) -> None:
        caps = create_freellmapi_adapter().get_model_capabilities("auto")
        assert caps is not None
        for cap in (Capability.CHAT, Capability.CODE, Capability.EMBEDDING, Capability.TOOL_CALLING):
            assert cap in caps.supports, cap

    def test_env_overrides_base_and_model(self, monkeypatch) -> None:
        monkeypatch.setenv("FREELLMAPI_BASE_URL", "http://127.0.0.1:9999/v1")
        monkeypatch.setenv("FREELLMAPI_MODEL", "qwen-3-235b")
        ad = create_freellmapi_adapter()
        assert ad.supported_models == ["qwen-3-235b"]

    def test_default_port_is_local(self, monkeypatch) -> None:
        """Self-hosted por diseño: el default apunta a localhost, nunca a un host externo."""
        monkeypatch.delenv("FREELLMAPI_BASE_URL", raising=False)
        ad = create_freellmapi_adapter()
        assert ad._base_url.startswith("http://localhost")  # noqa: SLF001
        assert "127.0.0.1" in ad._base_url or "localhost" in ad._base_url  # noqa: SLF001


class TestOptInRegistry:
    def test_not_registered_without_env(self, monkeypatch) -> None:
        monkeypatch.delenv("FREELLMAPI_BASE_URL", raising=False)
        assert "freellmapi" not in ProviderRegistry()._provider_factories  # noqa: SLF001

    def test_registered_with_env(self, monkeypatch) -> None:
        monkeypatch.setenv("FREELLMAPI_BASE_URL", "http://localhost:8787/v1")
        reg = ProviderRegistry()
        assert "freellmapi" in reg._provider_factories  # noqa: SLF001
        assert reg._provider_factories["freellmapi"]().provider_id == "freellmapi"  # noqa: SLF001

    def test_not_in_default_enabled_providers(self, monkeypatch) -> None:
        """Opt-in real: si se encendiera solo, cambiaría el routing sin permiso."""
        monkeypatch.delenv("FREELLMAPI_BASE_URL", raising=False)
        from cores.ai.runtime.interfaces import get_config

        assert "freellmapi" not in get_config().enabled_providers


class TestRoutingWeight:
    """Guard de regresión sobre el scoring: sin esto el provider se degrada en silencio."""

    def _router_src(self) -> str:
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent / "cores" / "ai" / "runtime" / "router.py").read_text(
            encoding="utf-8"
        )

    def test_tier_bonus_present(self) -> None:
        assert '"freellmapi": 0.05' in self._router_src()

    def test_prefer_free_group_includes_it(self) -> None:
        src = self._router_src()
        assert 'provider_id in ["ollama", "lmstudio", "opencode", "ollama_cloud", "omniroute", "freellmapi"]' in src

    def test_same_weight_as_omniroute(self) -> None:
        """Mismo nivel que omniroute: ambos son free self-hosted."""
        src = self._router_src()
        assert '"omniroute": 0.05' in src
        assert '"freellmapi": 0.05' in src


@pytest.mark.parametrize("provider_id", ["freellmapi"])
def test_provider_id_is_stable(provider_id: str) -> None:
    """El provider_id es parte del contrato de routing: no debe cambiar."""
    assert create_freellmapi_adapter().provider_id == provider_id


class TestPrecedenceRegression:
    """Bug real cazado 2026-09-28: `model or os.getenv(...) if env_model else ""`.

    Por precedencia de Python, con env_model vacío (todos los factories
    OpenAI-compatible) el model explícito se descartaba → supported_models == []
    → el registro NO podía mapear ningún model a su provider. Eso dejaba a
    FCC / OmniRoute / NVIDIA NIM sin resolver modelo en el routing, en silencio.
    """

    FACTORIES = ("omniroute", "fcc", "nvidia_nim", "freellmapi")

    def _build(self):
        from cores.ai.runtime import adapters

        return {
            "omniroute": adapters.create_omniroute_adapter,
            "fcc": adapters.create_fcc_adapter,
            "nvidia_nim": adapters.create_nvidia_adapter,
            "freellmapi": adapters.create_freellmapi_adapter,
        }

    def test_every_free_provider_exposes_its_model(self) -> None:
        for pid, factory in self._build().items():
            models = factory().supported_models
            assert models, f"{pid} expone 0 modelos (routing roto en silencio)"
            assert all(isinstance(m, str) and m for m in models), pid

    def test_registry_can_map_model_to_provider(self) -> None:
        import asyncio

        async def run():
            from cores.ai.runtime.registry import ProviderRegistry

            reg = ProviderRegistry()
            for factory in self._build().values():
                reg.register_provider(factory())
            return reg._model_to_provider  # noqa: SLF001

        mapping = asyncio.run(run())
        assert mapping, "mapa model->provider vacío: ningún provider resuelve modelo"
        assert set(mapping.values()) >= {"omniroute", "fcc", "nvidia_nim", "freellmapi"}

    def test_explicit_model_wins_over_empty_env_name(self) -> None:
        from cores.ai.runtime.adapters import create_freellmapi_adapter

        assert create_freellmapi_adapter(model="qwen-3-235b").supported_models == ["qwen-3-235b"]

    def test_env_model_name_still_works_when_given(self, monkeypatch) -> None:
        from cores.ai.runtime.adapters import OpenAICompatibleAdapter

        monkeypatch.setenv("MY_MODEL", "from-env")
        ad = OpenAICompatibleAdapter(provider_id="x", name="X", env_model="MY_MODEL")
        assert ad.supported_models == ["from-env"]
