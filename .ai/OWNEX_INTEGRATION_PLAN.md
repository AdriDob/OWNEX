# OWNEX Bounty Integration Plan

**Purpose:** Transform OWNEX from a passive bounty tracker into an active system that discovers, develops, and collects verifiable software bounties from Argentina.

**Philosophy:** Zero documentation about "how to make money" - only actionable integration with real opportunities and verified payment flows.

---

## 🎯 Objectives (What OWNEX Will Do)

| Objective | Description |
|-----------|-------------|
| **Discover real bounties** | Systematically check Algora, BountyHub, Opire, IssueHunt, make.fun for open, unverified, payable opportunities |
| **Verify opportunity validity** | Confirm: issue open, reward unclaimed, repo active, no competing PR, requirements accessible |
| **Select by capability match** | Match opportunities to developer skills (Python/JS/backend/frontend/testing/infra) - no professional experience required |
| **Prepare development environment** | Set up repo, understand codebase, identify good first issues, create development template |
| **Assist with code/PR** | Generate scaffolding, write tests, review PR quality, ensure meets contribution guidelines |
| **Prepare PR for submission** | Automate checklist, validate against repo requirements, format according to contribution guide |
| **Track acceptance & payment** | Monitor PR merge, trigger reward award, verify payment receipt, register in financial ledger |
| **No ghost opportunities** | Only pursue issues with: verified open status, claimable reward, demonstrable payment flow |

---

## 🏗️ Architecture (Reuse Existing, No New Aggregator)

**Principle:** Leverage OWNEX existing components - no duplicate bounty aggregator, no new database tables for status already tracked.

### Components Integrated:

| Component | What It Does | No Duplication Of |
|-----------|-------------|-------------------|
| **EventBus** | Emits `bounty:discovered`, `bounty:claiming`, `bounty:pr_merged`, `bounty:payment_received` | No new event system |
| **CURRENT_STATE.md** | Status snapshot includes `active_bounties`, `pending_payments` | No separate state file |
| **SESSION_CHECKPOINT.md** | Session tracking includes bounty progress | No new session format |
| **Financial ledger** | Existing `opportunity.env` / income tracking | No new accounting system |
| **Health endpoints** | `/api/health`, `/api/system/health` | No new API surfaces |

### Data Flow (No New Tables):

```
bounty_opportunity (existing concepts) 
  → verification_check (existing validation logic)
  → development_assist (existing code generation)
  → pr_submission (existing GitHub workflow)
  → payment_verification (existing financial pipeline)
  → ledger_update (existing income tracking)
```

---

## 🔍 Discovery Protocol (How We Find Real Opportunities)

### 1. **Source Checklist (Each Cycle)**

| Source | Check | Verification |
|--------|-------|--------------|
| **Algora** | `state:open` + `algora-pbc` comment + label:bounty | BountyOS-style: repo active, no assignee, no merged PR |
| **BountyHub** | Argentina supported + 0% commission claim | Stripe Connect onboarding test + individual bounty eligibility |
| **Opire** | API endpoint check + bounty active | Same rigor as Algora |
| **IssueHunt** | Issue open + reward unclaimed | Simple label/state check |
| **make.fun** | Competition open + entry feasible | No upfront cost, skills match, USDC payout possible |

### 2. **Filter (Pass/Fail)**

An opportunity **MUST** pass ALL:

- [ ] Issue state: open (not closed)
- [ ] Reward: unclaimed (not awarded yet)
- [ ] Repo: active (last commit < 90 days)
- [ ] No assignee: not assigned to another contributor
- [ ] No merged PR: solution not already in master
- [ ] Requirements accessible: no "professional experience required"
- [ ] Payable from Argentina: Stripe Connect available OR USDC crypto OR direct transfer confirmed
- [ ] Skills match: Python/JS/backend/frontend/testing/infra

**Fail any → Move to next opportunity. No exceptions.**

---

## 🛠️ Development Workflow (OWNEX-Assisted)

### Step 1: **Opportunity Selection**

```
Input: bounty_opportunity (title, repo, issue#, reward, requirements, tech_stack)
Output: selected OR "pass"

Criteria:
- tech_stack ∩ YOUR_SKILLS ≠ ∅
- estimated_effort ≤ YOUR_AVAILABLE_HOURS
- payment_method ∧ payable_from_argentina
```

