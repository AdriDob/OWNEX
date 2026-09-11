"""Opportunity Adapters — framework for connecting external platforms to OWNEX Work Cycles."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cores.opportunity.models import ScoredOpportunity


@dataclass
class RawOpportunity:
    """Raw opportunity data from external platform before OWNEX scoring."""

    id: str
    name: str
    description: str
    platform: str
    url: str | None = None
    reward: float = 0.0
    effort_hours: float = 1.0
    tags: list[str] = field(default_factory=list)
    cycle: str = "security"
    source_type: str = "platform"
    source_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class OpportunityAdapter:
    """Base class for all opportunity adapters."""

    platform: str = "unknown"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch raw opportunities from the platform."""
        raise NotImplementedError(f"{self.platform} adapter not implemented")

    def to_scored(self, raw: RawOpportunity, personal: Any | None = None) -> ScoredOpportunity:
        """Convert raw opportunity to scored OWNEX opportunity."""
        from cores.opportunity.scorer import score_opportunity

        return score_opportunity(
            opp_id=raw.id,
            name=raw.name,
            cycle=raw.cycle,
            source_type=raw.source_type,
            source_name=raw.source_name or self.platform,
            reward=raw.reward,
            effort_hours=raw.effort_hours,
            platform=raw.platform,
            technology_tags=raw.tags,
            url=raw.url,
            created_at=raw.created_at,
            personal=raw.metadata.get("personal"),
            original=raw.metadata.get("original"),
        )

    def is_enabled(self) -> bool:
        return self.enabled

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


