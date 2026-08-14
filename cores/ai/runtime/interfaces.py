"""OAR Core Interfaces — Universal AI Provider Operating System interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any


class Capability(StrEnum):
    """Model capabilities that affect routing decisions."""

    CHAT = "chat"
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    REASONING = "reasoning"
    CODE = "code"
    EMBEDDING = "embedding"
    JSON_MODE = "json_mode"
    LONG_CONTEXT = "long_context"  # >32k tokens
    MULTIMODAL = "multimodal"
    STRUCTURED_OUTPUT = "structured_output"
    PARALLEL_TOOL_CALLS = "parallel_tool_calls"


class TaskType(StrEnum):
    """Types of AI tasks for smart routing."""

    CHAT = "chat"
    CODE = "code"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    VALIDATION = "validation"
    REPORT = "report"
    PLANNING = "planning"
    LEARNING = "learning"
    REASONING = "reasoning"
    VISION = "vision"
    EMBEDDING = "embedding"
    DEBUG = "debug"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENTATION = "documentation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    BUG_BOUNTY = "bug_bounty"
    SECURITY_ANALYSIS = "security_analysis"


class ProviderTier(int, Enum):
    """Provider priority tiers (lower = preferred)."""

    LOCAL = 1  # Ollama, LM Studio - free, private
    FREE = 2  # OpenCode, free tiers - free, variable quality
    CHEAP = 3  # Groq, Together, DeepInfra - low cost
    PREMIUM = 4  # OpenRouter, NVIDIA - high quality, paid
    ENTERPRISE = 5  # Custom, dedicated - highest quality, highest cost


class HealthStatus(StrEnum):
    """Provider health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTH_FAILED = "auth_failed"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class ModelCapabilities:
    """Capabilities of a specific model."""

    model_id: str
    supports: set[Capability] = field(default_factory=set)
    max_context_tokens: int = 4096
    max_output_tokens: int = 4096
    supports_parallel_tools: bool = False
    vision_formats: list[str] = field(default_factory=list)  # ["image/png", "image/jpeg"]
    tool_call_format: str = "openai"  # "openai", "anthropic", "none"
    reasoning_effort_levels: list[str] = field(default_factory=list)  # ["low", "medium", "high"]


@dataclass(slots=True)
class ProviderHealth:
    """Live health metrics for a provider."""

    provider_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    error_rate: float = 0.0
    success_count: int = 0
    error_count: int = 0
    quota_remaining: int | None = None
    quota_reset_at: datetime | None = None
    last_check: datetime = field(default_factory=datetime.now)
    last_error: str | None = None
    uptime_seconds: float = 0.0
    quality_score: float = 1.0  # 0.0-1.0 based on response quality eval


