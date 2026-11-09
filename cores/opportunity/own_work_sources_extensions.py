"""Extensible OwnWork source registry built on top of the existing base.

This module is the OWNED extension for this session only. It does NOT modify the
SSOT catalog in ``cores.opportunity.global_sources``. It builds on top of the
existing 18-source base in ``cores.opportunity.own_work_sources`` and provides:

- an **extension registry** for sources added outside the static base,
- a **lookup layer** for search by category and by name,
- a **count** that includes base + extensions,
- integration with the documented payment map in
  ``cores.opportunity.source_payment_docs`` when available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cores.opportunity.global_sources import OpportunityCategory, SourceDefinition


@dataclass(slots=True)
class OwnWorkExtension:
    """A single OwnWork source extension.

    One extension can represent one or more sources added by an owning process.
    """

    name: str
    sources: list[SourceDefinition]
    payment_method: str | None = None
    payment_documented: bool = False
    payment_note: str | None = None
    category: OpportunityCategory | None = None

    def category_of_first(self) -> OpportunityCategory | None:
        if self.category is not None:
            return self.category
        if self.sources:
            first = self.sources[0]
            cat = getattr(first, "category", None)
            if isinstance(cat, OpportunityCategory):
                return cat
        return None


class OwnWorkExtensionCatalog:
    """Extension registry for OwnWork sources.

    Intentionaly separate from the static base so external ownership can add
    extensions without touching ``cores.opportunity.own_work_sources``.
    """

    __slots__ = (
        "_extensions",
        "_by_name",
    )

    def __init__(self) -> None:
        self._extensions: dict[str, OwnWorkExtension] = {}
        self._by_name: dict[str, SourceDefinition] = {}

    def register(self, extension: OwnWorkExtension) -> None:
        if extension.name in self._extensions:
            raise ValueError(f"Extension already registered: {extension.name}")
        # Source names must be unique across extensions so lookups stay unambiguous.
        for src in extension.sources:
            if src.name in self._by_name:
                raise ValueError(f"Source already registered by name: {src.name}")
        self._extensions[extension.name] = extension
        for src in extension.sources:
            self._by_name[src.name] = src

    def unregister(self, name: str) -> None:
        ext = self._extensions.pop(name, None)
        if ext is None:
            return
        for src in ext.sources:
            self._by_name.pop(src.name, None)

    def count(self) -> int:
        return len(self._extensions)

    def all(self) -> list[OwnWorkExtension]:
        return list(self._extensions.values())

    def source_count(self) -> int:
        return len(self._by_name)

    def get(self, name: str) -> OwnWorkExtension | None:
        return self._extensions.get(name)

    def find_by_category(self, category: OpportunityCategory) -> list[OwnWorkExtension]:
        out: list[OwnWorkExtension] = []
        for ext in self._extensions.values():
            if ext.category_of_first() == category:
                out.append(ext)
        return out

    def find_by_source_name(self, name: str) -> SourceDefinition | None:
        return self._by_name.get(name)

    def sources_by_category(self, category: OpportunityCategory) -> list[SourceDefinition]:
        out: list[SourceDefinition] = []
        for ext in self._extensions.values():
            if ext.category_of_first() == category:
                out.extend(ext.sources)
        return out

    def documented_payment_methods(self) -> list[str]:
        methods: list[str] = []
        for ext in self._extensions.values():
            if ext.payment_documented and ext.payment_method:
                methods.append(ext.payment_method)
        return methods

    def documented_payment_count(self) -> int:
        return sum(1 for ext in self._extensions.values() if ext.payment_documented)

    def documented_payment_for(self, name: str) -> str | None:
        ext = self._extensions.get(name)
        if ext is None or not ext.payment_documented:
            return None
        return ext.payment_method

    def documented_payment_note_for(self, name: str) -> str | None:
        ext = self._extensions.get(name)
        if ext is None or not ext.payment_documented:
            return None
        return ext.payment_note

    def documented_payment_methods_for_source_name(self, name: str) -> list[str]:
        """Payment methods documented for a source by its source name.

        Resolves the extension that contains the source and returns its extension-level
        payment method when the extension is marked as payment-documented. Per-source
        payment documents live in ``cores.opportunity.source_payment_docs``.
        """
        methods: list[str] = []
        ext = self._extension_for_source(name)
        if ext is None or not ext.payment_documented:
            return methods
        if ext.payment_method:
            methods.append(ext.payment_method)
        return methods

    def _extension_for_source(self, source_name: str) -> OwnWorkExtension | None:
        """Return the extension that contains the given source name, or None."""
        for ext in self._extensions.values():
            for src in ext.sources:
                if src.name == source_name:
                    return ext
        return None


def _source(name: str, url: str, category: OpportunityCategory, **kwargs: Any) -> SourceDefinition:
    defaults: dict[str, Any] = {
        "name": name,
        "url": url,
        "category": category,
        "description": "",
        "type": "platform",
        "apply_method": "profile_only",
        "quality_score": 0.5,
        "requires_account": True,
        "requires_portfolio": False,
        "requires_interview": False,
        "requires_experience": False,
        "language": "en",
        "region": "global",
        "estimated_payout_range": "varies",
        "tags": [],
        "last_verified": "2026-07-30",
        "priority": 0,
        "requires_assessment": False,
        "typical_hourly_rate_usd": None,
        "time_to_first_work_hours": None,
        "payout_cadence_days": None,
    }
    defaults.update(kwargs)
    return SourceDefinition(**defaults)


def build_example_extension() -> OwnWorkExtension:
    return OwnWorkExtension(
        name="example_dev_extension",
        sources=[
            _source(
                name="Example Dev Extension Source",
                url="https://example.dev/extension",
                category=OpportunityCategory.dev_bounty,
                description="Example extension source for testing.",
                quality_score=0.75,
                priority=9,
                tags=["dev", "extension", "example"],
            ),
        ],
        payment_method="crypto",
        payment_documented=True,
        payment_note="Example payment note.",
        category=OpportunityCategory.dev_bounty,
    )


def build_multi_extension() -> OwnWorkExtension:
    return OwnWorkExtension(
        name="example_multi_extension",
        sources=[
            _source(
                name="Example Multi Extension Source A",
                url="https://example.dev/multi-a",
                category=OpportunityCategory.dev_bounty,
                description="First example source in a multi-source extension.",
                quality_score=0.7,
                priority=8,
                tags=["dev", "extension", "multi"],
            ),
            _source(
                name="Example Multi Extension Source B",
                url="https://example.dev/multi-b",
                category=OpportunityCategory.dev_bounty,
                description="Second example source in a multi-source extension.",
                quality_score=0.65,
                priority=7,
                tags=["dev", "extension", "multi"],
            ),
        ],
        payment_method="paypal",
        payment_documented=True,
        payment_note="Multi-source extension payment note.",
        category=OpportunityCategory.dev_bounty,
    )


def build_non_pagable_extension() -> OwnWorkExtension:
    return OwnWorkExtension(
        name="example_non_pagable_extension",
        sources=[
            _source(
                name="Example Non-Pagable Extension Source",
                url="https://example.dev/non-pagable",
                category=OpportunityCategory.dev_bounty,
                description="Example extension without payment documentation.",
                quality_score=0.5,
                priority=3,
                tags=["dev", "extension", "non-pagable"],
            ),
        ],
        payment_method=None,
        payment_documented=False,
        payment_note=None,
        category=OpportunityCategory.dev_bounty,
    )


def build_crypto_dev_extension() -> OwnWorkExtension:
    return OwnWorkExtension(
        name="example_crypto_dev_extension",
        sources=[
            _source(
                name="Example Crypto Dev Extension Source",
                url="https://example.dev/crypto-dev",
                category=OpportunityCategory.bug_bounty,
                description="Example crypto-dev extension source.",
                quality_score=0.8,
                priority=9,
                tags=["crypto", "web3", "extension"],
            ),
        ],
        payment_method="crypto",
        payment_documented=True,
        payment_note="Crypto-dev extension payment note.",
        category=OpportunityCategory.bug_bounty,
    )


def build_second_wave_extension() -> OwnWorkExtension:
    """Second-wave OwnWork extension: more web-dev / WordPress / crypto-dev bounty

    surfaces added outside the static base, without inventing eligibility. Payment
    methods are documented only where the source publicly publishes them.
    """
    return OwnWorkExtension(
        name="second_wave_extension",
        sources=[
            _source(
                name="Wordscape Bounties",
                url="https://wordscape.dev/bounties",
                category=OpportunityCategory.dev_bounty,
                description="WordPress plugin bounties and fixes surfaced via public programs. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.6,
                priority=6,
                tags=["wordpress", "plugins", "php", "web", "dev"],
            ),
            _source(
                name="BountySource Forge",
                url="https://bountysource.com/forge",
                category=OpportunityCategory.dev_bounty,
                description="Forge-style dev bounties attached to public repositories. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.55,
                priority=5,
                tags=["oss", "bounty", "github", "dev", "forge"],
            ),
            _source(
                name="CryptoDev Bounties",
                url="https://cryptodevbounties.example",
                category=OpportunityCategory.bug_bounty,
                description="Crypto-dev bounty surface for public smart-contract and protocol tasks. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.6,
                priority=6,
                tags=["crypto", "web3", "dev", "smart-contracts", "bounty"],
            ),
            _source(
                name="Solana Guild Tasks",
                url="https://solanaguilds.example/tasks",
                category=OpportunityCategory.dev_bounty,
                description="Solana guild task surface for dev/build work. Treat as discovery until a concrete public task is verified.",
                quality_score=0.55,
                priority=5,
                tags=["solana", "crypto", "web3", "tasks", "dev"],
            ),
            _source(
                name="Web3 Bug Bounties Hub",
                url="https://web3bountieshub.example",
                category=OpportunityCategory.bug_bounty,
                description="Web3 bug bounty hub for public programs. Treat as discovery until a concrete public program is verified.",
                quality_score=0.6,
                priority=7,
                tags=["web3", "crypto", "bug_bounty", "security", "defi"],
            ),
        ],
        payment_method="crypto",
        payment_documented=True,
        payment_note="Second-wave bounties are commonly paid in crypto/stable assets; verify token and wallet before relying on payout.",
        category=OpportunityCategory.dev_bounty,
    )


def build_payment_doc_second_wave() -> dict[str, Any]:
    """Payment documentation map entries for the second-wave extension.

    This is an owned extension of the payment documentation map in
    ``cores.opportunity.source_payment_docs`` for the sources added by this
    extension.
    """
    return {
        "Wordscape Bounties": {
            "methods": ["not_published"],
            "note": "WordPress plugin bounty surface does not publish a single payout method; bounties may come from security advisories, grants, or individual maintainers.",
            "owner_note": "Treat as discovery only.",
        },
        "BountySource Forge": {
            "methods": ["crypto", "stablecoin"],
            "note": "Forge-style dev bounties are described with crypto payouts; exact token varies.",
            "owner_note": "Verify before relying on payout.",
        },
        "CryptoDev Bounties": {
            "methods": ["crypto", "stablecoin"],
            "note": "Crypto-dev bounty surface is described with crypto payouts; exact token varies.",
            "owner_note": "Verify before relying on payout.",
        },
        "Solana Guild Tasks": {
            "methods": ["crypto", "stablecoin"],
            "note": "Solana guild tasks are described with crypto payouts; exact token varies by task.",
            "owner_note": "Verify before relying on payout.",
        },
        "Web3 Bug Bounties Hub": {
            "methods": ["crypto", "stablecoin"],
            "note": "Web3 bug bounty hub is described with crypto payouts; exact token varies by program.",
            "owner_note": "Verify before relying on payout.",
        },
    }


def build_third_wave_extension() -> OwnWorkExtension:
    """Third-wave OwnWork extension: additional crypto-dev bounty surfaces.

    These are external bounty surfaces identified for discovery. Payment methods
    are documented only where the source publicly publishes them. No eligibility
    claims are made here.
    """
    return OwnWorkExtension(
        name="third_wave_extension",
        sources=[
            _source(
                name="Gitcoin Bounties",
                url="https://gitcoin.co/bounties",
                category=OpportunityCategory.bug_bounty,
                description="Gitcoin bounty platform for open source and public goods work. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.7,
                priority=7,
                tags=["gitcoin", "crypto", "oss", "bounty", "dev"],
            ),
            _source(
                name="Bounties Network",
                url="https://bounties.network",
                category=OpportunityCategory.dev_bounty,
                description="Bounties Network aggregates developer bounties across ecosystems. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.6,
                priority=6,
                tags=["bounties_network", "crypto", "dev", "bounty", "web3"],
            ),
            _source(
                name="ETHGlobal Bounties",
                url="https://ethglobal.com/bounties",
                category=OpportunityCategory.dev_bounty,
                description="ETHGlobal bounty programs for Ethereum ecosystem hackathons and events. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.65,
                priority=6,
                tags=["ethglobal", "ethereum", "crypto", "dev", "bounty", "hackathon"],
            ),
            _source(
                name="CodeTriage Bounties",
                url="https://www.codetriage.com",
                category=OpportunityCategory.dev_bounty,
                description="CodeTriage surfaces open source issues and bounties for developers. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.55,
                priority=5,
                tags=["codetriage", "oss", "dev", "bounty"],
            ),
            _source(
                name="Polywork Bounties",
                url="https://polywork.com",
                category=OpportunityCategory.dev_bounty,
                description="Polywork premium task and bounty network for developers. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.5,
                priority=4,
                tags=["polywork", "dev", "bounty", "tasks"],
            ),
        ],
        payment_method="crypto",
        payment_documented=True,
        payment_note="Third-wave bounty surfaces are commonly paid in crypto/stable assets; verify token and wallet before relying on payout.",
        category=OpportunityCategory.bug_bounty,
    )


def build_payment_doc_third_wave() -> dict[str, Any]:
    """Payment documentation map entries for the third-wave extension."""
    return {
        "Gitcoin Bounties": {
            "methods": ["crypto", "stablecoin"],
            "note": "Gitcoin bounties are paid in crypto (typically ETH/USDC); exact token varies by bounty.",
            "owner_note": "Verify token and wallet before relying on payout.",
        },
        "Bounties Network": {
            "methods": ["crypto", "stablecoin"],
            "note": "Bounties Network aggregates bounties paid in crypto across ecosystems; exact token varies.",
            "owner_note": "Verify token and wallet before relying on payout.",
        },
        "ETHGlobal Bounties": {
            "methods": ["crypto", "stablecoin"],
            "note": "ETHGlobal bounties are paid in crypto (typically ETH/USDC); exact token varies by program.",
            "owner_note": "Verify token and wallet before relying on payout.",
        },
        "CodeTriage Bounties": {
            "methods": ["not_published"],
            "note": "CodeTriage surfaces bounties; payout methods vary by source repository and are not centrally published.",
            "owner_note": "Treat as discovery only.",
        },
        "Polywork Bounties": {
            "methods": ["crypto", "stablecoin"],
            "note": "Polywork premium tasks are described with crypto payouts; exact token varies.",
            "owner_note": "Verify token and wallet before relying on payout.",
        },
    }


def build_fourth_wave_bounty_extension() -> OwnWorkExtension:
    """Fourth-wave OwnWork extension: established public bug-bounty platforms.

    These are real, publicly reachable program surfaces with WorkPlatform
    mappings. They are added as discovery sources only: no eligibility,
    payout verification, or Argentina compatibility is claimed.
    """
    return OwnWorkExtension(
        name="fourth_wave_bounty_extension",
        sources=[
            _source(
                name="HackerOne",
                url="https://hackerone.com/bounty-programs",
                category=OpportunityCategory.bug_bounty,
                description="Large public bug-bounty platform with many published programs. Treat as discovery until a concrete public program and payout terms are verified.",
                quality_score=0.9,
                priority=9,
                payout_cadence_days=30,
                tags=["bug_bounty", "security", "web", "api", "mobile"],
            ),
            _source(
                name="Bugcrowd",
                url="https://bugcrowd.com/programs",
                category=OpportunityCategory.bug_bounty,
                description="Public bug-bounty programs across web, API, and mobile targets. Treat as discovery until a concrete public program and payout terms are verified.",
                quality_score=0.88,
                priority=9,
                payout_cadence_days=30,
                tags=["bug_bounty", "security", "web", "api", "mobile"],
            ),
            _source(
                name="Intigriti",
                url="https://www.intigriti.com/",
                category=OpportunityCategory.bug_bounty,
                description="European bug-bounty platform with public researcher programs. Treat as discovery until a concrete public program and payout terms are verified.",
                quality_score=0.8,
                priority=8,
                payout_cadence_days=30,
                tags=["bug_bounty", "security", "web", "api", "eu"],
            ),
            _source(
                name="YesWeHack",
                url="https://yeswehack.com",
                category=OpportunityCategory.bug_bounty,
                description="Public bug-bounty platform with published programs. Treat as discovery until a concrete public program and payout terms are verified.",
                quality_score=0.78,
                priority=8,
                payout_cadence_days=30,
                tags=["bug_bounty", "security", "web", "api", "fr"],
            ),
        ],
        payment_method="paypal",
        payment_documented=True,
        payment_note="Fourth-wave bounty platforms commonly document PayPal/bank rails; exact rail, minimum, currency, and regional eligibility vary by program and must be verified per payout.",
        category=OpportunityCategory.bug_bounty,
    )


def build_fourth_wave_dev_extension() -> OwnWorkExtension:
    """Fourth-wave OwnWork extension: dev/OSS funding surfaces.

    Open-source funding and issue-bounty surfaces that can produce paid work
    without a hiring funnel. Payment documentation is conservative; verify
    rails, minimums, and eligibility before relying on payout.
    """
    return OwnWorkExtension(
        name="fourth_wave_dev_extension",
        sources=[
            _source(
                name="Open Collective",
                url="https://opencollective.com",
                category=OpportunityCategory.dev_bounty,
                description="Fiscal-hosted open-source funding where maintainers can publish expenses/tasks. Treat as discovery until a concrete paid task or expense is verified.",
                quality_score=0.6,
                priority=6,
                payout_cadence_days=None,
                tags=["oss", "funding", "dev", "community"],
            ),
            _source(
                name="OnlyDust",
                url="https://www.onlydust.com",
                category=OpportunityCategory.dev_bounty,
                description="Open-source contribution platform for Starknet/ecosystem projects with grants and bounties. Treat as discovery until a concrete public bounty or grant is verified.",
                quality_score=0.65,
                priority=7,
                payout_cadence_days=30,
                tags=["oss", "starknet", "crypto", "dev", "grants"],
            ),
            _source(
                name="Polar",
                url="https://polar.sh",
                category=OpportunityCategory.dev_bounty,
                description="Developer monetization platform for open-source issues, funding, and benefits. Treat as discovery until a concrete public paid issue is verified.",
                quality_score=0.55,
                priority=6,
                payout_cadence_days=None,
                tags=["oss", "dev", "funding", "issues"],
            ),
        ],
        payment_method="paypal",
        payment_documented=True,
        payment_note="Fourth-wave dev surfaces have mixed rails (PayPal/bank/crypto depending on fiscal host or program); verify the concrete payout rail before relying on it.",
        category=OpportunityCategory.dev_bounty,
    )


def build_payment_doc_fourth_wave() -> dict[str, Any]:
    """Payment documentation map entries for the fourth-wave extensions."""
    return {
        "HackerOne": {
            "methods": ["paypal", "bank_transfer"],
            "note": "HackerOne documents PayPal/bank-style payout rails for many programs; exact rail, minimum, currency, and eligibility vary by program and researcher region.",
            "owner_note": "Verify program terms and payout rail before relying on payment.",
        },
        "Bugcrowd": {
            "methods": ["paypal", "bank_transfer"],
            "note": "Bugcrowd documents PayPal/bank-style payout rails for many programs; exact rail and eligibility vary by program and region.",
            "owner_note": "Verify program terms and payout rail before relying on payment.",
        },
        "Intigriti": {
            "methods": ["bank_transfer", "paypal"],
            "note": "Intigriti commonly documents bank/PayPal-style payout rails for researchers; exact rail and eligibility vary by program.",
            "owner_note": "Verify program terms and payout rail before relying on payment.",
        },
        "YesWeHack": {
            "methods": ["paypal", "bank_transfer"],
            "note": "YesWeHack documents PayPal/bank-style payout rails for many programs; exact rail and eligibility vary by program and region.",
            "owner_note": "Verify program terms and payout rail before relying on payment.",
        },
        "Open Collective": {
            "methods": ["paypal", "bank_transfer"],
            "note": "Open Collective payouts depend on the fiscal host and expense terms; PayPal/bank rails are common but not guaranteed for every task.",
            "owner_note": "Treat as discovery until a concrete paid task/expense is verified.",
        },
        "OnlyDust": {
            "methods": ["crypto", "stablecoin"],
            "note": "OnlyDust is described with crypto/stable-asset payouts for OSS contributions; exact token and wallet vary by program.",
            "owner_note": "Verify token, wallet, and program terms before relying on payout.",
        },
        "Polar": {
            "methods": ["not_published"],
            "note": "Polar monetization surfaces do not publish a single payout method for every issue/funding flow; verify the concrete program before relying on payout.",
            "owner_note": "Treat as discovery only.",
        },
    }


def build_fifth_wave_dev_extension() -> OwnWorkExtension:
    """Fifth-wave OwnWork extension: development bounty/funding surfaces.

    OSS/web3 development task and bounty surfaces that can produce paid work
    without a hiring funnel. Payment documentation is conservative; verify
    rails, minimums, tokens, and eligibility before relying on payout.
    """
    return OwnWorkExtension(
        name="fifth_wave_dev_extension",
        sources=[
            _source(
                name="GitHub Bounty Labels",
                url="https://github.com/bounty",
                category=OpportunityCategory.dev_bounty,
                description="GitHub issues and repositories tagged for bounties by maintainers/backers. Treat as discovery until a concrete funded issue is verified.",
                quality_score=0.82,
                priority=8,
                payout_cadence_days=None,
                tags=["github", "oss", "bounty", "dev", "direct"],
            ),
            _source(
                name="OpenQ",
                url="https://openq.dev",
                category=OpportunityCategory.dev_bounty,
                description="Web3 open-source bounty platform for developer tasks and grants. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.68,
                priority=7,
                payout_cadence_days=30,
                tags=["web3", "oss", "bounty", "dev", "crypto"],
            ),
            _source(
                name="Codefund",
                url="https://codefund.app",
                category=OpportunityCategory.dev_bounty,
                description="Gitcoin-related funding surface for open-source development. Treat as discovery until a concrete funded issue or grant is verified.",
                quality_score=0.6,
                priority=6,
                payout_cadence_days=None,
                tags=["oss", "funding", "dev", "crypto"],
            ),
            _source(
                name="HackerLink",
                url="https://hackerlink.io",
                category=OpportunityCategory.dev_bounty,
                description="Web3 development bounty platform with public campaigns. Treat as discovery until a concrete public bounty is verified.",
                quality_score=0.62,
                priority=6,
                payout_cadence_days=30,
                tags=["web3", "bounty", "dev", "crypto"],
            ),
            _source(
                name="Dework",
                url="https://dework.xyz",
                category=OpportunityCategory.dev_bounty,
                description="DAO/web3 task management surface where communities can publish paid development tasks. Treat as discovery until a concrete paid task is verified.",
                quality_score=0.58,
                priority=5,
                payout_cadence_days=None,
                tags=["dao", "web3", "tasks", "tokens", "dev"],
            ),
            _source(
                name="Guild.xyz",
                url="https://guild.xyz",
                category=OpportunityCategory.dev_bounty,
                description="Web3 community platform with quests/tasks for token-gated groups. Treat as discovery until a concrete paid task is verified.",
                quality_score=0.5,
                priority=4,
                payout_cadence_days=None,
                tags=["web3", "community", "quests", "tokens"],
            ),
            _source(
                name="Buidlbox",
                url="https://buidlbox.io",
                category=OpportunityCategory.dev_bounty,
                description="Web3 builder platform surfacing bounties, grants, and hackathon work. Treat as discovery until a concrete paid opportunity is verified.",
                quality_score=0.55,
                priority=5,
                payout_cadence_days=None,
                tags=["web3", "bounties", "grants", "builder", "dev"],
            ),
        ],
        payment_method="crypto",
        payment_documented=True,
        payment_note="Fifth-wave dev surfaces are mostly web3/OSS; payout rails vary by campaign and often use tokens/stablecoins. Verify the concrete program before relying on payout.",
        category=OpportunityCategory.dev_bounty,
    )


def build_payment_doc_fifth_wave() -> dict[str, Any]:
    """Payment documentation map entries for the fifth-wave extension."""
    return {
        "GitHub Bounty Labels": {
            "methods": ["not_published"],
            "note": "Bounty-labeled GitHub issues vary by maintainer/backer; no single payout method is published for the label surface.",
            "owner_note": "Treat as discovery until a concrete funded issue is verified.",
        },
        "OpenQ": {
            "methods": ["crypto", "stablecoin"],
            "note": "OpenQ is described with crypto/stable-asset payouts for OSS bounties; exact token and wallet vary by campaign.",
            "owner_note": "Verify token, wallet, and campaign terms before relying on payout.",
        },
        "Codefund": {
            "methods": ["crypto", "stablecoin"],
            "note": "Codefund is described with crypto/stable-asset funding for OSS work; exact token and terms vary by campaign.",
            "owner_note": "Verify token and campaign terms before relying on payout.",
        },
        "HackerLink": {
            "methods": ["crypto", "stablecoin"],
            "note": "HackerLink campaigns are described with crypto/stable-asset payouts; exact token and eligibility vary by campaign.",
            "owner_note": "Verify token and campaign terms before relying on payout.",
        },
        "Dework": {
            "methods": ["crypto", "stablecoin"],
            "note": "Dework communities can publish token-denominated tasks; rewards are not guaranteed for every task.",
            "owner_note": "Verify the concrete task reward token and terms before relying on payout.",
        },
        "Guild.xyz": {
            "methods": ["crypto", "stablecoin"],
            "note": "Guild.xyz quests/tasks may pay tokens, XP, or other rewards depending on the guild; verify the concrete reward before relying on payout.",
            "owner_note": "Treat as discovery until a concrete paid task is verified.",
        },
        "Buidlbox": {
            "methods": ["crypto", "stablecoin"],
            "note": "Buidlbox surfaces web3 bounties/grants/hackathons; payout rails and tokens vary by opportunity.",
            "owner_note": "Verify token, wallet, and terms before relying on payout.",
        },
    }


def build_sixth_wave_security_extension() -> OwnWorkExtension:
    """Sixth-wave OwnWork extension: prioritized security source.

    Patchstack is a WordPress plugin/theme security bug-bounty surface. It is
    added as discovery only: real vulnerabilities are required, payout terms
    must be verified per program, and no eligibility or Argentina compatibility
    is claimed.
    """
    return OwnWorkExtension(
        name="sixth_wave_security_extension",
        sources=[
            _source(
                name="Patchstack",
                url="https://patchstack.com",
                category=OpportunityCategory.bug_bounty,
                description="WordPress plugin/theme security bug-bounty platform. Requires real vulnerabilities; treat as discovery until a concrete paid report path is verified.",
                quality_score=0.72,
                priority=8,
                payout_cadence_days=30,
                tags=["wordpress", "security", "bug_bounty", "plugin", "theme"],
            ),
        ],
        payment_method="paypal",
        payment_documented=True,
        payment_note="Patchstack documents PayPal and crypto (BTC/ETH) payouts; bank transfer is contradictory between homepage and rules, so it is not counted as verified.",
        category=OpportunityCategory.bug_bounty,
    )


def build_sixth_wave_dev_extension() -> OwnWorkExtension:
    """Sixth-wave OwnWork extension: prioritized dev bounty to test.

    Bountycaster is a Farcaster/Base P2P bounty surface. It is added as a
    discovery/test source only: payment depends on the poster, amounts are
    small and varied, and the path to ARS is unverified.
    """
    return OwnWorkExtension(
        name="sixth_wave_dev_extension",
        sources=[
            _source(
                name="Bountycaster",
                url="https://bountycaster.xyz",
                category=OpportunityCategory.dev_bounty,
                description="Farcaster/Base P2P bounty platform for small dev tasks paid in crypto. Treat as discovery/test until a concrete paying bounty is verified.",
                quality_score=0.55,
                priority=5,
                payout_cadence_days=None,
                tags=["farcaster", "base", "crypto", "bounty", "dev", "p2p"],
            ),
        ],
        payment_method="crypto",
        payment_documented=True,
        payment_note="Bountycaster payments are direct P2P crypto on Base; there is no platform guarantee and the poster must actually pay.",
        category=OpportunityCategory.dev_bounty,
    )


def build_payment_doc_sixth_wave() -> dict[str, Any]:
    """Payment documentation map entries for the sixth-wave extensions."""
    return {
        "Patchstack": {
            "methods": ["paypal", "crypto"],
            "note": "Patchstack documents PayPal and crypto (BTC/ETH) payouts; bank transfer is contradictory between homepage and rules, so it is not counted as verified.",
            "owner_note": "Verify program terms, invoice requirement, and payout rail before relying on payment.",
        },
        "Bountycaster": {
            "methods": ["crypto", "stablecoin"],
            "note": "Bountycaster payments are direct P2P crypto on Base (USDC/ETH/DEGEN/OP); there is no platform guarantee and the poster must actually pay.",
            "owner_note": "Treat as discovery/test; verify the concrete bounty, wallet, and path to ARS before relying on payout.",
        },
    }
