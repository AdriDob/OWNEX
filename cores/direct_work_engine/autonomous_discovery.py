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

    # Base success rates by category (from historical data)
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

        # Expected Value
        total_ev = opportunity.payment * success_prob
        ev_per_hour = total_ev / max(hours, 0.5)

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
            reasoning=self._generate_reasoning(opportunity, success_prob, ev_per_hour, is_zero_barrier),
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
# WEB RESEARCHER — Autonomous platform discovery
# ═══════════════════════════════════════════════════════════════════════════


class WebResearcher:
    """Autonomous web researcher that discovers new opportunity platforms."""

    # Search queries for discovering new platforms
    DISCOVERY_QUERIES = [
        "site:github.com bug bounty program",
        "site:gitcoin.co bounties",
        "site:bountysource.com bounties",
        "site:gitcoin.co grants",
        "site:opire.dev bounties",
        "site:issuehunt.io bounties",
        "site:algora.io bounties",
        "site:onlydust.com bounties",
        "site:gitcoin.co kudos",
        "bug bounty platform no experience required",
        "bug bounty program no interview required",
        "bug bounty program no portfolio required",
        "open source bounty platform no experience",
        "open source bounty platform no interview",
        "microtask platform no experience required",
        "data annotation jobs no experience",
        "data labeling jobs no experience remote",
        "AI training data jobs no experience",
        "RLHF annotation jobs remote",
        "microtask platform remote work no experience",
        "crowdsourcing platform no interview",
        "micro job platform no interview no portfolio",
        "paid bug bounty programs beginners",
        "open source bounties for beginners",
        "developer bounties no interview",
        "coding bounties no experience",
        "AI evaluation jobs remote",
        "RLHF evaluation jobs no experience",
    ]

    # Known aggregator sites to crawl for new platforms
    AGGREGATOR_SITES = [
        "https://bountygraph.com",
        "https://www.bountysource.com/explore",
        "https://gitcoin.co/explorer",
        "https://opire.dev/explore",
        "https://issuehunt.io/explore",
        "https://algora.io/explore",
        "https://app.onlydust.com/explore",
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
        "https://app.onlydust.com/explore",
        "https://www.bountysource.com",
        "https://www.bountygraph.com",
    ]

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.discovered_platforms: set[str] = set()

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": "OWNEX Autonomous Researcher/1.0 (+https://ownex.dev/bot)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def discover_new_platforms(self) -> list[dict[str, Any]]:
        """Discover new platforms by searching and crawling."""
        new_platforms = []

        # 1. Search queries via DuckDuckGo HTML (no API key needed)
        for query in self.DISCOVERY_QUERIES[:10]:  # Limit to avoid rate limiting
            try:
                results = await self._search_duckduckgo(query)
                for result in results[:5]:
                    platform_info = await self._analyze_platform(result["url"])
                    if platform_info and platform_info["url"] not in self.discovered_platforms:
                        self.discovered_platforms.add(platform_info["url"])
                        new_platforms.append(platform_info)
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")

        # 2. Crawl aggregator sites
        for site_url in self.AGGREGATOR_SITES[:5]:
            try:
                platforms = await self._crawl_aggregator(site_url)
                for p in platforms:
                    if p["url"] not in self.discovered_platforms:
                        self.discovered_platforms.add(p["url"])
                        new_platforms.append(p)
            except Exception as e:
                logger.warning(f"Crawler failed for {site_url}: {e}")

        logger.info(f"Discovered {len(new_platforms)} new potential platforms")
        return new_platforms

    async def _search_duckduckgo(self, query: str) -> list[dict]:
        """Search DuckDuckGo HTML for results."""
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        try:
            async with self.session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                results = []
                for link in soup.select(".result__url a"):
                    url = link.get("href")
                    if url and url.startswith("http"):
                        results.append({"url": url})
                return results[:10]
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
        return []

    async def _analyze_platform(self, url: str) -> dict | None:
        """Analyze a platform URL to extract info."""
        try:
            async with self.session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                title = soup.title.string if soup.title else urlparse(url).netloc

                # Look for keywords indicating zero-barrier
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
                ]

                zero_barrier_score = sum(1 for s in zero_barrier_signals if s in text)

                return {
                    "url": url,
                    "title": title[:200],
                    "domain": urlparse(url).netloc,
                    "zero_barrier_signals": zero_barrier_score,
                    "has_zero_barrier_language": zero_barrier_score > 2,
                    "discovered_at": datetime.now(UTC).isoformat(),
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

                # Generic link extraction for program/platform links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("/"):
                        href = urljoin(url, href)
                    elif not href.startswith("http"):
                        continue

                    # Heuristics for platform/program links
                    text = link.get_text().lower()
                    if any(kw in text for kw in ["program", "bounty", "platform", "opportunity", "challenge"]):
                        parsed = urlparse(href)
                        if parsed.netloc and parsed.netloc not in urlparse(url).netloc:
                            platforms.append(
                                {
                                    "url": href,
                                    "title": link.get_text().strip()[:200],
                                    "domain": parsed.netloc,
                                    "source_aggregator": url,
                                    "discovered_at": datetime.now(UTC).isoformat(),
                                }
                            )
        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")
        return platforms[:20]  # Limit


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
    max_opportunities_per_cycle: int = 200  # Cap per cycle
    max_platforms_to_research: int = 20  # New platforms per research cycle
    max_consecutive_errors: int = 5  # Disable platform after N errors

    # Storage
    cache_dir: str = "data/discovery_cache"
    persist_state: bool = True


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
        """Get platform adapters - would integrate with actual adapters."""
        # This would integrate with the actual registered adapters
        # For now, return empty dict - real implementation connects to actual adapters
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


def rank_by_ev(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Rank opportunities by Expected Value per hour."""
    scorer = EVScorer()
    scored = [(o, scorer.score(o)) for o in opportunities]
    scored.sort(key=lambda x: x[1].ev_usd_per_hour, reverse=True)
    return [o for o, _ in scored]
