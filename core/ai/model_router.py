"""Model Router — Intelligent model assignment with cost/speed/capacity optimization.

OWNEX uses a hierarchy of AI providers. This module routes each task
to the optimal model based on cost, speed, capacity, and privacy requirements.

Hierarchy:
  1. OmniRoute (primary)     — best quality, paid
  2. FCC Proxy (fallback)    — high quality via OpenRouter
  3. Ollama (local)          — free, private, slower
  4. OpenCode free models    — free tier, variable quality
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.model_router")


class TaskType(StrEnum):
    RESEARCH = "research"  # Reading docs, gathering context
    ANALYSIS = "analysis"  # Code review, vulnerability analysis
    VALIDATION = "validation"  # Verify findings, check quality
    REPORT = "report"  # Generate professional reports
    CODE = "code"  # Write or modify code
    LEARNING = "learning"  # Extract patterns, improve knowledge
    PLANNING = "planning"  # Strategic planning
    CHAT = "chat"  # Interactive conversation


class ProviderTier(int, Enum):
    PRIMARY = 1  # OmniRoute — best quality
    FALLBACK = 2  # FCC Proxy — good quality
    LOCAL = 3  # Ollama — free, private
    FREE = 4  # OpenCode free models
    DEVIN = 5  # Devin CLI — free development tool


@dataclass
class ModelProfile:
    """Profile for an AI model in the router."""

    name: str
    provider: str
    tier: ProviderTier
    cost_per_1k_input: float  # USD or tokens
    cost_per_1k_output: float
    avg_speed_ms: int  # Average response time in ms
    context_window: int  # Max context tokens
    capabilities: list[str]  # e.g., ["code", "analysis", "report"]
    is_available: bool = True
    last_error: str | None = None
    total_calls: int = 0
    failed_calls: int = 0
    avg_latency_ms: float = 0.0


@dataclass
class RoutingDecision:
    """Result of routing a task to a model."""

    task_type: TaskType
    selected_model: str
    provider: str
    tier: ProviderTier
    estimated_cost: float
    estimated_time_ms: int
    confidence: float
    fallbacks_used: list[str] = field(default_factory=list)
    privacy_ok: bool = True


class ModelRouter:
    """Routes tasks to the optimal model based on cost/speed/capacity.

    Uses a scoring system that balances:
    - Cost efficiency (cheaper models preferred for simple tasks)
    - Speed requirements (fast models for interactive tasks)
    - Capacity needs (complex tasks need larger context)
    - Privacy constraints (local models for sensitive data)
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._profiles: dict[str, ModelProfile] = {}
        self._task_model_map: dict[TaskType, list[str]] = {}
        self._load_defaults()
        if config_path:
            self._load_config(config_path)

    def _load_defaults(self) -> None:
        """Load default model profiles."""
        self._profiles = {
            # ── Tier 1: OmniRoute (Primary) ──
            "omniroute-gpt4o": ModelProfile(
                name="gpt-4o",
                provider="omniroute",
                tier=ProviderTier.PRIMARY,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                avg_speed_ms=1500,
                context_window=128000,
                capabilities=["code", "analysis", "report", "planning", "research", "chat"],
            ),
            "omniroute-claude-sonnet": ModelProfile(
                name="claude-sonnet-4",
                provider="omniroute",
                tier=ProviderTier.PRIMARY,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                avg_speed_ms=2000,
                context_window=200000,
                capabilities=["code", "analysis", "report", "planning", "research", "validation"],
            ),
            # ── Tier 2: FCC Proxy (Fallback) ──
            "fcc-gpt4o-mini": ModelProfile(
                name="gpt-4o-mini",
                provider="fcc",
                tier=ProviderTier.FALLBACK,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                avg_speed_ms=800,
                context_window=128000,
                capabilities=["code", "analysis", "chat"],
            ),
            "fcc-claude-haiku": ModelProfile(
                name="claude-haiku",
                provider="fcc",
                tier=ProviderTier.FALLBACK,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                avg_speed_ms=600,
                context_window=200000,
                capabilities=["research", "analysis", "chat", "learning"],
            ),
            # ── Tier 3: Ollama (Local) ──
            "ollama-qwen-coder": ModelProfile(
                name="qwen3-coder:8b",
                provider="ollama",
                tier=ProviderTier.LOCAL,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_speed_ms=3000,
                context_window=32768,
                capabilities=["code", "analysis", "research"],
            ),
            "ollama-hermes": ModelProfile(
                name="hermes-orion",
                provider="ollama",
                tier=ProviderTier.LOCAL,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_speed_ms=4000,
                context_window=32768,
                capabilities=["research", "planning", "learning"],
            ),
            # ── Tier 4: Free models ──
            "opencode-deepseek": ModelProfile(
                name="deepseek-v4-flash-free",
                provider="opencode",
                tier=ProviderTier.FREE,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_speed_ms=2000,
                context_window=128000,
                capabilities=["code", "analysis", "chat"],
            ),
            "opencode-nemotron": ModelProfile(
                name="nemotron-3-ultra-free",
                provider="opencode",
                tier=ProviderTier.FREE,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_speed_ms=1500,
                context_window=128000,
                capabilities=["chat", "research", "learning"],
            ),
            # ── Tier 5: Devin CLI (Free Development Tool) ──
            "devin-claude-sonnet": ModelProfile(
                name="anthropic/claude-sonnet-4-5",
                provider="devin",
                tier=ProviderTier.DEVIN,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_speed_ms=2500,
                context_window=200000,
                capabilities=["code", "refactor", "debug", "test", "optimize", "review", "plan"],
            ),
            "devin-deepseek": ModelProfile(
                name="opencode/deepseek-v4-flash-free",
                provider="devin",
                tier=ProviderTier.DEVIN,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_speed_ms=2000,
                context_window=128000,
                capabilities=["code", "analysis", "chat"],
            ),
        }

        # Map task types to compatible models (ordered by preference)
        self._task_model_map = {
            TaskType.CODE: ["devin-claude-sonnet", "fcc-gpt4o-mini", "ollama-qwen-coder", "opencode-deepseek"],
            TaskType.ANALYSIS: ["devin-claude-sonnet", "fcc-gpt4o-mini", "fcc-claude-haiku", "ollama-qwen-coder"],
            TaskType.RESEARCH: ["devin-claude-sonnet", "fcc-claude-haiku", "ollama-hermes", "opencode-nemotron"],
            TaskType.VALIDATION: [
                "devin-claude-sonnet",
                "omniroute-claude-sonnet",
                "fcc-claude-haiku",
                "fcc-gpt4o-mini",
            ],
            TaskType.REPORT: ["omniroute-claude-sonnet", "omniroute-gpt4o", "fcc-claude-haiku"],
            TaskType.LEARNING: ["ollama-hermes", "fcc-claude-haiku", "opencode-nemotron"],
            TaskType.PLANNING: ["omniroute-claude-sonnet", "fcc-gpt4o-mini", "ollama-hermes"],
            TaskType.CHAT: ["fcc-gpt4o-mini", "opencode-nemotron", "opencode-deepseek"],
        }

    def _load_config(self, config_path: str | Path) -> None:
        """Load custom model profiles from a JSON config."""
        path = Path(config_path)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for key, profile_data in data.get("profiles", {}).items():
                    if key in self._profiles:
                        for k, v in profile_data.items():
                            setattr(self._profiles[key], k, v)
                    else:
                        self._profiles[key] = ModelProfile(**profile_data)
                for task_type, models in data.get("task_mappings", {}).items():
                    if task_type in self._task_model_map:
                        self._task_model_map[TaskType(task_type)] = models
                logger.info("Loaded model router config from %s", path)
            except Exception as e:
                logger.warning("Failed to load model router config: %s", e)

    def route(
        self,
        task_type: TaskType,
        context_size: int = 0,
        privacy_required: bool = False,
        speed_critical: bool = False,
        max_cost: float | None = None,
    ) -> RoutingDecision:
        """Route a task to the optimal model."""
        candidates = self._task_model_map.get(task_type, [])
        if not candidates:
            candidates = [m for m in self._profiles if "chat" in self._profiles[m].capabilities]

        if privacy_required:
            # Prefer local models for sensitive tasks
            candidates.sort(key=lambda m: 0 if self._profiles[m].tier == ProviderTier.LOCAL else 1)

        fallbacks = []
        selected = None

        for model_key in candidates:
            profile = self._profiles.get(model_key)
            if not profile or not profile.is_available:
                continue

            if profile.context_window < context_size:
                fallbacks.append(model_key)
                continue

            if max_cost and profile.cost_per_1k_input > max_cost:
                fallbacks.append(model_key)
                continue

            if privacy_required and profile.tier != ProviderTier.LOCAL:
                fallbacks.append(model_key)
                continue

            selected = model_key
            break

        if not selected and fallbacks:
            # Use best available fallback
            selected = fallbacks[0]

        if not selected:
            # Ultimate fallback: first available model
            for key, profile in self._profiles.items():
                if profile.is_available:
                    selected = key
                    break

        if not selected:
            raise RuntimeError("No models available in any tier")

        profile = self._profiles[selected]
        profile.total_calls += 1

        # Calculate estimated cost and time
        estimated_input_tokens = context_size or 1000
        estimated_output_tokens = max(context_size // 2, 500) if context_size else 500

        estimated_cost = (
            profile.cost_per_1k_input * estimated_input_tokens / 1000
            + profile.cost_per_1k_output * estimated_output_tokens / 1000
        )
        estimated_time = profile.avg_speed_ms

        # Confidence based on tier and task match
        capability_match = task_type.value in profile.capabilities
        tier_confidence = {
            ProviderTier.PRIMARY: 0.95,
            ProviderTier.FALLBACK: 0.85,
            ProviderTier.LOCAL: 0.70,
            ProviderTier.FREE: 0.60,
            ProviderTier.DEVIN: 0.50,
        }
        confidence = tier_confidence[profile.tier]
        if not capability_match:
            confidence *= 0.8

        return RoutingDecision(
            task_type=task_type,
            selected_model=profile.name,
            provider=profile.provider,
            tier=profile.tier,
            estimated_cost=round(estimated_cost, 6),
            estimated_time_ms=estimated_time,
            confidence=round(confidence, 2),
            fallbacks_used=fallbacks,
            privacy_ok=not privacy_required or profile.tier == ProviderTier.LOCAL,
        )

    def report_failure(self, model_name: str) -> None:
        """Report a model failure to update availability."""
        for profile in self._profiles.values():
            if profile.name == model_name:
                profile.failed_calls += 1
                if profile.failed_calls > 3:
                    profile.is_available = False
                    profile.last_error = "Auto-disabled after 3+ failures"
                    logger.warning("Model %s disabled due to repeated failures", model_name)
                break

    def report_success(self, model_name: str, latency_ms: int) -> None:
        """Report a successful call to update metrics."""
        for profile in self._profiles.values():
            if profile.name == model_name:
                profile.avg_latency_ms = (
                    (profile.avg_latency_ms * 0.9 + latency_ms * 0.1) if profile.avg_latency_ms else latency_ms
                )
                break

    def get_available_models(self) -> list[str]:
        """List all currently available models."""
        return [p.name for p in self._profiles.values() if p.is_available]

    def get_tier_summary(self) -> dict[str, Any]:
        """Get a summary of model availability by tier."""
        summary = {}
        for tier in ProviderTier:
            models = [p for p in self._profiles.values() if p.tier == tier]
            summary[tier.name.lower()] = {
                "total": len(models),
                "available": sum(1 for m in models if m.is_available),
                "avg_cost_per_1k_input": round(sum(m.cost_per_1k_input for m in models) / max(len(models), 1), 6),
            }
        return summary


# Singleton
_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
