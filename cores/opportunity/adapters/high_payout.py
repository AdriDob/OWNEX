"""High-Payout Adapters — Crypto/Web3/AI Bug Bounty & Dev Bounties.

Platforms with $1,000-$250,000+ per vulnerability/bounty.
All confirmed to work from Argentina with international payment rails.

Argentina-confirmed platforms:
- Immunefi: $140M+ paid, $250K max bounty, crypto payments
- Sherlock: $16M pool size, USDC payments
- HackerOne: Global, Bugcrowd/PayPal/bank transfer
- OpenAI: $200-$20,000 per vulnerability
- Anthropic: Up to $35,000 per jailbreak
- Code4rena: Audit competitions $22K-$135K pools
- Gitcoin: Bounties $2K-$50K for security issues
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.adapters.high_payout")


@dataclass
class HighPayoutOpportunity:
    """A high-payout opportunity (bug bounty, dev bounty, audit)."""

    id: str
    platform: str
    title: str
    description: str
    category: str  # bug_bounty, dev_bounty, audit_competition
    pay_range: tuple[float, float]  # USD
    avg_payout: float
    skill_level: str  # beginner, intermediate, advanced, expert
    time_to_complete: str  # hours, days, weeks
    payment_method: str  # crypto, bank_transfer, paypal
    url: str = ""
    requirements: list[str] | None = None
    success_rate: float = 0.1  # Conservative estimate

    @property
    def barrier(self) -> str:
        return "High skill required"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "pay_range": list(self.pay_range),
            "avg_payout": self.avg_payout,
            "skill_level": self.skill_level,
            "time_to_complete": self.time_to_complete,
            "payment_method": self.payment_method,
            "requirements": self.requirements or [],
            "success_rate": self.success_rate,
            "url": self.url,
        }


class ImmunefiAdapter:
    """Immunefi — Web3 bug bounty platform ($140M+ paid, $250K max bounty)."""

    PLATFORM = "immunefi"

    OPPORTUNITIES = [
        {
            "title": "Critical Smart Contract Vulnerability",
            "category": "bug_bounty",
            "pay_range": (50000, 250000),
            "avg_payout": 75000,
            "skill_level": "expert",
            "time_to_complete": "1-4 weeks",
            "description": "Critical severity vulnerability in DeFi protocols (reentrancy, logic flaws, economic attacks)",
            "requirements": ["Solidity expertise", "Smart contract auditing", "DeFi knowledge"],
        },
        {
            "title": "High Severity Web3 Vulnerability",
            "category": "bug_bounty",
            "pay_range": (10000, 50000),
            "avg_payout": 25000,
            "skill_level": "advanced",
            "time_to_complete": "1-2 weeks",
            "description": "High severity issues in web applications, APIs, or infrastructure",
            "requirements": ["Web security", "API testing", "Blockchain basics"],
        },
        {
            "title": "Medium Severity Finding",
            "category": "bug_bounty",
            "pay_range": (1000, 10000),
            "avg_payout": 3000,
            "skill_level": "intermediate",
            "time_to_complete": "3-7 days",
            "description": "Medium severity bugs (XSS, CSRF, authentication bypasses)",
            "requirements": ["OWASP Top 10", "Web application security"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"immunefi_{i}",
                    platform="immunefi",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="crypto (USDC/ETH)",
                    requirements=opp["requirements"],
                    url="https://immunefi.com",
                    success_rate=0.05,  # 5% success rate for critical bugs
                )
            )
        return opportunities


class SherlockAdapter:
    """Sherlock — Web3 security platform ($16M pool, audit+bug bounty)."""

    PLATFORM = "sherlock"

    OPPORTUNITIES = [
        {
            "title": "Post-Launch Bug Bounty",
            "category": "bug_bounty",
            "pay_range": (5000, 100000),
            "avg_payout": 25000,
            "skill_level": "advanced",
            "time_to_complete": "1-3 weeks",
            "description": "Continuous security for live production code, stake-gated submissions",
            "requirements": ["Smart contract expertise", "DeFi protocols", "Live code testing"],
        },
        {
            "title": "Audit Competition",
            "category": "audit_competition",
            "pay_range": (10000, 50000),
            "avg_payout": 20000,
            "skill_level": "expert",
            "time_to_complete": "2-4 weeks",
            "description": "Comprehensive smart contract audit with prize pool distribution",
            "requirements": ["Audit experience", "Gas optimization", "Security patterns"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"sherlock_{i}",
                    platform="sherlock",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="crypto (USDC)",
                    requirements=opp["requirements"],
                    url="https://sherlock.xyz",
                    success_rate=0.08,
                )
            )
        return opportunities


class HackerOneAdapter:
    """HackerOne — Global bug bounty platform (works from Argentina, PayPal/bank transfer)."""

    PLATFORM = "hackerone"

    OPPORTUNITIES = [
        {
            "title": "Critical Vulnerability (Any Platform)",
            "category": "bug_bounty",
            "pay_range": (5000, 100000),
            "avg_payout": 15000,
            "skill_level": "expert",
            "time_to_complete": "1-4 weeks",
            "description": "Critical severity findings on major platforms (RCE, SQL injection, auth bypass)",
            "requirements": ["Advanced security skills", "Methodology", "Report writing"],
        },
        {
            "title": "High Severity Bug Bounty",
            "category": "bug_bounty",
            "pay_range": (1000, 10000),
            "avg_payout": 3000,
            "skill_level": "intermediate",
            "time_to_complete": "3-10 days",
            "description": "High severity issues (IDOR, business logic flaws, privilege escalation)",
            "requirements": ["Web security", "API security", "Bug bounty experience"],
        },
        {
            "title": "Medium Severity Finding",
            "category": "bug_bounty",
            "pay_range": (200, 1000),
            "avg_payout": 400,
            "skill_level": "beginner",
            "time_to_complete": "1-3 days",
            "description": "Medium severity bugs (XSS, CSRF, information disclosure)",
            "requirements": ["Basic security knowledge", "Reconnaissance tools"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"hackerone_{i}",
                    platform="hackerone",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="PayPal/bank transfer",
                    requirements=opp["requirements"],
                    url="https://hackerone.com",
                    success_rate=0.10,
                )
            )
        return opportunities


class OpenAIAdapter:
    """OpenAI Bug Bounty — AI security vulnerabilities ($200-$20,000)."""

    PLATFORM = "openai"

    OPPORTUNITIES = [
        {
            "title": "AI Safety Critical Vulnerability",
            "category": "bug_bounty",
            "pay_range": (5000, 20000),
            "avg_payout": 10000,
            "skill_level": "expert",
            "time_to_complete": "2-6 weeks",
            "description": "Critical AI safety issues (prompt injection, data exfiltration, jailbreaks)",
            "requirements": ["ML security", "Prompt engineering", "AI safety research"],
        },
        {
            "title": "OpenAI Security Vulnerability",
            "category": "bug_bounty",
            "pay_range": (500, 5000),
            "avg_payout": 1500,
            "skill_level": "intermediate",
            "time_to_complete": "1-2 weeks",
            "description": "Security vulnerabilities in OpenAI infrastructure or APIs",
            "requirements": ["Web security", "API testing", "Authentication"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"openai_{i}",
                    platform="openai",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="bank transfer",
                    requirements=opp["requirements"],
                    url="https://openai.com/security",
                    success_rate=0.03,
                )
            )
        return opportunities


class AnthropicAdapter:
    """Anthropic Model Safety Bug Bounty — Jailbreak detection ($35,000 max)."""

    PLATFORM = "anthropic"

    OPPORTUNITIES = [
        {
            "title": "Universal Jailbreak Discovery",
            "category": "bug_bounty",
            "pay_range": (10000, 35000),
            "avg_payout": 20000,
            "skill_level": "expert",
            "time_to_complete": "4-8 weeks",
            "description": "Novel, universal jailbreaks that bypass Constitutional Classifiers",
            "requirements": ["ML security", "Prompt engineering", "Constitutional AI"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"anthropic_{i}",
                    platform="anthropic",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="bank transfer",
                    requirements=opp["requirements"],
                    url="https://support.claude.com",
                    success_rate=0.02,
                )
            )
        return opportunities


class Code4renaAdapter:
    """Code4rena — Smart contract audit competitions ($22K-$135K pools)."""

    PLATFORM = "code4rena"

    OPPORTUNITIES = [
        {
            "title": "Audit Competition - Large Pool",
            "category": "audit_competition",
            "pay_range": (5000, 50000),
            "avg_payout": 15000,
            "skill_level": "expert",
            "time_to_complete": "2-4 weeks",
            "description": "Comprehensive smart contract audit with $100K+ prize pool",
            "requirements": ["Solidity expertise", "Audit methodology", "Gas optimization"],
        },
        {
            "title": "Audit Competition - Medium Pool",
            "category": "audit_competition",
            "pay_range": (2000, 15000),
            "avg_payout": 5000,
            "skill_level": "advanced",
            "time_to_complete": "1-2 weeks",
            "description": "Smart contract audit with $20K-$50K prize pool",
            "requirements": ["Solidity", "Security patterns", "DeFi knowledge"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"code4rena_{i}",
                    platform="code4rena",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="crypto (USDC)",
                    requirements=opp["requirements"],
                    url="https://code4rena.com",
                    success_rate=0.15,
                )
            )
        return opportunities


class GitcoinAdapter:
    """Gitcoin — Crypto bounties and security programs ($2K-$50K)."""

    PLATFORM = "gitcoin"

    OPPORTUNITIES = [
        {
            "title": "Chainlink Security Bounty",
            "category": "bug_bounty",
            "pay_range": (2000, 50000),
            "avg_payout": 8000,
            "skill_level": "advanced",
            "time_to_complete": "1-3 weeks",
            "description": "Security vulnerabilities in Chainlink infrastructure",
            "requirements": ["Web3 security", "Oracle protocols", "Smart contracts"],
        },
        {
            "title": "Dev Bounty - Web3 Project",
            "category": "dev_bounty",
            "pay_range": (500, 5000),
            "avg_payout": 1500,
            "skill_level": "intermediate",
            "time_to_complete": "1-2 weeks",
            "description": "Development tasks for Web3 projects (integrations, features, fixes)",
            "requirements": ["Solidity/Rust", "Web3 development", "Testing"],
        },
    ]

    async def fetch_opportunities(self) -> list[HighPayoutOpportunity]:
        opportunities = []
        for i, opp in enumerate(self.OPPORTUNITIES):
            opportunities.append(
                HighPayoutOpportunity(
                    id=f"gitcoin_{i}",
                    platform="gitcoin",
                    title=opp["title"],
                    description=opp["description"],
                    category=opp["category"],
                    pay_range=opp["pay_range"],
                    avg_payout=opp["avg_payout"],
                    skill_level=opp["skill_level"],
                    time_to_complete=opp["time_to_complete"],
                    payment_method="crypto (ETH/LINK)",
                    requirements=opp["requirements"],
                    url="https://gitcoin.co",
                    success_rate=0.12,
                )
            )
        return opportunities


class HighPayoutOrchestrator:
    """Orchestrates all high-payout adapters (crypto/web3/AI bug bounty + dev bounties).

    Argentina-confirmed platforms:
    - Immunefi: $140M+ paid, crypto payments, global access
    - Sherlock: $16M pool, USDC payments
    - HackerOne: Global, PayPal/bank transfer (Argentine researcher Daniel Orquera example)
    - OpenAI: $200-$20K, bank transfer
    - Anthropic: Up to $35K, bank transfer
    - Code4rena: $22K-$135K pools, USDC payments
    - Gitcoin: $2K-$50K, crypto payments
    """

    def __init__(self) -> None:
        self.adapters = [
            ImmunefiAdapter(),
            SherlockAdapter(),
            HackerOneAdapter(),
            OpenAIAdapter(),
            AnthropicAdapter(),
            Code4renaAdapter(),
            GitcoinAdapter(),
        ]

    async def fetch_all(self) -> list[HighPayoutOpportunity]:
        """Fetch from all high-payout platforms."""
        all_opps: list[HighPayoutOpportunity] = []
        for adapter in self.adapters:
            try:
                opps = await adapter.fetch_opportunities()
                all_opps.extend(opps)
                logger.info("[HIGH-PAYOUT] %s: %d opportunities", adapter.PLATFORM, len(opps))
            except Exception as e:
                logger.warning("[HIGH-PAYOUT] %s failed: %s", adapter.PLATFORM, e)
        return all_opps

    def get_summary(self) -> dict[str, Any]:
        """Get summary of high-payout landscape."""
        return {
            "platforms": ["immunefi", "sherlock", "hackerone", "openai", "anthropic", "code4rena", "gitcoin"],
            "total_platforms": len(self.adapters),
            "pay_range": "$200 - $250,000 per vulnerability",
            "avg_payout": "$15,000 per successful submission",
            "skill_levels": ["beginner", "intermediate", "advanced", "expert"],
            "payment_methods": ["crypto (USDC/ETH/LINK)", "PayPal", "bank transfer"],
            "barrier": "High skill required, but no geographic restrictions",
            "argentina_note": "All platforms confirmed to work from Argentina. HackerOne has active Argentine researchers (e.g., Daniel Orquera from Río Gallegos). Crypto payments avoid local currency controls.",
            "monthly_potential_conservative": "$2,000 - $10,000",
            "monthly_potential_aggressive": "$10,000 - $100,000+",
            "examples": [
                "Immunefi: $250K for critical vulnerability (July 2026)",
                "HackerOne: $250 reward for hardcoded token (Daniel Orquera, Argentina)",
                "OpenAI: Up to $20K for AI safety vulnerabilities",
                "Anthropic: Up to $35K for universal jailbreaks",
                "Code4rena: $135K audit pool (K2, April 2026)",
            ],
        }


# Singleton
_high_payout_orchestrator: HighPayoutOrchestrator | None = None


def get_high_payout_orchestrator() -> HighPayoutOrchestrator:
    """Get or create the global high-payout orchestrator."""
    global _high_payout_orchestrator
    if _high_payout_orchestrator is None:
        _high_payout_orchestrator = HighPayoutOrchestrator()
    return _high_payout_orchestrator
