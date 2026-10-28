# PRODUCT_ONE_PAGE.md — OWNEX Product Definition

**Version**: 1.0 · **Date**: 2026-09-30 · **Status**: DRAFT — PENDING APPROVAL

---

## WHAT

**OWNEX** is a **desktop application** that finds real technical work opportunities, evaluates which ones are actually actionable for you, helps you execute them, validates the results, and tracks when you actually get paid.

---

## WHO

**Primary User**: Technical professionals (developers, security researchers, AI engineers, cloud/DevOps engineers) who want to convert their skills into **verifiable income** without spending hours hunting across platforms.

**Not for**: Non-technical freelancers, people wanting "passive income", or anyone looking for a job board.

---

## PROBLEM

Technical work opportunities are scattered across **100+ platforms** (GitHub, HackerOne, Bugcrowd, Algora, Opire, GitHub Issues, Web3 grants, AI evaluation platforms, cloud bounties, security programs).

**Current pain**:
- Hours spent hunting across platforms
- No unified view of what's actually actionable *for you*
- Can't distinguish "looks good" from "you can actually do this and get paid"
- No unified tracking from discovery → payment
- Freelance platforms (Fiverr/Workana) dominate search but pay poorly for technical work

---

## PROMISE

> **OWNEX finds real technical work you can actually do, helps you ship it, and tells you when the money hits your account.**

---

## INPUT

| Input | Source |
|-------|--------|
| Your skills / tech stack | Onboarding + GitHub analysis |
| Your location / eligibility | Onboarding + country detection |
| Your payment rails | Onboarding (PayPal, Wise, crypto, bank) |
| Your risk tolerance | Onboarding (time-to-cash preference) |
| Your capacity | Calendar / weekly hours |
| External opportunities | 100+ sources (GitHub, HackerOne, Bugcrowd, Algora, Opire, Gitcoin, Web3 grants, AI eval platforms, cloud bounties, security programs, OSS bounties, grants/RFPs) |

---

## PROCESS (The Core Loop)

```
DISCOVER
    ↓  Continuous, automated, multi-source
EVALUATE
    ↓  Technical fit + Economic fit + Eligibility + Time-to-cash
SELECT
    ↓  You pick from ranked, evidence-backed recommendations
PREPARE
    ↓  OWNEX drafts PR/fix/submission + evidence package
EXECUTE
    ↓  You act; OWNEX handles submission, evidence, validation
VALIDATE
    ↓  Evidence → Verdict → Finding/Result
DELIVER
    ↓  Submit / Merge / Deliver
EARN
    ↓  Payment → Realized Cash
```

---

## OUTPUT

| Output | Description |
|--------|-------------|
| **Actionable Opportunities** | Ranked by `Technical Fit × Economic Value × Cash Confidence` |
| **Prepared Work** | Draft PR/bounty claim/grant submission + evidence package |
| **Execution Support** | Commands, evidence templates, validation checklists |
| **Verification** | Evidence bundles → Verdicts → Findings/Results |
| **Economic Truth** | Realized cash only (PAID = REALIZED) |
| **Daily Brief** | "3 opportunities ready. Best: Fix X in repo Y. $250. 2h. Blocker: payment rail." |

---

## ECONOMIC RESULT

| Metric | Definition |
|--------|------------|
| **REALIZED CASH** | Money in your account (PAID only) |
| **NET CASH** | Realized − fees − taxes |
| **MONEY/HOUR** | Realized ÷ your human hours |
| **TIME TO CASH** | Discovery → PAID |
| **ACCEPTANCE RATE** | Submitted → Accepted |
| **REPEATABILITY** | Can you do it again? |

**Only PAID = REALIZED CASH**. Never: expected, submitted, accepted, awarded.

---

## HUMAN ROLE

| You Decide | OWNEX Does |
|------------|------------|
| Which opportunity to pursue | Discovers, normalizes, deduplicates |
| Whether to accept a task | Fetches, normalizes, deduplicates |
| How to solve it | Fetches, normalizes, deduplicates |
| When to submit | Fetches, normalizes, deduplicates |
| Whether to accept payment | Fetches, normalizes, deduplicates |

