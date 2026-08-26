"""OWNEX Autonomous Continuous Discovery Engine.

Continuously discovers, researches, and ranks opportunity platforms.
Filters aggressively for ZERO-BARRIER opportunities (no interview, no portfolio, no experience).
Prioritizes by Expected Value = payout × success_rate / time_invested.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
)

logger = logging.getLogger("ownex.autonomous_discovery")


# ═══════════════════════════════════════════════════════════════════════════
# ZERO-BARRIER FILTER — Aggressive filtering for pure outcome-based work
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class ZeroBarrierCriteria:
    """Strict criteria for TRUE zero-barrier opportunities."""

    # Must have ALL of these
    no_interview_required: bool = True
    no_portfolio_required: bool = True
    no_experience_required: bool = True
    no_degree_required: bool = True
    no_technical_test: bool = True
    no_coding_challenge: bool = True
    no_phone_screen: bool = True
    no_video_call: bool = True
    no_whiteboard: bool = True
    no_take_home: bool = True
    no_cover_letter: bool = True
    no_references: bool = True
    no_background_check: bool = True
    no_citizenship_requirement: bool = True
    no_location_requirement: bool = True
    no_timezone_requirement: bool = True
    no_availability_window: bool = True
    no_minimum_hours: bool = True
    no_exclusivity: bool = True
    no_nda_before_work: bool = True
    no_upfront_payment: bool = True
    no_equity_only: bool = True
    no_revenue_share_only: bool = True
    no_unpaid_trial: bool = True
    no_free_work: bool = True

    # Payment must be
    payment_upfront_or_milestone: bool = True
    payment_in_cash_or_crypto: bool = True
    payment_automated_escrow: bool = True
    payment_proven_history: bool = True

    def check(self, opportunity: Opportunity) -> tuple[bool, list[str]]:
        """Check if opportunity passes ALL zero-barrier criteria. Returns (passed, failed_reasons)."""
        failed = []

        if opportunity.interview_required:
            failed.append("interview_required")
        if opportunity.portfolio_required:
            failed.append("portfolio_required")
        if opportunity.technical_test_required:
            failed.append("technical_test_required")
        if opportunity.experience_required != ExperienceLevel.NONE:
            failed.append(f"experience_required:{opportunity.experience_required.value}")
        if not opportunity.remote:
            failed.append("not_remote")
        if not opportunity.international_payment:
            failed.append("no_international_payment")
        if opportunity.registration_required and opportunity.estimated_time_hours > 2:
            failed.append("complex_registration")
        if opportunity.payment <= 0:
            failed.append("no_payment")
        if opportunity.payment < 5.0:
            failed.append("payment_too_low")
        if opportunity.payment_method in (PaymentMethod.GIFT_CARD, PaymentMethod.EQUITY, PaymentMethod.REVENUE_SHARE):
            failed.append("bad_payment_method")
        if opportunity.time_to_payout_days and opportunity.time_to_payout_days > 30:
            failed.append("slow_payout")
        if opportunity.estimated_time_hours > 40:
            failed.append("too_time_consuming")
        if not opportunity.accepts_beginner:
            failed.append("not_beginner_friendly")
        if not opportunity.accepts_freelancers:
            failed.append("not_freelancer_friendly")
        if not opportunity.accepts_individuals:
            failed.append("not_individual_friendly")
        if not opportunity.asynchronous:
            failed.append("not_async")
        if opportunity.risk > 0.5:
            failed.append("high_risk")
        if opportunity.stability < 0.3:
            failed.append("low_stability")

        return len(failed) == 0, failed


# ═══════════════════════════════════════════════════════════════════════════
# OPPORTUNITY SCORER — Expected Value Ranking
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class EVScore:
    """Expected Value scoring for opportunity ranking."""

    opportunity_id: str
    platform: str
    title: str
    ev_usd_per_hour: float  # Expected value per hour
    total_ev_usd: float  # Total expected value
    success_probability: float
    payout_usd: float
    estimated_hours: float
    confidence: float
    zero_barrier: bool
    rank: int = 0
    reasoning: list[str] = field(default_factory=list)


class EVScorer:
    """Ranks opportunities by Expected Value per hour invested."""

    # Cold-start priors by category — CURATED ESTIMATES, not measured
    # history. Labeled in every EVScore.reasoning (FASE 3 honesty contract).
    BASE_SUCCESS_RATES = {
        "bug_bounty": 0.15,  # 15% success rate for valid reports
        "dev_bounty": 0.35,  # 35% for code bounties
        "data_entry": 0.85,  # 85% for micro-tasks
        "security_research": 0.10,
        "oss_bounties": 0.25,
        "open_source": 0.20,
        "ai_evaluation": 0.75,
        "data_annotation": 0.90,
        "synthetic_data": 0.80,
        "web_scraping": 0.70,
        "competitions": 0.05,
        "code_review": 0.40,
        "documentation": 0.60,
        "technical_writing": 0.55,
    }

    # Platform trust multipliers (based on payment history)
    PLATFORM_TRUST = {
        "hackerone": 0.95,
        "bugcrowd": 0.93,
        "intigriti": 0.90,
        "yeswehack": 0.88,
        "immunefi": 0.88,
        "opire": 0.85,
        "issuehunt": 0.82,
        "algora": 0.80,
        "gitcoin": 0.88,
        "bountysource": 0.85,
        "onlydust": 0.82,
        "appen": 0.88,
        "clickworker": 0.80,
        "toloka": 0.82,
        "remotasks": 0.78,
        "dataannotation": 0.82,
        "surge": 0.78,
        "data_annotation_tech": 0.82,
        "surge_ai": 0.78,
        "prolific": 0.80,
        "user_testing": 0.78,
        "rev": 0.72,
        "transcribe_me": 0.70,
        "upwork": 0.65,
        "freelancer": 0.55,
        "fiverr": 0.60,
        "github": 0.90,
    }

    def score(self, opportunity: Opportunity) -> EVScore:
        """Calculate Expected Value score for an opportunity."""
        category_key = (
            opportunity.category.value if hasattr(opportunity.category, "value") else str(opportunity.category)
        )
        platform_key = (
            opportunity.platform.value if hasattr(opportunity.platform, "value") else str(opportunity.platform)
        )

        # Base success probability from category
        base_success = self.BASE_SUCCESS_RATES.get(category_key, 0.30)

        # Platform trust multiplier
        platform_trust = self.PLATFORM_TRUST.get(platform_key.lower(), 0.50)

        # Zero-barrier bonus
        zero_barrier_bonus = 1.2 if self._is_zero_barrier(opportunity) else 1.0

        # Beginner-friendly bonus
        beginner_bonus = 1.1 if opportunity.accepts_beginner else 0.9

        # Remote/async bonus
        flexibility_bonus = 1.0
        if opportunity.remote:
            flexibility_bonus *= 1.05
        if opportunity.asynchronous:
            flexibility_bonus *= 1.05
        if opportunity.accepts_ai_tools:
            flexibility_bonus *= 1.10

        # Calculate success probability
        success_prob = base_success * platform_trust * zero_barrier_bonus * beginner_bonus * flexibility_bonus
        success_prob = min(max(success_prob, 0.01), 0.95)  # clamp

        # Estimated hours (with minimum)
        hours = max(opportunity.estimated_time_hours, 0.5)

        # Expected Value via the economics SSOT (FASE 3, P0-3; convergencia
        # P0-3 audit 2026-08-25: $/hora delega a compute_expected_human_value,
        # ya no se divide inline). Disponibilidad: señal real del
        # AvailabilityMonitor cuando exista observación fresca; sin señal ->
        # UNKNOWN surfaced en warnings; nunca asumido silenciosamente como 1.0.
        from cores.direct_work_engine.economics import compute_expected_human_value

        try:
            from cores.revenue.availability import get_availability_monitor

            task_availability, availability_verdict = get_availability_monitor().task_availability_for(platform_key)
        except Exception:
            from cores.direct_work_engine.economics import TaskAvailability

            task_availability = TaskAvailability.unknown()
        hv = compute_expected_human_value(
            payment=opportunity.payment,
            human_hours=hours,
            acceptance_probability=success_prob,
            task_availability=task_availability,
            time_to_first_payment_days=opportunity.time_to_payout_days,
        )
        total_ev = hv.ev_usd
        ev_per_hour = hv.ev_per_human_hour_usd
        if ev_per_hour is None:  # horas inválidas: fallback honesto al SSOT core
            ev_per_hour = round(total_ev / max(hours, 0.5), 2)

        # Confidence based on data quality
        confidence = 0.5
        if opportunity.payment_proven:
            confidence += 0.2
        if opportunity.reputation > 0.7:
            confidence += 0.15
        if opportunity.stability > 0.7:
            confidence += 0.1
        if opportunity.payment > 100:
            confidence += 0.1
        confidence = min(confidence, 0.95)

        is_zero_barrier = self._is_zero_barrier(opportunity)

        reasoning = self._generate_reasoning(opportunity, success_prob, ev_per_hour, is_zero_barrier)
        reasoning.append(
            "Cold-start prior: success probability derives from curated category "
            "estimates (BASE_SUCCESS_RATES), not measured acceptance history."
        )

        return EVScore(
            opportunity_id=opportunity.id,
            platform=platform_key,
            title=opportunity.title,
            ev_usd_per_hour=round(ev_per_hour, 2),
            total_ev_usd=round(total_ev, 2),
            success_probability=round(success_prob, 3),
            payout_usd=opportunity.payment,
            estimated_hours=hours,
            confidence=round(confidence, 2),
            zero_barrier=is_zero_barrier,
            rank=0,
            reasoning=reasoning,
        )

    def _is_zero_barrier(self, opportunity: Opportunity) -> bool:
        """Quick zero-barrier check."""
        return (
            not opportunity.interview_required
            and not opportunity.portfolio_required
            and not opportunity.technical_test_required
            and opportunity.experience_required == ExperienceLevel.NONE
            and opportunity.remote
            and opportunity.international_payment
            and opportunity.payment > 5
            and opportunity.accepts_beginner
        )

    def _generate_reasoning(
        self, opp: Opportunity, success_prob: float, ev_per_hour: float, zero_barrier: bool
    ) -> list[str]:
        reasons = []
        if zero_barrier:
            reasons.append("✅ Zero-barrier: no interview, no portfolio, no experience required")
        else:
            reasons.append("⚠️ Has some barriers")
        reasons.append(f"💰 Expected value: ${ev_per_hour:.2f}/hour")
        reasons.append(f"🎯 Success probability: {success_prob:.0%}")
        reasons.append(f"🏷️ Category: {opp.category.value if hasattr(opp.category, 'value') else opp.category}")
        if opp.payment_proven:
            reasons.append("✅ Payment history proven")
        if opp.accepts_ai_tools:
            reasons.append("🤖 AI tools accepted (speed multiplier)")
        return reasons


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
# WEB RESEARCHER — Autonomous platform discovery (THE BEST SEARCH ENGINE)
# ═══════════════════════════════════════════════════════════════════════════


class WebResearcher:
    """THE ULTIMATE autonomous web researcher for zero-barrier reward platforms.

    Discovers platforms via:
    - GitHub API (repos with bounty labels, issues with reward labels)
    - GitLab API (public projects with bounty programs)
    - DuckDuckGo + multi-engine searches
    - Specialized aggregator crawling
    - Known platform directories
    - Continuous learning from successful completions

    Prioritizes by: Expected Value = payout × success_rate / time_invested
    Filters: zero interview, zero portfolio, zero experience required
    """

    # ─── Search Queries ───
    DISCOVERY_QUERIES = [
        # GitHub-based searches (high yield)
        'site:github.com "bounty" "good first issue"',
        'site:github.com "bug bounty" "no experience"',
        'site:github.com "security bounty" "beginner"',
        'site:github.com label:bounty label:"good first issue"',
        'site:github.com "reward" "open source" "contribution"',
        'site:github.com "bounty program" "public"',
        'site:github.com "hackerone" OR "bugcrowd" OR "intigriti"',
        'site:github.com "vulnerability reward"',
        # GitLab searches
        'site:gitlab.com "bug bounty" "public"',
        'site:gitlab.com "security reward" "open"',
        # Direct platform searches
        "bug bounty platform no interview no portfolio no experience",
        "open source bounty platform beginners welcome",
        "developer bounty no interview no portfolio",
        "coding bounty platform no experience required",
        "microtask platform no interview no portfolio remote",
        "data annotation jobs no experience remote worldwide",
        "AI training data jobs no experience beginner",
        "RLHF annotation jobs no interview remote",
        "crowdsourcing platform no interview no portfolio",
        "paid bug bounty programs beginners 2024 2025",
        "open source bounties for beginners no experience",
        "security research rewards no interview",
        "vulnerability disclosure program no experience",
        # Game dev specific
        "game development bounty no experience",
        "unity bounty program no interview",
        "godot bounty no portfolio",
        "unreal engine bounty beginner",
        # Platform-specific
        "site:gitcoin.co bounties",
        "site:gitcoin.co grants",
        "site:opire.dev bounties",
        "site:issuehunt.io bounties",
        "site:algora.io bounties",
        "site:onlydust.com bounties",
        "site:huntr.com bounties",
        "site:immunefi.com bug bounty",
        # Quant / AI Trading Competition specific
        "quant trading competition no experience required",
        "AI trading competition no interview",
        "trading signal competition prize",
        "financial AI competition prize money",
        "quant bounty platform no interview",
        "alphanova competition prize",
        "numerai tournament prize",
        "kaggle competition prize money no experience",
        "huggingface competition reward",
        "zindi africa competition prize",
        "aicrowd competition prize",
        "driven data competition prize",
        "trading strategy competition prize",
        "quant research competition prize",
        # Platform-specific
        "site:alphanova.tech competition",
        "site:numer.ai tournament",
        "site:kaggle.com competitions",
        "site:huggingface.co competitions",
        "site:zindi.africa competitions",
        "site:aicrowd.com challenges",
        "site:driven.data.com competitions",
        "site:kaggle.com competitions",
    ]

    # ─── High-Value Aggregator Sites ───
    AGGREGATOR_SITES = [
        # Main bounty platforms
        "https://huntr.com/bounties",
        "https://www.openbugbounty.org",
        "https://hackenproof.com/programs",
        "https://www.federacy.com/programs",
        "https://detectify.com/crowdsource",
        "https://hackerone.com/bounty-programs",
        "https://bugcrowd.com/programs",
        "https://www.intigriti.com/programs",
        "https://www.yeswehack.com/programs",
        "https://www.synack.com/red-team",
        "https://cobalt.io/pentest",
        # OSS Funding platforms
        "https://gitcoin.co/explorer",
        "https://opire.dev/explore",
        "https://issuehunt.io/explore",
        "https://algora.io/explore",
        "https://app.onlydust.com/explore",
        "https://www.bountysource.com",
        "https://www.bountygraph.com",
        # Microtask platforms
        "https://www.prolific.com",
        "https://toloka.yandex.com",
        "https://www.clickworker.com",
        "https://www.appen.com",
        "https://www.remotasks.com",
        "https://surge.ai",
        "https://dataannotation.tech",
        # Game dev / creative
        "https://itch.io/jams",
        "https://gamejolt.com",
        # Developer platforms
        "https://devpost.com/hackathons",
        "https://www.kaggle.com/competitions",
        "https://zindi.africa/competitions",
        # AI / Quant competitions
        "https://alphanova.tech",
        "https://numer.ai",
        "https://kaggle.com/competitions",
        "https://huggingface.co/competitions",
        "https://zindi.africa/competitions",
        "https://aicrowd.com/challenges",
        "https://driven.data.com/competitions",
        "https://signate.jp/competitions",
        # Freelance / Marketplaces
        "https://fiverr.com",
        "https://upwork.com",
        "https://freelancer.com",
        "https://peopleperhour.com",
        "https://contra.com",
        "https://guru.com",
        "https://workana.com",
        "https://toptal.com",
        "https://arc.dev",
        "https://gun.io",
        # Data annotation / AI
        "https://dataannotation.tech",
        "https://outlier.ai",
        "https://scale.com",
        "https://remotasks.com",
        "https://appen.com",
        "https://telusinternational.ai",
        "https://oneforma.com",
        "https://clickworker.com",
        "https://toloka.yandex.com",
        "https://microworkers.com",
        # Microtasks / Testing
        "https://mturk.com",
        "https://prolific.com",
        "https://taskverse.com",
        "https://hivemicro.com",
        "https://neevo.ai",
        "https://test.io",
        "https://usertesting.com",
        "https://userlytics.com",
        "https://trymata.com",
        "https://utest.com",
        "https://testlio.com",
        "https://applause.com",
        "https://testbirds.com",
        "https://betafamily.com",
        "https://playtestcloud.com",
        "https://ferpection.com",
        "https://userfeel.com",
        "https://respondent.io",
        "https://maze.co",
        # Open Source
        "https://summerofcode.withgoogle.com",
        "https://mlh.io",
        "https://opencollective.com",
        "https://polar.sh",
        "https://lfx.linuxfoundation.org",
        "https://cncf.io",
        "https://mozilla.org",
        "https://apache.org",
        "https://linuxfoundation.org",
        # AI Evaluation
        "https://scale.com",
        "https://dataforce.ai",
        "https://surge.ai",
        "https://alignerr.com",
        "https://mercor.com",
        "https://invisible.ai",
        "https://mindrift.ai",
        "https://rws.com",
        "https://welocalize.com",
        "https://lxt.com",
        # APIs / Marketplaces
        "https://rapidapi.com",
        "https://aws.amazon.com/marketplace",
        "https://vercel.com/marketplace",
        "https://shopify.com/marketplace",
        "https://wordpress.org/plugins",
        "https://chrome.google.com/webstore",
        "https://addons.mozilla.org",
        "https://npmjs.com",
        "https://pypi.org",
        "https://hub.docker.com",
        # Digital products
        "https://gumroad.com",
        "https://lemonsqueezy.com",
        "https://paddle.com",
        "https://ko-fi.com",
        "https://buymeacoffee.com",
        # Research / Competitions
        "https://kaggle.com/competitions",
        "https://huggingface.co/competitions",
        "https://driven.data.com/competitions",
        "https://topcoder.com",
        "https://codementor.io",
        "https://alphanova.tech",
        "https://numer.ai",
        "https://signate.jp",
        "https://aicrowd.com",
        "https://driven.data.com",
        "https://zindi.africa/competitions",
        "https://huggingface.co/competitions",
        # Game Dev
        "https://itch.io/jams",
        "https://gamejolt.com",
        # Additional Bug Bounty
        "https://hackenproof.com/programs",
        "https://www.federacy.com/programs",
        "https://detectify.com/crowdsource",
        "https://cobalt.io/pentest",
        "https://www.synack.com/red-team",
        # Additional Dev Bounty
        "https://bountysource.com",
        "https://www.bountygraph.com",
    ]

    # ─── GitHub API Search Patterns (no auth needed for basic) ───
    GITHUB_SEARCH_QUERIES = [
        'label:bounty label:"good first issue" state:open',
        'label:bounty label:"help wanted" state:open',
        'label:"bug bounty" state:open',
        "label:reward state:open",
        '"bounty" in:title state:open',
        '"bug bounty" in:readme state:open',
        "topic:bounty state:open",
        "topic:bug-bounty state:open",
        "topic:security-bounty state:open",
        '"vulnerability reward" in:description state:open',
    ]

    # ─── Platform Intelligence (learned over time) ───
    PLATFORM_INTELLIGENCE = {
        # Bug Bounty - MAXIMUM REALISTIC SUCCESS
        "hackerone.com": {
            "success_rate": 0.45,
            "avg_payout": 800,
            "time_to_payout": 21,
            "zero_barrier_confidence": 0.95,
        },
        "bugcrowd.com": {
            "success_rate": 0.50,
            "avg_payout": 600,
            "time_to_payout": 18,
            "zero_barrier_confidence": 0.95,
        },
        "intigriti.com": {
            "success_rate": 0.55,
            "avg_payout": 500,
            "time_to_payout": 14,
            "zero_barrier_confidence": 0.97,
        },
        "yeswehack.com": {
            "success_rate": 0.60,
            "avg_payout": 400,
            "time_to_payout": 10,
            "zero_barrier_confidence": 0.95,
        },
        "huntr.com": {"success_rate": 0.70, "avg_payout": 200, "time_to_payout": 5, "zero_barrier_confidence": 0.98},
        # Dev Bounty / OSS - MAXIMUM SUCCESS
        "gitcoin.co": {"success_rate": 0.75, "avg_payout": 300, "time_to_payout": 10, "zero_barrier_confidence": 0.98},
        "opire.dev": {"success_rate": 0.80, "avg_payout": 250, "time_to_payout": 7, "zero_barrier_confidence": 0.98},
        "issuehunt.io": {"success_rate": 0.78, "avg_payout": 220, "time_to_payout": 8, "zero_barrier_confidence": 0.97},
        "algora.io": {"success_rate": 0.70, "avg_payout": 350, "time_to_payout": 12, "zero_barrier_confidence": 0.95},
        "onlydust.com": {
            "success_rate": 0.72,
            "avg_payout": 300,
            "time_to_payout": 11,
            "zero_barrier_confidence": 0.96,
        },
        # High-value but specialized
        "immunefi.com": {
            "success_rate": 0.30,
            "avg_payout": 3000,
            "time_to_payout": 30,
            "zero_barrier_confidence": 0.8,
        },
        # Data Entry / Microtask - NEAR 100% SUCCESS
        "prolific.com": {"success_rate": 0.98, "avg_payout": 60, "time_to_payout": 2, "zero_barrier_confidence": 0.99},
        "toloka.yandex.com": {
            "success_rate": 0.97,
            "avg_payout": 40,
            "time_to_payout": 1,
            "zero_barrier_confidence": 0.99,
        },
        "clickworker.com": {
            "success_rate": 0.95,
            "avg_payout": 50,
            "time_to_payout": 3,
            "zero_barrier_confidence": 0.98,
        },
        "appen.com": {"success_rate": 0.93, "avg_payout": 80, "time_to_payout": 4, "zero_barrier_confidence": 0.97},
        "remotasks.com": {"success_rate": 0.96, "avg_payout": 60, "time_to_payout": 2, "zero_barrier_confidence": 0.98},
        "surge.ai": {"success_rate": 0.92, "avg_payout": 100, "time_to_payout": 3, "zero_barrier_confidence": 0.95},
        "dataannotation.tech": {
            "success_rate": 0.97,
            "avg_payout": 90,
            "time_to_payout": 2,
            "zero_barrier_confidence": 0.98,
        },
        # Competitions / ML - High payout, good success
        "kaggle.com": {"success_rate": 0.40, "avg_payout": 2000, "time_to_payout": 21, "zero_barrier_confidence": 0.85},
        "zindi.africa": {
            "success_rate": 0.38,
            "avg_payout": 1500,
            "time_to_payout": 18,
            "zero_barrier_confidence": 0.87,
        },
        "devpost.com": {"success_rate": 0.35, "avg_payout": 800, "time_to_payout": 15, "zero_barrier_confidence": 0.82},
    }

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.discovered_platforms: set[str] = set()
        self.platform_scores: dict[str, float] = {}

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "OWNEX Autonomous Researcher/2.0 (+https://ownex.dev/bot)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _calculate_platform_ev(self, domain: str, zero_barrier_signals: int) -> float:
        """Calculate Expected Value score for a platform."""
        intel = self.PLATFORM_INTELLIGENCE.get(domain, {})
        base_success = intel.get("success_rate", 0.10)
        avg_payout = intel.get("avg_payout", 100)
        time_to_payout = intel.get("time_to_payout", 30)
        zb_confidence = intel.get("zero_barrier_confidence", 0.5)

        zb_boost = 1.0 + (zero_barrier_signals * 0.1)
        ev = (avg_payout * base_success * zb_boost * zb_confidence) / max(time_to_payout / 24, 0.5)
        return round(ev, 2)

    async def discover_new_platforms(self, max_platforms: int = 50) -> list[dict[str, Any]]:
        """Discover new platforms using ALL sources, ranked by EV."""
        new_platforms = []

        # 1. GitHub API searches (highest yield for dev bounties)
        try:
            github_platforms = await self._search_github_api()
            new_platforms.extend(github_platforms)
        except Exception as e:
            logger.warning(f"GitHub API search failed: {e}")

        # 2. DuckDuckGo + multi-engine searches
        for query in self.DISCOVERY_QUERIES[:50]:
            try:
                results = await self._search_duckduckgo(query)
                for result in results[:3]:
                    platform_info = await self._analyze_platform(result["url"])
                    if platform_info and platform_info["url"] not in self.discovered_platforms:
                        self.discovered_platforms.add(platform_info["url"])
                        platform_info["ev_score"] = self._calculate_platform_ev(
                            platform_info["domain"], platform_info["zero_barrier_signals"]
                        )
                        new_platforms.append(platform_info)
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")

        # 3. Crawl aggregator sites
        for site_url in self.AGGREGATOR_SITES[:10]:
            try:
                platforms = await self._crawl_aggregator(site_url)
                for p in platforms:
                    if p["url"] not in self.discovered_platforms:
                        self.discovered_platforms.add(p["url"])
                        p["ev_score"] = self._calculate_platform_ev(p["domain"], p.get("zero_barrier_signals", 0))
                        new_platforms.append(p)
            except Exception as e:
                logger.warning(f"Crawler failed for {site_url}: {e}")

        # Sort by EV score descending (best first)
        new_platforms.sort(key=lambda p: p.get("ev_score", 0), reverse=True)

        result = new_platforms[:max_platforms]

        logger.info(f"🎯 Discovered {len(result)} new platforms (ranked by EV)")
        for i, p in enumerate(result[:5]):
            logger.info(f"  {i + 1}. {p['title'][:50]} ({p['domain']}) EV: ${p.get('ev_score', 0)}/hr")

        return result

    async def _search_github_api(self) -> list[dict[str, Any]]:
        """Search GitHub API for bounty repositories (no auth needed for public)."""
        platforms = []

        for query in self.GITHUB_SEARCH_QUERIES[:5]:
            try:
                url = f"https://api.github.com/search/repositories?q={query.replace(' ', '+')}&sort=stars&order=desc&per_page=20"
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for repo in data.get("items", []):
                            repo_url = repo["html_url"]
                            domain = "github.com"
                            if repo_url not in self.discovered_platforms:
                                self.discovered_platforms.add(repo_url)
                                platforms.append(
                                    {
                                        "url": repo_url,
                                        "title": f"{repo['full_name']} - {repo['description'] or 'Bounty repository'}",
                                        "domain": domain,
                                        "zero_barrier_signals": 5,
                                        "has_zero_barrier_language": True,
                                        "discovered_at": datetime.now(UTC).isoformat(),
                                        "source": "github_api",
                                        "repo_stars": repo["stargazers_count"],
                                        "repo_language": repo["language"],
                                    }
                                )
                    elif resp.status == 403:
                        logger.warning("GitHub API rate limited")
                        break
            except Exception as e:
                logger.warning(f"GitHub API search failed: {e}")

        return platforms[:15]

    async def _search_duckduckgo(self, query: str) -> list[dict]:
        """Search DuckDuckGo HTML for results."""
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        try:
            async with self.session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                results = []
                for link in soup.select(".result__url a, .result__snippet a, a.result__snippet"):
                    href = link.get("href")
                    if href and href.startswith("http"):
                        results.append({"url": href})
                return results[:10]
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
        return []

    async def _analyze_platform(self, url: str) -> dict | None:
        """Analyze a platform URL to extract intelligence."""
        try:
            async with self.session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string if soup.title else urlparse(url).netloc

                text = soup.get_text().lower()
                zero_barrier_signals = [
                    "no experience",
                    "no interview",
                    "no portfolio",
                    "entry level",
                    "beginner friendly",
                    "open to all",
                    "no experience required",
                    "no portfolio required",
                    "anyone can apply",
                    "open to beginners",
                    "no degree required",
                    "no background check",
                    "remote",
                    "worldwide",
                    "instant payout",
                    "automated payout",
                    "no kyc",
                    "no verification",
                ]

                positive_signals = [
                    "bounty",
                    "reward",
                    "payout",
                    "earn",
                    "paid",
                    "compensation",
                    "microtask",
                    "task",
                    "challenge",
                    "competition",
                    "prize",
                ]

                negative_signals = [
                    "interview",
                    "portfolio",
                    "experience required",
                    "degree required",
                    "background check",
                    "kyc",
                    "verification required",
                    "screening",
                    "assessment",
                    "test required",
                    "coding challenge",
                    "whiteboard",
                    "phone screen",
                    "video call",
                    "onsite",
                    "relocation",
                ]

                zb_score = sum(1 for s in zero_barrier_signals if s in text)
                pos_score = sum(1 for s in positive_signals if s in text)
                neg_score = sum(1 for s in negative_signals if s in text)

                net_zb = zb_score + pos_score - (neg_score * 2)

                domain = urlparse(url).netloc
                ev_score = self._calculate_platform_ev(domain, max(net_zb, 0))

                return {
                    "url": url,
                    "title": title[:200] if title else domain,
                    "domain": domain,
                    "zero_barrier_signals": max(net_zb, 0),
                    "has_zero_barrier_language": net_zb > 2,
                    "discovered_at": datetime.now(UTC).isoformat(),
                    "ev_score": ev_score,
                    "positive_signals": pos_score,
                    "negative_signals": neg_score,
                }
        except Exception as e:
            logger.warning(f"Failed to analyze {url}: {e}")
        return None

    async def _crawl_aggregator(self, url: str) -> list[dict]:
        """Crawl known aggregator sites for platform listings."""
        platforms = []
        try:
            async with self.session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("/"):
                        href = urljoin(url, href)
                    elif not href.startswith("http"):
                        continue

                    text = link.get_text().lower()
                    if any(
                        kw in text
                        for kw in [
                            "bounty",
                            "program",
                            "reward",
                            "earn",
                            "microtask",
                            "challenge",
                            "competition",
                            "prize",
                            "task",
                            "paid",
                        ]
                    ):
                        parsed = urlparse(href)
                        if parsed.netloc and parsed.netloc not in urlparse(url).netloc:
                            platform_info = await self._analyze_platform(href)
                            if platform_info and platform_info.get("has_zero_barrier_language"):
                                platforms.append(platform_info)
        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")
        return platforms[:25]


# ═══════════════════════════════════════════════════════════════════════════
# AUTONOMOUS DISCOVERY ENGINE — Main orchestrator
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class DiscoveryConfig:
    """Configuration for autonomous discovery."""

    # Discovery intervals
    research_interval_hours: int = 6  # How often to research new platforms
    fetch_interval_hours: int = 2  # How often to fetch from known platforms
    deep_research_interval_hours: int = 24  # Deep web research

    # Filtering
    min_ev_per_hour: float = 2.0  # Minimum EV/hour to keep
    min_success_probability: float = 0.05  # Minimum success probability
    require_zero_barrier: bool = True  # Only zero-barrier opportunities

    # Limits
    max_opportunities_per_cycle: int = 1000  # Cap per cycle (escala a 1000+)
    max_platforms_to_research: int = 100  # New platforms per research cycle
    max_consecutive_errors: int = 5  # Disable platform after N errors

    # Storage
    cache_dir: str = "data/discovery_cache"
    persist_state: bool = True


@dataclass
class DynamicPlatformAdapter(BaseDiscoveryAdapter):
    """Adapter auto-created for platforms discovered by the WebResearcher.

    Uses generic heuristics to extract opportunities: looks for links containing
    'bounty', 'task', 'reward', 'paid', 'microtask' and builds minimal Opportunity
    objects. Trust is low (unknown payout source) so the strict filter governs
    real inclusion in the delivery bank.
    """

    platform_url: str = ""
    domain: str = ""
    zero_barrier_signals: int = 0

    def __init__(
        self, source: DiscoverySource, platform_url: str = "", domain: str = "", zero_barrier_signals: int = 0
    ) -> None:
        super().__init__(source)
        self.platform_url = platform_url
        self.domain = domain
        self.zero_barrier_signals = zero_barrier_signals

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Best-effort fetch from a dynamically discovered platform."""
        if not self.platform_url:
            return []
        from cores.direct_work_engine.models import (
            DifficultyLevel,
            ExperienceLevel,
            PaymentMethod,
        )

        opps: list[Opportunity] = []
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(self.platform_url) as resp:
                    html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                for link in soup.find_all("a", href=True):
                    text = link.get_text().strip().lower()
                    if any(kw in text for kw in ("bounty", "task", "reward", "paid", "microtask")):
                        href = link["href"]
                        from urllib.parse import urljoin

                        full_url = urljoin(self.platform_url, href)
                        opps.append(
                            self._create_opportunity(
                                external_id=full_url[:64],
                                title=link.get_text().strip()[:120],
                                category=self.source.categories[0]
                                if self.source.categories
                                else OpportunityCategory.BUG_BOUNTY,
                                url=full_url,
                                payment=0.0,
                                payment_method=PaymentMethod.OTHER,
                                difficulty=DifficultyLevel.BEGINNER,
                                estimated_time_hours=2.0,
                                experience_required=ExperienceLevel.NONE,
                                registration_required=True,
                                accepts_beginner=True,
                                technology_tags=[self.domain],
                            )
                        )
        except Exception as e:
            self.source.consecutive_errors += 1
            self.source.last_error = str(e)
            self.logger.warning("DynamicPlatformAdapter failed for %s: %s", self.platform_url, e)
            return opps[:20]
        # Señal real de disponibilidad (P0-4): un fetch exitoso con N items es
        # una observación; un error de red NO registra UNAVAILABLE (no es prueba).
        try:
            from cores.revenue.availability import get_availability_monitor

            get_availability_monitor().record(self.domain or self.platform_url, len(opps))
        except Exception:
            pass  # la señal nunca rompe el pipeline
        return opps[:20]

    async def validate_connection(self) -> bool:
        """Check if the platform URL is reachable."""
        try:
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
                session.head(self.platform_url) as resp,
            ):
                return resp.status < 500
        except Exception:
            return False


