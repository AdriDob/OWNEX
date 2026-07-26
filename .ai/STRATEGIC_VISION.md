# ORION — Strategic Vision & Master Roadmap

> **Single source of truth for the complete ORION vision.**
> Consolidates: ORION_EVOLUTION_PROGRAM.md, STRATEGIC_AUDIT.md, AUDIT_2026-07.md, AGENT_CHARTER.md
> July 2026.

---

## Core Mission

Build a system that **produces growing, consistent revenue** by finding real vulnerabilities,
producing elite evidence, maximizing report acceptance, and compounding knowledge over time.

**Every feature answers:** *Does this increase the probability of finding real bugs, producing
excellent evidence, getting reports accepted, and automatically reinvesting earnings?*

If no → doesn't belong in the core.

---

## Seven Objectives (ranked)

```
1. Vulnerability Detection   — find real bugs autonomously
2. Evidence Quality          — produce submission-ready reports
3. Acceptance Rate           — learn what gets accepted/rejected
4. Monthly Revenue           — grow income consistently
5. Automation                — eliminate repetitive human work
6. Scalability               — handle more targets without more effort
7. Learning                  — improve with every execution
```

---

## Domains

### 1. Offensive Intelligence

**Goal:** Find real vulnerabilities autonomously. Not just hypothesize — confirm.

| Capability | Status | What's Missing |
|---|---|---|
| Static analysis (5 reasoners) | ✅ IDOR, SSRF, XSS, SQLi, Auth Bypass | No HTTP requests — all metadata-only |
| Hypothesis generation | ✅ Structured hypotheses with signals | Never confirmed against real endpoints |
| Contradiction engine | ✅ IDOR contradictions (7 types) | SSRF/XSS/SQLi/Auth contradictions only partially implemented |
| Relationship graph | ✅ Endpoint ownership inference | Not fed back into prioritization |
| Curiosity engine | ✅ Per-type expert questions | SSRF/Auth only have 2-4 questions each |
| Investigation planner | ✅ 5 vuln types, phases, tools | Not connected to tool execution |
| Triager simulator | ✅ 10 evidence checks, acceptance prediction | Static weights, never learns from real outcomes |
| PoC generation | ✅ curl/Python/JS/HTTPie/Burp | **Broken** — no headers, no auth, no host, no body |
| Nuclei template gen | ✅ Templates generated | Never executed |
| Report templates | ❌ **Missing** | No H1/BC/Inti markdown renderer |
| HTTP request testing | ❌ **Missing** | The single biggest gap in the system |
| Hypothesis → Finding | ❌ **Missing** | No promotion endpoint |

**Evolution path:**
- Reasoner expansion: CSRF, LFI, CMDi, GraphQL, Race Condition, CORS, Open Redirect, Business Logic
- Hybrid reasoning: static hints → HTTP probe confirms → tool execution validates → PoC auto-generates
- Cross-endpoint correlation: same pattern in 3 endpoints = higher confidence
- Cross-program correlation: same vuln class found in 2 programs = reusable technique
- Target memory: "this endpoint pattern was vulnerable before"
- Continuous learning: confirmed/rejected findings adjust reasoner weights automatically

---

### 2. Acceptance Intelligence

**Goal:** Maximize report acceptance rate through continuous learning from outcomes.

| Capability | Status | What's Missing |
|---|---|---|
| Quality gate | ✅ Adaptive threshold per vuln type | Static — learns only via FeedbackTuner/LLM |
| Pre-report review | ✅ 9-item COPILOT checklist | Not connected to acceptance history |
| Evidence scoring | ✅ 6 dimensions (20/20/15/15/15/15) | Never calibrated against real outcomes |
| Acceptance predictor | ✅ Triager simulator (0-100) | Static weights — never learns from real data |
| Feedback tuner | ✅ Weight adjustments via LLM | MIN_EVENTS=3 (no significance), never clears events |
| Report template library | ❌ **Missing** | No H1/BC/Inti-optimized templates |
| Outcome reason analyzer | ❌ **Missing** | "Why was this accepted/rejected?" — no structured analysis |
| Payout correlator | ❌ **Missing** | "What payout did this vuln type + program + evidence yield?" |
| Style learner | ❌ **Missing** | "What writing style has highest acceptance on H1?" |
| Response time tracker | ❌ **Missing** | "How long did each platform take to triage/pay?" |

