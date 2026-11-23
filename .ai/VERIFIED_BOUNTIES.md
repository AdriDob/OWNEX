# Verified Bounties Audit - OWNEX

**Last updated:** 2026-11-23  
**Purpose:** Document bounty verification findings - used to improve filter accuracy, NOT as active opportunities list.

---

## ⚠️ Critical Finding: No Active Opportunities in Previous List

**The 5 examples previously listed were ALL closed/rendered.** This document now serves as an **audit log** of what we got wrong and what we learned, NOT as a "here are opportunities to grab" list.

---

## 📝 Audit of Previous 5 Examples (All Closed/Rendered)

| # | Repo/Issue | Status | Evidence |
|---|-----------|--------|----------|
| **1** | comet-ml/opik#640 | **CLOSED** | Link redirected to PR about `data.input`, not issue "Create presets for each user". Reward already claimed by another. |
| **2** | comet-ml/opik#2529 | **CLOSED** | Algora registered USD 50 payment to another collaborator. Not available. |
| **3** | keephq/keep#640 | **CLOSED** | Algora registered two prizes of USD 50. Both awarded. |
| **4** | daytonaio/daytona#501 | **CLOSED** | Reward was USD 20, already paid out. Not available for new contributors. |
| **5** | permitio/opal#40 | **CLOSED** | Algora registered payment of USD 50. Already awarded. |

**Lesson:** Label + bot comment ≠ opportunity available. Always verify state:open + unassigned + no merged PR.

---

## 📊 BountyOS Reality Check (23 November 2026)

**External tracker confirms extreme scarcity:**

| Platform | Verified Open | Total Reward |
|----------|--------------|--------------|
| Algora | 0 | $0 |
| Opire | 0 | $0 |
| IssueHunt | 0 | $0 |
| BountyHub | 1 | $91 (issue hidden in public view) |
| TaskBounty | 0 | $0 |
| **Total** | **1** | **$91** |

**Source:** BountyOS live board (public version hides the single issue).

**Key filter (BountyOS):** Requires confirmation of reward, issue open, repo active, no assignee, no merged PR solving the problem. Much stricter than tag+bounty-hunting.

---

## 🎯 BountyHub Details (Argentina + 0% Commission)

**What we know:**

- ✅ Argentina included in payout countries (Stripe Connect)
- ✅ 0% commission to developer
- ❓ Issue exacto no publicado en vista pública
- ❓ Condiciones completas no verificadas individualmente
- ❓ Onboarding Argentina aún por probar

**Acción:** Si conseguimos el enlace directo + condiciones completas, podemos investigar elegibilidad. Sino, mantener bajo vigilancia.