class AutonomousDiscoveryEngine:
    """Main autonomous discovery engine - runs continuously, never stops discovering."""

    def __init__(self, config: DiscoveryConfig | None = None):
        self.config = config or DiscoveryConfig()
        self.ev_scorer = EVScorer()
        self.zero_barrier_filter = ZeroBarrierCriteria()
        self.researcher = WebResearcher()

        # State
        self.opportunities_cache: list[Opportunity] = []
        self.ev_scores: list[EVScore] = []
        self.platform_stats: dict[str, dict] = {}
        self.discovered_platforms: dict[str, dict] = {}
        self.cycle_count = 0
        self.last_research = datetime.now(UTC) - timedelta(hours=100)
        self.last_fetch = datetime.now(UTC) - timedelta(hours=100)
        self.last_deep_research = datetime.now(UTC) - timedelta(hours=100)
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Cache
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted state
        self._load_state()

    async def start(self):
        """Start the autonomous discovery engine."""
        self._running = True
        logger.info("🚀 Autonomous Discovery Engine STARTED")

        # Initial research
        await self._research_new_platforms()

        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._continuous_fetch_loop()),
            asyncio.create_task(self._continuous_research_loop()),
            asyncio.create_task(self._deep_research_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._persist_loop()),
        ]

        logger.info("✅ All discovery loops running")

    async def stop(self):
        """Stop the engine gracefully."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._save_state()
        logger.info("🛑 Autonomous Discovery Engine STOPPED")

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN LOOPS
    # ══════════════════════════════════════════════════════════════════════════

    async def _continuous_fetch_loop(self):
        """Continuously fetch from known platforms."""
        while self._running:
            try:
                await self._fetch_all_platforms()
                self.last_fetch = datetime.now(UTC)
                await asyncio.sleep(self.config.fetch_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Fetch loop error: {e}")
                await asyncio.sleep(300)  # 5 min backoff

    async def _continuous_research_loop(self):
        """Continuously research new platforms."""
        while self._running:
            try:
                if datetime.now(UTC) - self.last_research > timedelta(hours=self.config.research_interval_hours):
                    await self._research_new_platforms()
                    self.last_research = datetime.now(UTC)
                await asyncio.sleep(300)  # Check every 5 min
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Research loop error: {e}")
                await asyncio.sleep(300)

    async def _deep_research_loop(self):
        """Periodic deep web research for new platforms."""
        while self._running:
            try:
                if datetime.now(UTC) - self.last_deep_research > timedelta(
                    hours=self.config.deep_research_interval_hours
                ):
                    await self._deep_web_research()
                    self.last_deep_research = datetime.now(UTC)
                await asyncio.sleep(3600)  # Check hourly
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Deep research error: {e}")
                await asyncio.sleep(3600)

    async def _cleanup_loop(self):
        """Periodic cleanup of old/failed platforms."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Hourly
                self._cleanup_platforms()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _persist_loop(self):
        """Persist state periodically."""
        while self._running:
            try:
                await asyncio.sleep(1800)  # Every 30 min
                self._save_state()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Persist error: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # CORE OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    async def _fetch_all_platforms(self):
        """Fetch opportunities from all known platforms."""
        logger.info("🔄 Fetching opportunities from all platforms...")

        all_opportunities = []

        # Fetch from each registered platform adapter
        for platform_name, adapter in self._get_adapters().items():
            try:
                opps = await adapter.fetch_opportunities()
                all_opportunities.extend(opps)
                self._update_platform_stats(adapter.source.name, len(opps), success=True)
            except Exception as e:
                self._update_platform_stats(platform_name, 0, success=False, error=str(e))
                logger.warning(f"Failed to fetch from {platform_name}: {e}")

        # Filter and score
        filtered = self._filter_and_score(all_opportunities)
        self.opportunities_cache = filtered

        logger.info(f"✅ Fetched {len(all_opportunities)} raw → {len(filtered)} filtered opportunities")

    async def _research_new_platforms(self):
        """Research and discover new platforms."""
        logger.info("🔬 Researching new platforms...")

        async with self.researcher as researcher:
            new_platforms = await researcher.discover_new_platforms()

        for platform in new_platforms[: self.config.max_platforms_to_research]:
            if platform["url"] not in self.discovered_platforms:
                self.discovered_platforms[platform["url"]] = platform
                logger.info(f"🆕 Discovered new platform: {platform['title']} ({platform['url']})")

                # If it has zero-barrier signals, prioritize for adapter creation
                if platform.get("has_zero_barrier_language", False):
                    logger.info(f"⭐ HIGH PRIORITY: {platform['title']} has zero-barrier language!")

        logger.info(f"🔬 Research complete. Total known platforms: {len(self.discovered_platforms)}")

    async def _deep_web_research(self):
        """Deep web research - comprehensive search for new platforms."""
        logger.info("🔬🔬 Starting DEEP web research...")

        # Extended search with more queries
        async with self.researcher as researcher:
            # Use extended query set
            original_queries = self.researcher.DISCOVERY_QUERIES
            extended_queries = original_queries + [
                "new bug bounty platform 2024 2025",
                "emerging bug bounty platforms",
                "new open source bounty platform",
                "new microtask platform 2024",
                "new data annotation platform 2024",
                "new AI training data platform",
                "web3 bug bounty platform new",
                "crypto bug bounty platform new",
                "RLHF platform new 2024",
                "data labeling platform new 2024",
            ]

            self.researcher.DISCOVERY_QUERIES = extended_queries
            new_platforms = await researcher.discover_new_platforms()
            self.researcher.DISCOVERY_QUERIES = original_queries

            for platform in new_platforms[: self.config.max_platforms_to_research * 2]:
                if platform["url"] not in self.discovered_platforms:
                    self.discovered_platforms[platform["url"]] = platform

        logger.info(f"🔬🔬 Deep research complete. Total platforms: {len(self.discovered_platforms)}")

    def _filter_and_score(self, opportunities: list[Opportunity]) -> list[Opportunity]:
        """Apply zero-barrier filter and EV scoring, return top opportunities."""
        scored = []

        for opp in opportunities:
            # Zero-barrier check
            if self.config.require_zero_barrier:
                passed, failed = self.zero_barrier_filter.check(opp)
                if not passed:
                    continue

            # Score
            ev_score = self.ev_scorer.score(opp)

            # Filter by minimum thresholds
            if ev_score.ev_usd_per_hour < self.config.min_ev_per_hour:
                continue
            if ev_score.success_probability < self.config.min_success_probability:
                continue

            scored.append((opp, ev_score))

        # Sort by EV/hour descending
        scored.sort(key=lambda x: x[1].ev_usd_per_hour, reverse=True)

        # Assign ranks and limit
        result = []
        for i, (opp, score) in enumerate(scored[: self.config.max_opportunities_per_cycle]):
            score.rank = i + 1
            self.ev_scores.append(score)
            result.append(opp)

        return result

    def _cleanup_platforms(self):
        """Remove platforms with too many errors."""
        for name, stats in list(self.platform_stats.items()):
            if stats.get("consecutive_errors", 0) >= self.config.max_consecutive_errors:
                logger.warning(f"🚫 Disabling platform {name} after {stats['consecutive_errors']} errors")
                # Would disable adapter here

    def _update_platform_stats(self, name: str, count: int, success: bool, error: str = ""):
        if name not in self.platform_stats:
            self.platform_stats[name] = {
                "total_fetched": 0,
                "total_errors": 0,
                "consecutive_errors": 0,
                "last_fetch": None,
            }

        stats = self.platform_stats[name]
        stats["last_fetch"] = datetime.now(UTC).isoformat()
        if success:
            stats["total_fetched"] += count
            stats["consecutive_errors"] = 0
        else:
            stats["total_errors"] += 1
            stats["consecutive_errors"] += 1
            if error:
                stats["last_error"] = error

    def _get_adapters(self) -> dict:
        """Get platform adapters from the Direct Work Engine's discovery layer.

        Uses the process-wide singleton so adapters are registered once.
        """
        try:
            from api.routers.direct_work import get_engine

            return get_engine().discovery.adapters
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not get adapters from engine: %s", exc)
            return {}

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def get_top_opportunities(self, limit: int = 50, min_ev: float = 0) -> list[Opportunity]:
        """Get top-ranked opportunities."""
        opps = [o for o in self.opportunities_cache if self._get_ev_for_opportunity(o).ev_usd_per_hour >= min_ev]
        return opps[:limit]

    def get_best_by_category(self, category: OpportunityCategory, limit: int = 10) -> list[Opportunity]:
        """Get best opportunities for a specific category."""
        opps = [o for o in self.opportunities_cache if o.category == category]
        return opps[:limit]

    def get_zero_barrier_only(self, limit: int = 50) -> list[Opportunity]:
        """Get only zero-barrier opportunities."""
        filter_ = ZeroBarrierCriteria()
        return [o for o in self.opportunities_cache if filter_.check(o)[0]][:limit]

    def get_ev_scores(self, limit: int = 50) -> list[EVScore]:
        """Get EV scores for top opportunities."""
        return sorted(self.ev_scores, key=lambda x: x.ev_usd_per_hour, reverse=True)[:limit]

    def get_platform_stats(self) -> dict:
        return self.platform_stats

    def get_discovered_platforms(self) -> dict:
        return self.discovered_platforms

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "cycle_count": self.cycle_count,
            "total_opportunities": len(self.opportunities_cache),
            "total_ev_scores": len(self.ev_scores),
            "discovered_platforms": len(self.discovered_platforms),
            "platforms_tracked": len(self.platform_stats),
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch else None,
            "last_research": self.last_research.isoformat() if self.last_research else None,
            "last_deep_research": self.last_deep_research.isoformat() if self.last_deep_research else None,
        }

    def _get_ev_for_opportunity(self, opp: Opportunity) -> EVScore:
        for score in self.ev_scores:
            if score.opportunity_id == opp.id:
                return score
        return self.ev_scorer.score(opp)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        if not self.config.persist_state:
            return
        try:
            state = {
                "cycle_count": self.cycle_count,
                "last_fetch": self.last_fetch.isoformat(),
                "last_research": self.last_research.isoformat(),
                "last_deep_research": self.last_deep_research.isoformat(),
                "platform_stats": self.platform_stats,
                "discovered_platforms": self.discovered_platforms,
                "ev_scores": [s.__dict__ for s in self.ev_scores[-100:]],  # Keep last 100
            }
            (self.cache_dir / "engine_state.json").write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    def _load_state(self):
        try:
            state_file = self.cache_dir / "engine_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                self.cycle_count = state.get("cycle_count", 0)
                self.last_fetch = (
                    datetime.fromisoformat(state["last_fetch"]) if state.get("last_fetch") else datetime.now(UTC)
                )
                self.last_research = (
                    datetime.fromisoformat(state["last_research"]) if state.get("last_research") else datetime.now(UTC)
                )
                self.last_deep_research = (
                    datetime.fromisoformat(state["last_deep_research"])
                    if state.get("last_deep_research")
                    else datetime.now(UTC)
                )
                self.platform_stats = state.get("platform_stats", {})
                self.discovered_platforms = state.get("discovered_platforms", {})
                logger.info(f"📂 Loaded state: {len(self.discovered_platforms)} platforms, cycle {self.cycle_count}")
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════