### Step 2: **Environment Preparation** (Using OWNEX Infrastructure)

```
ONLY these actions (no new setup):

1. Clone repo: git clone <repo_url>
2. Open in your IDE (VS Code / VSCodium)
3. Run existing test suite: make test (or pytest)
4. Identify contribution area: look for "good first issue" labels, docs/, tests/, config/
5. Familiarize with contribution guide: CONTRIBUTING.md or README.md
```

**OWNEX assists with:**
- `scripts/dev` commands (test, check, fmt)
- Import path resolution
- mypy/type check fast mode
- Dependency status

### Step 3: **Code & PR Assistance**

**OWNEX provides (via existing skills):**

| Task | OWNEX Tool |
|------|------------|
| Code scaffolding | `scripts/dev` templates, mypy-assisted development |
| Test generation | `python scripts/dev test` (scoring + opportunity + scheduler-jobs) |
| PR checklist | Read existing CONTRIBUTING, apply patterns from accepted PRs |
| Code review | Compare against repo's coding patterns, import hygiene |
| Bug hunting | Use existing `make check` pipeline |

**You do (human judgment):**
- Actual implementation
- Test writing
- PR composition
- Final review decision

### Step 4: **PR Submission**

```
Command: git push origin HEAD <branch>
Action: Open PR via GitHub web or gh pr create

PR MUST Include:
- [ ] Clear title matching issue
- [ ] Description of changes
- [ ] Reference to issue number: closes #XXX
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)
- [ ] Follows repo's CONTRIBUTING.md
```

---

## 💰 Payment & Financial Tracking

### 4-Step Verification (Before Registering Income)

| Step | Verification | OWNEX Action |
|------|-------------|--------------|
| **1. PR merged** | GitHub shows PR merged to main | Wait for merge notification |
| **2. Reward awarded** | Algora/BountyHub/Opire issue shows "awarded" OR make.fun shows winner | Check issue/bounty console |
| **3. Payment initiated** | Platform shows payout started (Stripe, USDC, etc.) | Monitor email/webhook/console |
| **4. Funds received** | Money in your wallet/account (USDC, ARS via P2P, etc.) | Check wallet/bank/paypal |

**ONLY AFTER all 4 steps → Register in financial ledger.**

### 5. **Financial Registration (Existing System)**

Use OWNEX existing tracking:

```
- Income source: "bounty_<platform>_<issue#>"
- Amount: <USD amount>
- Date received: <YYYY-MM-DD>
- Payment method: "stripe_connect" | "usdc_wallet" | "p2p_ars" | "paypal"
- Commissions: <percentage> (0% for BountyHub, 23% for Algora, etc.)
- Income per hour: <amount> / <hours_invested>
- Net: <amount> - <commissions>
```

**Already tracked in:** Existing financial ledger, `opportunity.env`, session checkpoints.

---

## 📊 Progress Tracking (What We Measure)

### `PROGRESS_TRACKING_BOUNTY.md` (Created separately - see below)

### Key Metrics (Collected Automatically Where Possible):

| Metric | Source | Formula |
|--------|--------|---------|
| **Issues investigados** | Discovery log count | Count of opportunities checked |
| **Bounties confirmados** | Verification pass count | Issues passing all filters |
| **Issues reclamados** | Claim attempts | `attempt_bounty` actions |
| **PR enviados** | Git activity | `git log --oneline` count |
| **PR aceptados** | GitHub merge events | Merged PRs in target repos |
| **Recompensas adjudicadas** | Platform confirmation | Issue shows "awarded" |
| **Pagos recibidos y verificados** | Wallet/bank/paypal | Actual money received |
| **Horas invertidas** | Time tracking | `start/end` timestamps per session |
| **Ingreso efectivo por hora** | Financial calc | `total_usd_received / total_hours` |
| **Costos y comisiones** | Platform fees | `total_reward * fee_percentage` |

**All metrics flow into existing OWNEX tracking - no new database.**

---

## ✅ Integration with Existing OWNEX Systems

### Already-Available Assets:

