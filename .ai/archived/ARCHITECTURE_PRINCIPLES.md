# ORION Architecture Principles

> Every decision about ORION's code, modules, and integrations shall be evaluated against these principles.
> If a change violates any one of them, it must be redesigned or rejected.

---

## 1. Events First

Everything communicates through events. No module calls another module's methods directly. Events are the only contract between components.

- Every state change publishes an event
- Every event carries a correlation ID
- Every event is persisted in the Event Store
- No direct imports between application modules (CATEYE, ATLAS, HERMES, etc.)

## 2. Capabilities, Not Modules

COPILOT discovers what the system can do through the Capability Registry. No module name is hardcoded in business logic.

- Every action a module provides is registered as a capability
- COPILOT queries capabilities, not module APIs
- Adding a new integration never requires changing COPILOT's code

## 3. Every Decision Is Traceable

COPILOT's decisions are not black boxes. Each decision records:

- What event triggered it
- What context was available
- What knowledge graph data informed it
- What confidence level was assigned
- What actions were recommended
- What the outcome was

This chain enables post-mortem analysis, learning, and accountability.

## 4. Knowledge Accumulates

The Knowledge Graph is the system's long-term memory. Every entity, relationship, decision, and finding is recorded there.

- The Event Store is the "what happened" log
- The Knowledge Graph is the "what we know" model
- COPILOT queries the graph before deciding
- No module maintains its own private graph or entity store

## 5. No Duplication of Logic

Every piece of business logic exists in exactly one place.

- Before writing code, search for existing implementations
- Before creating a module, check if a capability already covers the need
- Duplicated code must be extracted into a shared service
- Duplicated data must be consolidated into the Knowledge Graph

## 6. Observable by Default

Every module must answer:

- What events does it publish?
- What events does it consume?
- What capabilities does it register?
- What is its health status?
- How long do its operations take?
- What errors does it produce?

No module is invisible. If it can't be observed, it can't be trusted.

## 7. Automation Is Safe and Reversible

Every automated action must have:

- A guard condition (should this run?)
- A timeout (how long can it take?)
- A rollback plan (what if it fails?)
- A human override (can I stop it?)

No automation runs without these four properties.

## 8. Data Is the Source of Truth; Views Are Derived

The Event Store, Knowledge Graph, and persisted state are the truth. Everything else — dashboards, reports, API responses, frontend state — is a derived view.

- Never trust frontend state as authoritative
- Never calculate the same metric in two places
- Never cache without invalidation strategy

## 9. Simplicity Over Complexity Accidental

When two solutions are equivalent in functionality, the simpler one wins.

- Prefer flat structures over deep hierarchies
- Prefer composition over inheritance
- Prefer stdlib over new dependencies
- Prefer existing patterns over novel abstractions

Complexity is only justified by measurable improvement in one of: stability, performance, security, observability, or user experience.

## 10. The System Improves With Use

Every human interaction, every decision outcome, every validation result feeds back into the system.

- FeedbackTuner adjusts confidence weights
- Decision outcomes update the Knowledge Graph
- Human approvals and rejections train COPILOT
- Metrics from production feed the scheduler

A system that doesn't learn is not a platform — it's a script.

---

## Enforcement

These principles are enforced through:

1. **Code review**: Every PR is evaluated against these 10 rules
2. **Architecture audit**: Before major changes, a formal audit against this document
3. **Pre-commit hooks**: Ruff + pytest verify technical quality
4. **Decision journal**: Architectural decisions are recorded with the principles they satisfy

---

## 11. The Core Is Stable; Innovation Happens at the Edges

The Event Bus, Event Store, Knowledge Graph, Capability Registry, and Decision Engine form a **stable core**. They should change rarely and only for architectural necessity.

Innovation — new capabilities, integrations, automations, workflows — occurs in modules, extensions, and apps that consume the core.

If five years from now the core is almost unchanged while the ecosystem has grown tenfold, the architecture was right.

---

## Enforcement

These principles are enforced through:

1. **Code review**: Every PR is evaluated against these 11 rules
2. **Architecture audit**: Before major changes, a formal audit against this document
3. **Pre-commit hooks**: Ruff + pytest verify technical quality
4. **Decision journal**: Architectural decisions are recorded with the principles they satisfy

---

*Last updated: 2026-07-13*
