## 🎯 **Session Priorities**

### Session 1: Pipeline Foundation

**1. Fix PoC Generation — P1.7 (1d)**

**Why**: Prerequisite for everything else. Without headers/auth/body/host, evidence is not copy-paste usable.

**What**: Add real test values to all PoC formats (curl, Python, JS, HTTPie, Burp).

**2. HTTP Probe Module — P1.1 (3d)**

**Why**: The #1 gap. Hypotheses stay theoretical without real HTTP requests.

**What**: `core/offensive/probe/` — takes a hypothesis → sends real requests → detects patterns → stores request/response → confirms or rejects.

**3. Hypothesis → Finding Promotion — P1.3 (1d)**

**Why**: Closes the pipeline. Ideas become managed findings.

**What**: POST endpoint + event to promote hypothesis to finding with all evidence.

---

### Session 2: Output & Quality

**4. Report Templates — P1.2 (2d)**

**Why**: A vulnerability is worth $0 if the report takes hours.

**What**: H1/BC/Inti markdown renderers. `/api/reports/{id}/render?platform=hackerone`.

**5. Report Critic (NEW — high priority)**

**Why**: Before sending, try to destroy your own report. If you can't, it's ready.

**What**: Pre-submission gate that attempts to find contradictions, missing evidence, broken PoC, ambiguous steps.

**6. Acceptance Intelligence (NEW — high priority)**

**Why**: Learn what gets paid. Per-platform, per-program evidence preferences.

**What**: `core/acceptance/` — analyzer, correlator, optimizer, templates.

---

### Session 3: Platforms & Learning

**7. Immunefi Connector — P1.4 (2d)**

**Why**: $100K+ bounties. Direct payout pipeline.

**What**: Connector to Immunefi platform for direct payout submission.

**8. Auto Feedback Loop — P1.6 (1d)**

**Why**: Closes 1 of 8 open feedback loops. Starts compounding improvement.

**What**: Automated learning from outcomes to improve accuracy.

**9. Code4rena Connector — P1.5 (2d)**

**Why**: Audit contest market.

**What**: Connector to Code4rena for contest submissions.

---

## What NOT to do next

**Item** | **Why not**
---------|----------
**New reasoners** (CSRF, LFI...) | More hypotheses don't help without probe
**Dashboard polish** | No reports to display yet
**Hermes desktop features** | Desktop execution without pipeline = no value
**Docker** | Premature optimization
**sentence-transformers** | Memory without revenue = data cemetery
**Financial analytics** | No money to analyze yet
**Memory Intelligence** | Valuable but depends on having outcomes to remember
**ROI Engine** | Depends on Acceptance Intelligence + outcome data

---

## Current Blockers (in order)

**Blocker** | **Blocks** | **Fix**
-----------|----------|--------
**No HTTP probe** | Finding discovery | Session 1
**PoC broken** | Usable evidence | Session 1
**No report templates** | Submission | Session 2
**No Report Critic** | Rejected reports | Session 2
**No Acceptance Intelligence** | No improvement | Session 2
**No platform connectors** | Can't submit | Session 3

---

## Progress Tracking

### By Session 3 end, ORION should be able to:

1. Take a target → recon → hypothesis → HTTP confirm → evidence → PoC → report → critic → submit
2. Track submission status → outcome → learn from acceptance/rejection
3. Predict acceptance probability before sending

That's the minimum viable revenue system. Everything before that is preparation.

---

## The question before every task

> **"Does this increase the probability of finding a real bug, getting it accepted, and getting paid?"**

If no → doesn't belong in the next session.
