# OWNEX Roadmap — Product Core

> **REGLAS**:
> 1. No más infraestructura. Solo producto. Si no es visible en Mission Control, no existe.
> 2. Cada sprint debe responder "¿qué oportunidad tengo hoy y cuál es la mejor acción?"
> 3. Si ya hay capital técnico (Rastro), usarlo. No crear desde cero.
> 4. Un Work Cycle funcionando > 5 a medias.
> 5. Dashboard primero, automatización después.

## OWNEX Architecture

```
                  OWNEX
                     |
              Mission Control
              (Dashboard Throughput)
                     |
     --------------------------------
     |              |               |
 Security        Forge          Wealth
 Cycle           Cycle           Cycle
     |
   Rastro
     |
 Knowledge Engine
     |
 Memory Layer
```

## PRÓXIMOS SPRINTS (orden estricto)

### FASE 0 — OWNEX Foundation ✅
- [x] Branding + Design System (negro/azul/blanco/dorado)
- [x] SplashScreen, AppSidebar, OrionSidebar, MissionControl
- [x] Infra estable: Ollama (1 modelo), FCC (router), Hermes, OpenCode, Cline
- [x] Memoria documental en `.ai/`

### FASE 1 — Mission Control v1 ⭐⭐⭐⭐⭐ (SIGUIENTE)

Crear la interfaz central que responda en 5 segundos: "¿Qué oportunidades hay hoy?"

- [ ] **Dashboard Throughput**: oportunidades detectadas, priorizadas, ciclos activos, tareas pendientes, acciones recomendadas, estado de agentes
- [ ] **Agent Fleet**: vista simple del estado de cada agente (Hermes 🟢, OpenCode 🟢, Cline 🟢, Ollama 🟢, FCC 🟡)
- [ ] **Opportunity Engine v0**: modelo de datos de oportunidad (type, source, reward, difficulty, confidence, recommended_action) sin APIs externas todavía
- [ ] **Activity Timeline**: qué pasó, cuándo, qué falta

### FASE 2 — Security Cycle v1 ⭐⭐⭐⭐⭐

Migrar Rastro como primer Work Cycle de OWNEX. No crear nada nuevo, convertir.

- [ ] Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning
- [ ] Executive Dashboard (CEO view, no técnico): "¿esta semana ganamos plata?"
- [ ] Knowledge capture: cada finding deja metadata de aprendizaje
- [ ] Pipeline E2E funcionando sin intervención

### FASE 3 — Opportunity Engine v1 ⭐⭐⭐⭐

- [ ] Modelo de scoring: $ esperado × (1 - dificultad) × prob. aceptación
- [ ] Inputs: dinero, dificultad, tiempo, competencia, experiencia previa, historial
- [ ] Output: top 5 oportunidades para hoy
- [ ] Integrar con TargetPrioritizer existente
- [ ] Feedback loop: lo que se aceptó/rechazó alimenta el score
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

## COMPLETED (no tocar)

| Feature | Estado |
|---------|--------|
| Revenue Pipeline | ✅ Finding → Evidence → Report → Platform → Payout |
| Offensive Intelligence (5 reasoners) | ✅ 101 tests |
| AI Bounty Auto-Hunter | ✅ 29 tests |
| Recon Intelligence (TargetPrioritizer) | ✅ 22 tests |
| Acceptance Intelligence (Learner) | ✅ 18+14 tests |
| Revenue Intelligence (USD/h) | ✅ 70 tests |
| Report Optimizer V2 | ✅ 23 tests |
| Verdict Auto-Learner | ✅ 14 tests |
| SlitherTool + Web3 reasoners | ✅ Creado |
| AI Bounty scan real | ✅ Scheduler escanea targets |
| Configuration Wizard v2 | ✅ 14 tests |
| Command System Fase 1 | ✅ 45 tests |
| Health Center unificado | ✅ 25 tests |
| Capital Dashboard Unificado | ✅ 5→1 páginas |
| Router 50→8 secciones | ✅ Consolidado |
| Frontend Consolidation | ✅ 8 secciones, 79 redirecciones |
| Hypothesis Challenger | ✅ Explicaciones alternativas + incertidumbre |
| OWNEX Rebranding | ✅ Frontend, CSS, sidebar, splash, documentación |
| Dev Bounty Research | ✅ Superteam, TaskBounty, Opire, IssueHunt |
| AI Work Research | ✅ Outlier, DataAnnotation, Mindrift, Stellar |
| Wealth Research | ✅ CoinGecko, Firefly III, Zerion, Plaid |
| Jobs Research | ✅ Freelancer.com, LinkedIn |
| Infra Stabilization | ✅ Ollama único, FCC purificado, Hermes/OpenCode/Cline configurados |

## Principios de producto

1. **Dashboard primero**: toda feature nueva debe ser visible en Mission Control.
2. **Un ciclo a la vez**: Security Cycle completo → después expandir.
3. **No más APIs externas sin validación interna**: el modelo de oportunidad existe antes de conectarlo a fuentes reales.
4. **Knowledge Engine es consecuencia, no objetivo**: aprender de cada finding/reporte automáticamente.
5. **Cero feature sin métrica**: si no se puede medir en el dashboard, no se construye.
