"""OWNEX Autonomous Opportunity Discovery — Global Source Database (OwnWork block)

This file is part of the OWNED scope for this session: a curated extension of the
global source database with a focus on the owner's working-style preferences.

Filter used for inclusion in this block:
- Development work, NOT freelance marketplaces.
- Web development / WordPress plugins / projects and bounties in the crypto-dev
  space, plus similar developer-oriented bounty/task surfaces.
- No professional experience required.
- No interview required.
- Argentina-compatible where the platform does not publish a regional restriction.
- Payment options explicitly documented as crypto, stablecoin, or
  bank transfer / PayPal where the platform publishes that; Stripe excluded
  unless the platform itself states Stripe involvement.

This is a SOURCE REGISTRY extension, not verified income.
"""

from __future__ import annotations

from cores.opportunity.global_sources import OpportunityCategory, SourceDefinition

# ═══════════════════════════════════════════════════════════════════════════════
# Catalog-side platform mapping for sources that have a known engine platform.
# Used by adapter prototypes when SourceDefinition itself has no platform field.
# Unmapped sources stay in the catalog and are NOT injected into the engine.
# ═══════════════════════════════════════════════════════════════════════════════

SOURCE_PLATFORM_MAP: dict[str, str] = {
    "GitHub Sponsors / funded issues (public repos)": "github",
    "IssueHunt": "issuehunt",
    "Algora": "algora",
    "Superteam Earn": "superteam",
    "Superteam": "superteam",
    "Opire": "opire",
    "Opyre": "opire",
    "Immunefi": "immunefi",
    "HackerOne": "hackerone",
    "Bugcrowd": "bugcrowd",
    "Intigriti": "intigriti",
    "YesWeHack": "yeswehack",
    "Open Collective": "opencollective",
    "GitHub Bounty Labels": "github",
}

# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 5 (own block): WEB DEV / WORDPRESS / CODER BOUNTIES — priority work
# Development work and bounties reachable without a hiring funnel.
# ═══════════════════════════════════════════════════════════════════════════════

WEB_DEV_SOURCES: list[SourceDefinition] = [
    # ── WordPress / web development bounties ──
    SourceDefinition(
        "WordPress Plugin Bounties (public programs)",
        "https://wordpress.org/plugins/",
        OpportunityCategory.dev_bounty,
        "Public WordPress plugin ecosystem; security and fix bounties surface on "
        "community and security advisories. Treat as discovery until a concrete "
        "program is verified.",
        "platform",
        "profile_only",
        quality_score=0.55,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["wordpress", "plugins", "php", "web", "security"],
        priority=5,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "GitHub Sponsors / funded issues (public repos)",
        "https://github.com/sponsors",
        OpportunityCategory.dev_bounty,
        "Open source maintainers can receive recurring sponsorships; some public "
        "repos surface funded issues or requests. Treat as discovery, not a "
        "guaranteed bounty.",
        "platform",
        "profile_only",
        quality_score=0.5,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["github", "oss", "dev", "sponsorship"],
        priority=5,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "IssueHunt",
        "https://issuehunt.io",
        OpportunityCategory.dev_bounty,
        "Developer-focused bounties attached to public repositories. Public issues with attached bounties are the core mechanic.",
        "platform",
        "profile_only",
        quality_score=0.7,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "github", "dev"],
        priority=7,
        payout_cadence_days=14,
    ),
    SourceDefinition(
        "Bountysource",
        "https://www.bountysource.com",
        OpportunityCategory.dev_bounty,
        "Community-driven bounties for open source issues and features. Public "
        "issue bounties are the main path; treat as discovery if a concrete "
        "program is not verified.",
        "platform",
        "profile_only",
        quality_score=0.6,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "community", "dev"],
        priority=6,
        payout_cadence_days=14,
    ),
    SourceDefinition(
        "SeaPay Bounties",
        "https://seapay.org",
        OpportunityCategory.dev_bounty,
        "Open-source bounty platform oriented to developer tasks and fixes. Treat as discovery until a concrete program is verified.",
        "platform",
        "profile_only",
        quality_score=0.5,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "dev", "community"],
        priority=4,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "Superteam Earn",
        "https://earn.superteam.fun",
        OpportunityCategory.dev_bounty,
        "Solana ecosystem tasks and bounties; public tasks with published rewards "
        "are the core surface. Treat as discovery if the task does not publish a "
        "clear reward.",
        "platform",
        "profile_only",
        quality_score=0.75,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["solana", "crypto", "tasks", "dev", "web3"],
        priority=8,
        payout_cadence_days=14,
    ),
    SourceDefinition(
        "Algora",
        "https://algora.io",
        OpportunityCategory.dev_bounty,
        "Developer task marketplace with crypto payouts on public tasks. Public tasks with attached rewards are the entry surface.",
        "platform",
        "profile_only",
        quality_score=0.65,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["crypto", "tasks", "dev", "web3"],
        priority=7,
        payout_cadence_days=14,
    ),
    SourceDefinition(
        "Opire",
        "https://opire.io",
        OpportunityCategory.dev_bounty,
        "Open-source bounty and donations surface; public issues with attached "
        "bounties are the main path. Treat as discovery if no concrete bounty is "
        "published.",
        "platform",
        "profile_only",
        quality_score=0.6,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "github", "dev"],
        priority=7,
        payout_cadence_days=14,
    ),
    SourceDefinition(
        "Opyre",
        "https://opyre.com",
        OpportunityCategory.dev_bounty,
        "Developer bounties and funded tasks on public repositories. Treat as discovery if a concrete public task is not published.",
        "platform",
        "profile_only",
        quality_score=0.55,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "dev", "github"],
        priority=6,
        payout_cadence_days=14,
    ),
    SourceDefinition(
        "BountyHub",
        "https://bountyhub.io",
        OpportunityCategory.dev_bounty,
        "Developer bounty surface for public issues and tasks. Treat as discovery until a concrete public bounty is verified.",
        "platform",
        "profile_only",
        quality_score=0.5,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "dev", "community"],
        priority=4,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "TaskBounty",
        "https://taskbounty.io",
        OpportunityCategory.dev_bounty,
        "Task/bug bounty surface for dev work. Treat as discovery until a concrete public task is verified.",
        "platform",
        "profile_only",
        quality_score=0.5,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["oss", "bounty", "tasks", "dev"],
        priority=4,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "FreelanceMap (dev tasks, not hiring)",
        "https://freelancemap.eu",
        OpportunityCategory.dev_bounty,
        "Small dev task listings; treat as discovery, not a verified bounty platform, until a concrete public task is verified.",
        "job_board",
        "profile_email",
        quality_score=0.4,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["dev", "tasks", "web"],
        priority=3,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "Stack Overflow Jobs / listings",
        "https://stackoverflow.com/jobs",
        OpportunityCategory.dev_bounty,
        "Developer listings surface; some freelance/contract gigs may appear. Treat as discovery; many listings are hiring, not outcome-based work.",
        "job_board",
        "profile_email",
        quality_score=0.4,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["dev", "job_board", "web"],
        priority=2,
        payout_cadence_days=None,
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY 6 (own block): CRYPTO / WEB3 DEV BOUNTIES AND PAYOUT SURFACES
# Development and security bounty surfaces tied to crypto / web3 projects.
# ═══════════════════════════════════════════════════════════════════════════════