| Asset | How It's Used |
|-------|--------------|
| **`scripts/dev`** | `test`, `check`, `fmt` - used during development |
| **`make check`** | Lint + typecheck + fast tests before PR |
| **`make test-fast`** | Scoring + opportunity + scheduler-jobs verification |
| **Ruff + pytest** | Quality gates after each change (Rule #10) |
| **Health endpoints** | Monitor system while bounty hunting |
| **CURRENT_STATE.md** | Track if system is healthy while working bounties |
| **Session checkpoint** | Track progress across sessions |

### No New Requirements:

- ❌ No new language runtime
- ❌ No new package manager
- ❌ No new CI/CD pipeline
- ❌ No new database tables
- ❌ No new authentication
- ❌ No new microservices

**Everything uses what OWNEX already has.**

---

## 🚦 Decision Gates (When to Proceed/Stop)

### Proceed When ALL:

- [ ] Opportunity passes full filter checklist
- [ ] Skills match your known capabilities
- [ ] Payment method verified payable from Argentina
- [ ] Estimated effort ≤ your available hours this week
- [ ] No conflicting priorities in OWNEX roadmap

### Stop When ANY:

- [ ] Issue closes before PR submitted
- [ ] PR gets rejected (no merge after 2 review cycles)
- [ ] Payment not received within 30 days of merge
- [ ] Commissions exceed 30% (unacceptable for small bounties)
- [ ] Hours invested > 2× estimated effort without progress
- [ ] No skills match after deep code review

---

## 📝 Quick Start (This Week)

### Day 1-2: **Discovery**

```
1. Run: python scripts/dev test (fast mode, excludes security tests)
2. Check health: curl http://localhost:8000/api/health
3. Review CURRENT_STATE.md - system OK?
4. Check BountyOS or similar for real-time bounty status
5. If opportunities found → apply filter checklist
```

### Day 3-5: **Development**

```
1. Select 1 opportunity passing all filters
2. Clone repo, run existing test suite
3. Identify contribution area (docs/tests/config)
4. Implement + tests (OWNEX-assisted via scripts/dev)
5. Create PR following CONTRIBUTING.md
```

### Day 6-7: **Tracking & Next**

```
1. Monitor PR merge status
2. If merged → wait for payment verification (max 7 days)
3. If payment received → register in financial ledger
4. If not → lessons logged, move to next opportunity
5. Update PROGRESS_TRACKING_BOUNTY.md
```

---

## 🎯 Success Criteria (Minimum Viable Results)

**Not "how much can we document"** but:

| Criteria | Threshold |
|----------|-----------|
| **Real opportunities found** | ≥1 per month passing full filter |
| **PRs submitted** | ≥1 per month |
| **PRs merged** | ≥1 per 3 submitted |
| **Payments received** | ≥1 per month |
| **Income verified** | ≥$50 USD/month consistent |
| **Hours/effort ratio** | ≤$20/hr effective rate |
| **No ghost opportunities** | 0% of pursued issues were closed/paid |

**If below thresholds after 3 months → reevaluate sources, not capabilities.**

---

## 📋 Philosophy Statement

> **OWNEX no vende un servicio al cliente. OWNEX trabaja para mí.**

> **Revenue Rule:** No feature enters roadmap without increasing vulnerability detection, quality of evidence, acceptance probability, or system learning.

> **Bounty Integration:** Only opportunities that can be executed, verified, and paid from Argentina. No ghost issues, no fake bounties, no catalog for catalog's sake.

> **Documentation Budget:** Maximum 2 new files per feature (we're at 2 - `OWNEX_INTEGRATION_PLAN.md` + `PROGRESS_TRACKING_BOUNTY.md`). Any more → feature poorly designed.

> **Zero Magic:** No "bounty points" system, no "algorithm recommends" magic. Every opportunity earns its place passing explicit filters. No exceptions.

---

## 🔄 Next Steps (After This Document)

1. **Create `PROGRESS_TRACKING_BOUNTY.md`** (priority #2 from your list)
2. **Audit `.ai/VERIFIED_BOUNTIES.md`** - mark closed examples, keep only real opportunities
3. **Test discovery protocol** - run against Algora/BountyHub/Opire for 1 week
4. **First bounty attempt** - if all checks pass, go for it
5. **Financial registration** - first verified payment into ledger
6. **Iterate** - adjust filters, sources, effort estimates based on real results

---

*Document generated: integration with existing OWNEX architecture, zero new dependencies, focus on verifiable results from Argentina.*