**You decide. OWNEX prepares, validates, tracks, and reminds.**

---

## AUTOMATION ROLE

| OWNEX Automates | Human Decides |
|-----------------|---------------|
| Discovery across 100+ sources | Which opportunity to pursue |
| Normalization & deduplication | Whether to accept a task |
| Eligibility checking (country, skills, KYC) | How to solve it |
| Technical evaluation (difficulty, fit) | When to submit |
| Economic evaluation (reward, time-to-cash, fees) | Whether to accept payment |
| Evidence collection & packaging | |
| Submission & delivery | |
| Validation & verification | |
| Payment tracking | |

**AI assists. Human decides. Policy enforces.**

---

## BOUNDARIES (What OWNEX Does NOT Do)

| Not OWNEX | Why |
|-----------|-----|
| ❌ Freelance marketplace (Fiverr/Workana/Upwork) | Competes on price, not technical value |
| ❌ Generic job board | Not a job board |
| ❌ CRM / client management | Not a CRM |
| ❌ Passive income generator | Requires human skill + action |
| ❌ Trading bot / financial advisor | Separate domain (Trading = separate) |
| ❌ CRM / project management for clients | Not a client manager |
| ❌ Browser automation platform | Browser = peripheral tool, not foundation |
| ❌ "Autonomous agent" that does everything | Human gates on irreversible actions |

---

## DAILY LOOP

```
OPEN OWNEX
    ↓
SEE: "3 opportunities ready. Best: Fix X in repo Y. $250. 2h. Blocker: payment rail."
    ↓
CLICK "Prepare" → OWNEX drafts PR + evidence
    ↓
YOU REVIEW → CLICK "Execute"
    ↓
OWNEEX submits PR, packages evidence
    ↓
YOU VALIDATE → CLICK "Deliver"
    ↓
SEE: "Payment received. $250 REALIZED. Money/hour: $113."
```

---

## SUCCESS CRITERIA

| Metric | Target |
|-------|--------|
| **Time to First Paid** | < 30 days from first open |
| **Money / Human Hour** | > $50/hr (technical work) |
| **Acceptance Rate** | > 60% (Submitted → Accepted) |
| **Time to Cash** | < 14 days (Submitted → PAID) |
| **Automation Rate** | > 80% (discovery → ready) |
| **Human Minutes / Paid Outcome** | < 120 min |
| **False Positive Rate** | < 5% (Recommended → Not Eligible) |

---

## NON-GOALS (Explicit)

| Non-Goal | Reason |
|----------|--------|
| Freelance marketplace (Fiverr/Workana/Upwork) | Competes on price, not technical value |
| Generic job board | Not a job board |
| CRM / client management | Not a CRM |
| Passive income / "money while you sleep" | Requires human skill + action |
| Trading bot / financial advisor | Separate domain (Trading = separate) |
| Browser automation platform | Browser = peripheral tool |
| "100% autonomous" agent | Human gates on irreversible actions |
| 100+ platform integrations as features | 100 sources = data, not 100 features |

---

## CORE LOOP (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                        OWNEX CORE LOOP                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   SOURCES (100+)                                            │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              OPPORTUNITY ENGINE                       │  │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │  │
│   │  │ SOURCE  │ │ NORMAL- │ │  DEDUP  │ │ ELIGIBILITY │  │  │
│   │  │ REGISTRY│ │  IZER   │ │         │ │   CHECK     │  │  │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └─────┬──────┘  │  │
│   │       │           │           │             │         │  │
│   │       ▼           ▼           ▼             ▼         │  │
│   │  ┌─────────────────────────────────────────────────┐   │  │
│   │  │           EVALUATION ENGINE                       │   │  │
│   │  │  Technical Fit × Economic Value × Cash Confidence │   │  │
│   │  └────────────────────┬────────────────────────────┘   │  │
│   │                       ▼                                │  │
│   │  ┌─────────────────────────────────────────────────┐   │  │
│   │  │              RANKING & RECOMMENDATION             │   │  │
│   │  └────────────────────┬────────────────────────────┘   │  │
│   │                       ▼                                │  │
│   └───────────────────────┼────────────────────────────────┘  │
│                           ▼                                   │
│                    OPPORTUNITY                                │
│                           │                                   │
│                           ▼                                   │
│                    ┌─────────┐                                │
│                    │ DECIDE  │ ◄── HUMAN GATE                  │
│                    └────┬────┘                                │
│                         ▼                                     │
│                    ┌─────────┐                                │
│                    │  WORK   │                                │
│                    └────┬────┘                                │
│                         ▼                                     │
│                    ┌─────────┐                                │
│                    │ EXECUTE │                                │
│                    └────┬────┘                                │
│                         ▼                                     │
│                    ┌─────────┐                                │
│                    │ VALIDATE│                                │
│                    └────┬────┘                                │
│                         ▼                                     │
│                    ┌─────────┐                                │
│                    │  RESULT │                                │
│                    └────┬────┘                                │
│                         ▼                                     │
│                    ┌─────────┐                                │
│                    │  PAID   │ ◄── ONLY THIS = REALIZED CASH  │
│                    └─────────┘                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## NON-GOALS (Explicit)

