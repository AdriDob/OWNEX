# Architecture Decisions

> Architectural Decision Records for ORION Platform.

## ADR-001: Modular Monolith with EventBus

**Status**: Accepted (2026-07)

**Context**: The system needs to support multiple applications (Hermes, ATLAS,
ODYSSEY, etc.) without the operational complexity of microservices.

**Decision**: Use a modular monolith with:
- `core/` — shared platform services (scheduler, event bus, DB manager, health)
- `apps/` — self-contained application plugins with their own DB, router, agent
- `core.events.event_bus` — async in-process EventBus for inter-app communication
- `core.extension` — hook system for sync behavior extension

**Consequences**:
- + Simple deployment (single process)
- + Shared identity vault, secrets, health
- + EventBus provides loose coupling without network overhead
- - All apps share the same Python process (memory, GIL)
- - An app crash can affect others (mitigated by error isolation)

## ADR-002: Extensions via Hook System (not Plugin Architecture)

**Status**: Accepted (2026-07)

**Context**: The project previously considered a full plugin architecture with
independent lifecycle, IPC, and sandboxing.

**Decision**: Use a simpler hook system instead. Extensions register callbacks
at named hook points (`before_scan`, `after_report`, etc.). No sandbox, no IPC.

**Consequences**:
- + Minimal overhead — extensions are just Python callbacks
- + Easy to write — no framework to learn beyond `@on_hook()`
- + Error isolation — exceptions in hooks don't crash the system
- - No process-level isolation — a buggy extension can corrupt in-memory state
- - Extensions must be trusted code

## ADR-003: Secrets Manager backed by Identity Vault

**Status**: Accepted (2026-07)

**Context**: Several apps need API keys (exchanges, scanners, AI providers).
Previously these were scattered in env vars, config files, and localStorage.

**Decision**: Centralize all secrets in `core/secrets/` backed by CATEYE's
IdentityVault (AES-256-GCM encrypted on disk). Env vars serve as fallback.

**Consequences**:
- + Single point of access and audit
- + AES-256-GCM encryption at rest
- + Env var fallback for backward compatibility
- - Requires IdentityVault to be initialized (non-fatal if missing)
- - Cache in memory — restart clears cache

## ADR-004: Unified Health Center

**Status**: Accepted (2026-07)

**Context**: Three legacy health systems existed:
- `cores/health/engine.py` — SystemHealthEngine
- `cores/recovery/health_monitor.py` — HealthMonitor
- `desktop/watchdog.py` — Watchdog

These produced contradictory statuses and had no shared state.

**Decision**: Create `core/health/engine.py` as the single source of truth.
Legacy systems are left in place but deprecated. The new HealthCenter:
- Registers health checks from all subsystems
- Runs checks on demand or on schedule
- Produces green/yellow/red status
- Persists snapshots in memory (last 100)

**Consequences**:
- + Single status to query
- + Extensible — any module can register checks
- + No migration needed — legacy systems still work
- - Legacy systems continue to run (wasted resources)
- - Snapshots are in-memory only (lost on restart)

## ADR-005: App Registry + Extension Registry

**Status**: Accepted (2026-07)

**Context**: The system has two kinds of loadable modules:
- `apps/` — full applications with DB, router, agent, frontend
- `extensions/` — lightweight hook-based behavior extensions

**Decision**: Keep two separate registries:
- `AppRegistry` for full apps (discovery, DB migrations, router mounting)
- `ExtensionRegistry` for extensions (discovery, hooks, capabilities)
- `AppRegistry.discover_extensions()` bridges to `ExtensionRegistry`

**Consequences**:
- + Clear separation of concerns (full app vs lightweight extension)
- + Apps can declare dependencies on extensions
- + Extensions can declare dependencies on app capabilities
- + No breaking changes to existing app system
- - Two registries to maintain (but code is minimal)

## ADR-006: No Automated Trading

**Status**: Accepted (2026-07)

**Context**: ATLAS module provides cryptocurrency analysis with buy/sell
recommendations.

**Decision**: ATLAS is analytical only. It NEVER executes trades automatically.
The COPILOT provides recommendations, but the user must confirm every action
that involves financial risk. Hermes never executes financial operations
without explicit user approval.

**Consequences**:
- + Zero risk of financial loss from automation bugs
- + User retains full control of money movements
- + COPILOT provides consultation (risk assessment, alternatives)
- - Requires user to be present for financial decisions
- - Slower reaction time vs automated trading

## ADR-007: Config Profiles

**Status**: Accepted (2026-07)

**Context**: Different users have different needs (hunting, trading, developing)
and different environments (desktop, server, offline).

**Decision**: Use config profiles — JSON files in `config/profiles/` that define
which apps, extensions, and features are enabled. Profiles are switchable at
runtime.

**Consequences**:
- + Single command to switch system behavior
- + Profiles can be shared and version-controlled
- + Minimal profile (core only) for resource-constrained environments
- - Profile switching requires restart of some subsystems
- - Profile conflicts must be resolved at load time
