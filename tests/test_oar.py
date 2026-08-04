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

        caps = registry.get_model_capabilities("qwen3-coder:8b")
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
        assert decision.model_id == "qwen3-coder:8b"
        assert decision.confidence > 0

        await monitor.stop()


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