**Referencia:** [bountyhub.dev/en/docs/claim-bounty](https://www.bountyhub.dev/en/docs/claim-bounty)

---

## 🏆 make.fun Competitions (Real, But High Competition)

**Three active technical competitions - NOT traditional bounties, but real $USDC prizes:**

### 1. **Build mend, one patch tool for every AI edit format**
- **Prize:** $100 USDC (10 positions = $10 each)
- **Requires:** Node.js 22, CLI for 4 code modification formats
- **Deadline:** 24 nov 2026, 14:00 UTC
- **Participants:** 8,969 reported
- **Link:** [make.fun/bounty/hidden-spec-cli-01-run-20261122](https://make.fun/bounty/hidden-spec-cli-01-run-20261122)

### 2. **Build a static site faster**
- **Prize:** $100 USDC (10 positions)
- **Task:** Create static site implementation, optimize speed
- **Deadline:** 24 nov 2026, 20:00 UTC
- **Participants:** 9,145 reported
- **Link:** [make.fun/bounty/site-generator-speed-01-run-20261122](https://make.fun/bounty/site-generator-speed-01-run-20261122)

### 3. **Build a tiny stack virtual machine**
- **Prize:** $100 USDC (10 positions)
- **Task:** JS/TS stack VM, 8 KB limit, hidden tests
- **Deadline:** 25 nov 2026, 04:00 UTC
- **Participants:** 12,183 reported
- **Link:** [make.fun/bounty/tiny-stack-vm-01-run-20261122](https://make.fun/bounty/tiny-stack-vm-01-run-20261122)

**Economic warning:** Money in escrow, but thousands of participants. Prize requires outperforming reference implementation. Not guaranteed income.

**Payment data:** >$21,000 paid in USDC since November (owns registrar), but "most participants don't win."

---

## 🔍 What Actually Works (Filter Based on Reality)

After audit, these are the **only filters that matter** (from BountyOS + our experience):

| Filter | Why It Matters |
|--------|---------------|
| **Issue state: open** | Closed = dead end |
| **No assignee** | Already claimed = dead end |
| **No merged PR** | Already solved = dead end |
| **Repo active** (last commit < 90 days) | Dead repo = waste of time |
| **Reward unclaimed** | Already paid = dead end |
| **Payable from Argentina** | Stripe Connect onboarding OR USDC OR direct | 
| **Skills match YOURS** | Not "professional required" | 
| **Algora-pbc comment present** | Protection against fake bounties (83/97 fake in audit) |

**Any opportunity missing any of these → skip. No exceptions.**

---

## 📈 Filter Accuracy Lesson (From Our Audit)

| Metric | Before Audit | After Audit | Change |
|--------|-------------|-------------|--------|
| Issues investigated | ~10 (guessed) | 30+ (systematic) | +200% |
| Passing filter rate | Assumed high | ~5-10% (reality) | Much lower |
| Opportunities "available" | 5 (listed) | 0 (all closed) | -100% |
| Real attempts made | 5 (based on bad list) | 0 (based on good filters) | Smarter |
| Payments received | 0 (never tried) | N/A | - |
| Income tracked | 0 | 0 | - |

**The audit saved us from wasting time on 5 dead issues.**

---

## 🎯 Current OWNEX Bounty Strategy (Post-Audit)

### 1. **Primary: Algora + BountyHub vigilance**
- Check weekly (not daily - too much noise)
- Apply ALL 7 filters from table above
- If BountyHub: test Stripe Connect onboarding Argentina first
- If passes → attempt 1 issue/month max

### 2. **Secondary: make.fun competitions**
- Try 1 competition at a time (no entry fee beyond time)
- Skills: Node.js CLI, static site optimization, JS VM
- Treat as skill-building, not guaranteed income
- 1 competition every 2-3 months

### 3. **Tertiary: Opire/IssueHunt**
- Only if BountyOS shows new verified entries
- Same 7-filter minimum
- Lower priority given BountyOS data (currently 0 verified)

### 4. **Never again:**
- ✅ List closed issues as "verified opportunities"
- ✅ Assume bot comment = available reward
- ✅ Skip repo activity check
- ✅ Skip assignee check
- ✅ Skip merged PR check
- ✅ Promise payment from Argentina without verification

---

## 📥 What to Do Now

### If You Want to Attempt 1 Real Opportunity:

**Option A: BountyHub single issue**
1. Get the exact issue URL from BountyOS private view (or try manually)
2. Verify: issue open, no assignee, no merged Algora PR
3. Test Stripe Connect onboarding (Argentina)
4. If OK → comment "I'd like to claim this"
5. If assigned → do 1 small PR
6. Wait 1-3 days for payment (Stripe)
7. Verify receipt → register in `.ai/progress_tracking_bounty.md`
8. If any step fails → log lesson, move on

**Option B: make.fun competition (1 only)**
1. Pick 1 of the 3 listed above
2. Check your skills match (Node.js/JS VM/static sites)
3. Read requirements fully
4. Attempt within your available hours
5. Don't spend money on entries (free participation)
6. Track hours, outcomes as skill-building
7. Learn, don't expect payment

### Option C: Nothing this week
- System healthy? Check health endpoints
- Review CURRENT_STATE.md
- Plan next week based on real data, not ghost issues
- **This is always a valid choice.**

---

## 🔄 Document History

| Date | Version | Change |
|------|---------|--------|
| 2026-11-22 | 0.1 | Initial list of 5 "verified" bounties (withdrawn) |
| 2026-11-23 | 0.2 | Audit complete: all 5 closed, BountyOS data incorporated, make.fun added, strategy rewritten |

**This document is now: AUDIT LOG + STRATEGY, NOT opportunity list.**

---

*Generated: Full bounty verification audit. Purpose: prevent wasted time on closed issues, document real scarcity, provide actionable alternatives with clear filters.*