@dataclass(slots=True)
class CostMetrics:
    """Cost tracking for a provider/model."""

    provider_id: str
    model_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    daily_budget_usd: float | None = None
    daily_spent_usd: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class RoutingContext:
    """Context for routing decisions."""

    task_type: TaskType
    messages: list[dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.3
    required_capabilities: set[Capability] = field(default_factory=set)
    preferred_providers: list[str] = field(default_factory=list)
    excluded_providers: list[str] = field(default_factory=list)
    privacy_required: bool = False
    speed_critical: bool = False
    max_cost_usd: float | None = None
    max_latency_ms: int | None = None
    context_size_estimate: int = 0
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoutingDecision:
    """Result of routing a request to a provider."""

    provider_id: str
    model_id: str
    task_type: TaskType
    confidence: float  # 0.0-1.0
    estimated_cost_usd: float
    estimated_latency_ms: int
    reasoning: str
    fallback_chain: list[str] = field(default_factory=list)
    privacy_ok: bool = True
    capabilities_met: set[Capability] = field(default_factory=set)
    capabilities_missing: set[Capability] = field(default_factory=set)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class AIRequest:
    """Unified AI request."""

    messages: list[dict[str, str]]
    task_type: TaskType = TaskType.CHAT
    model: str | None = None  # Override model selection
    provider: str | None = None  # Override provider selection
    max_tokens: int = 4096
    temperature: float = 0.3
    stream: bool = False
    tools: list[dict] | None = None
    tool_choice: str | None = None  # "auto", "none", "required", or specific function
    response_format: dict | None = None  # {"type": "json_object"} etc.
    images: list[dict] | None = None  # For vision: [{"type": "image_url", "image_url": {"url": "..."}}]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIResponse:
    """Unified AI response."""

    content: str
    provider_id: str
    model_id: str
    task_type: TaskType
    usage: dict[str, int] = field(
        default_factory=dict
    )  # {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    finish_reason: str | None = None
    tool_calls: list[dict] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkResult:
    """Result of a provider benchmark."""

    provider_id: str
    model_id: str
    task_type: TaskType
    success: bool
    latency_ms: float
    quality_score: float  # 0.0-1.0
    cost_usd: float
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


class AIProviderProtocol(ABC):
    """Universal interface that all AI providers must implement."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g., 'ollama', 'openrouter', 'groq')."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """List of model IDs this provider supports."""
        ...

    @abstractmethod
    def get_model_capabilities(self, model_id: str) -> ModelCapabilities | None:
        """Get capabilities for a specific model."""
        ...

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Check provider health and return live metrics."""
        ...

    @abstractmethod
    async def chat(self, request: AIRequest) -> AIResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def chat_stream(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Stream a chat completion response."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...

    def estimate_cost(self, request: AIRequest) -> float:
        """Estimate cost in USD for a request. Override for accuracy."""
        return 0.0

    def estimate_latency(self, request: AIRequest) -> int:
        """Estimate latency in ms for a request. Override for accuracy."""
        return 1000

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources."""
        ...


class HealthMonitorProtocol(ABC):
    """Interface for health monitoring."""

    @abstractmethod
    async def start(self) -> None:
        """Start continuous health monitoring."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop health monitoring."""
        ...

    @abstractmethod
    def get_health(self, provider_id: str) -> ProviderHealth | None:
        """Get current health for a provider."""
        ...

    @abstractmethod
    def get_all_health(self) -> dict[str, ProviderHealth]:
        """Get health for all providers."""
        ...

    @abstractmethod
    def get_healthy_providers(self) -> list[str]:
        """Get list of healthy provider IDs."""
        ...

    @abstractmethod
    def get_degraded_providers(self) -> list[str]:
        """Get list of degraded provider IDs."""
        ...

    @abstractmethod
    def get_unhealthy_providers(self) -> list[str]:
        """Get list of unhealthy provider IDs."""
        ...


class RouterProtocol(ABC):
    """Interface for smart routing."""

    @abstractmethod
    async def route(self, context: RoutingContext) -> RoutingDecision:
        """Route a request to the best provider."""
        ...

    @abstractmethod
    def record_outcome(
        self, decision: RoutingDecision, success: bool, latency_ms: float, quality: float, cost_usd: float
    ) -> None:
        """Record outcome for learning."""
        ...


class CostTrackerProtocol(ABC):
    """Interface for cost tracking."""

    @abstractmethod
    def record_usage(
        self, provider_id: str, model_id: str, input_tokens: int, output_tokens: int, cost_usd: float
    ) -> None:
        """Record token usage and cost."""
        ...

    @abstractmethod
    def get_costs(self, provider_id: str | None = None) -> dict[str, CostMetrics]:
        """Get cost metrics."""
        ...

    @abstractmethod
    def check_budget(self, provider_id: str, estimated_cost: float) -> bool:
        """Check if request fits within budget."""
        ...


class CacheProtocol(ABC):
    """Interface for response caching."""

    @abstractmethod
    async def get(self, key: str) -> AIResponse | None:
        """Get cached response."""
        ...

    @abstractmethod
    async def set(self, key: str, response: AIResponse, ttl_seconds: int = 3600) -> None:
        """Cache a response."""
        ...

    @abstractmethod
    async def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        ...


class BenchmarkEngineProtocol(ABC):
    """Interface for automated benchmarking."""

    @abstractmethod
    async def benchmark_provider(
        self, provider_id: str, model_id: str, task_types: list[TaskType] | None = None
    ) -> list[BenchmarkResult]:
        """Run benchmarks for a provider/model."""
        ...

    @abstractmethod
    async def benchmark_all(self, task_types: list[TaskType] | None = None) -> dict[str, list[BenchmarkResult]]:
        """Benchmark all available providers."""
        ...

    @abstractmethod
    def get_rankings(self, task_type: TaskType | None = None) -> list[tuple[str, str, float]]:
        """Get provider rankings (provider_id, model_id, score)."""
        ...


class LearningEngineProtocol(ABC):
    """Interface for routing optimization learning."""

    @abstractmethod
    def record_routing(self, decision: RoutingDecision, success: bool, quality: float) -> None:
        """Record a routing decision outcome."""
        ...

    @abstractmethod
    def get_preferences(self, task_type: TaskType, user_id: str | None = None) -> dict[str, float]:
        """Get learned provider preferences for a task type."""
        ...


class FailoverEngineProtocol(ABC):
    """Interface for intelligent failover."""

    @abstractmethod
    def get_fallback_chain(self, primary_provider: str, context: RoutingContext) -> list[str]:
        """Get ordered fallback providers."""
        ...

    @abstractmethod
    def record_failure(self, provider_id: str, error: Exception) -> None:
        """Record a provider failure."""
        ...

    @abstractmethod
    def is_circuit_open(self, provider_id: str) -> bool:
        """Check if circuit breaker is open for a provider."""
        ...


@dataclass
class OARConfig:
    """Global OAR configuration."""

    # Provider settings
    enabled_providers: list[str] = field(
        default_factory=lambda: [
            "ollama",
            "opencode",
            "fcc",
            "openrouter",
            "nvidia_nim",
            "groq",
            "together",
            "deepinfra",
            "cerebras",
            "lmstudio",
            "freebuff",
        ]
    )
    default_provider: str = "ollama"
    default_model: str = "qwen3-coder:8b"

    # Routing settings
    enable_smart_routing: bool = True
    privacy_mode: bool = False
    prefer_local: bool = True
    prefer_free: bool = True
    max_cost_per_request_usd: float | None = 0.10

    # Health monitoring
    health_check_interval_seconds: int = 60
    health_check_timeout_seconds: int = 10
    circuit_breaker_threshold: int = 3
    circuit_breaker_timeout_seconds: int = 300

    # Cost tracking
    daily_budget_usd: float | None = 10.0
    track_costs: bool = True

    # Caching
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_size_mb: int = 100

    # Benchmarking
    auto_benchmark: bool = True
    benchmark_interval_hours: int = 24

    # Learning
    enable_learning: bool = True
    learning_window_days: int = 30


# Default configuration instance
_DEFAULT_CONFIG: OARConfig | None = None


def get_config() -> OARConfig:
    """Get global OAR configuration."""
    global _DEFAULT_CONFIG
    if _DEFAULT_CONFIG is None:
        _DEFAULT_CONFIG = OARConfig()
    return _DEFAULT_CONFIG


def configure(config: OARConfig) -> None:
    """Set global OAR configuration."""
    global _DEFAULT_CONFIG
    _DEFAULT_CONFIG = config