**What ORION must learn per outcome:**

```
Why accepted?   → evidence quality? severity? program need? clear reproduction?
Why rejected?   → duplicate? OOS? invalid impact? weak PoC? not reproducible?
How much paid?  → bounty amount, bonus, speed bonus
How long?       → time to triage, time to bounty, time to payout
What was asked? → triager questions, missing evidence, clarification needed
What was missing? → screenshots? video? curl command? impact explanation?
What style?     → concise vs verbose? technical vs business? format used?
```

**Required new module:** `core/acceptance/` with:
- `analyzer.py` — structured outcome analysis from submission records
- `correlator.py` — correlates evidence features with acceptance
- `optimizer.py` — generates report improvement recommendations
- `templates/` — platform-optimized markdown templates

---

### 3. Target Intelligence

**Goal:** Never waste time on low-ROI targets. Automatically prioritize by expected value.

| Capability | Status | What's Missing |
|---|---|---|
| Program CRUD | ✅ Full model + API | ✅ Complete |
| Bounty scraper | ✅ H1/BC/Inti scrapers | Only 3 platforms |
| Program intel (AI dossier) | ✅ Difficulty, competition, speed | Never validated against actual experience |
| Money radar | ✅ ORION SCORE ranking | Static formula, no learning |
| Next action engine | ✅ EVH scoring (0.4/0.25/0.2/0.15) | **Magic numbers** — never learn from outcomes |
| Scope reader | ✅ HTML/PDF scope parser | No per-endpoint in_scope/out_of_scope flag |
| Reward learner | ✅ Payout adjustments per vuln type | **Bug** — `_load_adjustments` iterates empty dict |
| Target prioritization | ❌ **Missing** | No unified "where do I spend my next hour?" |
| Tech stack fingerprinting | ❌ **Missing** | No identification of technologies per target |
| Similar company clustering | ❌ **Missing** | "If company A was vulnerable to X, company B might be too" |
| Competition estimator | ❌ **Missing** | No tracking of how many researchers target each program |
| Expected value calculator | ❌ **Missing** | No `reward × acceptance_prob × speed` formula |

**Required new module:** `core/target_intelligence/` with:
- `prioritizer.py` — unified target score from all signals
- `fingerprinter.py` — tech stack detection from endpoints/headers
- `cluster.py` — company/technology similarity clustering
- `competition.py` — estimated researcher competition per program

---

### 4. Evidence Intelligence

**Goal:** Produce submission-ready evidence. Copy-paste quality. No manual editing needed.

| Capability | Status | What's Missing |
|---|---|---|
| Evidence bundle | ✅ Composer with PoC, CVSS, CWE, CAPEC, MITRE, OWASP | **Critical bugs** — no headers/auth/body/host in PoC |
| Playwright headless | ✅ Installed, basic DOM XSS detection | Not used for screenshots, HAR, or visual PoC |
| Nuclei templates | ✅ Generated from evidence | Never executed |
| Timeline | ✅ Field exists in Hypothesis model | **Never populated** — always empty |
| Report readiness score | ✅ 7 required + 5 optional checks | No pre-submission quality gate |
| Burp sequence | ❌ Field exists | Always empty — never implemented |
| Screenshot evidence | ❌ **Missing** | No visual evidence capture |
| HAR file capture | ❌ **Missing** | No network request/response recording |
| Diagram generation | ❌ **Missing** | No architecture/flow diagrams for reports |
| Video PoC | ❌ **Missing** | No screencast recording for complex vulnerabilities |

