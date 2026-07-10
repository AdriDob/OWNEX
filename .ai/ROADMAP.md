# Roadmap — Rastro / CATEYE

> Priorizado por impacto: Seguridad → Estabilidad → Tests → Integración → Rendimiento → UX → Docs → Features

## Completado (Verificado)

- [x] Fase 0: Security Hardening (8 vulnerabilidades críticas resueltas)
- [x] Fase 1: Persistencia de circuit breakers + reward learning + health snapshots
- [x] Fase 2: DedupTracker unificado con fingerprints normalizados
- [x] Fase 3: Scheduler adaptativo con priorización por reward learning
- [x] Fase 4: Rate limit por user-id + localStorage hardening
- [x] Fase 5: Release hardening (12 fixes: event-loop, WAL, tasks, indexes, etc.)
- [x] Fase 6: Documentación consolidada + portable installer

## Pendiente (v3.1 — ORION Reasoning Layer)

### Prioridad Alta

- [ ] **Hypothesis Challenger**: Refutación activa antes de validar
- [ ] **Evidence Graph**: Evidencia a favor y en contra en cada Verdict
- [ ] **Adaptive Report Gate**: Threshold por tipo de vulnerabilidad

### Prioridad Media

- [ ] **FeedbackLearner pipeline**: Pesos adaptativos del ConfidenceScorer

### Deuda Técnica

- [ ] Unificar 3 sistemas de salud superpuestos (SystemHealthEngine, HealthMonitor, Watchdog)
- [ ] Agregar persistencia a health snapshots en RecoveryStore
- [ ] Conectar DuplicateDetector con el DedupTracker unificado
- [ ] Mover API keys del frontend al backend (IdentityVault)
- [ ] Auditoría de dependencias no utilizadas

## Criterios para Marcar como Completo

Una funcionalidad se considera "completa" cuando:
1. Código implementado y funcionando
2. Tests existentes y pasando
3. Integración verificada con módulos dependientes
4. Sin vulnerabilidades de seguridad conocidas
5. Estado registrado en COMPLETED_FEATURES.json
6. Referenciado en INTEGRATION_REGISTRY.json