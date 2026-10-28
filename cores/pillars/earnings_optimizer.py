"""Earnings Optimizer — Maximizes intelligent income across all pillars.

Core principle: MAXIMIZE PAID REVENUE / HUMAN MINUTE

Considers:
- Payment method compatibility (Argentina)
- Barrier level
- EV/hour
- Time to first pay
- Skill requirements
- Platform availability
- Diversification
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.pillars.optimizer")


@dataclass
class EarningsStrategy:
    """An optimized earnings strategy.

    CRITICAL DISTINCTION:
    - MARKET_POTENTIAL: What the ecosystem CAN pay (ceiling, not expectation)
    - PERSONAL_FORECAST: What YOU can reasonably expect based on YOUR data
    - ACTUAL_CASH: What you've actually received
    """

    name: str
    pillars: list[dict[str, Any]]
    total_monthly_low: float  # MARKET POTENTIAL - low end
    total_monthly_high: float  # MARKET POTENTIAL - high end
    hours_per_day: float
    time_to_first_pay: str
    risk_level: str  # low, medium, high, very_high
    argentina_compatible: bool = True
    notes: str = ""
    # NEW: Personal tracking fields
    personal_verified_rate: float | None = None  # Your actual verified rate
    personal_forecast: float | None = None  # Your forecast based on history
    actual_cash: float = 0.0  # Actual cash received
    conversion_rate: float | None = None  # Your actual opportunity→cash conversion
    bottleneck: str | None = None  # Current bottleneck in your pipeline

    @property
    def market_potential(self) -> str:
        """Market potential - ecosystem ceiling, NOT personal expectation."""
        if self.total_monthly_high >= 1_000_000:
            return f"${self.total_monthly_low:,.0f} - NO CEILING"
        return f"${self.total_monthly_low:,.0f} - ${self.total_monthly_high:,.0f}"

    @property
    def market_potential_note(self) -> str:
        """Clarification that market potential is not personal expectation."""
        return "Ceiling of ecosystem, NOT personal expectation"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pillars": self.pillars,
            "market_potential": self.market_potential,
            "market_potential_note": self.market_potential_note,
            "hours_per_day": self.hours_per_day,
            "time_to_first_pay": self.time_to_first_pay,
            "risk_level": self.risk_level,
            "argentina_compatible": self.argentina_compatible,
            "notes": self.notes,
            "personal_verified_rate": self.personal_verified_rate,
            "personal_forecast": self.personal_forecast,
            "actual_cash": self.actual_cash,
            "conversion_rate": self.conversion_rate,
            "bottleneck": self.bottleneck,
        }


class EarningsOptimizer:
    """Optimizes earnings across all pillars for maximum income."""

    def __init__(self) -> None:
        self.strategies = self._init_strategies()

    def _init_strategies(self) -> list[EarningsStrategy]:
        """Initialize earnings strategies."""
        return [
            # ── CONSERVATIVE: Stable income, low risk ────────
            EarningsStrategy(
                name="Conservative — Stable Income",
                pillars=[
                    {"name": "AI Tasks", "monthly": "$1,000-3,000", "hours": 1.0, "pay": "$15-50/h"},
                    {"name": "Data Annotation", "monthly": "$500-2,000", "hours": 0.5, "pay": "$15-50/h"},
                    {"name": "QA Testing", "monthly": "$500-2,000", "hours": 0.5, "pay": "$10-100/bug"},
                ],
                total_monthly_low=2_000,
                total_monthly_high=7_000,
                hours_per_day=2.0,
                time_to_first_pay="1-2 weeks",
                risk_level="low",
                notes="Guaranteed income. No skill investment needed. Start here.",
            ),
            # ── GROWTH: Skill building + income ──────────────
            EarningsStrategy(
                name="Growth — Build Skills While Earning",
                pillars=[
                    {"name": "AI Tasks", "monthly": "$1,000-3,000", "hours": 1.0, "pay": "$15-50/h"},
                    {"name": "Dev Bounty", "monthly": "$500-3,000", "hours": 1.0, "pay": "$50-2K/bounty"},
                    {"name": "QA Testing", "monthly": "$500-2,000", "hours": 0.5, "pay": "$10-100/bug"},
                    {"name": "Bug Bounty (learning)", "monthly": "$0-2,000", "hours": 1.0, "pay": "$200-10K/bounty"},
                ],
                total_monthly_low=2_000,
                total_monthly_high=10_000,
                hours_per_day=3.5,
                time_to_first_pay="1-2 weeks",
                risk_level="medium",
                notes="Diversified. Learning Web3 security while earning.",
            ),
            # ── HIGH VALUE: Maximum income potential ──────────
            EarningsStrategy(
                name="High Value — Maximum Earnings",
                pillars=[
                    {
                        "name": "Web3 Bug Bounty (Immunefi)",
                        "monthly": "$5,000-50,000",
                        "hours": 2.0,
                        "pay": "$1K-500K/bounty",
                    },
                    {
                        "name": "Web2 Bug Bounty (HackerOne)",
                        "monthly": "$2,000-15,000",
                        "hours": 1.0,
                        "pay": "$500-250K/bounty",
                    },
                    {"name": "AI Tasks (backup)", "monthly": "$1,000-3,000", "hours": 0.5, "pay": "$15-50/h"},
                ],
                total_monthly_low=8_000,
                total_monthly_high=68_000,
                hours_per_day=3.5,
                time_to_first_pay="2-8 weeks",
                risk_level="high",
                notes="Requires smart contract security skills. Highest ceiling.",
            ),
            # ── WEB3 FOCUSED: Smart contract specialization ──
            EarningsStrategy(
                name="Web3 Specialist — Smart Contract Security",
                pillars=[
                    {"name": "Immunefi Bounties", "monthly": "$10,000-100,000", "hours": 3.0, "pay": "$1K-500K/bounty"},
                    {"name": "HackenProof", "monthly": "$2,000-10,000", "hours": 0.5, "pay": "$500-50K/bounty"},
                    {"name": "AI Tasks (backup)", "monthly": "$500-2,000", "hours": 0.5, "pay": "$15-50/h"},
                ],
                total_monthly_low=12_500,
                total_monthly_high=112_000,
                hours_per_day=4.0,
                time_to_first_pay="3-8 weeks",
                risk_level="high",
                notes="Full Web3 specialization. Requires Solidity + security skills.",
            ),
            # ── FULL SPECTRUM: All 5 pillars ─────────────────
            EarningsStrategy(
                name="Full Spectrum — All 5 Pillars",
                pillars=[
                    {
                        "name": "Bug Bounty (Web2+Web3)",
                        "monthly": "$3,000-30,000",
                        "hours": 1.5,
                        "pay": "$500-500K/bounty",
                    },
                    {"name": "AI Tasks", "monthly": "$1,000-5,000", "hours": 1.0, "pay": "$15-50/h"},
                    {"name": "Dev Bounty", "monthly": "$500-8,000", "hours": 1.0, "pay": "$50-15K/bounty"},
                    {"name": "QA Testing", "monthly": "$500-3,000", "hours": 0.5, "pay": "$10-100/bug"},
                    {"name": "Data Annotation", "monthly": "$500-3,000", "hours": 0.5, "pay": "$15-50/h"},
                ],
                total_monthly_low=5_500,
                total_monthly_high=49_000,
                hours_per_day=4.5,
                time_to_first_pay="1-2 weeks",
                risk_level="medium",
                notes="Maximum diversification. If one pillar fails, others compensate.",
            ),
            # ── UNBOUNDED: Autonomous Intelligence Systems ─────
            EarningsStrategy(
                name="Unbounded — Autonomous Intelligence",
                pillars=[
                    {
                        "name": "OWNEX Autopilot (24/7)",
                        "monthly": "NO CEILING",
                        "hours": 0.5,  # Monitoring only
                        "pay": "System scales independently of time",
                    },
                    {
                        "name": "Automated Recon Pipeline",
                        "monthly": "NO CEILING",
                        "hours": 0.0,  # Fully automated
                        "pay": "Scalable vulnerability discovery",
                    },
                    {
                        "name": "AI-Powered Report Generation",
                        "monthly": "NO CEILING",
                        "hours": 0.0,  # Fully automated
                        "pay": "Submit 100+ reports/day automatically",
                    },
                    {
                        "name": "Multi-Platform Distribution",
                        "monthly": "NO CEILING",
                        "hours": 0.0,  # Fully automated
                        "pay": "Same finding → 20 platforms simultaneously",
                    },
                ],
                total_monthly_low=50_000,
                total_monthly_high=1_000_000,  # Million+ possible
                hours_per_day=0.5,  # Monitoring only
                time_to_first_pay="4-12 weeks",
                risk_level="very_high",
                notes="UNBOUNDED. System scales, not human time. Requires OWNEX maturity + automation. Single critical bounty can break ceiling.",
            ),
            # ── HYBRID: Human + AI Synergy ─────────────────────
            EarningsStrategy(
                name="Hybrid — Human Intelligence × AI Scale",
                pillars=[
                    {
                        "name": "Strategic Target Selection (Human)",
                        "monthly": "$10,000-100,000",
                        "hours": 1.0,
                        "pay": "You choose WHAT, AI finds HOW",
                    },
                    {
                        "name": "AI Vulnerability Discovery (OWNEX)",
                        "monthly": "NO CEILING",
                        "hours": 0.0,
                        "pay": "AI finds what humans miss",
                    },
                    {
                        "name": "Human Review & Validation",
                        "monthly": "$5,000-50,000",
                        "hours": 1.0,
                        "pay": "You validate, AI scales",
                    },
                    {
                        "name": "Strategic Platform Relations",
                        "monthly": "$5,000-20,000",
                        "hours": 0.5,
                        "pay": "Build reputation → private programs",
                    },
                ],
                total_monthly_low=20_000,
                total_monthly_high=500_000,
                hours_per_day=2.5,
                time_to_first_pay="3-8 weeks",
                risk_level="high",
                notes="Human intelligence + AI scale. You provide direction, AI provides execution. Best of both worlds.",
            ),
        ]

    def get_strategy(self, name: str) -> EarningsStrategy | None:
        """Get strategy by name."""
        for s in self.strategies:
            if s.name == name:
                return s
        return None

    def get_recommended_strategy(
        self,
        risk_tolerance: str = "medium",
        available_hours: float = 4.0,
        has_web3_skills: bool = False,
        needs_immediate_income: bool = True,
        has_autonomous_systems: bool = False,
        wants_unbounded: bool = False,
    ) -> EarningsStrategy:
        """Recommend the best strategy based on user profile.

        Args:
            risk_tolerance: low, medium, high, very_high
            available_hours: Hours per day available
            has_web3_skills: Smart contract security expertise
            needs_immediate_income: Need cash flow now vs long-term upside
            has_autonomous_systems: OWNEX automation maturity
            wants_unbounded: Explicitly seeking ceiling-free income
        """
        if wants_unbounded and has_autonomous_systems:
            return self.strategies[5]  # Unbounded - Autonomous Intelligence

        if wants_unbounded:
            return self.strategies[6]  # Hybrid - Human + AI

        if risk_tolerance == "low" or needs_immediate_income:
            return self.strategies[0]  # Conservative

        if risk_tolerance == "high" and has_web3_skills:
            return self.strategies[3]  # Web3 Specialist

        if risk_tolerance == "high":
            return self.strategies[2]  # High Value

        return self.strategies[4]  # Full Spectrum

    def get_argentina_optimized(self) -> dict[str, Any]:
        """Get Argentina-optimized earnings plan."""
        return {
            "payment_methods": [
                {"method": "PayPal", "fee": "3-4%", "availability": "All platforms", "recommended": True},
                {"method": "Payoneer", "fee": "3-6.5%", "availability": "All platforms", "recommended": True},
                {"method": "Crypto (USDT/USDC)", "fee": "1-3%", "availability": "All platforms", "recommended": True},
                {
                    "method": "Wire Transfer",
                    "fee": "$10-20 flat",
                    "availability": "Most platforms",
                    "recommended": False,
                },
                {"method": "Banco USD", "fee": "0%", "availability": "Post-2025", "recommended": True},
            ],
            "legal": {
                "since": "April 2025",
                "change": "Argentina lifted 'cepo cambiario'",
                "result": "Can receive USD directly in Argentine bank account",
                "tax": "Declare via ARCA (electronic invoice)",
                "status": "Legal and regulated",
            },
            "optimal_flow": {
                "step_1": "Receive payment via PayPal/Payoneer/Crypto",
                "step_2": "Option A: Withdraw to USD bank account (new since 2025)",
                "step_3": "Option B: Withdraw via Payoneer to local bank",
                "step_4": "Option C: Convert via P2P crypto (USDT→ARS)",
                "step_5": "Declare income via ARCA electronic invoice",
            },
            "market_potential": {
                "conservative": "$2,000-5,000 (ecosystem ceiling)",
                "optimistic": "$10,000-30,000 (ecosystem ceiling)",
                "exceptional": "$30,000-100,000+ (ecosystem ceiling)",
                "unbounded": "$50,000 - NO CEILING (autonomous systems)",
                "note": "These are ecosystem ceilings, NOT personal expectations. Unbounded requires AI automation.",
            },
            "personal_forecast": {
                "current": "UNKNOWN - insufficient history",
                "requires": "Actual operational data to compute personal forecast",
                "action": "Execute opportunities → collect results → OWNEX computes your forecast",
            },
        }

    def get_learning_path(self) -> dict[str, Any]:
        """Get the optimal learning path for maximum earnings."""
        return {
            "phase_1": {
                "name": "Foundation (Week 1-2)",
                "focus": "Immediate income + basics",
                "actions": [
                    "Register on Outlier.ai → earn $15-50/h",
                    "Register on uTest → earn $10-100/bug",
                    "Register on HackerOne + Bugcrowd → browse programs",
                    "Install OWASP ZAP + Burp Suite (free)",
                    "Learn: HTTP, APIs, authentication, authorization",
                ],
                "market_potential": "$200-800",
                "personal_forecast": "UNKNOWN - requires actual results",
                "time": "2-3 hours/day",
            },
            "phase_2": {
                "name": "Web2 Skills (Week 3-8)",
                "focus": "Bug bounty fundamentals",
                "actions": [
                    "Complete PortSwigger Web Security Academy (free)",
                    "Practice on HackTheBox, TryHackMe",
                    "Start HackerOne disclosed reports",
                    "Find first IDOR/XSS/SSRF",
                    "Submit first report → $200-2,000",
                ],
                "market_potential": "$500-3,000",
                "personal_forecast": "UNKNOWN - requires actual results",
                "time": "3-4 hours/day",
            },
            "phase_3": {
                "name": "Web3 Security (Month 3-6)",
                "focus": "Smart contract auditing",
                "actions": [
                    "Learn Solidity basics (CryptoZombies - free)",
                    "Learn: reentrancy, flash loans, oracle manipulation",
                    "Install Slither + Mythril + Echidna",
                    "Audit practice on Damn Vulnerable DeFi",
                    "First Immunefi bounty → $1,000-10,000",
                ],
                "market_potential": "$2,000-10,000",
                "personal_forecast": "UNKNOWN - requires actual results",
                "time": "3-4 hours/day",
            },
            "phase_4": {
                "name": "Specialization (Month 6-12)",
                "focus": "High-value targets",
                "actions": [
                    "Specialize in DeFi protocols",
                    "Target Immunefi $100K+ programs",
                    "Build reputation for private invitations",
                    "Automate recon with OWNEX",
                    "Bounties: $5,000-50,000+",
                ],
                "market_potential": "$10,000-30,000",
                "personal_forecast": "UNKNOWN - requires actual results",
                "time": "2-3 hours/day",
            },
            "phase_5": {
                "name": "Mastery (Year 2+)",
                "focus": "Top 1% territory",
                "actions": [
                    "Full-time bug bounty",
                    "Access to private programs",
                    "Protocol-level auditing",
                    "Consulting + auditing fees",
                    "Bounties: $20,000-100,000+",
                ],
                "market_potential": "$30,000-100,000+",
                "personal_forecast": "UNKNOWN - requires actual results",
                "time": "3-5 hours/day",
            },
        }

    def update_personal_metrics(
        self,
        strategy_name: str,
        opportunities_attempted: int,
        opportunities_executed: int,
        opportunities_accepted: int,
        opportunities_paid: int,
        total_cash_received: float,
        bottleneck: str | None = None,
    ) -> None:
        """Update personal metrics based on actual operational results.

        This is the bridge between MARKET_POTENTIAL and PERSONAL_FORECAST.
        OWNEX calls this after collecting real results to compute your actual performance.

        Args:
            strategy_name: Which strategy to update
            opportunities_attempted: How many opportunities you tried
            opportunities_executed: How many you actually completed
            opportunities_accepted: How many were accepted by the platform
            opportunities_paid: How many resulted in actual payment
            total_cash_received: Total cash actually received (USD)
            bottleneck: Current bottleneck (e.g., "conversion", "payment", "access")
        """
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            logger.warning("[Optimizer] Strategy not found: %s", strategy_name)
            return

        # Compute personal metrics
        if opportunities_attempted > 0:
            execution_rate = opportunities_executed / opportunities_attempted
            acceptance_rate = opportunities_accepted / opportunities_executed if opportunities_executed > 0 else 0
            payment_rate = opportunities_paid / opportunities_accepted if opportunities_accepted > 0 else 0
            overall_conversion = opportunities_paid / opportunities_attempted

            strategy.personal_verified_rate = total_cash_received / opportunities_paid if opportunities_paid > 0 else 0
            strategy.conversion_rate = overall_conversion
            strategy.actual_cash = total_cash_received
            strategy.bottleneck = bottleneck

            # Simple forecast: extrapolate current verified rate × expected opportunities
            # This is intentionally conservative - it's YOUR verified rate, not market ceiling
            if strategy.personal_verified_rate > 0 and overall_conversion > 0:
                # Assume similar opportunity volume going forward
                expected_opportunities_per_month = opportunities_attempted * 4  # Extrapolate from current sample
                strategy.personal_forecast = (
                    strategy.personal_verified_rate * expected_opportunities_per_month * overall_conversion
                )
            else:
                strategy.personal_forecast = None

            logger.info(
                "[Optimizer] Updated %s: attempted=%d, executed=%d, accepted=%d, paid=%d, cash=$%.2f, conversion=%.2f%%, forecast=$%.2f",
                strategy_name,
                opportunities_attempted,
                opportunities_executed,
                opportunities_accepted,
                opportunities_paid,
                total_cash_received,
                overall_conversion * 100,
                strategy.personal_forecast or 0,
            )
        else:
            logger.warning("[Optimizer] No opportunities attempted for %s", strategy_name)

    def to_dict(self) -> dict[str, Any]:
        """Serialize optimizer state."""
        return {
            "strategies": [s.to_dict() for s in self.strategies],
            "argentina_optimized": self.get_argentina_optimized(),
            "learning_path": self.get_learning_path(),
        }


# Singleton
_earnings_optimizer: EarningsOptimizer | None = None


def get_earnings_optimizer() -> EarningsOptimizer:
    """Get or create the global earnings optimizer."""
    global _earnings_optimizer
    if _earnings_optimizer is None:
        _earnings_optimizer = EarningsOptimizer()
    return _earnings_optimizer
