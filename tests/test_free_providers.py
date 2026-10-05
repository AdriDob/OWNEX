"""Free 24/7 providers — pinning de la selección curada (solo modelos gratis verificados).

2026-09-15: tras verificar en vivo qué devuelve contenido real (FCC claude no-thinking,
NVIDIA deepseek-v4-flash-0731, OmniRoute auto/*), la cadena y los catálogos quedan
acotados. Este test evita que reintroduzcan modelos pagos o EOL en la selección.
"""

from __future__ import annotations


class TestCopilotRouterFreeChain:
    def test_chain_starts_with_fcc_and_keeps_free_fallback(self):
        from cores.copilot.providers.router import get_provider_router

        names = [p.name for p in get_provider_router().providers]
        # Claves free 24/7 primero (ordeN verificado en vivo 2026-09-15).
        assert names[0] == "fcc"
        assert "nvidia" in names[:4]
        assert "omniroute" in names
        # Devin/Freebuff conservados (decisión owner) al final, no estorban.
        assert "devin" in names
        assert "freebuff" in names
        assert names.index("devin") > names.index("ollama")
        assert names.index("freebuff") > names.index("ollama")

    def test_fcc_models_are_only_verified_claude(self):
        from cores.copilot.providers.fcc_provider import FCCProvider

        p = FCCProvider()
        assert p.FREE_MODELS == ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]

    def test_nvidia_models_are_live_ids(self):
        from cores.copilot.providers.nvidia_provider import NvidiaProvider

        p = NvidiaProvider()
        assert "deepseek-ai/deepseek-v4-flash-0731" in p._supported_models
        assert not any("nv-ai-foundation" in m for m in p._supported_models)
        assert not any("llama-3.1-70b" in m for m in p._supported_models)  # EOL 2026-08-26

    def test_omniroute_default_is_auto_best_free(self):
        from cores.copilot.providers.omniroute_provider import _OMNIROUTE_MODELS, OmniRouteProvider

        assert all(m.startswith("auto/") for m in _OMNIROUTE_MODELS)
        assert OmniRouteProvider()._default_model == "auto/best-free"


class TestOARFreeDefaults:
    def test_enabled_providers_are_only_free(self):
        from cores.ai.runtime.interfaces import get_config

        cfg = get_config()
        assert cfg.enabled_providers == [
            "ollama",
            "opencode",
            "ollama_cloud",
            "fcc",
            "nvidia_nim",
            "omniroute",
            "groq",
            "cerebras",
            "together",
            "deepinfra",
        ]
        assert cfg.default_provider == "ollama"
        assert cfg.default_model == "qwen2.5:3b-instruct"

    def test_registry_has_ollama_cloud_and_omniroute(self):
        from cores.ai.runtime.interfaces import OARConfig
        from cores.ai.runtime.registry import ProviderRegistry

        reg = ProviderRegistry(OARConfig())
        assert "ollama_cloud" in reg._provider_factories
        assert "omniroute" in reg._provider_factories

    def test_router_scoring_lists_free_providers(self):
        import inspect

        from cores.ai.runtime.router import SmartRouter

        src = inspect.getsource(SmartRouter._score_candidate)
        # El scoring prefer_free debe reconocer los nuevos providers gratuitos.
        assert "ollama_cloud" in src
        assert "omniroute" in src
        assert "groq" in src
        assert "cerebras" in src
        assert "together" in src
        assert "deepinfra" in src


class TestUnifiedOmnirouteCurated:
    def test_unified_omniroute_models_are_auto(self):
        from cores.ai.unified_provider import UnifiedAIProvider

        p = UnifiedAIProvider()
        assert all(m.startswith("auto/") for m in p._omniroute_models)
