from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.publisher import ExecutionEventPublisher

logger = logging.getLogger("ownex.execution.metrics")


class MetricsEngine:
    """Collects and publishes metrics for workflow executions.

    Measures:
    - CPU, RAM, Tokens, Cost, API Calls, Bandwidth, Cache Hits
    - Retries, Failures
    - Approval Time, Human Time, Automation Time
    """

    def __init__(self, publisher: ExecutionEventPublisher | None = None) -> None:
        self.publisher = publisher or ExecutionEventPublisher()
        self._global_metrics: dict[str, Any] = {
            "total_executions": 0,
            "total_duration_ms": 0.0,
            "total_cost_usd": 0.0,
            "total_api_calls": 0,
            "total_retries": 0,
            "total_failures": 0,
        }

    def record_node_metrics(
        self,
        ctx: RuntimeContext,
        *,
        cpu_ms: float = 0.0,
        ram_mb: float = 0.0,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        api_calls: int = 0,
        bandwidth_bytes: int = 0,
        cache_hit: bool = False,
    ) -> None:
        ctx.metrics.cpu_ms += cpu_ms
        ctx.metrics.ram_mb += ram_mb
        ctx.metrics.tokens_used += tokens_used
        ctx.metrics.cost_usd += cost_usd
        ctx.metrics.api_calls += api_calls
        ctx.metrics.bandwidth_bytes += bandwidth_bytes
        if cache_hit:
            ctx.metrics.cache_hits += 1

    def record_retry(self, ctx: RuntimeContext) -> None:
        ctx.metrics.retries += 1

    def record_failure(self, ctx: RuntimeContext) -> None:
        ctx.metrics.failures += 1

    def record_approval_time(self, ctx: RuntimeContext, duration_ms: float) -> None:
        ctx.metrics.approval_time_ms += duration_ms
        ctx.metrics.human_time_ms += duration_ms

    def collect_and_publish(self, ctx: RuntimeContext) -> dict[str, Any]:
        metrics = ctx.metrics.to_dict()
        self._global_metrics["total_executions"] += 1
        self._global_metrics["total_duration_ms"] += metrics.get("cpu_ms", 0)
        self._global_metrics["total_cost_usd"] += metrics.get("cost_usd", 0)
        self._global_metrics["total_api_calls"] += metrics.get("api_calls", 0)
        self._global_metrics["total_retries"] += metrics.get("retries", 0)
        self._global_metrics["total_failures"] += metrics.get("failures", 0)

        self.publisher.metrics_collected(ctx.execution_id, metrics)
        return metrics

    def get_global_metrics(self) -> dict[str, Any]:
        return dict(self._global_metrics)
