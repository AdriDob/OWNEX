"""Cycle Registry — declarative registration of Work Cycles.

Allows modules to declare cycles declaratively, similar to Flask blueprints
or FastAPI routers. The registry collects cycle definitions and the
CycleService materializes them in the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.cycles.models import CycleStatus


@dataclass
class CycleDefinition:
    """Declarative definition of a Work Cycle."""

    slug: str
    name: str
    description: str
    category: str = "general"
    priority: int = 0
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    def to_cycle_data(self) -> dict[str, Any]:
        """Convert to Cycle model data dict."""
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "enabled": self.enabled,
            "status": CycleStatus.IDLE.value,
            "config": self.config,
        }


class CycleRegistry:
    """Registry for collecting and managing CycleDefinitions.

    Usage:
        registry = CycleRegistry()
        registry.register(CycleDefinition(slug="security", name="Security", ...))
        registry.register(CycleDefinition(slug="forge", name="Forge", ...))

        # Later, materialize in database:
        service = get_cycle_service()
        for defn in registry.all():
            if not service.get_by_slug(defn.slug):
                service.create(defn.to_cycle_data())
    """

    def __init__(self) -> None:
        self._definitions: dict[str, CycleDefinition] = {}

    def register(self, definition: CycleDefinition) -> None:
        """Register a cycle definition. Raises if slug already exists."""
        if definition.slug in self._definitions:
            raise ValueError(f"Cycle with slug '{definition.slug}' already registered")
        self._definitions[definition.slug] = definition

    def get(self, slug: str) -> CycleDefinition | None:
        return self._definitions.get(slug)

    def all(self) -> list[CycleDefinition]:
        return list(self._definitions.values())

    def by_category(self, category: str) -> list[CycleDefinition]:
        return [d for d in self._definitions.values() if d.category == category]

    def enabled(self) -> list[CycleDefinition]:
        return [d for d in self._definitions.values() if d.enabled]

    def clear(self) -> None:
        self._definitions.clear()


# Global registry instance
_default_registry: CycleRegistry | None = None


def get_cycle_registry() -> CycleRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = CycleRegistry()
        _seed_defaults(_default_registry)
    return _default_registry


def _seed_defaults(registry: CycleRegistry) -> None:
    """Register OWNEX default work cycles."""
    # SECURITY — Bug bounty / vulnerability research
    registry.register(
        CycleDefinition(
            slug="security",
            name="Security",
            description="Bug bounty, vulnerability research, Rastro pipeline",
            category="offensive",
            priority=10,
            config={
                "source_apps": ["rastro", "aegis"],
                "auto_priority": True,
            },
        )
    )

    # FORGE — Dev bounties, OSS contributions
    registry.register(
        CycleDefinition(
            slug="forge",
            name="Forge",
            description="Dev bounties, OSS contributions, code review rewards",
            category="development",
            priority=8,
            config={
                "platforms": ["superteam", "opire", "algora", "issuehunt"],
                "auto_discover": True,
            },
        )
    )

    # PULSE — AI work, microtasks
    registry.register(
        CycleDefinition(
            slug="pulse",
            name="Pulse",
            description="AI training, data annotation, microtask platforms",
            category="ai_work",
            priority=6,
            config={
                "platforms": ["outlier", "dataannotation", "mindrift", "remotasks"],
                "skill_match": True,
            },
        )
    )

    # VAULT — Wealth, investments, finance
    registry.register(
        CycleDefinition(
            slug="vault",
            name="Vault",
            description="Portfolio management, crypto, DeFi, arbitrage, financial analysis",
            category="finance",
            priority=7,
            config={
                "data_sources": ["coingecko", "defillama", "coingecko"],
                "auto_rebalance": False,
            },
        )
    )

    # ATLAS — Research, intelligence, OSINT
    registry.register(
        CycleDefinition(
            slug="atlas",
            name="Atlas",
            description="Research, OSINT, trend analysis, CVE tracking, market intelligence",
            category="intelligence",
            priority=5,
            config={
                "sources": ["cve", "github", "twitter", "rss"],
                "alert_threshold": "high",
            },
        )
    )
