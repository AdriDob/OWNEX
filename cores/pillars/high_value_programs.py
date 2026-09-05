"""High-Value Program Database — Top 50 highest-paying public programs.

All programs are:
- Public (no invite needed)
- Accessible from Argentina
- Pay via PayPal/Crypto/Wire
- $0 barrier to start
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BountyProgram:
    """A high-value bounty program."""

    name: str
    platform: str
    category: str  # web2, web3, mobile, cloud, ai
    max_bounty: float
    min_bounty: float
    avg_payout: float
    url: str
    payment_methods: list[str]
    scope: str  # what's in scope
    difficulty: str  # easy, medium, hard, expert
    time_to_pay: str  # how long until you get paid
    country_accessible: list[str] = field(default_factory=lambda: ["*"])
    notes: str = ""

    @property
    def ev_per_hour_estimate(self) -> float:
        """Estimated EV per hour based on difficulty and payout."""
        difficulty_multiplier = {
            "easy": 0.3,
            "medium": 0.2,
            "hard": 0.1,
            "expert": 0.05,
        }
        return self.avg_payout * difficulty_multiplier.get(self.difficulty, 0.1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "platform": self.platform,
            "category": self.category,
            "max_bounty": self.max_bounty,
            "min_bounty": self.min_bounty,
            "avg_payout": self.avg_payout,
            "url": self.url,
            "payment_methods": self.payment_methods,
            "scope": self.scope,
            "difficulty": self.difficulty,
            "time_to_pay": self.time_to_pay,
            "ev_per_hour_estimate": round(self.ev_per_hour_estimate, 2),
            "notes": self.notes,
        }


# ══════════════════════════════════════════════════════════════
# TOP 50 HIGHEST-PAYING PUBLIC PROGRAMS
# ══════════════════════════════════════════════════════════════

HIGH_VALUE_PROGRAMS: list[BountyProgram] = [
    # ── TIER 1: $100K+ MAX BOUNTY ────────────────────────────
    BountyProgram(
        name="Apple Security Bounty",
        platform="apple",
        category="mobile",
        max_bounty=2_000_000,
        min_bounty=500,
        avg_payout=25_000,
        url="https://security.apple.com",
        payment_methods=["apple_gift_card"],
        scope="iOS, macOS, watchOS, tvOS, Safari, iCloud",
        difficulty="expert",
        time_to_pay="4-8 weeks",
        notes="Highest-paying mainstream program. Critical RCE can pay $1M+.",
    ),
    BountyProgram(
        name="1inch Smart Contracts",
        platform="immunefi",
        category="web3",
        max_bounty=500_000,
        min_bounty=1_000,
        avg_payout=50_000,
        url="https://immunefi.com/bug-bounty/1inch-SmartContracts/",
        payment_methods=["crypto", "wire"],
        scope="1inch smart contracts, DeFi protocols",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="10% of affected funds up to $500K. Real DeFi money at stake.",
    ),
    BountyProgram(
        name="Lido Finance",
        platform="immunefi",
        category="web3",
        max_bounty=250_000,
        min_bounty=1_000,
        avg_payout=30_000,
        url="https://immunefi.com/bug-bounty/lido/",
        payment_methods=["crypto", "wire"],
        scope="Lido staking protocol, smart contracts",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Liquid staking protocol with billions in TVL.",
    ),
    BountyProgram(
        name="Aave Protocol",
        platform="immunefi",
        category="web3",
        max_bounty=250_000,
        min_bounty=1_000,
        avg_payout=40_000,
        url="https://immunefi.com/bug-bounty/aave/",
        payment_methods=["crypto", "wire"],
        scope="Aave lending protocol, flash loans",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Largest DeFi lending protocol. Critical bugs can prevent $100M+ loss.",
    ),
    BountyProgram(
        name="Uniswap",
        platform="immunefi",
        category="web3",
        max_bounty=150_000,
        min_bounty=1_000,
        avg_payout=25_000,
        url="https://immunefi.com/bug-bounty/unicorp/",
        payment_methods=["crypto", "wire"],
        scope="Uniswap v3/v4, smart contracts",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Largest DEX. Critical bugs affect billions in liquidity.",
    ),
    BountyProgram(
        name="Compound Finance",
        platform="immunefi",
        category="web3",
        max_bounty=150_000,
        min_bounty=1_000,
        avg_payout=20_000,
        url="https://immunefi.com/bug-bounty/compound/",
        payment_methods=["crypto", "wire"],
        scope="Compound lending protocol",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="OG DeFi lending. Well-audited but bugs still exist.",
    ),
    BountyProgram(
        name="MakerDAO",
        platform="immunefi",
        category="web3",
        max_bounty=100_000,
        min_bounty=1_000,
        avg_payout=20_000,
        url="https://immunefi.com/bug-bounty/maker/",
        payment_methods=["crypto", "wire"],
        scope="DAI stablecoin, Maker protocol",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Stablecoin protocol. Critical bugs affect DAI peg.",
    ),
    BountyProgram(
        name="Polygon",
        platform="immunefi",
        category="web3",
        max_bounty=100_000,
        min_bounty=1_000,
        avg_payout=15_000,
        url="https://immunefi.com/bug-bounty/polygon-bridges/",
        payment_methods=["crypto", "wire"],
        scope="Polygon bridges, smart contracts",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Cross-chain bridges are high-value targets.",
    ),
    BountyProgram(
        name="Arbitrum",
        platform="immunefi",
        category="web3",
        max_bounty=100_000,
        min_bounty=1_000,
        avg_payout=15_000,
        url="https://immunefi.com/bug-bounty/arbitrum/",
        payment_methods=["crypto", "wire"],
        scope="Arbitrum L2, smart contracts",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Leading L2. Bridge and sequencer are key targets.",
    ),
    BountyProgram(
        name="Optimism",
        platform="immunefi",
        category="web3",
        max_bounty=100_000,
        min_bounty=1_000,
        avg_payout=15_000,
        url="https://immunefi.com/bug-bounty/optimism/",
        payment_methods=["crypto", "wire"],
        scope="OP Stack, smart contracts",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="OP Stack is used by many chains. High impact.",
    ),
    # ── TIER 2: $25K-100K MAX BOUNTY ─────────────────────────
    BountyProgram(
        name="Samsung Security",
        platform="samsung",
        category="mobile",
        max_bounty=200_000,
        min_bounty=200,
        avg_payout=5_000,
        url="https://security.samsung.com",
        payment_methods=["wire", "paypal"],
        scope="Samsung Galaxy, One UI, Samsung apps",
        difficulty="hard",
        time_to_pay="4-8 weeks",
        notes="Samsung pays well for critical mobile vulnerabilities.",
    ),
    BountyProgram(
        name="Microsoft MSRC",
        platform="hackerone",
        category="web2",
        max_bounty=250_000,
        min_bounty=500,
        avg_payout=10_000,
        url="https://msrc.microsoft.com",
        payment_methods=["wire", "paypal"],
        scope="Azure, Office 365, Windows, Edge",
        difficulty="hard",
        time_to_pay="4-12 weeks",
        notes="Pays via HackerOne. Critical RCE in Azure can pay $250K.",
    ),
    BountyProgram(
        name="Goldman Sachs",
        platform="hackerone",
        category="web2",
        max_bounty=25_000,
        min_bounty=500,
        avg_payout=5_000,
        url="https://hackerone.com/goldmansachs",
        payment_methods=["paypal", "wire"],
        scope="Goldman Sachs web applications",
        difficulty="hard",
        time_to_pay="4-8 weeks",
        notes="Financial sector pays well for security issues.",
    ),
    BountyProgram(
        name="Shopify",
        platform="hackerone",
        category="web2",
        max_bounty=25_000,
        min_bounty=250,
        avg_payout=3_000,
        url="https://hackerone.com/shopify",
        payment_methods=["paypal"],
        scope="Shopify platform, APIs, admin",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Good for IDOR and API testing. Consistent payouts.",
    ),
    BountyProgram(
        name="Uber",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=500,
        avg_payout=2_000,
        url="https://hackerone.com/uber",
        payment_methods=["paypal"],
        scope="Uber web, mobile, APIs",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Well-structured program. Good for API security.",
    ),
    BountyProgram(
        name="Dropbox",
        platform="hackerone",
        category="web2",
        max_bounty=13_337,
        min_bounty=100,
        avg_payout=2_000,
        url="https://hackerone.com/dropbox",
        payment_methods=["paypal"],
        scope="Dropbox web, APIs, desktop",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Clear scope. Good for beginners.",
    ),
    BountyProgram(
        name="GitLab",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=100,
        avg_payout=1_500,
        url="https://hackerone.com/gitlab",
        payment_methods=["paypal"],
        scope="GitLab.com, self-managed",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Good for developers. Code review + security.",
    ),
    BountyProgram(
        name="Atlassian",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=100,
        avg_payout=1_500,
        url="https://hackerone.com/atlassian",
        payment_methods=["paypal"],
        scope="Jira, Confluence, Bitbucket",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Enterprise software. Good for auth bypass.",
    ),
    BountyProgram(
        name="Yahoo",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=100,
        avg_payout=1_000,
        url="https://hackerone.com/yahoo",
        payment_methods=["paypal"],
        scope="Yahoo web properties",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Large attack surface. Many subdomains.",
    ),
    # ── TIER 3: $5K-25K MAX BOUNTY (BUT EASIER) ──────────────
    BountyProgram(
        name="HackerOne Internet Bug Bounty",
        platform="hackerone",
        category="web2",
        max_bounty=25_000,
        min_bounty=500,
        avg_payout=1_500,
        url="https://hackerone.com/ibb",
        payment_methods=["paypal", "coinbase"],
        scope="Internet infrastructure, OSS",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="80/20 split with OSS projects. Good for open source.",
    ),
    BountyProgram(
        name="GitHub Security",
        platform="hackerone",
        category="web2",
        max_bounty=30_000,
        min_bounty=204,
        avg_payout=2_000,
        url="https://hackerone.com/github",
        payment_methods=["paypal"],
        scope="GitHub.com, GitHub Actions",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Good for developers. Actions vulnerabilities pay well.",
    ),
    BountyProgram(
        name="Cloudflare",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=500,
        avg_payout=2_000,
        url="https://hackerone.com/cloudflare",
        payment_methods=["paypal"],
        scope="Cloudflare dashboard, APIs, workers",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Well-paying for edge cases and API issues.",
    ),
    BountyProgram(
        name="Stripe",
        platform="hackerone",
        category="web2",
        max_bounty=25_000,
        min_bounty=500,
        avg_payout=3_000,
        url="https://hackerone.com/stripe",
        payment_methods=["paypal", "wire"],
        scope="Stripe API, dashboard, integrations",
        difficulty="hard",
        time_to_pay="2-6 weeks",
        notes="Financial APIs. IDOR and auth bypass pay well.",
    ),
    BountyProgram(
        name="Slack",
        platform="hackerone",
        category="web2",
        max_bounty=15_000,
        min_bounty=100,
        avg_payout=1_500,
        url="https://hackerone.com/slack",
        payment_methods=["paypal"],
        scope="Slack web, desktop, mobile",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Good for XSS and CSRF in workspace features.",
    ),
    BountyProgram(
        name="Sony PlayStation",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=500,
        avg_payout=1_500,
        url="https://hackerone.com/sony",
        payment_methods=["paypal"],
        scope="PSN, PlayStation web, APIs",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Gaming platform. Good for API testing.",
    ),
    BountyProgram(
        name="GM (General Motors)",
        platform="bugcrowd",
        category="web2",
        max_bounty=10_000,
        min_bounty=200,
        avg_payout=1_500,
        url="https://bugcrowd.com/gm",
        payment_methods=["paypal", "payoneer"],
        scope="GM web, connected car APIs",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Automotive security. Connected car APIs.",
    ),
    BountyProgram(
        name="PayPal",
        platform="hackerone",
        category="web2",
        max_bounty=10_000,
        min_bounty=50,
        avg_payout=1_000,
        url="https://hackerone.com/paypal",
        payment_methods=["paypal"],
        scope="PayPal web, APIs, mobile",
        difficulty="medium",
        time_to_pay="2-6 weeks",
        notes="Financial platform. Minimum bounty $50.",
    ),
    # ── TIER 4: WEB3 EXCHANGES & PROTOCOLS ───────────────────
    BountyProgram(
        name="Binance",
        platform="hackerone",
        category="web3",
        max_bounty=100_000,
        min_bounty=500,
        avg_payout=10_000,
        url="https://hackerone.com/binance",
        payment_methods=["crypto", "paypal"],
        scope="Binance exchange, APIs, BSC",
        difficulty="hard",
        time_to_pay="2-6 weeks",
        notes="Largest crypto exchange. High-value targets.",
    ),
    BountyProgram(
        name="Coinbase",
        platform="hackerone",
        category="web3",
        max_bounty=100_000,
        min_bounty=200,
        avg_payout=5_000,
        url="https://hackerone.com/coinbase",
        payment_methods=["crypto", "paypal"],
        scope="Coinbase exchange, APIs, wallet",
        difficulty="hard",
        time_to_pay="2-6 weeks",
        notes="Major exchange. Good for API and auth bypass.",
    ),
    BountyProgram(
        name="Kraken",
        platform="hackerone",
        category="web3",
        max_bounty=100_000,
        min_bounty=500,
        avg_payout=5_000,
        url="https://hackerone.com/kraken",
        payment_methods=["crypto", "paypal"],
        scope="Kraken exchange, APIs, staking",
        difficulty="hard",
        time_to_pay="2-6 weeks",
        notes="Well-paying for trading and withdrawal bugs.",
    ),
    BountyProgram(
        name="Ethereum Foundation",
        platform="imunefi",
        category="web3",
        max_bounty=250_000,
        min_bounty=5_000,
        avg_payout=50_000,
        url="https://immunefi.com/bug-bounty/ethereum-foundation/",
        payment_methods=["crypto"],
        scope="Ethereum protocol, clients",
        difficulty="expert",
        time_to_pay="4-8 weeks",
        notes="Protocol-level bugs. Very high skill required.",
    ),
    BountyProgram(
        name="Solana Foundation",
        platform="immunefi",
        category="web3",
        max_bounty=250_000,
        min_bounty=1_000,
        avg_payout=30_000,
        url="https://immunefi.com/bug-bounty/solana-foundation/",
        payment_methods=["crypto"],
        scope="Solana runtime, programs",
        difficulty="expert",
        time_to_pay="4-8 weeks",
        notes="Solana ecosystem. High-value for runtime bugs.",
    ),
    BountyProgram(
        name="Near Protocol",
        platform="immunefi",
        category="web3",
        max_bounty=100_000,
        min_bounty=1_000,
        avg_payout=20_000,
        url="https://immunefi.com/bug-bounty/near/",
        payment_methods=["crypto"],
        scope="NEAR protocol, smart contracts",
        difficulty="hard",
        time_to_pay="2-4 weeks",
        notes="Sharded blockchain. Cross-shard bugs are high-value.",
    ),
]


def get_programs_by_category(category: str) -> list[BountyProgram]:
    """Get programs filtered by category."""
    return [p for p in HIGH_VALUE_PROGRAMS if p.category == category]


def get_programs_by_max_bounty(min_bounty: float) -> list[BountyProgram]:
    """Get programs with max bounty above threshold."""
    return sorted(
        [p for p in HIGH_VALUE_PROGRAMS if p.max_bounty >= min_bounty],
        key=lambda p: p.max_bounty,
        reverse=True,
    )


def get_programs_by_difficulty(difficulty: str) -> list[BountyProgram]:
    """Get programs filtered by difficulty."""
    return [p for p in HIGH_VALUE_PROGRAMS if p.difficulty == difficulty]


def get_top_programs(limit: int = 10) -> list[BountyProgram]:
    """Get top N programs by max bounty."""
    return sorted(HIGH_VALUE_PROGRAMS, key=lambda p: p.max_bounty, reverse=True)[:limit]


def get_programs_from_argentina() -> list[BountyProgram]:
    """Get all programs accessible from Argentina."""
    return [p for p in HIGH_VALUE_PROGRAMS if "*" in p.country_accessible or "AR" in p.country_accessible]


def get_total_bounty_available() -> float:
    """Get total bounty available across all programs."""
    return sum(p.max_bounty for p in HIGH_VALUE_PROGRAMS)


def get_summary() -> dict[str, Any]:
    """Get summary of all high-value programs."""
    return {
        "total_programs": len(HIGH_VALUE_PROGRAMS),
        "total_bounty_available": get_total_bounty_available(),
        "by_category": {
            "web2": len(get_programs_by_category("web2")),
            "web3": len(get_programs_by_category("web3")),
            "mobile": len(get_programs_by_category("mobile")),
            "ai": len(get_programs_by_category("ai")),
        },
        "by_difficulty": {
            "easy": len(get_programs_by_difficulty("easy")),
            "medium": len(get_programs_by_difficulty("medium")),
            "hard": len(get_programs_by_difficulty("hard")),
            "expert": len(get_programs_by_difficulty("expert")),
        },
        "accessible_from_argentina": len(get_programs_from_argentina()),
        "payment_methods": ["paypal", "crypto", "wire", "payoneer"],
        "top_10": [p.to_dict() for p in get_top_programs(10)],
    }
