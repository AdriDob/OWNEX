# OWNEX

**Personal Work & Income Operating System**  
**Version:** 9.0.0 · **Python:** 3.11+ · **Stack:** FastAPI · Vue 3 · TypeScript · Tauri v2  
**Status:** Active development

OWNEX is a local-first personal system for discovering technical work, evaluating requirements, preparing applications and deliverables, executing selected development workflows, and tracking income evidence. It is a private tool for its owner, not a product or SaaS offering.

> **Reality rule:** an opportunity is not income. An application is not a payout. A code-complete connector is not a live-validated integration.

## What works today

| Capability | Status | Evidence / limits |
|---|---|---|
| Opportunity catalog and discovery | Implemented, validation incomplete | The 2026-11-09 adaptation snapshot recorded 176 deduplicated source definitions; this is not 176 active jobs or Argentina-verified sources |
| Remote-job pipeline | Implemented | Five feeds (Remotive, Arbeitnow, RemoteOK, Jobicy, WeWorkRemotely), explainable matching, profile, tracker, and draft preparation; final submission remains human-controlled |
| Employment classification | Implemented | Permanent, temporary, independent, microtask, and bounty work are classified separately |
| Unified income plan | Implemented | Aggregates first-day actions, accepted streams, Work Bank, and remote-job signals; estimated opportunity value is not realized cash |
| Income ledger | Implemented | Distinguishes potential, expected, approved, pending, paid, and withdrawn states |
| Financial connections | Integration pending | IOL OAuth2/refresh/quotes/WebSocket, PPI, Binance read-only, and manual CSV/JSON/XLSX imports exist; real-account validation is still required |
| Portfolio normalization | Implemented with limits | Keeps currencies separate and records provenance; no invented FX conversions |
| OWNEX MCP server | Implemented, read-oriented | Nine read-only tools, consent scopes, audit log; no trade or withdrawal tools |
| Security workflows | Implemented in parts | Reconnaissance, hypothesis, validation, evidence, and report pipeline; inspect current tests and runtime status |
| Frontend | Build status varies | Vue 3 + TypeScript + Vite; check current CI/build rather than relying on a stale route count |
| Desktop / Android | Build work exists | Tauri v2 and Capacitor Android projects; verify current release artifacts and device flows |
| Wear OS | Experimental | Partial implementation; not install-verified |
| Quant strategies | Planned / experimental | No trading income is included in the work-income scenarios below |

The detailed, dated record is [`.ai/CURRENT_STATE.md`](.ai/CURRENT_STATE.md). Architecture findings are documented in the audit and decision records.

## Current income potential: scenarios, not forecasts

**Verified OWNEX-generated income: USD 0.** There is not yet enough source-level history of accepted tasks and completed withdrawals to calculate a statistical monthly forecast.

The following are transparent planning scenarios based on *actually paid* technical hours, not advertised rates multiplied by imaginary availability:

| Scenario | Paid hours / month | Assumed effective net rate | Illustrative monthly net |
|---|---:|---:|---:|
| No accepted work | 0 | — | USD 0 |
| First small payout | 5–15 | USD 5–10/h | USD 25–150 |
| Early repeatability | 20–40 | USD 5–15/h | USD 100–600 |
| Validated part-time flow | 40–80 | USD 10–20/h | USD 400–1,600 |
| High-skill, steady task supply | 80–120 | USD 20–30/h | USD 1,600–3,600 |

These are arithmetic scenarios, not expected earnings or promises. They assume that tasks are available, the account is accepted, work is approved, and the hours are actually paid. Bounties are irregular and must be modeled per accepted reward, not as hourly salary. Taxes, withdrawal fees, FX costs, unpaid screening, revisions, and rejected work can reduce effective net income.

