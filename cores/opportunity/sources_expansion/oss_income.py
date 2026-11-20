"""Open Source Income family — new monetization circuits (2026-11-19).

Not job boards: funded OSS issues, AI coding competitions, paid
mentorship/stipends, grants and discovery directories. Every entry is a
real, publicly-known program. ``family`` carries the sub-circuit so the
pipeline can distinguish issue bounties from competitions, stipends and
grants — they have very different payout semantics.

Honesty notes baked into metadata:
- Competitions pay by position, not by participation (make.fun, Codeheat).
- Mentorship/stipend programs are seasonal calls, not open task pools.
- Grants fund your own FOSS project — OWNEX itself is private; only a
  standalone OSS component would qualify.
- make.fun terms require public repo + AI-session transcripts + broad
  license — do not submit proprietary OWNEX code.
"""

from cores.opportunity.sources_expansion._common import src

OSS_ISSUE_BOUNTIES = [
    src(
        "Paid Open Source Projects (directory)",
        "https://github.com/kunovsky/paid-open-source-projects",
        "bounties",
        "Community directory of OSS projects that pay for bugs/features; each issue must be re-verified in its origin repo.",
        family="oss_issue_bounty",
        type="directory",
        apply_method="direct_message",
        quality=0.7,
        account=False,
        payout_range="$20-500+/issue",
        priority=8,
        tags=["oss", "bounty", "directory"],
    ),
]

AI_CODING_COMPETITIONS = [
    src(
        "make.fun",
        "https://make.fun",
        "bounties",
        "Coding competitions with USDC prizes (Solana); public HTTP API + MCP server. Winners-only payout; requires public repo + AI-session transcripts + broad license grant.",
        family="ai_competition",
        apply_method="api",
        quality=0.75,
        account=True,
        argentina_ok=True,  # USDC/Solana payout reachable; sanctions screening applies
        payout_range="USDC prizes by position",
        priority=9,
        tags=["competition", "usdc", "ai_agents", "solana"],
    ),
    src(
        "OpenGift",
        "https://opengift.io",
        "bounties",
        "Software challenges, crowdfunding and hackathons with incentives; payout mechanics and Argentina withdrawal unverified.",
        family="ai_competition",
        quality=0.55,
        account=True,
        priority=6,
        tags=["hackathon", "crowdfunding", "experimental"],
    ),
    src(
        "Codeheat (FOSSASIA)",
        "https://codeheat.org",
        "bounties",
        "FOSSASIA open-source contribution contest; PRs/issues evaluated per cycle with prizes — not per-contribution pay.",
        family="ai_competition",
        quality=0.6,
        account=True,
        priority=6,
        tags=["oss", "contest", "fossasia", "seasonal"],
    ),
]

MENTORSHIP_STIPENDS = [
    src(
        "Google Summer of Code",
        "https://summerofcode.withgoogle.com",
        "junior_jobs",
        "Paid OSS mentorship program; published stipends for Argentina (USD 750-3,000 by project size, 2026). Requires proposal + selection; seasonal.",
        family="mentorship",
        apply_method="profile_only",
        quality=0.9,
        account=True,
        argentina_ok=True,
        payout_range="USD 750-3,000/stipend",
        payout_days=30,
        priority=9,
        tags=["stipend", "mentorship", "gsoc", "seasonal", "argentina"],
    ),
    src(
        "LFX Mentorship (Linux Foundation)",
        "https://mentorship.lfx.linuxfoundation.org",
        "junior_jobs",
        "Paid mentorship on LF projects (~12 weeks); some programs stipend ~USD 1,900 (AR, from Jul-2026). Watch for open calls — currently zero accepting.",
        family="mentorship",
        apply_method="profile_only",
        quality=0.85,
        account=True,
        argentina_ok=True,
        payout_range="~USD 1,900/program (stipend tracks)",
        priority=8,
        tags=["stipend", "mentorship", "linux", "seasonal"],
    ),
    src(
        "Outreachy",
        "https://www.outreachy.org",
        "junior_jobs",
        "USD 7,000 paid remote internship (3 months) for underrepresented groups in tech; eligibility-restricted + selection. Next cycle after Dec-2026 round.",
        family="mentorship",
        apply_method="profile_only",
        quality=0.8,
        account=True,
        argentina_ok=True,
        payout_range="USD 7,000/internship",
        priority=7,
        tags=["stipend", "internship", "eligibility_restricted", "seasonal"],
    ),
    src(
        "Summer of Bitcoin",
        "https://www.summerofbitcoin.org",
        "junior_jobs",
        "Bitcoin OSS contributions with BTC stipends; student-focused, evaluation + proposal required. Seasonal.",
        family="mentorship",
        apply_method="profile_only",
        quality=0.7,
        account=True,
        payout_range="BTC stipends by program",
        priority=6,
        tags=["stipend", "bitcoin", "student", "seasonal"],
    ),
]

OSS_GRANTS = [
    src(
        "NLnet Foundation",
        "https://nlnet.ng",
        "bounties",
        "FOSS grants ~EUR 5,000-50,000 for free-software projects; requires published FOSS-licensed result. Next ordinary deadline 2027-01-03. OWNEX is private — only a standalone OSS component qualifies.",
        family="grant",
        apply_method="profile_only",
        quality=0.85,
        account=True,
        payout_range="EUR 5,000-50,000/grant",
        payout_days=60,
        priority=7,
        tags=["grant", "foss", "proposal", "seasonal"],
    ),
    src(
        "Alpha-Omega Project",
        "https://alpha-omega.dev",
        "bounties",
        "Funding for security of critical OSS projects; for established projects with demonstrated impact — not beginner task pool.",
        family="grant",
        apply_method="profile_only",
        quality=0.7,
        account=True,
        priority=5,
        tags=["grant", "security", "oss", "proposal"],
    ),
    src(
        "Sovereign Tech Fund",
        "https://www.sovereign.tech",
        "bounties",
        "Funds open digital infrastructure/dev tools/FOSS security; Challenge mode for teams. Requires substantial scope+impact proposal.",
        family="grant",
        apply_method="profile_only",
        quality=0.7,
        account=True,
        payout_range="project-scale grants",
        priority=5,
        tags=["grant", "infrastructure", "proposal"],
    ),
]

OSS_DISCOVERY = [
    src(
        "OSS.Fund Directory",
        "https://www.oss.fund/directory/",
        "bounties",
        "Directory of ~92 active OSS-funding listings (bounties, grants, crowdfunding, maintainer support). Discovery engine for new monetization circuits — listings are NOT opportunities until verified.",
        family="discovery",
        type="directory",
        apply_method="direct_message",
        quality=0.75,
        account=False,
        priority=8,
        tags=["directory", "oss", "discovery", "meta"],
    ),
]

OSS_INCOME_EXTRA = OSS_ISSUE_BOUNTIES + AI_CODING_COMPETITIONS + MENTORSHIP_STIPENDS + OSS_GRANTS + OSS_DISCOVERY
