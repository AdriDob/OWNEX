"""OAR Smart Router — Intelligent task routing to optimal providers."""

from __future__ import annotations

import logging

from .interfaces import (
    AIRequest,
    Capability,
    CostTrackerProtocol,
    FailoverEngineProtocol,
    HealthMonitorProtocol,
    OARConfig,
    RoutingContext,
    RoutingDecision,
    TaskType,
    get_config,
)
from .registry import ProviderRegistry

logger = logging.getLogger("oar.router")


class SmartRouter:
    """Smart routing engine that selects the best provider for each task."""

    def __init__(
        self,
        registry: ProviderRegistry,
        health_monitor: HealthMonitorProtocol,
        cost_tracker: CostTrackerProtocol | None = None,
        failover_engine: FailoverEngineProtocol | None = None,
        config: OARConfig | None = None,
    ):
        self._registry = registry
        self._health = health_monitor
        self._cost = cost_tracker
        self._failover = failover_engine
        self._config = config or get_config()
        self._task_capability_map = self._build_task_capability_map()
        self._routing_history: list[RoutingDecision] = []

    def _build_task_capability_map(self) -> dict[TaskType, set[Capability]]:
        """Map task types to required capabilities."""
        return {
            TaskType.CHAT: {Capability.CHAT},
            TaskType.CODE: {Capability.CODE, Capability.TOOL_CALLING},
            TaskType.RESEARCH: {Capability.CHAT, Capability.LONG_CONTEXT},
            TaskType.ANALYSIS: {Capability.CHAT, Capability.REASONING},
            TaskType.VALIDATION: {Capability.CHAT, Capability.REASONING},
            TaskType.REPORT: {Capability.CHAT, Capability.LONG_CONTEXT, Capability.STRUCTURED_OUTPUT},
            TaskType.PLANNING: {Capability.CHAT, Capability.REASONING, Capability.LONG_CONTEXT},
            TaskType.LEARNING: {Capability.CHAT, Capability.LONG_CONTEXT},
            TaskType.REASONING: {Capability.REASONING, Capability.CHAT},
            TaskType.VISION: {Capability.VISION, Capability.CHAT},
            TaskType.EMBEDDING: {Capability.EMBEDDING},
            TaskType.DEBUG: {Capability.CODE, Capability.REASONING, Capability.TOOL_CALLING},
            TaskType.REFACTOR: {Capability.CODE, Capability.REASONING, Capability.LONG_CONTEXT},
            TaskType.TEST: {Capability.CODE, Capability.TOOL_CALLING},
            TaskType.DOCUMENTATION: {Capability.CHAT, Capability.LONG_CONTEXT},
            TaskType.TRANSLATION: {Capability.CHAT},
            TaskType.SUMMARIZATION: {Capability.CHAT, Capability.LONG_CONTEXT},
            TaskType.BUG_BOUNTY: {
                Capability.CHAT,
                Capability.REASONING,
                Capability.LONG_CONTEXT,
                Capability.TOOL_CALLING,
            },
            TaskType.SECURITY_ANALYSIS: {
                Capability.CHAT,
                Capability.REASONING,
                Capability.CODE,
                Capability.LONG_CONTEXT,
            },
        }

    async def route(self, context: RoutingContext) -> RoutingDecision:
        """Route a request to the best provider."""
        # Determine required capabilities for task type
        required_caps = self._task_capability_map.get(context.task_type, {Capability.CHAT})
        context.required_capabilities |= required_caps

        # Estimate context size
        if not context.context_size_estimate:
            context.context_size_estimate = sum(len(m.get("content", "")) for m in context.messages) // 4

        # Get candidate models
        candidates = self._registry.filter_models(context)
        if not candidates:
            raise RuntimeError("No suitable providers found for request")

        # Score each candidate
        scored = []
        for provider_id, model_id in candidates:
            score = await self._score_candidate(provider_id, model_id, context)
            if score > 0:
                scored.append((score, provider_id, model_id))

        if not scored:
            # Fallback: any available model
            provider_id, model_id = candidates[0]
            return self._create_decision(provider_id, model_id, context, 0.1, "fallback: no scored candidates")

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_provider, best_model = scored[0]

        # Build fallback chain
        fallback_chain = [p for _, p, _ in scored[1:5]]

        # Check failover engine for additional fallbacks
        if self._failover:
            extra_fallbacks = self._failover.get_fallback_chain(best_provider, context)
            for fb in extra_fallbacks:
                if fb not in fallback_chain and fb != best_provider:
                    fallback_chain.append(fb)

        return self._create_decision(best_provider, best_model, context, best_score, "scored", fallback_chain)

    async def _score_candidate(
        self,
        provider_id: str,
        model_id: str,
        context: RoutingContext,
    ) -> float:
        """Score a provider/model combination for the given context."""
        provider = self._registry.get_provider(provider_id)
        if not provider:
            return 0.0

        health = self._health.get_health(provider_id)
        caps = self._registry.get_model_capabilities(model_id)

        # Base score
        score = 0.5

        # Health factor (0-0.3)
        if health:
            if health.status.value == "healthy":
                score += 0.3
            elif health.status.value == "degraded":
                score += 0.1
            else:
                return 0.0  # Unhealthy providers get 0

            # Latency bonus/penalty
            if health.latency_ms < 500:
                score += 0.1
            elif health.latency_ms > 5000:
                score -= 0.1

        # Capability match (0-0.2)
        if caps:
            matched = len(context.required_capabilities & caps.supports)
            total = len(context.required_capabilities) or 1
            score += 0.2 * (matched / total)

            # Missing required capabilities = penalty
            missing = context.required_capabilities - caps.supports
            if missing:
                score -= 0.1 * len(missing)

        # Privacy preference
        if context.privacy_required:
            if provider_id in ["ollama", "lmstudio"]:
                score += 0.2
            else:
                score -= 0.3

        # Speed critical
        if context.speed_critical:
            if health and health.latency_ms < 1000:
                score += 0.15
            elif provider_id in ["groq", "cerebras", "together"]:
                score += 0.1  # Known fast providers

        # Cost optimization
        if self._config.prefer_free:
            if provider_id in ["ollama", "lmstudio", "opencode"]:
                score += 0.15
            elif provider_id in ["groq", "together", "deepinfra"]:
                score += 0.05

        if self._config.prefer_local and provider_id in ["ollama", "lmstudio"]:
            score += 0.1

        # Budget check
        if context.max_cost_usd and self._cost:
            req = AIRequest(messages=context.messages, max_tokens=context.max_tokens, task_type=context.task_type)
            estimated = provider.estimate_cost(req)
            if estimated > context.max_cost_usd:
                return 0.0
            if not self._cost.check_budget(provider_id, estimated):
                score -= 0.2

        # Tier preference (local > free > cheap > premium > enterprise)
        tier_bonus = {
            "ollama": 0.1,
            "lmstudio": 0.1,
            "opencode": 0.05,
            "groq": 0.0,
            "together": 0.0,
            "deepinfra": 0.0,
            "cerebras": 0.0,
            "fcc": -0.05,
            "openrouter": -0.1,
            "nvidia_nim": -0.1,
        }
        score += tier_bonus.get(provider_id, 0.0)

        # Context window check
        if caps and context.context_size_estimate > caps.max_context_tokens * 0.9:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _create_decision(
        self,
        provider_id: str,
        model_id: str,
        context: RoutingContext,
        confidence: float,
        reasoning: str,
        fallback_chain: list[str] | None = None,
    ) -> RoutingDecision:
        """Create a routing decision."""
        provider = self._registry.get_provider(provider_id)
        caps = self._registry.get_model_capabilities(model_id)

        # Estimate cost and latency
        estimated_cost = 0.0
        estimated_latency = 1000
        if provider:
            req = AIRequest(messages=context.messages, max_tokens=context.max_tokens, task_type=context.task_type)
            estimated_cost = provider.estimate_cost(req)
            estimated_latency = provider.estimate_latency(req)

        health = self._health.get_health(provider_id)
        if health:
            estimated_latency = int(health.latency_ms or estimated_latency)

        met = set()
        missing = set()
        if caps:
            met = context.required_capabilities & caps.supports
            missing = context.required_capabilities - caps.supports

        decision = RoutingDecision(
            provider_id=provider_id,
            model_id=model_id,
            task_type=context.task_type,
            confidence=confidence,
            estimated_cost_usd=estimated_cost,
            estimated_latency_ms=estimated_latency,
            reasoning=reasoning,
            fallback_chain=fallback_chain or [],
            privacy_ok=not context.privacy_required or provider_id in ["ollama", "lmstudio"],
            capabilities_met=met,
            capabilities_missing=missing,
        )

        self._routing_history.append(decision)
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-500:]

        return decision

    def record_outcome(
        self, decision: RoutingDecision, success: bool, latency_ms: float, quality: float, cost_usd: float
    ) -> None:
        """Record outcome for learning."""
        # Update provider health metrics
        health = self._health.get_health(decision.provider_id)
        if health:
            if success:
                health.success_count += 1
            else:
                health.error_count += 1
                health.last_error = f"Routing failed: quality={quality:.2f}"
            health.latency_ms = (health.latency_ms * 0.9 + latency_ms * 0.1) if health.latency_ms else latency_ms
            health.quality_score = health.quality_score * 0.9 + quality * 0.1

        # Record cost
        if self._cost:
            self._cost.record_usage(decision.provider_id, decision.model_id, 0, 0, cost_usd)


def create_smart_router(
    registry: ProviderRegistry,
    health_monitor: HealthMonitorProtocol,
    cost_tracker: CostTrackerProtocol | None = None,
    failover_engine: FailoverEngineProtocol | None = None,
    config: OARConfig | None = None,
) -> SmartRouter:
    """Factory function to create a SmartRouter."""
    return SmartRouter(registry, health_monitor, cost_tracker, failover_engine, config)