**Evolution path:**
- Fix PoC generation (headers, auth, host, body, real test values)
- Add Playwright screenshot + HAR capture for evidence
- Add before/after response comparison in report
- Add video PoC for complex workflows (auth bypass, race conditions)
- Auto-populate timeline from pipeline execution
- Pre-submission quality gate that validates evidence before allowing submission

---

### 5. Automation (While You Sleep)

**Goal:** ORION works autonomously respecting platform policies and configurable limits.

| Capability | Status | What's Missing |
|---|---|---|
| Recon pipeline | ✅ 15-phase UnifiedScanner | ✅ Complete |
| Scheduler | ✅ DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT | ✅ Complete |
| Auto-report on confirmed | ✅ EventBus subscriber | ✅ Complete |
| Hypothesis generation | ✅ 5 reasoners async | No auto-promotion to finding |
| Data cleaning | ❌ **Missing** | No auto-archival of stale targets/findings |
| Inconsistency detection | ❌ **Missing** | No cross-reference validation |
| Opportunity detection | ❌ **Missing** | No "new program in your niche" alerts |
| Self-documentation | ❌ **Missing** | No auto-generated runbooks |
| Auto-learning | ❌ **Missing** | 8 open feedback loops — data collected but not consumed |

**Nightly automation cycle (while you sleep):**

```
1. Sync all platforms (payouts, submissions, status changes)
2. Run recon on active targets (if cooldown elapsed)
3. Generate hypotheses on new endpoints
4. Run HTTP probes on high-confidence hypotheses
5. Generate evidence bundles for confirmed hypotheses
6. Promote confirmed to findings (auto if confidence > 0.9)
7. Generate report drafts for confirmed findings
8. Update target scores with latest data
9. Analyze acceptance/payout outcomes → adjust weights
10. Detect and flag inconsistencies
11. Index new knowledge in memory + KG
12. Auto-archive stale/inactive targets
```

---

### 6. Financial Intelligence

**Goal:** Intelligent payout management. Not auto-trading — recommendation and tracking.

| Capability | Status | What's Missing |
|---|---|---|
| Payout recommender | ✅ 10 methods, 8 platforms, ARS ranking | Static data, hardcoded exchange rate |
| Revenue pipeline | ✅ 6 methods, 6 events, 31 tests | Immunefi/C4/Huntr not connected |
| KYC tracker | ✅ CRUD per platform | Not connected to real platform KYC status |
| Route optimizer | ✅ 5 withdrawal routes, fee calc | Static, no real-time rate APIs |
| Tax notes | ✅ 9 Argentina references | Static text, no tax calculator |
| Emergency routes | ✅ Fallback selection | ✅ Complete |
| Truth layer | ✅ Append-only ledger | ✅ Strong architecture |
| Reconciliation | ✅ 6 discrepancy types | In-memory history — lost on restart |
| Withdrawal lifecycle | ✅ Tracked, reorg-safe | **Critical** — in-memory `_WITHDRAWALS` dict |
| CoinGecko | ✅ 30+ crypto prices | 24h change bug, in-memory cache only |
| ROI tracking | ❌ **Missing** | No USD/hour per program/vuln/target |
| Compound strategy | ❌ **Missing** | No auto-reinvestment recommendations |
| Fiscal optimization | ❌ **Missing** | No tax planning, no optimal payout timing |
| Diversification engine | ❌ **Missing** | No "spread payouts across methods" calculator |
| Payout simulation | ❌ **Missing** | No "what if I withdraw now vs next month" |

**Financial Intelligence architecture:**
- **Module:** `core/financial/intelligence/` — recommendation layer (never executes without approval)
- **Module:** `core/financial/simulation/` — what-if analysis for payout routes, timing, reinvestment
- **Post-processing only** — reads from ledger, never writes. Can suggest, never execute without user.

