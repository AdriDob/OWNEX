# NON_GOALS.md — OWNEX Explicit Non-Goals

**Version**: 1.0 · **Date**: 2026-09-30

---

## Explicitly NOT Building

| Non-Goal | Reason |
|----------|--------|
| **Freelance marketplace (Fiverr/Workana/Upwork)** | Competes on price, not technical value. OWNEX is for technical work with verifiable outcomes. |
| **Generic job board** | Not a job board. OWNEX finds technical work, not job postings. |
| **CRM / client management** | Not a CRM. OWNEX manages work execution, not client relationships. |
| **Passive income / "money while you sleep"** | Requires human skill + action. No passive income promises. |
| **Trading bot / financial advisor** | Separate domain (Trading = separate, isolated, DRY_RUN). |
| **Browser automation platform** | Browser = peripheral tool for specific tasks, not product foundation. |
| **"100% autonomous" agent** | Human gates on all irreversible actions. Autonomy = execution policy, not absence of human. |
| **100+ platform integrations as features** | 100 sources = data/config, not 100 features. One Opportunity Engine, many sources. |
| **CRM / client management** | Not a CRM. OWNEX manages work execution, not client relationships. |
| **Generic project management** | Not a PM tool. Work is tied to executable opportunities with verifiable outcomes. |
| **Generic AI chatbot** | AI = infrastructure (classify, summarize, prepare), not the product. |
| **Universal platform aggregator** | Sources = normalized data, not product features. One Opportunity Engine. |

---

## Explicitly Out of Scope for MVP

| Feature | Reason |
|---------|--------|
| Multi-user / team workspaces | Single-user desktop first |
| Cloud sync / multi-device | Local-first, optional sync later |
| Mobile app | Desktop-first, mobile = companion only |
| Web dashboard | Desktop-first, web = dev/QA only |
| Plugin marketplace | Core first, extensions later |
| Custom workflow builder | Core loop fixed, config later |
| Multi-language UI | English + Spanish only v1 |
| Advanced analytics / BI | Core loop first, analytics later |
| Team collaboration features | Single-user first |
| Marketplace for adapters | Core adapters first, registry later |

---

## Explicitly NOT Promising

| Claim | Why Not |
|---------|---------|
| "100% autonomous" | Human gates on irreversible actions |
| "100% local" | Some sources require cloud APIs |
| "Guaranteed income" | Only PAID = REALIZED CASH |
| "100% autonomous AI" | AI = infrastructure, Human Gate on irreversible |
| "Set and forget" | Human Gates on irreversible actions |
| "Passive income" | Human skill + action required |
| "Replaces Upwork/Fiverr" | Different model: technical work, not price competition |

---

## Explicitly Deprecated (From Current Codebase)

| Component | Status | Replacement |
|-----------|--------|-------------|
| Fiverr adapter | DEPRECATED | Removed from core |
| Workana adapter | DEPRECATED | Removed from core |
| Upwork adapter | DEPRECATED | Removed from core |
| Freelancer.com adapter | DEPRECATED | Removed from core |
| `cores/revenue_multiplier/` | DEPRECATED | Merge into RevenueEngine |
| `cores/ledger/` | DEPRECATED | Merge into RevenueEngine |
| `cores/autopilot/` | DEPRECATED | → ExecutionPolicy |
| `cores/personal_infrastructure/` | DEPRECATED | Remove |
| `cores/revenue_multiplier/` | DEPRECATED | Merge into RevenueEngine |
| `cores/autopilot/` | DEPRECATED | → ExecutionPolicy |
| `cores/personal_infrastructure/` | DEPRECATED | Remove |
| `cores/autopilot/` | DEPRECATED | → ExecutionPolicy |
| `cores/personal_infrastructure/` | DEPRECATED | Remove |
| `cores/validation/` + `engine/validation` + `execution/validation` | CONSOLIDATE | → ValidationService |
| `cores/scheduler/` (3 implementations) | CONSOLIDATE | → SchedulerService |
| `cores/revenue/` + `revenue_tracker/` + `financial/` | CONSOLIDATE | → RevenueEngine |
| `cores/opportunity/adapters/` + `executors/` + `api/adapters/` | CONSOLIDATE | → SourceRegistry + Adapters |

---

## Architectural Non-Goals

| Non-Goal | Why |
|----------|-----|
| Microservices | Modular monolith until proven need |
| Kubernetes / Kubernetes-native | Desktop-first, single binary |
| Event sourcing / CQRS | Overkill for desktop app |
| GraphQL API | REST + WS sufficient |
| Distributed tracing | Overhead not justified yet |
| Service mesh | Single binary, no mesh |
| Service discovery | Single binary |
| Feature flags | Config-driven, not platform |
| A/B testing | Desktop app, not web |
| Multi-tenant | Single-user desktop first |

---

## Explicitly NOT Doing

| Activity | Why |
|----------|-----|
| Adding new engines/agents/orchestrators | Consolidation phase |
| Adding new platforms as features | Sources = data, not features |
| Building new dashboards | 5 concepts max |
| New AI agents/autonomy layers | AI = infrastructure |
| New scoring engines | One ranking, multiple dimensions |
| New dashboards per domain | 5 concepts max |
| New automation layers | ExecutionPolicy only |
| New scoring systems | One ranking, multiple dimensions |

---

**Rule**: If it doesn't directly serve `SOURCE → OPPORTUNITY → WORK → RESULT → MONEY`, it's a non-goal.