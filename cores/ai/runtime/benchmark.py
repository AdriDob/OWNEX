"""OAR Benchmark Engine — Automated provider evaluation."""

from __future__ import annotations

import asyncio
import logging
import time

from .interfaces import (
    AIProviderProtocol,
    BenchmarkEngineProtocol,
    BenchmarkResult,
    OARConfig,
    TaskType,
    get_config,
)
from .registry import ProviderRegistry

logger = logging.getLogger("oar.benchmark")


BENCHMARK_PROMPTS: dict[TaskType, list[str]] = {
    TaskType.CHAT: [
        "Explain quantum computing in simple terms.",
        "Write a short story about a robot learning to paint.",
    ],
    TaskType.CODE: [
        "Write a Python function to find the longest palindromic substring.",
        "Create a REST API endpoint with FastAPI for user management.",
    ],
    TaskType.RESEARCH: [
        "Summarize the key differences between transformer architectures.",
        "Compare different vector database options for RAG systems.",
    ],
    TaskType.ANALYSIS: [
        "Analyze this code for security vulnerabilities: [code snippet]",
        "Review this architecture for scalability bottlenecks.",
    ],
    TaskType.REASONING: [
        "Solve this logic puzzle: [puzzle]",
        "Step through this mathematical proof.",
    ],
    TaskType.BUG_BOUNTY: [
        "Identify potential IDOR vulnerabilities in this API design.",
        "Analyze this authentication flow for security issues.",
    ],
    TaskType.SECURITY_ANALYSIS: [
        "Review this code for OWASP Top 10 vulnerabilities.",
        "Analyze this network configuration for misconfigurations.",
    ],
    TaskType.REPORT: [
        "Write a professional bug bounty report for an IDOR finding.",
        "Create an executive summary of a penetration test.",
    ],
}


class BenchmarkEngine(BenchmarkEngineProtocol):
    """Automated benchmarking for provider evaluation."""

    def __init__(
        self,
        registry: ProviderRegistry,
        config: OARConfig | None = None,
    ):
        self._registry = registry
        self._config = config or get_config()
        self._results: dict[str, list[BenchmarkResult]] = {}  # provider_id -> results

    async def benchmark_provider(
        self,
        provider_id: str,
        model_id: str,
        task_types: list[TaskType] | None = None,
    ) -> list[BenchmarkResult]:
        """Run benchmarks for a specific provider/model."""
        provider = self._registry.get_provider(provider_id)
        if not provider:
            logger.warning("Provider %s not found for benchmarking", provider_id)
            return []

        if model_id not in provider.supported_models:
            logger.warning("Model %s not supported by %s", model_id, provider_id)
            return []

        task_types = task_types or [
            TaskType.CHAT,
            TaskType.CODE,
            TaskType.RESEARCH,
            TaskType.ANALYSIS,
            TaskType.REASONING,
        ]

        results = []
        for task_type in task_types:
            prompts = BENCHMARK_PROMPTS.get(task_type, BENCHMARK_PROMPTS[TaskType.CHAT])
            for prompt in prompts:
                result = await self._run_benchmark(provider, model_id, task_type, prompt)
                results.append(result)

        # Store results
        if provider_id not in self._results:
            self._results[provider_id] = []
        self._results[provider_id].extend(results)

        # Keep only recent results (last 100 per provider)
        self._results[provider_id] = self._results[provider_id][-100:]

        return results

    async def _run_benchmark(
        self,
        provider: AIProviderProtocol,
        model_id: str,
        task_type: TaskType,
        prompt: str,
    ) -> BenchmarkResult:
        """Run a single benchmark."""
        from .interfaces import AIRequest

        request = AIRequest(
            messages=[{"role": "user", "content": prompt}],
            task_type=task_type,
            model=model_id,
            max_tokens=1024,
            temperature=0.3,
        )

        start = time.monotonic()
        success = False
        quality = 0.0
        cost = 0.0
        error = None

        try:
            response = await provider.chat(request)
            latency = (time.monotonic() - start) * 1000
            success = bool(response.content)
            cost = response.cost_usd

            # Simple quality heuristic: response length and structure
            if response.content:
                quality = min(1.0, len(response.content) / 500)  # Normalize
                # Bonus for structured responses
                if any(marker in response.content for marker in ["```", "1.", "2.", "- ", "**"]):
                    quality = min(1.0, quality + 0.1)

        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            error = str(e)
            logger.warning("Benchmark failed for %s/%s: %s", provider.provider_id, model_id, e)

        return BenchmarkResult(
            provider_id=provider.provider_id,
            model_id=model_id,
            task_type=task_type,
            success=success,
            latency_ms=latency,
            quality_score=quality,
            cost_usd=cost,
            error=error,
        )

    async def benchmark_all(self, task_types: list[TaskType] | None = None) -> dict[str, list[BenchmarkResult]]:
        """Benchmark all available providers."""
        all_results = {}

        for provider_id, provider in self._registry._providers.items():
            for model_id in provider.supported_models:
                results = await self.benchmark_provider(provider_id, model_id, task_types)
                key = f"{provider_id}:{model_id}"
                all_results[key] = results

                # Small delay between providers to avoid rate limits
                await asyncio.sleep(1)

        return all_results

    def get_rankings(self, task_type: TaskType | None = None) -> list[tuple[str, str, float]]:
        """Get provider rankings by composite score."""
        rankings = []

        for provider_id, results in self._results.items():
            for result in results:
                if task_type and result.task_type != task_type:
                    continue

                # Composite score: quality * 0.5 + speed * 0.3 + cost_efficiency * 0.2
                speed_score = max(0, 1 - result.latency_ms / 10000)  # 10s = 0
                cost_score = 1.0 if result.cost_usd == 0 else max(0, 1 - result.cost_usd / 0.01)

                composite = result.quality_score * 0.5 + speed_score * 0.3 + cost_score * 0.2

                rankings.append((provider_id, result.model_id, composite))

        # Sort by composite score descending
        rankings.sort(key=lambda x: x[2], reverse=True)
        return rankings


# Global benchmark engine instance
_benchmark_engine: BenchmarkEngine | None = None


def get_benchmark_engine(
    registry=None,
    config: OARConfig | None = None,
) -> BenchmarkEngine:
    """Get global benchmark engine."""
    global _benchmark_engine
    if _benchmark_engine is None:
        if registry is None:
            from .registry import get_registry

            registry = get_registry(config)
        _benchmark_engine = BenchmarkEngine(registry, config)
    return _benchmark_engine


async def run_scheduled_benchmarks(
    registry=None,
    config: OARConfig | None = None,
) -> dict[str, list[BenchmarkResult]]:
    """Run scheduled benchmarks for all providers."""
    engine = get_benchmark_engine(registry, config)
    return await engine.benchmark_all()
