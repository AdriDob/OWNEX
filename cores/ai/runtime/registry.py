"""OAR Provider Registry — Manages provider lifecycle with capability negotiation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .adapters import (
    OllamaAdapter,
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
from .interfaces import (
    AIProviderProtocol,
    Capability,
    ModelCapabilities,
    OARConfig,
    RoutingContext,
    get_config,
)

logger = logging.getLogger("oar.registry")


class ProviderRegistry:
    """Registry for AI providers with capability negotiation and health tracking."""

    def __init__(self, config: OARConfig | None = None):
        self._config = config or get_config()
        self._providers: dict[str, AIProviderProtocol] = {}
        self._provider_factories: dict[str, Callable[[], AIProviderProtocol]] = {}
        self._model_to_provider: dict[str, str] = {}
        self._capabilities_cache: dict[str, ModelCapabilities] = {}
        self._initialized = False

        # Register built-in provider factories
        self._provider_factories = {
            "ollama": lambda: OllamaAdapter(),
            "openrouter": lambda: create_openrouter_adapter(),
            "groq": lambda: create_groq_adapter(),
            "together": lambda: create_together_adapter(),
            "deepinfra": lambda: create_deepinfra_adapter(),
            "cerebras": lambda: create_cerebras_adapter(),
            "nvidia_nim": lambda: create_nvidia_adapter(),
            "fcc": lambda: create_fcc_adapter(),
            "opencode": lambda: create_opencode_adapter(),
            "lmstudio": lambda: create_lmstudio_adapter(),
        }

    def register_factory(self, provider_id: str, factory: Callable[[], AIProviderProtocol]) -> None:
        """Register a provider factory for lazy initialization."""
        self._provider_factories[provider_id] = factory
        logger.debug("Registered provider factory: %s", provider_id)

    def register_provider(self, provider: AIProviderProtocol) -> None:
        """Register an already-initialized provider."""
        self._providers[provider.provider_id] = provider
        for model_id in provider.supported_models:
            self._model_to_provider[model_id] = provider.provider_id
            try:
                caps = provider.get_model_capabilities(model_id)
                if caps:
                    self._capabilities_cache[model_id] = caps
            except Exception as e:
                logger.warning("Failed to get capabilities for %s/%s: %s", provider.provider_id, model_id, e)
        logger.info("Registered provider: %s (%d models)", provider.provider_id, len(provider.supported_models))

    async def initialize(self) -> None:
        """Initialize all enabled providers from factories."""
        if self._initialized:
            return

        for provider_id in self._config.enabled_providers:
            if provider_id in self._provider_factories:
                try:
                    provider = self._provider_factories[provider_id]()
                    self.register_provider(provider)
                except Exception as e:
                    logger.warning("Failed to initialize provider %s: %s", provider_id, e)

        self._initialized = True
        logger.info("Provider registry initialized with %d providers", len(self._providers))

    def get_provider(self, provider_id: str) -> AIProviderProtocol | None:
        """Get a provider by ID."""
        return self._providers.get(provider_id)

    def get_provider_for_model(self, model_id: str) -> AIProviderProtocol | None:
        """Get the provider that serves a specific model."""
        provider_id = self._model_to_provider.get(model_id)
        if provider_id:
            return self._providers.get(provider_id)
        return None

    def list_providers(self) -> list[dict[str, Any]]:
        """List all registered providers with their status."""
        result = []
        for provider in self._providers.values():
            health = getattr(provider, "_last_health", None)
            result.append(
                {
                    "provider_id": provider.provider_id,
                    "name": provider.name,
                    "models": provider.supported_models,
                    "health": health.status.value if health else "unknown",
                    "latency_ms": health.latency_ms if health else 0,
                }
            )
        return result

    def get_model_capabilities(self, model_id: str) -> ModelCapabilities | None:
        """Get capabilities for a model."""
        return self._capabilities_cache.get(model_id)

    def get_models_with_capability(self, capability: Capability) -> list[tuple[str, str]]:
        """Get all (provider_id, model_id) pairs that support a capability."""
        result = []
        for model_id, caps in self._capabilities_cache.items():
            if capability in caps.supports:
                provider_id = self._model_to_provider.get(model_id)
                if provider_id:
                    result.append((provider_id, model_id))
        return result

    def get_available_models(self) -> list[str]:
        """Get all available model IDs."""
        return list(self._model_to_provider.keys())

    def filter_models(self, context: RoutingContext) -> list[tuple[str, str]]:
        """Filter models based on routing context requirements."""
        candidates = []

        for model_id, provider_id in self._model_to_provider.items():
            provider = self._providers.get(provider_id)
            if not provider:
                continue

            # Check excluded providers
            if provider_id in context.excluded_providers:
                continue

            # Check capabilities
            caps = self._capabilities_cache.get(model_id)
            if caps:
                missing = context.required_capabilities - caps.supports
                if missing and not context.preferred_providers:
                    continue

                # Check context window
                if context.context_size_estimate > caps.max_context_tokens:
                    continue

            # Check privacy
            if context.privacy_required and provider_id not in ["ollama", "lmstudio"]:
                continue

            candidates.append((provider_id, model_id))

        # Prioritize preferred providers
        if context.preferred_providers:
            candidates.sort(key=lambda x: 0 if x[0] in context.preferred_providers else 1)

        return candidates


# Global registry instance
_registry: ProviderRegistry | None = None


def get_registry(config: OARConfig | None = None) -> ProviderRegistry:
    """Get global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry(config)
    return _registry


async def initialize_registry(config: OARConfig | None = None) -> ProviderRegistry:
    """Initialize and return the global registry."""
    registry = get_registry(config)
    await registry.initialize()
    return registry
