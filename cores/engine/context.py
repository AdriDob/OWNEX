"""Context Engine — builds enriched context for AI calls.

Every AI call gets a structured AgentContext with fragments from multiple
sources. No naked prompts. The model receives an expedition, not a message.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.engine.base import Engine
from core.engine.classification import Opportunity

logger = logging.getLogger("ownex.context")


# ── Context types ──────────────────────────────────────────────────


@dataclass
class ContextFragment:
    """A single piece of context from one source."""

    source: str  # "platform_docs", "user_history", "memory", "credentials"
    content: str
    relevance: float = 1.0  # 0.0 to 1.0, for prioritization
    token_estimate: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Full context prepared for an AI call.

    This is what the model actually receives.
    Everything is structured, no naked prompts.
    """

    opportunity: Opportunity
    fragments: list[ContextFragment] = field(default_factory=list)
    system_prompt: str = ""
    built_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_tokens: int = 0
    depth: str = "standard"  # "quick", "standard", "deep"

    def add(self, fragment: ContextFragment) -> None:
        self.fragments.append(fragment)
        self.total_tokens += fragment.token_estimate

    def to_prompt(self) -> str:
        parts = ["# OWNEX Agent Context", ""]
        parts.append(f"## Opportunity: {self.opportunity.name}")
        parts.append(f"- ID: {self.opportunity.id}")
        parts.append(f"- Cycle: {self.opportunity.cycle}")
        parts.append(f"- Source: {self.opportunity.source_type} / {self.opportunity.source_name}")
        parts.append(f"- Estimated Value: ${self.opportunity.estimated_reward_max:.2f}")
        parts.append(f"- Estimated Effort: {self.opportunity.estimated_effort_hours}h")
        parts.append(f"- URL: {self.opportunity.url}")
        parts.append("")

        # Sort fragments by relevance descending
        sorted_fragments = sorted(self.fragments, key=lambda f: f.relevance, reverse=True)
        for frag in sorted_fragments:
            parts.append(f"### [{frag.source}] (relevance: {frag.relevance:.2f})")
            parts.append(frag.content)
            parts.append("")

        return "\n".join(parts)


# ── Context sources ────────────────────────────────────────────────


class ContextSource(ABC):
    """A source of context information."""

    @abstractmethod
    async def fetch(self, opportunity: Opportunity, depth: str = "standard") -> list[ContextFragment]: ...


class MemoryContextSource(ContextSource):
    """Reads from the system's durable memory store."""

    def __init__(self, memory_store: Any | None = None) -> None:
        self.memory_store = memory_store

    async def fetch(self, opportunity: Opportunity, depth: str = "standard") -> list[ContextFragment]:
        # Stub: in production reads from memory/skill store
        fragments: list[ContextFragment] = []
        if self.memory_store:
            try:
                entries = self.memory_store.get_relevant(str(opportunity.id))
                for entry in entries[:5]:
                    fragments.append(
                        ContextFragment(
                            source="memory",
                            content=entry.content,
                            relevance=0.8,
                        )
                    )
            except Exception:
                pass
        return fragments


class SystemContextSource(ContextSource):
    """Provides current system state."""

    def __init__(self, registry: Any | None = None) -> None:
        self.registry = registry

    async def fetch(self, opportunity: Opportunity, depth: str = "standard") -> list[ContextFragment]:
        fragments: list[ContextFragment] = []
        if self.registry:
            try:
                health_data = {}
                for name in ("pipeline_engine", "scheduler", "observation_engine"):
                    eng = self.registry.get(name)
                    if eng:
                        health_data[name] = await eng.health()
                content_lines = ["**System Status:**"]
                for name, h in health_data.items():
                    content_lines.append(f"- {name}: {h.get('status', 'unknown')}")
                fragments.append(
                    ContextFragment(
                        source="system",
                        content="\n".join(content_lines),
                        relevance=0.5,
                        token_estimate=50,
                    )
                )
            except Exception:
                pass
        return fragments


# ── Context Engine ─────────────────────────────────────────────────


class ContextEngine(Engine):
    """Builds structured context around an opportunity for AI models.

    AgentContext → System prompt builder → to LLM
    Reduces token waste and improves response quality.
    """

    name = "context_engine"

    def __init__(self, memory_store: Any | None = None, registry: Any | None = None) -> None:
        super().__init__()
        self.sources: dict[str, ContextSource] = {
            "memory": MemoryContextSource(memory_store),
            "system": SystemContextSource(registry),
        }
        self.registry = registry

    def register_source(self, name: str, source: ContextSource) -> None:
        self.sources[name] = source

    async def build_context(
        self,
        opportunity: Opportunity,
        depth: str = "standard",
        role: str = "analyst",
    ) -> AgentContext:
        """Build a full AgentContext for an opportunity.

        Gathers fragments from all sources, then builds a structured prompt.
        """
        context = AgentContext(opportunity=opportunity, depth=depth)

        # Gather fragments from all sources
        for name, source in self.sources.items():
            try:
                fragments = await source.fetch(opportunity, depth)
                for f in fragments:
                    context.add(f)
            except Exception as e:
                logger.warning("Context source %s failed: %s", name, e)

        # Build system prompt
        context.system_prompt = self._build_system_prompt(context, role)

        return context

    SYSTEM_PROMPTS: dict[str, str] = {
        "analyst": (
            "You are an autonomous work analyst for OWNEX. "
            "Given an opportunity and its context, provide:\n"
            "1. Technical assessment (feasibility, difficulty)\n"
            "2. Value assessment (is this worth doing?)\n"
            "3. Risk assessment (what could go wrong?)\n"
            "4. Recommended approach\n"
        ),
        "planner": (
            "You are an autonomous work planner for OWNEX. "
            "Given an opportunity and context, create a detailed execution plan:\n"
            "1. Steps required (in order)\n"
            "2. Capabilities needed\n"
            "3. Estimated time per step\n"
            "4. Potential blockers\n"
            "5. Fallback strategies\n"
        ),
        "executor": (
            "You are an autonomous executor for OWNEX. "
            "Given an opportunity and execution plan, execute each step:\n"
            "1. Execute step by step\n"
            "2. Report progress after each step\n"
            "3. Log any errors or unexpected results\n"
            "4. Continue until plan is complete or blocked\n"
        ),
        "validator": (
            "You are a validator for OWNEX. "
            "Given an execution result, validate:\n"
            "1. Was the expected outcome achieved?\n"
            "2. Are there side effects or regressions?\n"
            "3. Quality score (0-10)\n"
            "4. Learning points\n"
        ),
    }

    def _build_system_prompt(self, context: AgentContext, role: str = "analyst") -> str:
        base = self.SYSTEM_PROMPTS.get(role, self.SYSTEM_PROMPTS["analyst"])
        return f"{base}\n\n{context.to_prompt()}"

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "sources": list(self.sources.keys()),
            "depth": "standard",
        }
