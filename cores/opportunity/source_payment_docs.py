"""Documented payment methods for curated sources (OWNEX-owned extension).

This module documents, where a source PUBLICLY states a payment method, which
methods appear. It does NOT verify PayPal, bank transfer, crypto, or stablecoin
compatibility for any specific user or account, and it does NOT claim that a
source will pay to Argentina. It is a SOURCE REGISTRY extension only.

Payment method labels used here are documentation-friendly labels, not
automated verdict inputs. The engine's payment compatibility layer remains the
place that evaluates compatibility for a concrete account/profile.
"""

from __future__ import annotations

from typing import Any

# Publicly documented payment options per source, where the platform states them.
# Empty list / "not_published" means the source does not clearly publish a method
# from the owner's preferred set (crypto / stablecoin / bank transfer / PayPal),
# or publishes only a vague "varies" statement.
PaymentDoc = dict[str, Any]

KNOWN_PAYMENT_METHODS: dict[str, PaymentDoc] = {
    # ── Web dev / dev bounty surfaces ──
    "IssueHunt": {
        "methods": ["paypal"],
        "note": "Public bounties surface on IssueHunt; payment terms vary by bounty and maintainer.",
        "owner_note": "Verify before relying on payout.",
    },
    "Bountysource": {
        "methods": ["paypal", "bank_transfer"],
        "note": "Community bounties on Bountysource historically support PayPal- and bank-related payouts depending on the bounty and region.",
        "owner_note": "Terms vary; verify before relying on payout.",
    },
    "Superteam Earn": {
        "methods": ["crypto", "stablecoin"],
        "note": "Solana ecosystem tasks commonly pay in crypto/stable tokens; exact token varies by task.",
        "owner_note": "On-chain payout is typical; confirm token and wallet before relying on payout.",
    },
    "Algora": {
        "methods": ["crypto", "stablecoin"],
        "note": "Algora tasks are described as crypto-paid; exact token varies by task.",
        "owner_note": "On-chain payout is typical; confirm token and wallet before relying on payout.",
    },
    "Opire": {
        "methods": ["crypto", "stablecoin"],
        "note": "Opire is described as an open-source bounty/donation surface with crypto-adjacent payouts; exact method varies.",
        "owner_note": "Verify before relying on payout.",
    },
    "Opyre": {
        "methods": ["crypto", "stablecoin"],
        "note": "Opyre is described with crypto payouts on public tasks; exact token varies.",
        "owner_note": "Verify before relying on payout.",
    },
    "BountyHub": {
        "methods": ["crypto", "stablecoin"],
        "note": "BountyHub is described as a crypto-adjacent bounty surface; exact method varies.",
        "owner_note": "Verify before relying on payout.",
    },
    "TaskBounty": {
        "methods": ["crypto", "stablecoin"],
        "note": "TaskBounty is described with crypto payouts; exact method varies.",
        "owner_note": "Verify before relying on payout.",
    },
    "SeaPay Bounties": {
        "methods": ["crypto", "stablecoin"],
        "note": "SeaPay is described as a bounty-oriented surface; exact method varies.",
        "owner_note": "Verify before relying on payout.",
    },
    "GitHub Sponsors / funded issues (public repos)": {
        "methods": ["not_published"],
        "note": "GitHub Sponsors supports multiple payout rails depending on maintainer setup, region, and Stripe Connect eligibility; public funded issues are treated as discovery only.",
        "owner_note": "Treat as discovery only; do not rely on payout without verifying a concrete funded issue.",
    },
    "GitHub Sponsors": {
        "methods": ["paypal", "bank_transfer"],
        "note": "GitHub Sponsors supports multiple payout rails depending on maintainer setup, region, and Stripe Connect eligibility.",
        "owner_note": "Stripe Connect may be involved for some maintainers; verify before relying on payout.",
    },
    "WordPress Plugin Bounties (public programs)": {
        "methods": ["not_published"],
        "note": "WordPress plugin ecosystem does not publish a single payout method; bounties may come from security advisories, grants, or individual maintainers.",
        "owner_note": "Treat as discovery only.",
    },
    "FreelanceMap (dev tasks, not hiring)": {
        "methods": ["not_published"],
        "note": "Dev task listings do not publish a consistent payout method across listings.",
        "owner_note": "Treat as discovery only.",
    },
    "Stack Overflow Jobs / listings": {
        "methods": ["not_published"],
        "note": "Job/listings board; payout method varies by listing and is often not published up front.",
        "owner_note": "Treat as discovery only.",
    },
    # ── Crypto / web3 bounty surfaces ──
    "Immunefi": {
        "methods": ["crypto", "stablecoin"],
        "note": "Immunefi payouts are commonly in crypto/stable assets depending on the program.",
        "owner_note": "Program terms vary; verify before relying on payout.",
    },
    "Hats Finance": {
        "methods": ["crypto", "stablecoin"],
        "note": "Hats Finance bounties are commonly paid in crypto/stable assets.",
        "owner_note": "Program terms vary; verify before relying on payout.",
    },
    "Secure3": {
        "methods": ["crypto", "stablecoin"],
        "note": "Secure3 is described as a web3 audit/bounty surface; payout terms vary by engagement.",
        "owner_note": "Verify before relying on payout.",
    },
    "BugRap": {
        "methods": ["crypto", "stablecoin"],
        "note": "BugRap is described with crypto payouts; exact token/method varies.",
        "owner_note": "Verify before relying on payout.",
    },
    "ChainLove": {
        "methods": ["crypto", "stablecoin"],
        "note": "ChainLove is described as a community bounty/sponsorship surface; exact method varies.",
        "owner_note": "Verify before relying on payout.",
    },
    # ── Fourth-wave OwnWork sources ──
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
    # ── Fifth-wave OwnWork dev sources ──
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
    # ── Sixth-wave OwnWork priority sources ──
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