CRYPTO_DEV_SOURCES: list[SourceDefinition] = [
    SourceDefinition(
        "Immunefi",
        "https://immunefi.com",
        OpportunityCategory.bug_bounty,
        "Web3/Crypto bug bounty platform. Public programs with published bounty "
        "ranges. Treat as DISCOVER/COMMIT only after a concrete public program is "
        "verified.",
        "platform",
        "profile_only",
        quality_score=0.85,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["web3", "crypto", "bug_bounty", "security", "defi"],
        priority=9,
        payout_cadence_days=30,
    ),
    SourceDefinition(
        "Hats Finance",
        "https://hats.finance",
        OpportunityCategory.bug_bounty,
        "Web3 bug bounty surface for smart-contract and protocol vulnerabilities. "
        "Public programs with published ranges; treat as discovery if no concrete "
        "program is verified.",
        "platform",
        "profile_only",
        quality_score=0.75,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["web3", "crypto", "bug_bounty", "security", "defi"],
        priority=8,
        payout_cadence_days=30,
    ),
    SourceDefinition(
        "Secure3",
        "https://secure3.io",
        OpportunityCategory.bug_bounty,
        "Web3 security audit marketplace and bounty surface. Treat as discovery until a concrete public audit/bounty is verified.",
        "platform",
        "profile_only",
        quality_score=0.6,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["web3", "crypto", "security", "audit", "dev"],
        priority=6,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "BugRap",
        "https://bugrap.com",
        OpportunityCategory.bug_bounty,
        "Bug bounty surface with web3 exposure. Treat as discovery until a concrete public program is verified.",
        "platform",
        "profile_only",
        quality_score=0.55,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["bug_bounty", "web3", "crypto", "security"],
        priority=5,
        payout_cadence_days=None,
    ),
    SourceDefinition(
        "ChainLove",
        "https://chainlove.org",
        OpportunityCategory.bug_bounty,
        "Community-oriented bounty/sponsorship surface for security work. Treat as discovery until a concrete public bounty is verified.",
        "platform",
        "profile_only",
        quality_score=0.5,
        requires_portfolio=False,
        requires_interview=False,
        requires_experience=False,
        region="global",
        estimated_payout_range="varies",
        tags=["crypto", "security", "bounty", "community"],
        priority=4,
        payout_cadence_days=None,
    ),
]


class OwnWorkSourceRegistry:
    """OwnWork block registry: web-dev + crypto-dev curated sources.

    Kept separate from the main CURATED block by intention: this file is the
    OWNED extension for this session. The main global_sources module keeps a
    single SSOT for all curated sources; this registry mirrors a curated subset
    only for convenience of this block and is intended to be merged into the
    main catalog flow in a later consolidation step.
    """

    CATEGORY_NAME_DEVELOPMENT_WORK = "development_work"
    CATEGORY_NAME_CRYPTO_DEV = "crypto_dev"

    @staticmethod
    def get_development_work_sources() -> list[SourceDefinition]:
        return list(WEB_DEV_SOURCES)

    @staticmethod
    def get_crypto_dev_sources() -> list[SourceDefinition]:
        return list(CRYPTO_DEV_SOURCES)

    @staticmethod
    def get_all() -> list[SourceDefinition]:
        return WEB_DEV_SOURCES + CRYPTO_DEV_SOURCES

    @staticmethod
    def count() -> int:
        return len(WEB_DEV_SOURCES) + len(CRYPTO_DEV_SOURCES)
