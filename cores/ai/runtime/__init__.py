"""OAR Unified API — Main entry point for all AI operations."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from .cache import SemanticCache, get_cache
from .context import ContextManager, get_context_manager
from .cost import CostTracker, get_cost_tracker
from .failover import FailoverEngine, get_failover_engine
from .health import HealthMonitor, get_health_monitor, initialize_health_monitor
from .interfaces import (
    AIProviderProtocol,
    AIRequest,
    AIResponse,
    Capability,
    CostTrackerProtocol,
    FailoverEngineProtocol,
    HealthMonitorProtocol,
    LearningEngineProtocol,
    OARConfig,
    RoutingContext,
    RoutingDecision,
    TaskType,
    get_config,
)
from .learning import LearningEngine, get_learning_engine
from .registry import ProviderRegistry, get_registry, initialize_registry
from .router import SmartRouter, create_smart_router

logger = logging.getLogger("oar")


class OAR:
    """OWNEX AI Runtime — Unified AI provider operating system."""

    def __init__(self, config: OARConfig | None = None):
        self._config = config or get_config()
        self._registry: ProviderRegistry | None = None
        self._health: HealthMonitor | None = None
        self._router: SmartRouter | None = None
        self._cost: CostTracker | None = None
        self._failover: FailoverEngine | None = None
        self._cache: SemanticCache | None = None
        self._context: ContextManager | None = None
        self._learning: LearningEngine | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all OAR components."""
        if self._initialized:
            return

        logger.info("Initializing OAR...")

        # Initialize registry (loads providers)
        self._registry = await initialize_registry(self._config)

        # Initialize health monitor
        self._health = await initialize_health_monitor(self._registry, self._config)

        # Initialize other components
        self._cost = get_cost_tracker(self._config)
        self._failover = get_failover_engine(self._registry, self._health, self._config)
        self._cache = get_cache(self._config)
        self._context = get_context_manager(self._config)
        self._learning = get_learning_engine(self._config)

        # Initialize router with all dependencies
        self._router = create_smart_router(
            self._registry,
            self._health,
            self._cost,
            self._failover,
            self._config,
        )

        self._initialized = True
        logger.info("OAR initialized successfully with %d providers", len(self._registry._providers))

    async def shutdown(self) -> None:
        """Shutdown all components."""
        if self._health:
            await self._health.stop()
        for provider in self._registry._providers.values() if self._registry else []:
            await provider.close()
        logger.info("OAR shutdown complete")

    # ===== Core API =====

    async def ask(
        self,
        prompt: str,
        task_type: TaskType = TaskType.CHAT,
        session_id: str | None = None,
        **kwargs,
    ) -> str:
        """Simple ask - returns just the content."""
        response = await self.chat(prompt, task_type, session_id, **kwargs)
        return response.content

    async def chat(
        self,
        prompt: str | list[dict[str, str]],
        task_type: TaskType = TaskType.CHAT,
        session_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        stream: bool = False,
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        response_format: dict | None = None,
        images: list[dict] | None = None,
        **kwargs,
    ) -> AIResponse:
        """Main chat completion endpoint with smart routing and failover."""
        if not self._initialized:
            await self.initialize()

        # Normalize prompt to messages
        messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        # Apply context from session
        request = AIRequest(
            messages=messages,
            task_type=task_type,
            model=model,
            provider=provider,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            images=images,
            metadata=kwargs,
        )

        if self._context:
            request = self._context.prepare_request(request, session_id)

        # Check cache first (only for non-streaming, non-tool requests)
        cache_key = None
        if not stream and not tools and self._cache and self._config.enable_cache:
            cache_key = self._cache._generate_key(
                {
                    "messages": request.messages,
                    "model": request.model,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "task_type": request.task_type.value,
                }
            )
            cached = await self._cache.get(cache_key)
            if cached:
                logger.debug("Cache hit for request")
                return cached

        # Route to best provider
        routing_context = RoutingContext(
            task_type=task_type,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            required_capabilities=set(),
            preferred_providers=[provider] if provider else [],
            excluded_providers=[],
            privacy_required=kwargs.get("privacy_required", False),
            speed_critical=kwargs.get("speed_critical", False),
            max_cost_usd=kwargs.get("max_cost_usd", self._config.max_cost_per_request_usd),
            max_latency_ms=kwargs.get("max_latency_ms"),
            context_size_estimate=sum(len(m.get("content", "")) for m in request.messages) // 4,
            user_id=kwargs.get("user_id"),
            session_id=session_id,
        )

        # Add required capabilities based on request features
        if tools:
            routing_context.required_capabilities.add(Capability.TOOL_CALLING)
        if images:
            routing_context.required_capabilities.add(Capability.VISION)
        if response_format and response_format.get("type") == "json_object":
            routing_context.required_capabilities.add(Capability.JSON_MODE)
        if request.max_tokens > 8000:
            routing_context.required_capabilities.add(Capability.LONG_CONTEXT)

        decision = await self._router.route(routing_context)

        # Execute with failover
        response = await self._execute_with_failover(decision, request, routing_context)

        # Update context
        if self._context:
            self._context.update_from_response(session_id, request, response)

        # Cache successful response
        if cache_key and response.content and not response.metadata.get("error"):
            await self._cache.set(cache_key, response, self._config.cache_ttl_seconds)

        # Record learning
        if self._learning:
            quality = 1.0 if response.content else 0.0
            self._learning.record_routing(decision, bool(response.content), quality)

        return response

    async def _execute_with_failover(
        self,
        decision: RoutingDecision,
        request: AIRequest,
        context: RoutingContext,
    ) -> AIResponse:
        """Execute request with automatic failover."""
        providers_to_try = [decision.provider_id] + decision.fallback_chain

        last_error = None
        for provider_id in providers_to_try:
            if self._failover and self._failover.is_circuit_open(provider_id):
                logger.debug("Circuit open for %s, skipping", provider_id)
                continue

            provider = self._registry.get_provider(provider_id)
            if not provider:
                continue

            try:
                # Update request with selected provider/model
                request.provider = provider_id
                request.model = decision.model_id

                response = await provider.chat(request)

                # Record success
                if self._failover:
                    self._failover.record_success(provider_id)
                if self._router:
                    self._router.record_outcome(
                        decision,
                        bool(response.content),
                        response.latency_ms,
                        1.0 if response.content else 0.0,
                        response.cost_usd,
                    )

                # Add routing metadata
                response.metadata["routing_decision"] = {
                    "provider": decision.provider_id,
                    "model": decision.model_id,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                    "fallbacks_used": len(providers_to_try) - 1,
                }

                return response

            except Exception as e:
                last_error = e
                logger.warning("Provider %s failed: %s", provider_id, e)

                if self._failover:
                    self._failover.record_failure(provider_id, e)

                # Record failure
                if self._router:
                    self._router.record_outcome(decision, False, 0, 0.0, 0.0)

                continue

        # All providers failed
        return AIResponse(
            content="",
            provider_id="none",
            model_id="none",
            task_type=request.task_type,
            cost_usd=0.0,
            latency_ms=0.0,
            finish_reason="error",
            metadata={"error": str(last_error) if last_error else "All providers failed"},
        )

    async def reason(self, prompt: str, **kwargs) -> AIResponse:
        """Reasoning-focused completion."""
        return await self.chat(prompt, TaskType.REASONING, **kwargs)

    async def code(self, prompt: str, **kwargs) -> AIResponse:
        """Code generation completion."""
        return await self.chat(prompt, TaskType.CODE, **kwargs)

    async def vision(self, prompt: str, images: list[dict], **kwargs) -> AIResponse:
        """Vision completion."""
        return await self.chat(prompt, TaskType.VISION, images=images, **kwargs)

    async def embedding(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings."""
        if not self._initialized:
            await self.initialize()

        # Find provider with embedding capability
        for provider in self._registry._providers.values():
            try:
                return await provider.embed(texts, model)
            except Exception:
                continue
        raise RuntimeError("No provider supports embeddings")

    async def stream(self, prompt: str, **kwargs) -> Any:
        """Stream chat completion."""
        # For streaming, we need a different approach - yield chunks
        request = AIRequest(
            messages=[{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt,
            task_type=kwargs.get("task_type", TaskType.CHAT),
            stream=True,
            **{k: v for k, v in kwargs.items() if k != "task_type"},
        )

        if not self._initialized:
            await self.initialize()

        routing_context = RoutingContext(
            task_type=request.task_type,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        decision = await self._router.route(routing_context)
        provider = self._registry.get_provider(decision.provider_id)

        if provider:
            request.provider = decision.provider_id
            request.model = decision.model_id
            async for chunk in provider.chat_stream(request):
                yield chunk

    # ===== Diagnostics =====

    def status(self) -> dict[str, Any]:
        """Get OAR status."""
        return {
            "initialized": self._initialized,
            "providers": self._registry.list_providers() if self._registry else [],
            "health": self._health.get_all_health() if self._health else {},
            "costs": self._cost.get_budget_status() if self._cost else {},
            "cache": self._cache.get_stats() if self._cache else {},
            "learning": self._learning.get_provider_stats() if self._learning else {},
        }

    def doctor(self) -> dict[str, Any]:
        """Comprehensive diagnostics."""
        if not self._initialized:
            return {"error": "OAR not initialized"}

        healthy = self._health.get_healthy_providers() if self._health else []
        degraded = self._health.get_degraded_providers() if self._health else []
        unhealthy = self._health.get_unhealthy_providers() if self._health else []

        return {
            "overall": "healthy" if healthy else "unhealthy",
            "providers": {
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "total": len(healthy) + len(degraded) + len(unhealthy),
            },
            "health_details": self._health.get_all_health() if self._health else {},
            "cost_budget": self._cost.get_budget_status() if self._cost else {},
            "cache_stats": self._cache.get_stats() if self._cache else {},
            "top_recommendations": {tt.value: self._learning.get_recommendations(tt) for tt in TaskType}
            if self._learning
            else {},
            "circuit_breakers": {pid: self._failover.is_circuit_open(pid) for pid in (healthy + degraded + unhealthy)}
            if self._failover
            else {},
        }


# Global OAR instance
_oar: OAR | None = None


def get_oar(config: OARConfig | None = None) -> OAR:
    """Get global OAR instance."""
    global _oar
    if _oar is None:
        _oar = OAR(config)
    return _oar


async def initialize_oar(config: OARConfig | None = None) -> OAR:
    """Initialize and return global OAR."""
    oar = get_oar(config)
    await oar.initialize()
    return oar


# Convenience functions for simple usage
async def ai_ask(prompt: str, **kwargs) -> str:
    """Quick ask function."""
    oar = await initialize_oar()
    return await oar.ask(prompt, **kwargs)


async def ai_chat(prompt: str, **kwargs) -> AIResponse:
    """Quick chat function."""
    oar = await initialize_oar()
    return await oar.chat(prompt, **kwargs)


async def ai_reason(prompt: str, **kwargs) -> AIResponse:
    """Quick reason function."""
    oar = await initialize_oar()
    return await oar.reason(prompt, **kwargs)


async def ai_code(prompt: str, **kwargs) -> AIResponse:
    """Quick code function."""
    oar = await initialize_oar()
    return await oar.code(prompt, **kwargs)
