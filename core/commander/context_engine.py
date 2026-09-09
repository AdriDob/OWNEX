"""Shared Context Engine for the Commander.

Builds a unified context from all available sources before any action
is taken. Used by the Copilot, the Commander, and any agent.

Sources combined:
  - Provider health (ProviderMonitor)
  - Agent registry status
  - Capability availability
  - Memory (short-term and long-term)
  - Evidence Graph
  - Knowledge Graph
  - Decision Journal
  - System state (pipeline, agents, findings, opportunities)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.ai.model_router import get_model_router
from core.ai_router.failover import get_failover_engine
from core.commander.audit import get_audit_logger
from core.copilot.providers.router import get_provider_router

logger = logging.getLogger("orion.commander.context")


@dataclass
class ContextBlock:
    """A block of context from a specific source."""

    source: str
    data: dict[str, Any]
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


@dataclass
class UnifiedContext:
    """Unified context built from all available sources."""

    session_id: str
    blocks: dict[str, ContextBlock] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    health_status: str = "unknown"
    active_provider: str = ""
    active_model: str = ""
    available_agents: list[str] = field(default_factory=list)
    available_capabilities: list[str] = field(default_factory=list)
    decision_history_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def get_block(self, source: str) -> ContextBlock | None:
        return self.blocks.get(source)

    def add_block(self, block: ContextBlock) -> None:
        self.blocks[block.source] = block

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "health_status": self.health_status,
            "active_provider": self.active_provider,
            "active_model": self.active_model,
            "available_agents": self.available_agents,
            "available_capabilities": self.available_capabilities,
            "decision_history_summary": self.decision_history_summary,
            "blocks": {k: v.to_dict() for k, v in self.blocks.items()},
            "summary": self.summary,
            "timestamp": self.timestamp,
        }

    def get_prompt_context(self, max_block_size: int = 2000) -> str:
        """Return context formatted as a prompt for LLM consumption."""
        lines = []

        # System status
        lines.append("## SYSTEM STATUS")
        lines.append(f"Health: {self.health_status}")
        if self.active_provider:
            lines.append(f"Active Provider: {self.active_provider}")
        if self.active_model:
            lines.append(f"Active Model: {self.active_model}")
        lines.append("")

        # Provider status
        if "providers" in self.blocks:
            lines.append("## PROVIDERS")
            prov_data = self.blocks["providers"].data
            overall = prov_data.get("overall", "unknown")
            healthy = prov_data.get("healthy_count", 0)
            total = prov_data.get("total_count", 0)
            lines.append(f"Overall: {overall} ({healthy}/{total} healthy)")
            providers = prov_data.get("providers", {})
            for name, info in providers.items():
                if isinstance(info, dict):
                    state = info.get("state", "unknown")
                    models = info.get("models_count", 0)
                    lines.append(f"  - {name}: {state} ({models} models)")
                else:
                    lines.append(f"  - {name}: {info}")
            lines.append("")

        # Available agents
        if self.available_agents:
            lines.append("## AVAILABLE AGENTS")
            for agent in self.available_agents[:10]:
                lines.append(f"  - {agent}")
            lines.append("")

        # Available capabilities
        if self.available_capabilities:
            lines.append("## AVAILABLE CAPABILITIES")
            for cap in self.available_capabilities[:15]:
                lines.append(f"  - {cap}")
            lines.append("")

        # Decision summary
        if self.decision_history_summary:
            lines.append("## RECENT DECISIONS")
            ds = self.decision_history_summary
            lines.append(f"  Total: {ds.get('total', 0)}, Successes: {ds.get('successful', 0)}")
            lines.append("")

        return "\n".join(lines)


class ContextEngine:
    """Builds unified context from all OWNEX subsystems."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self._audit_logger = get_audit_logger()

    async def build_context_async(self) -> UnifiedContext:
        """Build complete unified context asynchronously."""
        ctx = UnifiedContext(session_id=self.session_id)

        # 1. Provider health
        ctx.add_block(await self._build_provider_block_async())

        # 2. Model router status
        ctx.add_block(self._build_model_router_block())

        # 3. AI router / failover
        ctx.add_block(self._build_failover_block())

        # 4. Provider router (Copilot)
        ctx.add_block(self._build_copilot_router_block())

        # 5. Decision journal summary
        ctx.add_block(self._build_decision_block())

        # 6. System state (pipeline, agents, findings, opportunities)
        ctx.add_block(await self._build_system_context_block_async())

        # Derive summary fields
        ctx.health_status = self._derive_health_status(ctx)
        ctx.active_provider = self._derive_active_provider(ctx)
        ctx.active_model = self._derive_active_model(ctx)

        return ctx

    async def _build_provider_block_async(self) -> ContextBlock:
        """Build block from ProviderMonitor (async version)."""
        try:
            from core.orion.health.provider_monitor import get_provider_monitor

            monitor = get_provider_monitor()
            report = await monitor.check_all()

            providers_data = {}
            for name, prov in report.providers.items():
                providers_data[name] = {
                    "state": prov.state.value,
                    "models_count": prov.models_count,
                    "latency_ms": round(prov.latency_ms, 1),
                    "last_error": prov.last_error,
                    "endpoint": prov.endpoint,
                }

            return ContextBlock(
                source="providers",
                data={
                    "overall": report.overall.value,
                    "healthy_count": report.healthy_count,
                    "total_count": report.total_count,
                    "providers": providers_data,
                },
            )
        except Exception as e:
            logger.warning("Failed to build provider block: %s", e)
            return ContextBlock(source="providers", data={"error": str(e)})

    def _build_model_router_block(self) -> ContextBlock:
        """Build block from ModelRouter."""
        try:
            router = get_model_router()
            tier_summary = router.get_tier_summary()
            available = router.get_available_models()

            return ContextBlock(
                source="model_router",
                data={
                    "tiers": {k: v for k, v in tier_summary.items()},
                    "available_models": available[:20],
                    "total_profiles": len(router._profiles),
                },
            )
        except Exception as e:
            logger.warning("Failed to build model router block: %s", e)
            return ContextBlock(source="model_router", data={"error": str(e)})

    def _build_failover_block(self) -> ContextBlock:
        """Build block from FailoverEngine."""
        try:
            fe = get_failover_engine()
            return ContextBlock(
                source="failover",
                data={
                    "chain": fe.failover_chain,
                    "history_count": len(fe._history),
                    "last_switches": fe.get_history(limit=5),
                },
            )
        except Exception as e:
            logger.warning("Failed to build failover block: %s", e)
            return ContextBlock(source="failover", data={"error": str(e)})

    def _build_copilot_router_block(self) -> ContextBlock:
        """Build block from Copilot ProviderRouter."""
        try:
            prov_router = get_provider_router()
            providers_data = {
                p.name: {
                    "priority": p._config.priority if hasattr(p, "_config") else 0,
                    "models": p._config.models if hasattr(p, "_config") else [],
                }
                for p in prov_router.providers
            }

            return ContextBlock(
                source="copilot_router",
                data={"providers": providers_data, "count": len(prov_router.providers)},
            )
        except Exception as e:
            logger.warning("Failed to build copilot router block: %s", e)
            return ContextBlock(source="copilot_router", data={"error": str(e)})

    async def _build_system_context_block_async(self) -> ContextBlock:
        """Build block from system state (pipeline, agents, findings, opportunities)."""
        try:
            from cores.ai.context.engine import get_orion_context

            ctx_data = get_orion_context(force_refresh=False)
            counts = ctx_data.get("counts", {})
            pipeline = ctx_data.get("pipeline", {})

            return ContextBlock(
                source="system_context",
                data={
                    "counts": counts,
                    "pipeline": pipeline,
                    "earnings": ctx_data.get("earnings", {}),
                    "opportunities": ctx_data.get("top_opportunities", []),
                    "next_action": ctx_data.get("next_action", {}),
                },
            )
        except Exception as e:
            logger.warning("Failed to build system context block: %s", e)
            return ContextBlock(source="system_context", data={"error": str(e)})

    def _build_decision_block(self) -> ContextBlock:
        """Build block from Decision Journal."""
        try:
            audit_logger = get_audit_logger()
            summary = audit_logger.get_session_summary(self.session_id)
            recent = audit_logger.get_entries(limit=5, session_id=self.session_id)

            return ContextBlock(
                source="decisions",
                data={
                    "summary": summary,
                    "recent_entries": recent,
                },
            )
        except Exception as e:
            logger.warning("Failed to build decision block: %s", e)
            return ContextBlock(source="decisions", data={"error": str(e)})

    def _derive_health_status(self, ctx: UnifiedContext) -> str:
        """Derive overall health status from all blocks."""
        provider_block = ctx.get_block("providers")
        if provider_block and "overall" in provider_block.data:
            return provider_block.data["overall"]
        return "unknown"

    def _derive_active_provider(self, ctx: UnifiedContext) -> str:
        """Derive the currently active provider."""
        failover_block = ctx.get_block("failover")
        if failover_block and "chain" in failover_block.data:
            chain = failover_block.data["chain"]
            if chain:
                return chain[0]
        return ""

    def _derive_active_model(self, ctx: UnifiedContext) -> str:
        """Derive the currently active model."""
        model_block = ctx.get_block("model_router")
        if model_block and "available_models" in model_block.data:
            models = model_block.data["available_models"]
            if models:
                return models[0]
        return ""

    async def get_prompt_for_task_async(self, task_description: str, task_type: str = "chat") -> str:
        """Build a prompt-ready context string for a given task (async)."""
        ctx = await self.build_context_async()
        return ctx.get_prompt_context()

    def get_prompt_for_task(self, task_description: str, task_type: str = "chat") -> str:
        """Build a prompt-ready context string for a given task (sync wrapper)."""
        try:
            return asyncio.get_event_loop().run_until_complete(
                self.get_prompt_for_task_async(task_description, task_type)
            )
        except RuntimeError:
            return asyncio.run(self.get_prompt_for_task_async(task_description, task_type))