class AdapterRegistry:
    """Registry for opportunity adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, type[OpportunityAdapter]] = {}

    def register(self, platform: str, adapter_class: type[OpportunityAdapter]) -> None:
        self._adapters[platform.lower()] = adapter_class

    def get(self, platform: str) -> type[OpportunityAdapter] | None:
        return self._adapters.get(platform.lower())

    def all(self) -> dict[str, type[OpportunityAdapter]]:
        return self._adapters.copy()

    def enabled(self) -> dict[str, type[OpportunityAdapter]]:
        return {k: v for k, v in self._adapters.items() if v({}).enabled}


_adapter_registry: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _adapter_registry
    if _adapter_registry is None:
        _adapter_registry = AdapterRegistry()
        _seed_defaults(_adapter_registry)
    return _adapter_registry


def _seed_defaults(registry: AdapterRegistry) -> None:
    """Register built-in adapters (lazy import to avoid circular deps)."""
    # Security adapters (Rastro)
    # NOTE: cores/opportunity/adapters/security.py (legacy SecurityAdapter/
    # AegisAdapter) is shadowed by the security/ package of the same name, so
    # it is loaded from its file path explicitly instead of by module import.
    try:
        import importlib.util
        from pathlib import Path

        _legacy_path = Path(__file__).with_name("security.py")
        _spec = importlib.util.spec_from_file_location("cores.opportunity.adapters.security_legacy", _legacy_path)
        if _spec is not None and _spec.loader is not None:
            _legacy_mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_legacy_mod)
            registry.register("rastro", _legacy_mod.SecurityAdapter)
            registry.register("aegis", _legacy_mod.AegisAdapter)
    except (ImportError, AttributeError, OSError):
        pass

    # Forge adapters (Dev Bounty)
    try:
        from cores.opportunity.adapters.forge import (
            AlgoraAdapter,
            ForgeAdapter,
            OpireAdapter,
            SuperteamAdapter,
        )

        registry.register("superteam", SuperteamAdapter)
        registry.register("opire", OpireAdapter)
        registry.register("algora", AlgoraAdapter)
        registry.register("forge", ForgeAdapter)
    except ImportError:
        pass

    # IssueHunt
    try:
        from cores.opportunity.adapters.issuehunt import IssueHandAdapter, IssueHuntAdapter

        registry.register("issuehunt", IssueHuntAdapter)
        registry.register("issuehand", IssueHandAdapter)
    except ImportError:
        pass

    # Opire/Opyre
    try:
        from cores.opportunity.adapters.opire import OpireAdapter as OpireAdapterNew
        from cores.opportunity.adapters.opire import OpyreAdapter

        registry.register("opire", OpireAdapterNew)
        registry.register("opyre", OpyreAdapter)
    except ImportError:
        pass

    # LinkedIn
    try:
        from cores.opportunity.adapters.linkedin import LinkedInEasyApplyAdapter, LinkedInJobsAdapter

        registry.register("linkedin", LinkedInJobsAdapter)
        registry.register("linkedin_easyapply", LinkedInEasyApplyAdapter)
    except ImportError:
        pass

    # Freelancer
    try:
        from cores.opportunity.adapters.freelancer import (
            FreelancerAdapter,
            FreelancerMicrotaskAdapter,
        )

        registry.register("freelancer", FreelancerAdapter)
        registry.register("freelancer_microtask", FreelancerMicrotaskAdapter)
    except ImportError:
        pass

    # AR job boards (read-only discovery, manual apply — backup income)
    try:
        from cores.opportunity.adapters.ar_jobs import (
            BumeranAdapter,
            ComputrabajoAdapter,
            ZonaJobsAdapter,
        )

        registry.register("zonajobs", ZonaJobsAdapter)
        registry.register("bumeran", BumeranAdapter)
        registry.register("computrabajo", ComputrabajoAdapter)
    except ImportError:
        pass

    # Microtask marketplaces (keyed live fetch or curated fallback, manual apply)
    try:
        from cores.opportunity.adapters.microtask import (
            ClickworkerAdapter,
            ProlificAdapter,
            TolokaAdapter,
        )

        registry.register("toloka", TolokaAdapter)
        registry.register("prolific", ProlificAdapter)
        registry.register("clickworker", ClickworkerAdapter)
    except ImportError:
        pass

    # OpenCollective
    try:
        from cores.opportunity.adapters.opencollective import (
            OpenCollectiveAdapter,
            OpenCollectiveProjectsAdapter,
        )

        registry.register("opencollective", OpenCollectiveAdapter)
        registry.register("opencollective_projects", OpenCollectiveProjectsAdapter)
    except ImportError:
        pass

    # Pulse adapters
    try:
        from cores.opportunity.adapters.pulse import (
            DataAnnotationAdapter,
            FreelancerMicrotaskAdapter,
            LinkedInEasyApplyAdapter,
            MindriftAdapter,
            OpyreMicrotaskAdapter,
            OutlierAdapter,
            RemotasksAdapter,
        )

        registry.register("outlier", OutlierAdapter)
        registry.register("dataannotation", DataAnnotationAdapter)
        registry.register("mindrift", MindriftAdapter)
        registry.register("remotasks", RemotasksAdapter)
        registry.register("freelancer_microtask", FreelancerMicrotaskAdapter)
        registry.register("linkedin_easyapply", LinkedInEasyApplyAdapter)
        registry.register("opyre_microtask", OpyreMicrotaskAdapter)
    except ImportError:
        pass

    # Vault adapters
    try:
        from cores.opportunity.adapters.vault import (
            BinanceAdapter,
            CoinGeckoAdapter,
            DefiLlamaAdapter,
            FireflyAdapter,
        )

        registry.register("coingecko", CoinGeckoAdapter)
        registry.register("firefly", FireflyAdapter)
        registry.register("binance", BinanceAdapter)
        registry.register("defillama", DefiLlamaAdapter)
    except ImportError:
        pass

    # Atlas adapters
    try:
        from cores.opportunity.adapters.atlas import AtlasAdapter

        registry.register("cve", AtlasAdapter)
        registry.register("osint", AtlasAdapter)
    except ImportError:
        pass

    # Security adapters (Bug Bounty platforms)
    try:
        from cores.opportunity.adapters.security import (
            BugcrowdAdapter,
            Code4renaAdapter,
            HackerOneAdapter,
            ImmunefiAdapter,
            IntigritiAdapter,
            SherlockAdapter,
            SynackAdapter,
            YesWeHackAdapter,
        )

        registry.register("hackerone", HackerOneAdapter)
        registry.register("bugcrowd", BugcrowdAdapter)
        registry.register("intigriti", IntigritiAdapter)
        registry.register("yeswehack", YesWeHackAdapter)
        registry.register("immunefi", ImmunefiAdapter)
        registry.register("synack", SynackAdapter)
        registry.register("sherlock", SherlockAdapter)
        registry.register("code4rena", Code4renaAdapter)
    except ImportError:
        pass


def get_adapters() -> dict[str, OpportunityAdapter]:
    """Get adapter instances for all enabled adapters."""
    registry = get_adapter_registry()
    adapters = {}

    for platform, adapter_class in registry.enabled().items():
        try:
            adapters[platform] = adapter_class(config={"enabled": True})
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("Failed to instantiate adapter %s: %s", platform, e)

    return adapters


async def fetch_all_opportunities(
    personal: Any | None = None,
    enabled_only: bool = True,
) -> list[ScoredOpportunity]:
    """Fetch opportunities from all enabled adapters."""
    from cores.opportunity.models import ScoredOpportunity

    registry = get_adapter_registry()
    all_opportunities: list[ScoredOpportunity] = []

    items = registry.enabled() if enabled_only else registry.all()
    for platform, adapter_class in items.items():
        try:
            adapter = adapter_class(config={"enabled": True})
            if not adapter.is_enabled():
                continue
            raw_opps = await adapter.fetch_opportunities()
            scored = [adapter.to_scored(raw) for raw in raw_opps]
            all_opportunities.extend(scored)
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("Adapter %s failed: %s", platform, e)

    return all_opportunities


__all__ = [
    "RawOpportunity",
    "OpportunityAdapter",
    "AdapterRegistry",
    "get_adapter_registry",
    "get_adapters",
    "fetch_all_opportunities",
    "ScoredOpportunity",
]