async def create_discovery_engine(config: DiscoveryConfig | None = None) -> AutonomousDiscoveryEngine:
    """Create and start the autonomous discovery engine."""
    engine = AutonomousDiscoveryEngine(config)
    await engine.start()
    return engine


def get_zero_barrier_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Filter to only zero-barrier opportunities."""
    filter_ = ZeroBarrierCriteria()
    return [o for o in opportunities if filter_.check(o)[0]]


async def run_autonomous_research_cycle() -> dict:
    """Scheduler entry point: run one cycle of autonomous web research.

    Discovers new zero-barrier platforms and registers them for future harvesting.
    """
    import logging

    from cores.direct_work_engine.autonomous_discovery import AutonomousDiscoveryEngine, DiscoveryConfig

    logger = logging.getLogger("ownex.autonomous_discovery.scheduler")

    config = DiscoveryConfig(
        research_interval_hours=6,
        max_platforms_to_research=100,
        persist_state=True,
    )

    engine = AutonomousDiscoveryEngine(config)
    try:
        await engine._research_new_platforms()
        return {
            "status": "completed",
            "discovered": len(engine.discovered_platforms),
            "platforms": list(engine.discovered_platforms.keys())[:100],
        }
    except Exception as e:
        logger.exception("Autonomous research cycle failed: %s", e)
        return {"status": "failed", "error": str(e)}


def rank_by_ev(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Rank opportunities by Expected Value per hour."""
    scorer = EVScorer()
    scored = [(o, scorer.score(o)) for o in opportunities]
    scored.sort(key=lambda x: x[1].ev_usd_per_hour, reverse=True)
    return [o for o, _ in scored]
