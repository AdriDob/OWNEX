"""Shared factory for OWNEX source-catalog expansion entries.

Keeps the 500+ source catalog dense and consistent: every entry is a real,
publicly-known work platform. ``source_family`` carries the niche
sub-classification (level-2 taxonomy) so the canonical 5-category enum stays
stable while niches remain queryable.

Payment policy fields:
- ``argentina_ok``: source publicly accepts Argentina-based workers OR pays
  via methods reachable from Argentina (crypto/USDC, PayPal, Payoneer,
  Wise, crypto-stablecoins). ``False`` means restricted — pair with
  ``payment_fallback`` metadata in FALLBACK_CHAINS.
- Payment fallback (e.g. private-message negotiation) is tracked in
  ``PAYMENT_FALLBACKS`` (module-level dict) rather than per-entry columns,
  keeping SourceDefinition stable while the agent edits global_sources.
"""

from __future__ import annotations

from typing import Any


def _sd(**kw: Any):
    """Lazy SourceDefinition factory — resolves the dataclass at call time so
    this module imports cleanly even while global_sources is mid-edit."""
    from cores.opportunity.global_sources import SourceDefinition

    return SourceDefinition(**kw)


def src(
    name: str,
    url: str,
    category: Any,
    description: str,
    *,
    type: str = "platform",
    apply_method: str = "profile_only",
    quality: float = 0.6,
    portfolio: bool = False,
    interview: bool = False,
    experience: bool = False,
    assessment: bool = False,
    rate: float | None = None,
    first_work_h: float | None = None,
    payout_days: int | None = None,
    payout_range: str = "varies",
    language: str = "en",
    argentina_ok: bool = True,
    family: str = "",
    tags: list[str] | None = None,
    priority: int = 5,
    account: bool = True,
    verified: str = "2026-11-10",
):
    """Compact SourceDefinition constructor for catalog expansion."""
    return _sd(
        name=name,
        url=url,
        category=category,
        description=description,
        type=type,
        apply_method=apply_method,
        quality_score=quality,
        requires_account=account,
        requires_portfolio=portfolio,
        requires_interview=interview,
        requires_experience=experience,
        requires_assessment=assessment,
        typical_hourly_rate_usd=rate,
        time_to_first_work_hours=first_work_h,
        payout_cadence_days=payout_days,
        estimated_payout_range=payout_range,
        language=language,
        argentina_ok=argentina_ok,
        source_family=family,
        tags=tags or [],
        priority=priority,
        last_verified=verified,
    )
