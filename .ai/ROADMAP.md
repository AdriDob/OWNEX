# Roadmap — OWNEX Platform

> **Regla de Oro:** Revenue Rule — Ninguna feature entra al roadmap si no aumenta al menos uno de: detección de vulnerabilidades, calidad de evidencia, probabilidad de aceptación, o aprendizaje del sistema. No hay excepciones.

## Arquitectura OWNEX

```
OWNEX
    |
Mission Control
(Throughput Dashboard)
    |
------------------------
|       |       |       |
Security Forge   Wealth  Intelligence
Cycle    Cycle    Cycle    Cycle
  |       |        |        |
Rastro  Forge    Vault    Atlas
  |
Knowledge Engine
  |
Memory Layer
```

## Ciclos de Trabajo (Work Cycles)

| Ciclo | Nombre | Estado | Prioridad |
|-------|--------|--------|-----------|
| 🔵 | **Rastro** (Security) | ✅ Activo — En consolidación | **FASE 1** |
| 🟣 | **Forge** (Dev Bounty) | 📝 Diseño | FASE 4 |
| 🟢 | **Pulse** (AI Work) | 📝 Diseño | FASE 4 |
| 🟡 | **Vault** (Wealth) | ⚠️ Parcial | FASE 4 |
| ⚪ | **Atlas** (Intelligence) | 📝 Diseño | FASE 5 |
| 🤖 | **Orion** (Coordinator) | ✅ Existe | Transversal |

---

## FASES DE IMPLEMENTACIÓN

### FASE 0 — OWNEX Foundation ✅ COMPLETADA
- [x] Branding + Design System (negro/azul/blanco/dorado)
- [x] SplashScreen, AppSidebar, OrionSidebar, MissionControl
- [x] Infra estable: Ollama (1 modelo), FCC (router), Hermes, OpenCode, Cline
- [x] Memoria documental en `.ai/`
- [x] **OWNEX_DESIGN_SYSTEM.md** — Documentación completa del Design System v1

### FASE 1 — Mission Control v1 ⭐⭐⭐⭐⭐ (EN CURSO)

Crear la interfaz central que responda en 5 segundos: **"¿Qué oportunidades hay hoy?"**

- [ ] **Dashboard Throughput**: oportunidades detectadas, priorizadas, ciclos activos, tareas pendientes, acciones recomendadas, estado de agentes
- [ ] **Agent Fleet**: vista simple del estado de cada agente (Hermes 🟢, OpenCode 🟢, Cline 🟢, Ollama 🟢, FCC 🟡)
- [ ] **Opportunity Engine v0**: modelo de datos de oportunidad (type, source, reward, difficulty, confidence, recommended_action) sin APIs externas todavía
- [ ] **Activity Timeline**: qué pasó, cuándo, qué falta
- [ ] **Command Palette** como navegación principal (Ctrl+K)

**Tests objetivo:** 20-25 tests nuevos
**Archivos nuevos máx:** 3-4

### FASE 2 — Security Cycle v1 ⭐⭐⭐⭐⭐ (SIGUIENTE)

Migrar Rastro como primer Work Cycle de OWNEX. No crear nada nuevo, convertir.

- [ ] Pipeline E2E: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning
- [ ] Executive Dashboard (CEO view): "¿Esta semana ganamos plata?"
- [ ] Knowledge capture: cada finding deja metadata de aprendizaje
- [ ] Pipeline E2E funcionando sin intervención manual

**Tests objetivo:** 30-40 tests (reutilizando + extendiendo Rastro existente)
**Archivos nuevos máx:** 2-3 (adapters + wiring)

### FASE 3 — Opportunity Engine v1 ⭐⭐⭐⭐

- [ ] Modelo de scoring: $ esperado × (1 - dificultad) × prob. aceptación
- [ ] Inputs: dinero, dificultad, tiempo, competencia, experiencia previa, historial
- [ ] Output: top 5 oportunidades para hoy
- [ ] Integrar con TargetPrioritizer existente
- [ ] Feedback loop: lo aceptado/rechazado alimenta el score
- [ ] Tests

### FASE 4 — Work Cycle Expansion ⭐⭐⭐⭐

Solo después de que Security Cycle funcione E2E sin intervención.

- [ ] **Forge Adapter**: Superteam Earn, Opire
- [ ] **Pulse Adapter**: Outlier, DataAnnotation, Mindrift
- [ ] **Wealth Consolidation**: CoinGecko + Firefly III dashboard

### FASE 5 — Automatización ⭐⭐⭐⭐⭐

- [ ] Decisión autónoma: ¿local vs FCC según tarea?
- [ ] Auto-submission pipeline (Finding → Evidence → Report → Submit → Payout)
- [ ] Agentes independientes por ciclo con coordinador multi-agente

### FASE 6 — Tauri Desktop + Android Companion ⭐⭐⭐⭐

- [ ] Tauri + Vue 3 build (OWNEX.exe)
- [ ] Python backend como sidecar
- [ ] Android Companion app (notificaciones, approvals, métricas, wallet, agent status)
- [ ] Sincronización WebView / WebSocket

---

## ARCHITECTURE BUDGET (por feature)

- Máximo: 2 archivos nuevos, 1 dependencia, 1 evento, 1 capability, 1 contrato, 20 tests
- Si necesita más → la feature está mal diseñada

---

## PRIORIDADES REVENUE RULE

| Pregunta | Respuesta Actual |
|----------|------------------|
| ¿Qué parte aumenta la detección? | Mission Control v1 → Opportunity Engine |
| ¿Qué parte reduce falsos positivos? | Security Cycle v1 → Knowledge Engine |
| ¿Qué parte mejora la aceptación? | Report Optimizer → Acceptance Intelligence |
| ¿Qué parte mejora el aprendizaje? | Knowledge Engine → Evolution Engine |
| ¿Qué parte mejora la autonomía? | Agent Fleet → Multi-agent Coordinator |
| ¿Qué parte mejora Expected Revenue? | Opportunity Score Engine |
| ¿Qué parte solo mejora arquitectura? | ❌ EVITAR — no entra al sprint |

---

## SPRINT ACTUAL: FASE 1 — Mission Control v1

| Task | Estado | Tests | Owner |
|------|--------|-------|-------|
| Throughput Dashboard | ⏳ Pendiente | 8-10 | Frontend |
| Agent Fleet View | ⏳ Pendiente | 4-5 | Frontend |
| Opportunity Engine v0 (Data Model) | ⏳ Pendiente | 6-8 | Backend |
| Activity Timeline | ⏳ Pendiente | 3-4 | Frontend |
| Command Palette as Primary Nav | ⏳ Pendiente | 4-5 | Frontend |

---

## REFERENCIAS

- `.ai/OWNEX_ARCHITECTURE.md` — 4 capas, 3 motores, ciclos de trabajo
- `.ai/OWNEX_DESIGN_SYSTEM.md` — Design System v1 completo
- `.ai/OWNEX_MISSION_CONTROL_SPEC.md` — Spec detallada Mission Control
- `.ai/TASK_QUEUE.md` — Cola de tareas priorizada
- `.ai/CURRENT_STATE.md` — Estado verificado actual
- `.ai/STRATEGIC_AUDIT.md` — Marco de auditoría estratégica (10 preguntas + 18 dimensiones)