| Non-Goal | Reason |
|----------|--------|
| Fiverr / Workana / Upwork integration | Competes on price, not technical value |
| Generic freelance marketplace | Not a marketplace |
| CRM / client management | Not a CRM |
| Passive income / "money while you sleep" | Requires human skill + action |
| Trading bot / financial advisor | Separate domain (Trading = separate) |
| Browser automation platform | Browser = peripheral tool |
| "100% autonomous" agent | Human gates on irreversible actions |
| 100+ platform integrations as features | 100 sources = data, not 100 features |

---

## GLOSSARY (Canonical Definitions)

| Term | Definition |
|------|------------|
| **Source** | A platform, program, or feed that emits opportunities (GitHub, HackerOne, Algora, etc.) |
| **Opportunity** | A canonical, deduplicated work unit with reward, requirements, eligibility, evidence |
| **Work** | A task derived from an opportunity, assigned to a human, with clear deliverable |
| **Task** | Atomic unit of work within a Work item |
| **Mission** | A user-defined goal (e.g., "$1,000 this month") that groups Work |
| **Execution** | The act of performing Work (coding, writing, testing, submitting) |
| **Result** | The delivered artifact (PR, report, fix, document, exploit) |
| **Evidence** | Verifiable proof that Work was done correctly (logs, screenshots, diffs, hashes) |
| **Payment** | Money transferred from platform to user |
| **Revenue** | Economic event (potential → expected → submitted → accepted → awarded → **PAID**) |
| **Capital** | Post-payment economic state (cash, liquidity, investments, runway) |
| **Finding** | Security: technically confirmed vulnerability with EvidenceBundle |
| **Security** | Domain: Observation → Hypothesis → Candidate → Validation → Evidence → Verdict → Finding → Report |
| **Source** | External platform/program emitting opportunities |
| **Adapter** | Code that translates a Source into canonical Opportunity |
| **Human Gate** | Mandatory human approval before irreversible external action |
| **EvidenceBundle** | Verifiable proof package (request, response, diff, hashes, provenance) |
| **PolicyEngine** | Decides ALLOW/DENY/REQUIRE_APPROVAL for every external action |

---

## BOUNDARIES

| In Scope | Out of Scope |
|----------|--------------|
| GitHub, HackerOne, Bugcrowd, Algora, Opire, Gitcoin, Web3 grants, AI eval, Cloud bounties, Security programs, OSS bounties, Grants/RFPs, Specialized engineering | Fiverr, Workana, Upwork, generic freelance, generic job boards, CRM, trading (separate), passive income, "100% autonomous" |
| GitHub Issues, Security bounties, AI eval, Web3 grants, Cloud/DevOps, Infra, Data/ML, Specialized engineering, Grants/RFPs | Freelancing, generic marketplaces, client management, passive income |

---

## SUCCESS = ONE PAGE

If you can read this page and explain OWNEX to a peer in 60 seconds → **PRODUCT DEFINITION COMPLETE**.

If not → **REWRITE**.

---

**END OF PRODUCT ONE PAGE**