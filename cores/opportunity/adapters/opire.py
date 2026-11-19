"""Opire/Opyre Adapter — OSS issue bounties platform (Forge cycle).

API pública verificada en vivo: GET https://api.opire.dev/rewards (sin auth).
Cada item es un reward sobre un GitHub issue; ``pendingPrice.value`` viene en
centavos USD (``unit: "USD_CENT"``). ``claimerUsers``/``tryingUsers`` vacíos
significan bounty sin competencia — la señal de mayor ROI del ciclo forge.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.opportunity.adapters.opire")

OPIRE_API_BASE = "https://api.opire.dev"

# Umbrales del ciclo pulse: tarea corta y con recompensa que valga el envío.
MAX_MICROTASK_HOURS = 4.0
MIN_MICROTASK_REWARD = 25.0


def _reward_usd(item: dict[str, Any]) -> float:
    """Convert pendingPrice (USD_CENT) to dollars; 0 si ausente o inválido."""
    price = item.get("pendingPrice") or {}
    value = price.get("value")
    if value is None:
        return 0.0
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return 0.0


class OpireAdapter(OpportunityAdapter):
    """Opire.com adapter - OSS issue bounties (Forge cycle)."""

    platform: str = "opire"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opire", config)
        super().__init__(merged_config)
        self.token = self.config.get("token") or self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch active rewards from the public Opire API."""
        try:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(f"{OPIRE_API_BASE}/rewards", headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning("Opire API returned %s", resp.status_code)
                    return []

                data = resp.json()
                rewards = data if isinstance(data, list) else data.get("data", [])

                raw_opps: list[RawOpportunity] = []
                for reward in rewards[:20]:
                    claimers = reward.get("claimerUsers") or []
                    trying = reward.get("tryingUsers") or []
                    languages = [str(lang).lower() for lang in (reward.get("programmingLanguages") or []) if lang]
                    project = reward.get("project") or {}
                    raw_opps.append(
                        RawOpportunity(
                            id=f"opire_{reward.get('id')}",
                            name=reward.get("title") or "Opire Bounty",
                            description=(f"Opire reward on {project.get('name', 'GitHub issue')}: {reward.get('title', '')}"),
                            platform="opire",
                            url=reward.get("url") or "",
                            reward=_reward_usd(reward),
                            effort_hours=float(reward.get("estimatedHours", 6)),
                            tags=["oss", "bounty", *languages],
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="opire",
                            metadata={
                                "original": reward,
                                "claimers": len(claimers),
                                "trying": len(trying),
                                "uncontested": not claimers and not trying,
                            },
                            created_at=str(reward.get("createdAt", "")),
                        )
                    )

                return raw_opps
        except Exception as e:
            logger.warning("OpireAdapter fetch failed: %s", e)
            return []


class OpyreAdapter(OpportunityAdapter):
    """Opyre.com adapter - OSS issue bounties (Forge cycle, alias/alternative to Opire)."""

    platform: str = "opyre"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opyre", config)
        super().__init__(merged_config)
        self.token = self.config.get("token") or self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from the real Opire feed (Opyre era un alias).

        ``api.opyre.com`` y ``api.opire.com`` no resuelven DNS (verificado).
        Se delega en el adapter Opire ya verificado en vivo para no devolver
        listas vacías silenciosas.
        """
        opps = await OpireAdapter(self.config).fetch_opportunities(personal)
        return [
            RawOpportunity(
                id=o.id.replace("opire_", "opyre_", 1),
                name=o.name,
                description=o.description,
                platform="opyre",
                url=o.url,
                reward=o.reward,
                effort_hours=o.effort_hours,
                tags=o.tags,
                cycle="forge",
                source_type="dev_bounty",
                source_name="opyre",
                metadata=o.metadata,
                created_at=o.created_at,
            )
            for o in opps
        ]


class OpyreMicrotaskAdapter(OpportunityAdapter):
    """Opyre micro-tasks / quick fixes adapter (Pulse cycle)."""

    platform: str = "opyre_microtask"
    cycle: str = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("opyre_micro", config)
        super().__init__(merged_config)
        self.token = self.config.get("token") or self.config.get("api_key")

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Derive quick-fix micro-tasks from the real Opire feed.

        ``api.opyre.com`` no resuelve DNS (verificado). En lugar de inventar un
        endpoint, se filtra el feed real de Opire por bajo esfuerzo y sin
        competencia — los mismos criterios que la estrategia de primer ingreso.
        """
        opps = await OpireAdapter(self.config).fetch_opportunities(personal)
        quick = [o for o in opps if o.effort_hours <= MAX_MICROTASK_HOURS and o.reward >= MIN_MICROTASK_REWARD]
        return [
            RawOpportunity(
                id=f"opyre_micro_{o.id.removeprefix('opire_')}",
                name=f"[Quick] {o.name}",
                description=o.description,
                platform="opyre_microtask",
                url=o.url,
                reward=o.reward,
                effort_hours=o.effort_hours,
                tags=["quick-fix", "microtask", *o.tags],
                cycle="pulse",
                source_type="microtask",
                source_name="opyre_microtask",
                metadata=o.metadata,
                created_at=o.created_at,
            )
            for o in quick[:15]
        ]
