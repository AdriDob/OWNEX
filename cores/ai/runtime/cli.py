"""OAR CLI — Diagnostics and management commands."""

from __future__ import annotations

import asyncio
import json

import click

from . import initialize_oar


@click.group()
def cli():
    """OWNEX AI Runtime (OAR) - AI Provider Operating System."""
    pass


@cli.command()
@click.option("--json-output", is_flag=True, help="Output as JSON")
def doctor(json_output: bool):
    """Run comprehensive OAR diagnostics."""

    async def run_doctor():
        oar = await initialize_oar()
        result = oar.doctor()

        if json_output:
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo("=" * 50)
            click.echo("OWNEX AI Runtime (OAR) - Doctor Report")
            click.echo("=" * 50)
            click.echo(f"Overall Status: {result.get('overall', 'unknown').upper()}")
            click.echo()

            providers = result.get("providers", {})
            click.echo(f"Providers: {providers.get('total', 0)} total")
            click.echo(f"  ✓ Healthy: {len(providers.get('healthy', []))}")
            click.echo(f"  ⚠ Degraded: {len(providers.get('degraded', []))}")
            click.echo(f"  ✗ Unhealthy: {len(providers.get('unhealthy', []))}")
            click.echo()

            if providers.get("healthy"):
                click.echo("Healthy: " + ", ".join(providers["healthy"]))
            if providers.get("degraded"):
                click.echo("Degraded: " + ", ".join(providers["degraded"]))
            if providers.get("unhealthy"):
                click.echo("Unhealthy: " + ", ".join(providers["unhealthy"]))
            click.echo()

            # Health details
            health = result.get("health_details", {})
            if health:
                click.echo("Health Details:")
                for pid, h in health.items():
                    click.echo(f"  {pid}: {h.status.value} ({h.latency_ms:.0f}ms, err={h.error_rate:.1%})")
                click.echo()

            # Cost budget
            budget = result.get("cost_budget", {})
            if budget:
                click.echo("Cost Budget:")
                click.echo(f"  Daily Budget: ${budget.get('daily_budget_usd', 0):.2f}")
                click.echo(f"  Daily Spent: ${budget.get('daily_spent_usd', 0):.4f}")
                click.echo(f"  Remaining: ${budget.get('daily_remaining_usd', 0):.2f}")
                click.echo(f"  Total: ${budget.get('total_cost_usd', 0):.4f}")
                click.echo()

            # Cache stats
            cache = result.get("cache_stats", {})
            if cache:
                click.echo("Cache:")
                click.echo(f"  Entries: {cache.get('entries', 0)}")
                click.echo(f"  Hit Rate: {cache.get('hit_rate', 0):.1%}")
                click.echo()

            # Circuit breakers
            breakers = result.get("circuit_breakers", {})
            if breakers:
                open_breakers = [k for k, v in breakers.items() if v]
                if open_breakers:
                    click.echo("Open Circuit Breakers:")
                    for b in open_breakers:
                        click.echo(f"  ⚠ {b}")

    asyncio.run(run_doctor())


@cli.command()
@click.option("--provider", help="Specific provider to check")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def status(provider: str | None, json_output: bool):
    """Show OAR status."""

    async def run_status():
        oar = await initialize_oar()
        result = oar.status()

        if provider and "providers" in result:
            result["providers"] = [p for p in result["providers"] if p.get("provider_id") == provider]

        if json_output:
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo("OAR Status")
            click.echo("-" * 30)
            click.echo(f"Initialized: {result.get('initialized', False)}")
            click.echo(f"Providers: {len(result.get('providers', []))}")

            for p in result.get("providers", []):
                click.echo(f"  {p.get('provider_id')}: {p.get('name')} - {p.get('health')}")

    asyncio.run(run_status())


# ruff: noqa: E402
from .interfaces import TaskType


@cli.command()
@click.argument("prompt")
@click.option(
    "--task",
    type=click.Choice([t.value for t in TaskType]),
    default="chat",
)
@click.option("--provider", help="Force specific provider")
@click.option("--model", help="Force specific model")
@click.option("--stream", is_flag=True, help="Stream response")
def ask(prompt: str, task: str, provider: str | None, model: str | None, stream: bool):

    async def run_ask():
        oar = await initialize_oar()

        if stream:
            async for chunk in oar.stream(prompt, task_type=TaskType(task), provider=provider, model=model):
                click.echo(chunk, nl=False)
            click.echo()
        else:
            response = await oar.chat(prompt, TaskType(task), provider=provider, model=model)
            click.echo(response.content)
            click.echo()
            click.echo(
                f"[Provider: {response.provider_id}/{response.model_id}, "
                f"Latency: {response.latency_ms:.0f}ms, Cost: ${response.cost_usd:.6f}]"
            )

    asyncio.run(run_ask())


@cli.command()
@click.option(
    "--task",
    type=click.Choice([t.value for t in TaskType]),
    default="chat",
)
def benchmark(task: str):
    """Run benchmarks for all providers."""
    from .benchmark import get_benchmark_engine
    from .interfaces import TaskType
    from .registry import get_registry

    async def run_benchmark():
        await initialize_oar()
        registry = get_registry()
        engine = get_benchmark_engine(registry)

        click.echo(f"Running benchmarks for task: {task}...")
        results = await engine.benchmark_all([TaskType(task)])

        for key, res_list in results.items():
            if res_list:
                avg_latency = sum(r.latency_ms for r in res_list) / len(res_list)
                avg_quality = sum(r.quality_score for r in res_list) / len(res_list)
                success_rate = sum(1 for r in res_list if r.success) / len(res_list)
                click.echo(
                    f"  {key}: success={success_rate:.0%}, latency={avg_latency:.0f}ms, quality={avg_quality:.2f}"
                )

        rankings = engine.get_rankings(TaskType(task))
        click.echo("\nTop Rankings:")
        for i, (pid, mid, score) in enumerate(rankings[:5]):
            click.echo(f"  {i + 1}. {pid}/{mid}: {score:.3f}")

    asyncio.run(run_benchmark())


@cli.command()
@click.option("--days", default=30, help="Learning window in days")
def learn(days: int):
    """Show learned routing preferences."""
    from .interfaces import TaskType
    from .learning import get_learning_engine

    async def run_learn():
        await initialize_oar()
        learning = get_learning_engine()

        click.echo(f"Learned Preferences (last {days} days)")
        click.echo("-" * 40)

        for tt in TaskType:
            prefs = learning.get_preferences(tt)
            if prefs:
                click.echo(f"\n{tt.value}:")
                for provider, score in sorted(prefs.items(), key=lambda x: x[1], reverse=True)[:5]:
                    click.echo(f"  {provider}: {score:.3f}")

    asyncio.run(run_learn())


@cli.command()
def providers():
    """List all available providers and models."""
    from .registry import get_registry

    async def run_providers():
        await initialize_oar()
        registry = get_registry()

        click.echo("Available Providers & Models")
        click.echo("=" * 50)

        for p in registry.list_providers():
            click.echo(f"\n{p['provider_id']} ({p['name']}) - {p['health']}")
            for model in p["models"]:
                caps = registry.get_model_capabilities(model)
                cap_str = ", ".join(caps.supports) if caps else "unknown"
                click.echo(f"  - {model} [{cap_str}]")

    asyncio.run(run_providers())


if __name__ == "__main__":
    cli()
