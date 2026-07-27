"""Security Cycle Adapter — Rastro / Aegis integration.

Maps existing CATEYE bug bounty pipeline to Security Work Cycle.
"""

from __future__ import annotations

from typing import Any

from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class SecurityBaseAdapter(OpportunityAdapter):
    """Base adapter for Security platforms."""

    platform: str = "security"
    cycle: str = "security"


class SecurityAdapter(SecurityBaseAdapter):
    """Adapter for Rastro/Aegis security opportunities.

    Maps existing CATEYE bug bounty findings and pipeline to Security Work Cycle.
    """

    platform: str = "rastro"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch opportunities from Rastro pipeline."""
        try:
            from core.database.manager import get_db_manager
            from core.opportunity import get_engine

            engine = get_engine()
            opportunities = engine.get_all()

            if not opportunities:
                mgr = get_db_manager()
                if "orion" in mgr.list_databases():
                    engine.discover_all()
                    opportunities = engine.get_all()

            raw_opps: list[RawOpportunity] = []
            for opp in opportunities:
                raw_opps.append(
                    RawOpportunity(
                        id=f"rastro_{opp.id}",
                        name=opp.name,
                        description=opp.description or opp.name,
                        platform="rastro",
                        url=opp.public_url,
                        reward=float(opp.estimated_payout or 0),
                        effort_hours=float(opp.estimated_effort_hours or 1.0),
                        tags=list(opp.technology_tags),
                        cycle="security",
                        source_type="platform",
                        source_name=opp.source.name if opp.source else "rastro",
                        metadata={"original": opp, "personal": None},
                        created_at=opp.created_at.isoformat() if opp.created_at else None,
                    )
                )

            return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("SecurityAdapter fetch failed: %s", e)
            return []


class AegisAdapter(SecurityBaseAdapter):
    """Adapter for Aegis pentesting findings."""

    platform: str = "aegis"

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Aegis findings as opportunities."""
        try:
            from core.database.manager import get_db_manager

            mgr = get_db_manager()
            if "aegis" not in mgr.list_databases():
                return []

            session = mgr.get_session("aegis")
            try:
                findings = session.execute(
                    "SELECT * FROM aegis_vuln_findings WHERE status = 'open' LIMIT 50"
                ).fetchall()

                raw_opps: list[RawOpportunity] = []
                for row in findings:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"aegis_{row.id}",
                            name=row.title or f"Finding {row.id}",
                            description=row.description or "",
                            platform="aegis",
                            url=None,
                            reward=0.0,
                            effort_hours=2.0,
                            tags=[row.vuln_type] if row.vuln_type else ["finding"],
                            cycle="security",
                            source_type="finding",
                            source_name="aegis",
                            metadata={"original": dict(row._mapping)},
                            created_at=row.created_at.isoformat()
                            if hasattr(row, "created_at") and row.created_at
                            else None,
                        )
                    )

                return raw_opps
            finally:
                session.close()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("AegisAdapter fetch failed: %s", e)
            return []