_context_engine: ContextEngine | None = None


def get_context_engine(session_id: str = "default") -> ContextEngine:
    """Get or create a ContextEngine singleton."""
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine(session_id=session_id)
    return _context_engine


async def build_context_async(session_id: str = "default") -> UnifiedContext:
    """Build and return unified context (async)."""
    engine = get_context_engine(session_id)
    return await engine.build_context_async()


def build_context(session_id: str = "default") -> UnifiedContext:
    """Build and return unified context (sync wrapper)."""
    engine = get_context_engine(session_id)
    try:
        return asyncio.get_event_loop().run_until_complete(engine.build_context_async())
    except RuntimeError:
        return asyncio.run(engine.build_context_async())


async def get_prompt_context_async(task_description: str = "", task_type: str = "chat") -> str:
    """Build prompt-ready context (async)."""
    engine = get_context_engine()
    return await engine.get_prompt_for_task_async(task_description, task_type)


def get_prompt_context(task_description: str = "", task_type: str = "chat") -> str:
    """Build prompt-ready context (sync wrapper)."""
    engine = get_context_engine()
    return engine.get_prompt_for_task(task_description, task_type)


def log_context_to_audit(objective: str, result: str, context: UnifiedContext | None = None) -> None:
    """Log a context-built action to the audit log."""
    audit_logger = get_audit_logger()
    ctx_data = context.to_dict() if context else {}
    audit_logger.log(
        objective=objective,
        reasoning=f"Context-based action using {len(ctx_data.get('blocks', {}))} context blocks",
        tools_used=["context_engine"],
        changes_made=[],
        validation="context_built",
        result=result,
        provider_used=ctx_data.get("active_provider", "unknown"),
        model_used=ctx_data.get("active_model", "unknown"),
        agent_id="commander",
        success=result == "completed",
    )
