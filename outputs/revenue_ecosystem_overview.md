% Revenue Ecosystem Overview (OWNEX v8.0)
% Generated: 2026-10-31
% Per: OWNEX_REVENUE_ECOSYSTEM_INTEGRATION_BUNDLE.md master renewal directive

2026-10-31

## Purpose
Product taxonomy and how it maps to OWNEX's Core Loop

## Core Loop
DISCOVER → EVALUATE → PREPARE → EXECUTE → VERIFY → EARN → LEARN

## Source Categories

### Security Bounties
- **Sources**: bugbounty
- **Description**: Vulnerability disclosure programs with scope, rules, severity model, and payout policy
- **Evidence Grades**: B
- **Priority**: 3
- **Argentina Status**: conditional (USD/USDC-ETH routes need verification)
- **Typical Reward**: variable $1K-$10K
- **Max Advertised**: $1M+/contest
- **Workflow**: reportes enviados → triage → validación → payout
- **Payout Methods**: USD (H1, Bugcrowd, Intigriti) / USDC-ETH (Immunefi)
- **Recurrence**: intermittent
- **Human Gate**: required (verify and submit always - no auto-submit)
- **Status**: 21/21 tests passing, verified via core/opportunity/payment_trail.py

### Developer Bounties
- **Sources**: taskbounty, github_bounties, opire
- **Description**: Platforms where developers can obtain paid work or tasks (AI training, coding, GitHub PRs)
- **Evidence Grades**: B, C, C
- **Priority**: [2, None, None]
- **Argentina Status**: ['conditional', 'denied', 'conditional']
- **Typical Reward**: variable
- **Max Advertised**: ['TBD', 'N/A', '$200-$13K']
- **Workflow**: depends on platform (PR-based, API-based, registration-based)
- **Payout Methods**: USDC/ETH, USD, USDC/SOL
- **Recurrence**: intermittent / variable / unknown
- **Human Gate**: AI policy: no auto-submit (taskbounty); varies by platform
- **Status**: taskbounty: 21/21 tests passing; github_bounties: low evidence; opire: mixed receipts

### Crypto Infrastructure & x402
- **Sources**: 
- **Description**: x402 provider APIs, Agent task marketplaces, DAO bounties, grants
- **Evidence Grades**: N, /, A,  , (, f, r, o, m,  , A, p, p, e, n, d, i, x,  , 1,  , r, e, s, e, a, r, c, h, )
- **Priority**: P0-P5 sequence per integration bundle
- **Argentina Status**: conditional (routes need verification per §11)
- **Typical Reward**: USDC per-call, variable monthly
- **Max Advertised**: x402 median seller: $0.01/30 days; top sellers: $2,393/week
- **Workflow**: Pulse → discover APIs → Forge → evaluate traffic → Execute → human-approved publication → Verify → Earn → Learn
- **Payout Methods**: USDC (Base/Solana/Polygon), user wallet
- **Recurrence**: passive (per-call) / variable (bounties) / one-time (grants)
- **Human Gate**: human-approved publication (no paid production endpoints without explicit authorization)
- **Status**: research Appendix 1: 58 crypto sources + 18 fiat = 76 total in dashboard

### Grants & Funding
- **Sources**: 
- **Description**: Foundation grants, retroactive public goods funding, micro-grants
- **Evidence Grades**: N, /, A,  , (, f, r, o, m,  , r, e, s, e, a, r, c, h, )
- **Priority**: lower priority (one-time, not recurring)
- **Argentina Status**: conditional
- **Typical Reward**: $1K-$500K (one-time)
- **Max Advertised**: $50K-$500K+
- **Workflow**: application → milestones → retroactive funding
- **Payout Methods**: SOL/USDC/ETH/OP tokens
- **Recurrence**: 2-3x/year (seasonal/cyclic) / one-time (micro-grants)
- **Human Gate**: application required; assessment per grant
- **Status**: research Appendix 1: Sections F-J (Foundation Grants)

## Core Loop Integration

### DISCOVER
- Pulse cycle: feed ingestion from all registered sources (every 30 min proposed), deduplication, freshness, opportunity discovery. Presented in Daily Brief with 5 source categories.

### EVALUATE
- Forge cycle: 12-dimension opportunity scoring model (not summed, displayed as reasoned breakdown). Argentina filtering per user preferences. Beginner accessibility scoring.Displayed in source detail pages.

### PREPARE
- Adapters in PREPARE_ASSISTED state: draft PRs, evidence collection, checklists, workspaces. Human approval for external submissions. Source-specific preparation workflows.

### EXECUTE
- Adapters in EXECUTE_HUMAN_APPROVAL state: human approves claim, bid, PR, report, application, upload, or transaction. Per-source execution tracking. No auto-submit.

### VERIFY
- Revenue reconciliation: advertised max vs observed vs received. Only confirmed receipts with evidence increase verified income. RevenueEvents with provenance.

### EARN
- Track: work submitted, work accepted/merged, award approved, payment pending, payment received and verified, funds available, funds withdrawn/convert to ARS, fees/gas/taxes/losses.

### LEARN
- Per-source performance record based on user's own verified activity. Source scores updated after each cycle. Confidence and evidence age tracked. Unresolved questions documented.

## Argentina Filtering

### User Preferences

