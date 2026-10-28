"""Tests for OAR components."""

from __future__ import annotations

import pytest

from cores.ai.runtime import (
    OAR,
    Capability,
    CostTracker,
    FailoverEngine,
    HealthMonitor,
    LearningEngine,
    OARConfig,
    ProviderRegistry,
    RoutingContext,
    SmartRouter,
    TaskType,
    get_config,
)
from cores.ai.runtime.adapters import (
    create_cerebras_adapter,
    create_deepinfra_adapter,
    create_fcc_adapter,
    create_groq_adapter,
    create_lmstudio_adapter,
    create_nvidia_adapter,
    create_opencode_adapter,
    create_openrouter_adapter,
    create_together_adapter,
)


class TestOARConfig:
    def test_default_config(self):
        config = get_config()
        assert isinstance(config, OARConfig)
        assert "ollama" in config.enabled_providers
        assert config.prefer_local is True
        assert config.prefer_free is True

    def test_custom_config(self):
        config = OARConfig(
            enabled_providers=["ollama", "groq"],
            prefer_local=False,
            daily_budget_usd=5.0,
        )
        assert config.enabled_providers == ["ollama", "groq"]
        assert config.prefer_local is False
        assert config.daily_budget_usd == 5.0


class TestProviderRegistry:
    @pytest.mark.asyncio
    async def test_registry_initialization(self):
        config = OARConfig(enabled_providers=["ollama"])
        registry = ProviderRegistry(config)
        await registry.initialize()

        assert registry._initialized
        assert "ollama" in registry._providers
        provider = registry.get_provider("ollama")
        assert provider is not None
        assert provider.provider_id == "ollama"

    @pytest.mark.asyncio
    async def test_model_capabilities(self):
        config = OARConfig(enabled_providers=["ollama"])
        registry = ProviderRegistry(config)
        await registry.initialize()

        caps = registry.get_model_capabilities("qwen2.5:3b-instruct")
        assert caps is not None
        assert Capability.CHAT in caps.supports
        assert Capability.CODE in caps.supports
        assert caps.max_context_tokens == 32768


class TestHealthMonitor:
    @pytest.mark.asyncio
    async def test_health_check(self):
        config = OARConfig(enabled_providers=["ollama"])
        registry = ProviderRegistry(config)
        await registry.initialize()

        monitor = HealthMonitor(registry, config)
        await monitor.start()

        health = monitor.get_health("ollama")
        # Ollama might not be running, so just check structure
        assert health is not None or "ollama" in monitor.get_all_health()

        await monitor.stop()


class TestCostTracker:
    def test_cost_recording(self):
        tracker = CostTracker()
        # Use a model with known pricing
        tracker.record_usage("openrouter", "openai/gpt-4o-mini", 1000, 500)

        costs = tracker.get_costs()
        key = "openrouter:openai/gpt-4o-mini"
        assert key in costs
        assert costs[key].total_input_tokens == 1000
        assert costs[key].total_output_tokens == 500
        assert costs[key].total_cost_usd > 0

    def test_budget_check(self):
        config = OARConfig(daily_budget_usd=0.01)
        tracker = CostTracker(config)

        # Should fit in budget
        assert tracker.check_budget("openrouter", 0.001) is True

        # Record some usage that exceeds budget
        tracker.record_usage("openrouter", "openai/gpt-4o-mini", 100000, 50000)

        # Should exceed budget
        assert tracker.check_budget("openrouter", 0.001) is False


class TestFailoverEngine:
    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        config = OARConfig(enabled_providers=["ollama"], circuit_breaker_threshold=2)
        registry = ProviderRegistry(config)
        await registry.initialize()

        from cores.ai.runtime.health import HealthMonitor

        monitor = HealthMonitor(registry, config)
        await monitor.start()

        failover = FailoverEngine(registry, monitor, config)

        # Record failures
        failover.record_failure("ollama", Exception("Test error"))
        failover.record_failure("ollama", Exception("Test error"))

        # Circuit should be open
        assert failover.is_circuit_open("ollama") is True

        # Record success should eventually close it
        failover.record_success("ollama")
        failover.record_success("ollama")

        await monitor.stop()