Current public examples illustrate the gap between advertised rates and eligibility:
- Outlier's current coding-community listing includes Argentina and PayPal/AirTM, but requires expertise or professional experience and identity/skills validation; projects and hours vary. [Current coding community](https://app.outlier.ai/opportunities/4705643005)
- OpenTrain AI advertises per-task coding work for Argentina, but its listings require hands-on backend expertise and professional English; one recruitment listing also describes a conversational AI interview and coding challenge. It is **not** classified as interview-free or beginner-eligible. [OpenTrain AI role](https://www.opentrain.ai/jobs/backend-software-engineer-for-ai-coding-tasks--cmv7ep1jl000502o277l5i2xq7/)

OWNEX must keep **POTENTIAL**, **EXPECTED**, **APPROVED**, **PENDING**, **PAID**, **WITHDRAWN**, and **EXTERNALLY_VERIFIED** separate. Do not show scenario totals as money earned.

See [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md) for source candidates, constraints, payment checks, and measurement rules.

## Core principles

- **Local-first:** personal data stays local by default.
- **Evidence before ranking:** expose country eligibility, experience, interview, assessment, payout, and uncertainty.
- **Human approval:** keep the user in control of applications, sensitive access, and financial actions.
- **One source of truth:** avoid duplicate engines, registries, event buses, and stores.
- **Honest accounting:** potential, expected, approved, pending, paid, and withdrawn are distinct states.
- **Private utility:** OWNEX is used by its owner; do not add SaaS subscriptions, customer billing, or product-sales revenue to its income model.

## Architecture

OWNEX is designed as a modular monolith: one FastAPI backend, a Vue 3 + TypeScript frontend, a shared data layer, and optional desktop/mobile shells.

- Backend: Python 3.11+, FastAPI
- Frontend: Vue 3, TypeScript, Vite
- Desktop: Tauri v2
- Mobile: Capacitor Android
- Data: SQLite for local development; PostgreSQL support exists
- Integrations: provider-specific connectors and manual import paths
- AI: local-first routing with optional external providers

**Known structural debt:** `core/` and `cores/` remain intertwined, and two event-bus implementations have been identified. Consolidation is domain-by-domain and must follow the architecture decisions and current audit. Do not assume these are already unified.

## Opportunity sources

OWNEX is intended to organize opportunities across:

- Permanent remote employment and junior roles
- Software development and open-source bounties
- Bug bounty and application security programs
- AI coding and code-evaluation tasks
- QA and software testing
- Data engineering, analytics, and automation
- IT, DevOps, cloud, and infrastructure work
- Developer platforms, paid issues, and competitions
- Freelance marketplaces such as Fiverr and Freelancer (kept separate from employment)

**Upwork is intentionally excluded** from active discovery and recommendations. RWS TrainAI and CrowdGen are excluded from priority recommendations per user preference.

New discovery candidates to validate include Jobbi, gigs.sh, Awesome Agent Bounties, TerminalHire, OpenTrain AI, Gitpay, Algora, Opire, IssueHunt, BountyHub, OnlyDust, Gitcoin, Devpost, Topcoder, ETHGlobal, DoraHacks, HackerOne, Bugcrowd, Intigriti, YesWeHack, Outlier, Mercor, micro1, Wellfound, YC Work at a Startup, and additional employer career pages. These are discovery candidates, not all verified opportunities or active integrations.

Every source must be checked independently for Argentina eligibility, experience requirements, interviews/video, assessments, work type, payment rails, fees, minimum withdrawal, and actual payout availability. See [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md).

### Payment fallback for Stripe-dependent bounties

Stripe is not an automatic source-exclusion rule. For a Stripe-dependent bounty, OWNEX should first check native payout options and platform rules. Where the platform and bounty terms permit it, prepare a private message to the owner/sponsor proposing an alternative payment method (for example PayPal or bank transfer), and require written confirmation of amount, currency, fees, timing, and acceptance conditions **before work begins**. Opire's documentation states that bounty creators review submitted PRs and arrange payment directly; claiming a bounty does not itself trigger payment. This must not be generalized to platforms or programs whose rules prohibit off-platform payment. [Opire payment rules](https://docs.opire.dev/rewards/pricing)

## Financial integrations

The connection layer includes integration work for:

- InvertirOnline (IOL)
- Portfolio Personal (PPI)
- Binance (read-only)
- Manual imports for providers without a supported public API

**Important:** mocked tests and implementation against documentation do not equal live validation. Real credentials, provider permissions, terms, and end-to-end reconciliation remain necessary. Financial MCP access is deny-by-default until consent is granted. The read-only MCP server does not expose trading or withdrawal tools.

## Quick start

### Linux development

```bash
git clone https://github.com/AdriDob/OWNEX.git
cd OWNEX

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..

python run.py
```

In a second terminal:

```bash
cd frontend
npm run dev
```

Check dependency files and scripts before running commands. Back up valuable local data before migrations or destructive maintenance.

## Verification

Typical checks (use the repository's current scripts where applicable):

```bash
python scripts/dev test
python scripts/dev test-fast
make check
cd frontend && npm run build
```

Test and build results have changed during parallel development. Check the latest CI run and [current engineering state](.ai/CURRENT_STATE.md); this README intentionally avoids freezing an unverified test count.

## Documentation

- [Current engineering state](.ai/CURRENT_STATE.md)
- [Architecture audit](.ai/OWNEX_GLOBAL_ARCHITECTURE_AUDIT.md)
- [Duplication and consolidation plan](.ai/OWNEX_DUPLICATION_CONSOLIDATION.md)
- [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md)
- [Deep revenue opportunity study](docs/DEEP_REVENUE_OPPORTUNITY_STUDY.md) — historical research; read its caveats and do not treat SaaS/product monetization examples as OWNEX income goals.

## License

See [LICENSE](LICENSE) and [LICENSE-MIT-legacy.txt](LICENSE-MIT-legacy.txt). The repository documents a license transition: versions distributed under MIT retain the permissions granted under that license; later versions are marked proprietary. See `outputs/OWNEX_V15/LICENSE_DECISION.md` for the project's own decision record.
So the project is proprietary **going forward**; the historical versions are

---
## Capability Matrix — VERIFIED / BUILD_VERIFIED / INTEGRATION_PENDING / EXPERIMENTAL / PLANNED / BLOCKED

| Priority | Capability | Status | Notes |
|---|---|---|---|
| **P0** | **Registro y tareas técnicas** | **VERIFIED** | Python, scripts, debugging, APIs y código; registro directo sin experiencia profesional |
| **P0** | **Recompensas por entregas** | **VERIFIED** | Issues, pull requests y tareas remuneradas; pago por entrega aceptada |
| **P0** | **AI coding** | **VERIFIED** | Programación, revisión, corrección y testing de código con asistencia de IA |
| **P1** | **Freelance por tareas** | **BUILD_VERIFIED** | Entregas pequeñas y concretas en Fiverr/Freelancer; pending full integration |
| **P1** | **Open source remunerado** | **BUILD_VERIFIED** | Contribuciones financiadas y programas de recompensas; pending full integration |
| **P2** | **Bug bounty y auditorías** | **PLANNED** | Hallazgos técnicos y competencias de seguridad; motor en desarrollo |
| **P2** | **Empleos junior** | **PLANNED** | Alternativa de ingresos recurrentes; pending integración con motor de ejecución |
| **Ciclo OWNEX** | **BUILD_VERIFIED** | DISCOVER→VERIFY→QUALIFY→PREPARE→EXECUTE→DELIVER→EARN→OPTIMIZE; pipeline implementado |
| **Composición $10K** | **PLANNED** | $3K dev recurrente + $2.5K GitHub + $2K AI coding + $1.5K freelance + $1K bug bounty |
| **Preguntas prioritarias** | **BUILD_VERIFIED** | ¿Dónde hay trabajo? ¿Sin experiencia profesional? ¿Qué tareas puedo resolver con Python/IA? ¿Pago en Argentina? |
| **Éxito definitivo** | **PLANNED** | Encontrar trabajo técnico accesible, ejecutar con automatización/IA, entregar y cobrar |

*Legend: VERIFIED = confirmado con evidencia; BUILD_VERIFIED = build-stable with tests passing; INTEGRATION_PENDING = definido pero no fully wired; EXPERIMENTAL = prototipado; PLANNED = roadmap goal; BLOCKED = waiting external decision*

*Generated: 2026-11-09 | Source: V15 repository reconciliation — aligned with OWNEX priorities document*
not. Any claim that OWNEX was never open source, or that all rights in all
versions are reserved, would be false. Decision record:
`outputs/OWNEX_V15/LICENSE_DECISION.md`.

---

**Built for personal leverage, with evidence over hype.**