- Argentina availability must be verified
- Prefer no professional experience requirement
- Prefer no interview
- Prefer no portfolio or reputation requirement
- Prefer no client acquisition
- Prefer no long selection process
- Prefer no test; allow at most one reasonable aptitude assessment
- Identify KYC/ID requirements, wallet requirements, stake, paid onboarding, application, reputation, technical barriers

### Source Statuses

- **taskbounty**: conditional Argentina + beginner-friendly (0/5 barrier) = medium priority for Argentina-focused user
- **github_bounties**: denied Argentina + low evidence = not recommended for Argentina-focused workflows
- **agenthansa**: denied Argentina + fake platform = excluded from active sources
- **opire**: conditional Argentina + beginner-friendly but mixed receipts = conditional priority
- **bugbounty**: conditional Argentina + beginner-friendly + security skill required = medium priority

## Revenue Accounting

- **advertised_maximum_reward**: Shown separately in source detail pages, never included in scoring, never treated as expected income
- **typical_or_observed_reward**: Actual observed payouts with supporting evidence, displayed by source
- **estimated_opportunity_value**: Separate dimension, not summed across platforms or sources
- **work_submitted_pr_opened**: Tracked per source, part of the EARN phase
- **work_accepted_merged**: Tracked per source, part of the VERIFY/EARN phase
- **award_approved**: Only with sufficient evidence grade (A or B); documented with provenance
- **payment_pending**: Tracked separately; does not become 'received' until verified
- **payment_received_verified**: Only confirmed receipts with supporting evidence increase verified income
- **funds_available_wallet_account**: Pending payout route verification; part of ongoing tracking
- **funds_withdrawn_converted_ars**: Argentina conversion tracked separately with route verification status
- **fees_gas_taxes_refunds_losses**: Tracked per platform terms; part of the full revenue truth

## Adapter Architecture

- **Principle**: Do not build 85 bespoke engines. Adapter boundaries around stable protocols with thin provider-specific implementations.

- **Capability States**:
  - MANUAL_ONLY
  - DISCOVERY_READ_ONLY
  - PREPARE_ASSISTED
  - EXECUTE_HUMAN_APPROVAL
  - AUTO_REVERSIBLE

- **Shared Connector Families**:
  - Official REST/HTTP API connector
  - GraphQL connector
  - MCP client connector
  - CLI/process adapter
  - GitHub issues/PR/releases adapter
  - Webhook/event adapter
  - In-app browser adapter for permitted web workflows
  - On-chain read/indexer adapter
  - Wallet signing interface (external key custody; never store seed phrases/private keys in OWNEX)
  - Payout-status/import adapter

- **Source Adapter Mapping**:
  - **bugbounty**: Official REST/HTTP API adapter (EXECUTE_HUMAN_APPROVAL)
  - **taskbounty**: MCP client connector / REST API adapter (PREPARE_ASSISTED / EXECUTE_HUMAN_APPROVAL)
  - **github_bounties**: GitHub issues/PR/releases adapter (MANUAL_ONLY)
  - **opire**: REST API connector (no auth) (MANUAL_ONLY / PREPARE_ASSISTED)
  - **agenthansa**: MANUAL_ONLY (platform flagged as fake)

## Implementation Priorities

### PP0: Research integrity and registry: ingest all candidate records, normalize duplicates, capture evidence, resolve conflicts, label stale/unknown/payment-risk, preserve raw source text

### PP1: Shared contracts and source discovery: canonical Source/Opportunity contracts, source registry, evidence/provenance, deduplication, refresh policy, read-only discovery path

### PP2: First practical adapters: select providers after checking Argentina eligibility, reliable payment path, beginner friction, real demand, official API/terms, safe integration feasibility. Prefer one source per genuinely different adapter family.

### PP3: Work preparation and assisted execution: GitHub issue/PR or task workflows with sandboxed workspaces, evidence, and human approval for external submissions

### PP4: Payment and revenue reconciliation: import and verify actual receipts, network, fees, and off-ramp outcomes. Do not start with automated wallet transfers.

### PP5: Additional providers: add more only when evidence and user value justify maintenance cost

### PP6: Continuous monitoring and improvement: Pulse cycle re-evaluation, evidence grade updates, Argentina route re-verification, new source additions only with justification


## Acceptance Criteria

- All three research inputs are preserved and traceable
- Unique operators/products are deduplicated without collapsing distinct services
- Contradictions and future-dated claims are explicitly tracked
- Every source is classified by what it actually does (WorkSource, SecurityProgram, etc.)
- Payment providers and aggregators are not misrepresented as earning sources
- Argentina availability and actual payout paths are separately evidenced
- Reward ceilings, projections, observed payouts, and actual receipts are separate
- The registry integrates into the existing canonical architecture (not a parallel engine)
- The first adapters use shared contracts and pass contract tests
- No unapproved financial action or external submission is possible
- Browser-based workflows remain in-app where technically supported and permitted
- New work does not introduce a second Core Loop, duplicate engines, or an 85-adapter monolith
- Every claim about compatibility, automation, payment, and source activity can be traced to evidence and a verification date

---
*Original research preserved in appendices. Evidence grades A-D. Argentina availability separately verified. Reward ceilings kept separate from expected value. No 85 bespoke engines.)*