class TestSmartRouter:
    @pytest.mark.asyncio
    async def test_routing(self):
        config = OARConfig(enabled_providers=["ollama"])
        registry = ProviderRegistry(config)
        await registry.initialize()

        from cores.ai.runtime.health import HealthMonitor

        monitor = HealthMonitor(registry, config)
        await monitor.start()

        router = SmartRouter(registry, monitor, config=config)

        context = RoutingContext(
            task_type=TaskType.CODE,
            messages=[{"role": "user", "content": "Write a hello world function"}],
            max_tokens=1000,
        )

        decision = await router.route(context)

        assert decision.provider_id == "ollama"
        assert decision.model_id == "qwen2.5:3b-instruct"
        assert decision.confidence > 0

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_un_provider_caido_no_es_candidato(self):
        """`filter_models` descarta providers con salud que lo impide.

        Sin este filtro, un provider con `auth_failed` o `quota_exceeded`
        seguía siendo candidato y el routing terminaba en él aunque otro
        estuviera sano. Medido 2026-10-05: la respuesta llegaba en inglés
        desde FCC mientras ollama estaba healthy.

        Y `UNKNOWN` **sí** se acepta: al arrancar todavía no hay datos de
        salud, y quedarse sin candidatos sería peor que probar.
        """
        from cores.ai.runtime.interfaces import HealthStatus, ProviderHealth

        config = OARConfig(enabled_providers=["ollama"])
        registry = ProviderRegistry(config)
        await registry.initialize()

        context = RoutingContext(
            task_type=TaskType.CODE,
            messages=[{"role": "user", "content": "hola"}],
            max_tokens=1000,
        )
        provider = registry.get_provider("ollama")
        assert provider is not None
        base = registry.filter_models(context)
        assert ("ollama", "qwen2.5:3b-instruct") in base, "precondición: el prefijo no debe cambiar"

        def con_salud(status: HealthStatus) -> list[tuple[str, str]]:
            # Asignación directa, igual que `HealthMonitor` (`health.py:105`):
            # `_last_health` no está en `AIProviderProtocol` y por eso el type
            # checker se queja en los dos sitios. Es el patrón que ya usa el
            # código de producción, no una excepción de este test.
            provider._last_health = ProviderHealth(  # type: ignore[attr-defined]
                provider_id="ollama", status=status, latency_ms=1.0, success_count=1
            )
            return registry.filter_models(context)

        for malo in (HealthStatus.UNHEALTHY, HealthStatus.AUTH_FAILED, HealthStatus.QUOTA_EXCEEDED):
            assert con_salud(malo) == [], f"{malo} no debe ser candidato"

        for bueno in (HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNKNOWN):
            assert con_salud(bueno) == base, f"{bueno} debe seguir siendo candidato"

        # Sin dato de salud (arranque en frío) también debe servir.
        provider._last_health = None  # type: ignore[attr-defined]
        assert registry.filter_models(context) == base


class TestLearningEngine:
    def test_learning(self):
        config = OARConfig()
        learning = LearningEngine(config)

        from cores.ai.runtime.interfaces import RoutingDecision

        decision = RoutingDecision(
            provider_id="ollama",
            model_id="qwen3-coder:8b",
            task_type=TaskType.CODE,
            confidence=0.8,
            estimated_cost_usd=0.0,
            estimated_latency_ms=3000,
            reasoning="test",
        )

        learning.record_routing(decision, True, 0.9)

        prefs = learning.get_preferences(TaskType.CODE)
        assert "ollama" in prefs
        assert prefs["ollama"] > 0


class TestAdapters:
    def test_adapter_creation(self):
        # Test all adapter factories create valid instances
        adapters = [
            create_openrouter_adapter("test-key"),
            create_groq_adapter("test-key"),
            create_together_adapter("test-key"),
            create_deepinfra_adapter("test-key"),
            create_cerebras_adapter("test-key"),
            create_nvidia_adapter("test-key"),
            create_fcc_adapter("test-key"),
            create_opencode_adapter(),
            create_lmstudio_adapter(),
        ]

        for adapter in adapters:
            assert adapter.provider_id
            assert adapter.name
            assert isinstance(adapter.supported_models, list)


class TestOARIntegration:
    @pytest.mark.asyncio
    async def test_oar_initialization(self):
        config = OARConfig(enabled_providers=["ollama"])
        oar = OAR(config)
        await oar.initialize()

        assert oar._initialized
        assert oar._registry is not None
        assert oar._router is not None

        status = oar.status()
        assert status["initialized"] is True

        await oar.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestRecentRouting:
    def test_recent_routing_empty_before_requests(self):
        from cores.ai.runtime import OAR, OARConfig

        oar = OAR(OARConfig(enabled_providers=[]))
        recent = oar._recent_routing(20)
        assert recent == []

    def test_recent_routing_sanitizes_decisions(self):
        from types import SimpleNamespace

        from cores.ai.runtime import OAR, OARConfig

        oar = OAR(OARConfig(enabled_providers=[]))

        class _D:
            provider_id = "fcc"
            model_id = "m-1"
            confidence = 0.9
            estimated_cost_usd = 0.01
            estimated_latency_ms = 120
            fallback_chain = ["ollama"]
            privacy_ok = True
            task_type = SimpleNamespace(value="code")
            timestamp = "2026-01-01"

        oar._router = SimpleNamespace(_routing_history=[_D()])  # type: ignore[attr-defined]
        recent = oar._recent_routing(20)
        assert len(recent) == 1
        row = recent[0]
        assert row["provider_id"] == "fcc"
        assert row["task_type"] == "code"
        assert "messages" not in row and "prompt" not in row


class TestLocalFirstOrder:
    """Pin canonical OAR order: local > free-remote > fcc > openrouter (SSOT router.py tier_bonus)."""

    def _router(self):
        from types import SimpleNamespace

        from cores.ai.runtime.router import SmartRouter

        class FakeReg:
            def get_provider(self, pid):
                return SimpleNamespace(provider_id=pid)

            def get_model_capabilities(self, mid):
                return SimpleNamespace(max_context_tokens=32000, supports=set())

        class FakeHealth:
            def get_health(self, pid):
                return SimpleNamespace(status=SimpleNamespace(value="healthy"), latency_ms=100)

        return SmartRouter(FakeReg(), FakeHealth(), config=None)

    async def test_local_beats_fcc_beats_openrouter(self):

        from cores.ai.runtime.interfaces import RoutingContext, TaskType

        router = self._router()
        ctx = RoutingContext(
            task_type=TaskType.CHAT,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
        )
        scores = {}
        for pid in ("ollama", "opencode", "groq", "fcc", "openrouter"):
            scores[pid] = await router._score_candidate(pid, "m", ctx)
        assert scores["ollama"] > scores["fcc"] > scores["openrouter"]
        assert scores["ollama"] >= scores["opencode"] >= scores["groq"] >= scores["fcc"]
