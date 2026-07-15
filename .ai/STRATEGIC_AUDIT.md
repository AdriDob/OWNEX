# Strategic Audit — Chief Architect Framework

> **Purpose**: Permanent governing audit standard for every change to ORION.
> Every modification must be evaluated against this framework before implementation.
> **Goal**: ORION at 10/10 real, not perceived.

## Core Principle

Every change must increase **at least one** of these metrics measurably:
- Revenue
- Detección (finding rate)
- Precisión (accuracy/precision)
- Aceptación (report acceptance rate)
- Autonomía (hours saved)
- Estabilidad (uptime / crash rate)
- Escalabilidad (targets/hour)
- Observabilidad (debug time)
- Seguridad (risk reduction)
- UX (time-to-task)
- ROI (value/cost)

## Ten Questions Before Any Change

1. ¿Qué problema real resuelve?
2. ¿Por qué existe ese problema?
3. ¿Existe ya un componente que pueda resolverlo?
4. ¿Estoy duplicando lógica?
5. ¿Estoy aumentando el acoplamiento?
6. ¿Estoy rompiendo algún principio arquitectónico?
7. ¿Este cambio podrá mantenerse durante años?
8. ¿Este cambio hace más simple el sistema?
9. ¿Este cambio aumenta la autonomía?
10. ¿Este cambio acerca realmente a ORION al objetivo de encontrar mejores vulnerabilidades y producir más ingresos?

If any answer is negative → reject the change.

## Evaluation Axes

### Architecture (cohesion, coupling, extensibility, stability, simplicity, events, contracts, interfaces, versioning, compatibility)

### Security (secrets, permissions, sandbox, audit, cryptography, supply chain, isolation, rollback, validation, least privilege)

### Autonomy (how much human work does it eliminate? Every repetitive process must be automatable)

### Bug Bounty Impact (does it help find better vulns? Reduce FP? Increase acceptance? Reduce time per report? Prioritize better? Learn?)

### Code Quality (testable, decoupled, observable, documented, reversible, idempotent, thread-safe, async-safe, typed, deterministic)

## Prohibited

- Duplicated code
- Duplicated configuration
- Inconsistent events
- Ambiguous names
- Unnecessary singletons
- Circular dependencies
- Giant modules
- Repeated logic
- Technical debt
- Magic / implicit behavior
- Hidden side-effects
- Inconsistent APIs

## Mandatory Integration

Every new component must auto-integrate with:
- Event Bus
- Event Store
- Capability Registry
- Knowledge Graph
- Documentation Platform
- Setup Wizard
- Metrics
- Health Center
- IdentityVault
- COPILOT
- Execution Platform

No isolated components allowed.

## Before Implementing Any Feature

Generate:
1. Expected impact
2. Risks
3. Dependencies
4. Alternatives
5. Maintenance cost
6. Expected ROI
7. Roadmap compatibility
8. Rollback plan
9. Required tests
10. Success metrics

## Priority Order (never sacrifice a higher level for a lower one)

1. **Corrección**
2. **Seguridad**
3. **Estabilidad**
4. **Arquitectura**
5. **Observabilidad**
6. **Rendimiento**
7. **Autonomía**
8. **Escalabilidad**
9. **Experiencia de usuario**
10. **Nuevas funcionalidades**

## Scoring Dimensions (0-10)

Every audit must score:
- Arquitectura
- Seguridad
- Runtime
- Event System
- Execution Platform
- Knowledge Graph
- COPILOT
- Integraciones
- Observabilidad
- Testing
- Documentación
- UX
- Companion
- Escalabilidad
- Autonomía
- Aprendizaje
- ROI
- Preparación para Producción

For each score < 10: deliver a concrete, prioritized, measurable plan to close the gap.

## Acceptance Criterion

Not "code compiles" but:

> **ORION es más estable, más simple, más autónomo y más efectivo para producir resultados reales que antes del cambio.**