---

### 7. Desktop Intelligence (Hermes)

**Goal:** True desktop agent. Manage Windows/Linux, tools, services, and development environment.

| Capability | Status | What's Missing |
|---|---|---|
| 15 CLI commands | ✅ backup, status, health, logs, doctor, etc. | Read-only monitoring, no real action |
| Permission system | ✅ 5 risk levels | No COPILOT authority bridge |
| Security layer | ✅ 13 PS patterns, 6 blocked paths | **Security theater** — `validate_action(**kwargs)` never called |
| Tool registry | ✅ 10 tool classes | Install/update unimplemented. Security tools absent |
| Event publisher | ✅ 7 event types | ✅ Complete |
| JSONL history | ✅ Action logging | Not API-queryable |
| Windows admin | ❌ **Missing** | No service management, no registry, no scheduled tasks execution |
| Software installer | ❌ **Missing** | No silent install/upgrade/uninstall |
| Desktop automation | ❌ **Missing** | No browser/provision/UI automation |
| Security tools | ❌ **Missing** | Cannot run nmap, subfinder, nuclei, or any tool |
| Diagnostic engine | ❌ **Missing** | No automated troubleshooting |
| Performance monitor | ❌ **Missing** | No trend-based anomaly detection |
| Developer tools | ❌ **Missing** | No git/venv/build automation |

**Required upgrade:** Hermes v1.0 — Real Desktop Agent
- `@security_check` decorator wrapping ALL execution paths
- Tool execution via `cores/tools/` (nmap, subfinder, nuclei, httpx, etc.)
- Windows: service management, registry, scheduled tasks, chocolatey/winget install
- Linux: systemd management, apt/pacman, flatpak
- macOS: brew management, launchctl
- Diagnostic: `hermes doctor --deep` runs comprehensive system health
- Chainable commands: `hermes run "recon target.com && analyze && report"`

---

### 8. Dashboard (Mission Control)

**Goal:** Premium command center. Configurable, fast, intelligent.

| Capability | Status | What's Missing |
|---|---|---|
| Mission Control | ✅ Health score, KPIs, activity, bottlenecks | Static layout, 30s polling |
| Financial Truth | ✅ 6 KPI cards, 4 tabs, proportional bar | No revenue charts |
| Health Center | ✅ Status, checks, history | List only — no chart |
| Intelligence Dashboard | ✅ Trend doughnut, bar charts | Sparse |
| Knowledge Graph | ✅ Full backend API | **Zero frontend** — no visual graph |
| Revenue Pipeline | ✅ 6 API endpoints | **Zero frontend** |
| Widget system | ❌ **Missing** | No drag-and-drop, no layout persistence |
| Real-time data | ❌ **Missing** | Polling only (30s), no SSE/WebSocket |
| KPI animations | ❌ **Missing** | No count-up, no sparklines, no "last updated" |
| Empty states | ❌ **Missing** | Text-only — no illustrations, no CTAs |
| Premium feel | ❌ **Missing** | No brand animation, no guided tours, no what's new |

