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
    """An optimized earnings strategy."""

    name: str
    pillars: list[dict[str, Any]]
    total_monthly_low: float
    total_monthly_high: float
    hours_per_day: float
    time_to_first_pay: str
    risk_level: str  # low, medium, high
    argentina_compatible: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pillars": self.pillars,
            "total_monthly": f"${self.total_monthly_low:,.0f} - ${self.total_monthly_high:,.0f}",
            "hours_per_day": self.hours_per_day,
            "time_to_first_pay": self.time_to_first_pay,
            "risk_level": self.risk_level,
            "argentina_compatible": self.argentina_compatible,
            "notes": self.notes,
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
    ) -> EarningsStrategy:
        """Recommend the best strategy based on user profile."""
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
            "monthly_target_conservative": "$2,000-5,000",
            "monthly_target_optimistic": "$10,000-30,000",
            "monthly_target_exceptional": "$30,000-100,000+",
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
                "expected_income": "$200-800",
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
                "expected_income": "$500-3,000",
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
                "expected_income": "$2,000-10,000",
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
                "expected_income": "$10,000-30,000",
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
                "expected_income": "$30,000-100,000+",
                "time": "3-5 hours/day",
            },
        }

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
