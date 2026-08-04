"""OAR Cost Tracker — Real cost tracking and budget management."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .interfaces import CostMetrics, CostTrackerProtocol, OARConfig, get_config

logger = logging.getLogger("oar.cost")


class CostTracker(CostTrackerProtocol):
    """Tracks real costs across providers and enforces budgets."""

    def __init__(self, config: OARConfig | None = None):
        self._config = config or get_config()
        self._metrics: dict[str, CostMetrics] = {}  # key: "provider_id:model_id"
        self._daily_spent: dict[str, float] = {}  # key: "YYYY-MM-DD"
        self._provider_pricing: dict[
            str, dict[str, tuple[float, float]]
        ] = {}  # provider -> model -> (input_cost, output_cost)
        self._load_default_pricing()

    def _load_default_pricing(self) -> None:
        """Load default pricing for known providers (USD per 1K tokens)."""
        self._provider_pricing = {
            "openrouter": {
                "openai/gpt-4o": (0.01, 0.03),
                "openai/gpt-4o-mini": (0.00015, 0.0006),
                "anthropic/claude-3.5-sonnet": (0.003, 0.015),
                "anthropic/claude-3-haiku": (0.00025, 0.00125),
                "google/gemini-pro-1.5": (0.00125, 0.005),
                "google/gemini-flash-1.5": (0.000075, 0.0003),
                "meta-llama/llama-3.1-70b-instruct": (0.0009, 0.0009),
                "qwen/qwen-2.5-72b-instruct": (0.0009, 0.0009),
            },
            "nvidia_nim": {
                "meta/llama-3.1-8b-instruct": (0.0002, 0.0002),
                "meta/llama-3.1-70b-instruct": (0.0009, 0.0009),
                "nvidia/nemotron-3-ultra": (0.002, 0.002),
            },
            "groq": {
                "llama-3.1-8b-instant": (0.0, 0.0),  # Free tier
                "llama-3.1-70b-versatile": (0.0, 0.0),
                "mixtral-8x7b-32768": (0.0, 0.0),
                "gemma2-9b-it": (0.0, 0.0),
            },
            "together": {
                "meta-llama/Llama-3.1-8B-Instruct-Turbo": (0.00018, 0.00018),
                "meta-llama/Llama-3.1-70B-Instruct-Turbo": (0.00088, 0.00088),
            },
            "deepinfra": {
                "meta-llama/Meta-Llama-3.1-8B-Instruct": (0.00015, 0.00015),
                "meta-llama/Meta-Llama-3.1-70B-Instruct": (0.00075, 0.00075),
            },
            "cerebras": {
                "llama3.1-8b": (0.0, 0.0),  # Free
                "llama3.1-70b": (0.0, 0.0),
            },
            "fcc": {
                "claude-sonnet-4-5": (0.003, 0.015),
                "claude-haiku": (0.00025, 0.00125),
            },
            "ollama": {},
            "opencode": {},
            "lmstudio": {},
        }

    def _get_key(self, provider_id: str, model_id: str) -> str:
        return f"{provider_id}:{model_id}"

    def _get_daily_key(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def record_usage(
        self,
        provider_id: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float | None = None,
    ) -> None:
        """Record token usage and cost."""
        key = self._get_key(provider_id, model_id)
        daily_key = self._get_daily_key()

        if key not in self._metrics:
            pricing = self._provider_pricing.get(provider_id, {}).get(model_id, (0.0, 0.0))
            daily_budget = self._config.daily_budget_usd
            self._metrics[key] = CostMetrics(
                provider_id=provider_id,
                model_id=model_id,
                cost_per_1k_input=pricing[0],
                cost_per_1k_output=pricing[1],
                daily_budget_usd=daily_budget,
            )

        metrics = self._metrics[key]

        # Calculate cost if not provided
        if cost_usd is None:
            cost_usd = (
                metrics.cost_per_1k_input * input_tokens / 1000 + metrics.cost_per_1k_output * output_tokens / 1000
            )

        metrics.total_input_tokens += input_tokens
        metrics.total_output_tokens += output_tokens
        metrics.total_cost_usd += cost_usd

        # Track daily spend
        self._daily_spent[daily_key] = self._daily_spent.get(daily_key, 0.0) + cost_usd
        metrics.daily_spent_usd = self._daily_spent[daily_key]

        # Check daily budget
        if self._config.daily_budget_usd and metrics.daily_spent_usd > self._config.daily_budget_usd:
            logger.warning(
                "Daily budget exceeded: $%.2f / $%.2f (provider=%s, model=%s)",
                metrics.daily_spent_usd,
                self._config.daily_budget_usd,
                provider_id,
                model_id,
            )

        logger.debug(
            "Recorded usage: %s/%s - %d in, %d out, $%.6f (daily: $%.4f)",
            provider_id,
            model_id,
            input_tokens,
            output_tokens,
            cost_usd,
            metrics.daily_spent_usd,
        )

    def get_costs(self, provider_id: str | None = None) -> dict[str, CostMetrics]:
        """Get cost metrics, optionally filtered by provider."""
        if provider_id:
            return {k: v for k, v in self._metrics.items() if v.provider_id == provider_id}
        return self._metrics.copy()

    def get_total_cost(self, provider_id: str | None = None) -> float:
        """Get total cost across all or specific provider."""
        return sum(m.total_cost_usd for m in self.get_costs(provider_id).values())

    def get_daily_spent(self) -> float:
        """Get total spent today."""
        return self._daily_spent.get(self._get_daily_key(), 0.0)

    def check_budget(self, provider_id: str, estimated_cost: float) -> bool:
        """Check if estimated cost fits within budget."""
        if not self._config.daily_budget_usd:
            return True

        daily_spent = self.get_daily_spent()
        return (daily_spent + estimated_cost) <= self._config.daily_budget_usd

    def get_budget_status(self) -> dict[str, Any]:
        """Get current budget status."""
        daily_spent = self.get_daily_spent()
        budget = self._config.daily_budget_usd
        return {
            "daily_budget_usd": budget,
            "daily_spent_usd": daily_spent,
            "daily_remaining_usd": max(0, budget - daily_spent) if budget else None,
            "budget_exceeded": budget and daily_spent > budget,
            "total_cost_usd": self.get_total_cost(),
            "by_provider": {
                pid: sum(m.total_cost_usd for m in metrics.values())
                for pid, metrics in self._group_by_provider().items()
            },
        }

    def _group_by_provider(self) -> dict[str, dict[str, CostMetrics]]:
        result: dict[str, dict[str, CostMetrics]] = {}
        for key, metrics in self._metrics.items():
            if metrics.provider_id not in result:
                result[metrics.provider_id] = {}
            result[metrics.provider_id][key] = metrics
        return result

    def reset_daily(self) -> None:
        """Reset daily spend (called at midnight)."""
        self._daily_spent.clear()
        for metrics in self._metrics.values():
            metrics.daily_spent_usd = 0.0
            metrics.last_reset = datetime.now()
        logger.info("Daily cost counters reset")

    def set_model_pricing(
        self, provider_id: str, model_id: str, input_cost_per_1k: float, output_cost_per_1k: float
    ) -> None:
        """Set custom pricing for a model."""
        if provider_id not in self._provider_pricing:
            self._provider_pricing[provider_id] = {}
        self._provider_pricing[provider_id][model_id] = (input_cost_per_1k, output_cost_per_1k)

        key = self._get_key(provider_id, model_id)
        if key in self._metrics:
            self._metrics[key].cost_per_1k_input = input_cost_per_1k
            self._metrics[key].cost_per_1k_output = output_cost_per_1k


# Global cost tracker instance
_cost_tracker: CostTracker | None = None


def get_cost_tracker(config: OARConfig | None = None) -> CostTracker:
    """Get global cost tracker."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker(config)
    return _cost_tracker