**Dashboard evolution:**
- Phase 1: Widget system + KG visualization + Revenue pipeline frontend
- Phase 2: Real-time SSE/WebSocket + KPI animations + sparklines
- Phase 3: Premium polish (brand animation, guided tours, what's new, toast stacking)

---

### 9. Integrations & Open Source

**Goal:** Never reinvent. Integrate when the best open-source solution exists.

| Area | Current | Best OSS Alternative | Verdict |
|---|---|---|---|
| Bug bounty tools | 15+ tools integrated (subfinder, nuclei, etc.) | Same tools | **Keep** — already best-in-class |
| Knowledge Graph | Custom SQLite | Neo4j/ArangoDB | **Keep** — SQLite is correct for <10K nodes |
| Desktop automation | Hermes (custom) | AutoGPT/N8N | **Keep** — different purpose |
| Dashboard | Custom Vue 3 + Chart.js | Grafana/Redash | **Keep** — correct for transactional UI |
| ML Embeddings | Column exists, **not used** | sentence-transformers | **Add** — natural next step |
| Workflow engine | Custom YAML | Temporal/Prefect/Airflow | **Keep** — custom is lighter |
| Browser automation | Playwright | Same | **Keep** — already best choice |
| Vector database | None | ChromaDB/LanceDB | **Wait** — not needed until >10K memories |

**Pending integrations (priority order):**
1. Immunefi platform connector (highest payout platform)
2. Code4rena platform connector (audit contests)
3. Nuclei template executor (run generated templates)
4. sentence-transformers (semantic memory search for COPILOT)
5. Exchange rate API (replace hardcoded `_DOLAR_BLUE_RATE`)
6. Slack webhook (notifications)
7. Huntr platform connector
8. DolarAPI (Argentina exchange rates)

---

### 10. Learning Systems

**Goal:** Every execution teaches the system. Every outcome improves future decisions.

| Feedback Loop | Status | Problem |
|---|---|---|
| Reasoner → outcomes | ❌ Open | `record_outcome()` exists but nobody calls it |
| ConfidenceScorer → FeedbackTuner | ✅ Closed | But requires LLM, MIN_EVENTS=3, events never cleared |
| RewardLearner → Scheduler | ⚠️ Partial | `_load_adjustments()` bug — never restores persisted data |
| Evolution → Behavior | ❌ Open | MetricEvent written, never consumed |
| COPILOT decision → future decisions | ❌ Open | `make_decision()` is 100% static |
| Recommender → learning | ❌ Open | Pure if-else, no outcome tracking |
| NextAction → weight learning | ❌ Open | 0.4/0.25/0.2/0.15 are magic numbers |
| KG → weight learning | ❌ Open | Edge weights always 1.0 |
| Memory → decisions | ❌ Open | Memory stored but never queried for decisions |
| KnowledgeAsset → promotion | ❌ Open | Drafts die as drafts |

**Fix priority:**
1. Subscribe `finding:status_changed` → auto-call `record_outcome()` (P0)
2. Fix `RewardLearner._load_adjustments()` bug (P0)
3. Replace LLM FeedbackLearner with statistical Bayesian update (P1)
4. Wire COPILOT `make_decision()` to `recall()` + KG + RewardLearner (P1)
5. Make NextActionEngine weights learnable from outcomes (P1)
6. Auto-promote KnowledgeAssets from draft → validated with evidence accumulation (P2)
7. Evolve edge weights based on accepted/rejected findings (P2)

---

### 11. Quality

**Goal:** Continuous quality improvement. Remove complexity. Delete dead code.

| Area | Status | Action |
|---|---|---|
| 107 stub commands | ❌ Dead code | Reduce to 20-30 real handlers or eliminate |
| WorkflowEngine in-memory | ❌ Fragile | Persist to SQLite or consolidate into Execution Runtime |
| KG edge weights always 1.0 | ❌ Fake promise | Either implement adaptive weights or remove field |
| Memory embedding column unused | ❌ Fake promise | Either implement sentence-transformers or remove field |
| Hermes `HERMES_AUTO_BACKUP` never triggers | ❌ Dead config | Implement or remove |
| Hermes package `install` unimplemented | ❌ Dead code | Implement or remove |
| Hermes security kwargs-only | ❌ Security theater | Implement `@security_check` decorator |
| SyncPipeline bypassed | ❌ Dead code | Integrate into scheduler |
| Dashboard.vue redundant | ❌ Duplicate | Consolidate into MissionControl |
| FREEZE_CHECKLIST.md | ❌ Obsolete | Delete |
| 30+ root .md files outdated | ❌ Documentation pollution | Archive to `docs/` or delete |
| `.env` with API keys in git | 🔴 **Critical** | Remove from history, rotate keys NOW |
| 4 different version numbers | ❌ Inconsistent | Single source `VERSION` → sync in CI |
| Only 1 Alembic migration | ❌ Diverged schema | Add Alembic check to CI |
| No frontend tests | ❌ Quality gap | Add vitest |
| No CI lint step | ❌ Quality gap | Add `ruff check` to `test.yml` |
| No smoke test in release | ❌ Quality gap | Wire `smoke_test.py` to `release.yml` |

---

## ROI-Ranked Roadmap

### P0 — This Week (4 items, <2h each, block everything)

| # | Item | Impact | Effort |
|---|---|---|---|
| 1 | Rotate exposed API keys + scrub from git | 🔴 Security | 30min |
| 2 | Fix `RewardLearner._load_adjustments()` (empty dict loop) | 🔴 Learning | 15min |
| 3 | Fix withdrawal persistence (`_WITHDRAWALS` dict → SQLite) | 🔴 Data loss | 1h |
| 4 | Fix `withdrawal_completed` event bug (`if False`) | 🔴 Events | 5min |

### P1 — Phase 1: Revenue Ready (2-3 weeks)

| # | Item | ROI | Effort | Dependencies |
|---|---|---|---|---|
| 5 | HTTP probe module — auto-confirm hypotheses | ⭐⭐⭐⭐⭐ | 2-3d | Reasoners |
| 6 | Report templates (H1/BC/Inti markdown) + render endpoint | ⭐⭐⭐⭐⭐ | 1-2d | EvidenceComposer |
| 7 | Hypothesis → Finding promotion endpoint | ⭐⭐⭐⭐⭐ | 1d | OffensiveEngine |
| 8 | Immunefi platform connector | ⭐⭐⭐⭐⭐ | 1-2d | RevenuePipeline |
| 9 | Code4rena platform connector | ⭐⭐⭐⭐ | 1-2d | RevenuePipeline |
| 10 | Auto feedback loop (finding:status_changed subscriber) | ⭐⭐⭐⭐ | 1d | Reasoners |
| 11 | Fix PoC generation (headers, auth, host, body) | ⭐⭐⭐⭐ | 1d | EvidenceComposer |
| 12 | Expected Value prioritizer (reward × acceptance_prob) | ⭐⭐⭐⭐ | 2d | TargetIntelligence |

### P2 — Phase 2: Platform Hardening (1 month)

| # | Item | ROI | Effort |
|---|---|---|---|
| 13 | Docker + docker-compose (backend + PostgreSQL) | ⭐⭐⭐⭐ | 1-2d |
| 14 | Knowledge Graph frontend (D3 force-directed) | ⭐⭐⭐⭐ | 3-5d |
| 15 | Revenue pipeline frontend (payout funnel, ROI charts) | ⭐⭐⭐⭐ | 2-3d |
| 16 | Consolidate Dashboard → MissionControl | ⭐⭐⭐ | 1d |
| 17 | Add Ruff lint + frontend tests + smoke test to CI | ⭐⭐⭐ | 1d |
| 18 | Auto-backup with rotation (systemd timer) | ⭐⭐⭐ | 1d |
| 19 | Command System: reduce stubs to real handlers | ⭐⭐⭐ | 3-5d |
| 20 | Widget-based dashboard (drag & drop, layout persist) | ⭐⭐⭐ | 5-7d |
| 21 | Alembic check in CI + reconcile migrations | ⭐⭐⭐ | 1d |
| 22 | Single version source + sync all manifests | ⭐⭐ | 1d |

### P3 — Phase 3: AI & Learning (1-2 months)

| # | Item | ROI | Effort |
|---|---|---|---|
| 23 | Acceptance Intelligence module (`core/acceptance/`) | ⭐⭐⭐⭐⭐ | 1-2w |
| 24 | Target Intelligence module (`core/target_intelligence/`) | ⭐⭐⭐⭐⭐ | 1-2w |
| 25 | COPILOT decisions with memory + KG + RewardLearner | ⭐⭐⭐⭐ | 3-5d |
| 26 | sentence-transformers + semantic memory search | ⭐⭐⭐⭐ | 2-3d |
| 27 | Replace LLM FeedbackLearner with Bayesian stats | ⭐⭐⭐ | 2-3d |
| 28 | EvolutionEngine auto-skip inefficient tools | ⭐⭐⭐ | 2-3d |
| 29 | Adaptive KG edge weights from outcomes | ⭐⭐⭐ | 2-3d |
| 30 | NextActionEngine learnable weights | ⭐⭐⭐ | 2-3d |

### P4 — Phase 4: Desktop Intelligence (2-3 weeks)

| # | Item | ROI | Effort |
|---|---|---|---|
| 31 | Hermes `@security_check` decorator (real security) | ⭐⭐⭐⭐ | 1d |
| 32 | Hermes security tool execution (nmap, nuclei, etc.) | ⭐⭐⭐⭐ | 3-5d |
| 33 | Hermes Windows admin (services, registry, tasks) | ⭐⭐⭐ | 3-5d |
| 34 | Hermes chainable commands | ⭐⭐⭐ | 2-3d |
| 35 | Hermes + Command System bridge | ⭐⭐⭐ | 2-3d |

### P5 — Phase 5: Premium UX & Expansion (ongoing)

| # | Item | ROI | Effort |
|---|---|---|---|
| 36 | New reasoners (CSRF, LFI, CMDi, GraphQL, Race, CORS) | ⭐⭐⭐⭐ | 1-2w |
| 37 | Premium visual polish (count-up, sparklines, brand) | ⭐⭐⭐ | ongoing |
| 38 | Guided tours + "What's New" panel | ⭐⭐ | 3-5d |
| 39 | New platform connectors (Huntr, etc.) | ⭐⭐ | per connector |
| 40 | Compound strategy engine (recommendation only) | ⭐⭐⭐ | 1w |
| 41 | Fiscal optimization + tax planning | ⭐⭐ | 1w |
| 42 | Deterministic simulation for backtesting strategies | ⭐⭐⭐ | 1w |

---

## Anti-Patterns to Avoid

| Anti-pattern | Why |
|---|---|
| Build before verifying it doesn't exist | AGENT_CHARTER §2 — always search first |
| Auto-execute financial transactions | Never — recommendation only, user approves |
| Architecture without revenue impact | Revenue Rule — every change must increase $
| Perfect UI before functional gaps | Functional > aesthetic (but don't neglect UX) |
| Add modules without EventBus/KG | STRATEGIC_AUDIT — every component must auto-integrate |
| Refactor stable code | PRODUCTION_RULES — don't touch what works |
| Grow without consolidation | AGENT_CHARTER §9 — grow by consolidation, not expansion |
| Learn without feedback loops | Closed loops only — open loops are data cemeteries |

---

## Measuring Progress

| Metric | How |
|---|---|
| Findings confirmed / week | Pipeline produces real findings |
| Reports submitted / week | Pipeline produces submissions |
| Acceptance rate | Accepted / (accepted + rejected) |
| Average payout | Total $ / accepted reports |
| Revenue / month | Monthly payout sum |
| Hypothesis → Finding rate | % of hypotheses that become real findings |
| Human time saved | Hours ORION works autonomously |
| ROI per target | $ earned / hours spent per target |
| Feedback loops closed | 0 → 10 (all closed = learning system) |
| Evidence quality score | Pre-submission quality gate score trend |

---

## Strategic North Star

> **ORION debe encontrar, confirmar, evidenciar, reportar y cobrar vulnerabilidades reales con mínima intervención humana, mejorando con cada ciclo.**

Not a framework. Not a chatbot. Not a scanner collection.

A **personal security intelligence system** that compounds knowledge, improves daily, and produces growing income.
