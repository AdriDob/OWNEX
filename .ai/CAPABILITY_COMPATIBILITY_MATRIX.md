# Matriz de Compatibilidad — OWNEX 4 Áreas

> **Fecha:** 2026-10-23
> **Objetivo:** Analizar capacidades existentes contra la visión ampliada de OWNEX (SOFTWARE, GESTIÓN, INVERSIÓN, EXTRA WORK)
> **Regla:** Preservar todo el trabajo existente. No reescribir. Solo extender/adaptar donde sea necesario.

---

## 1. CAPACIDADES EXISTENTES ANALIZADAS

### 1.1 SOFTWARE (Desarrollo de Software, QA, Bug Bounty, Seguridad)

| Capacidad | Archivos/Modulos | Estado Comprobado | Área Propuesta | Acción | Riesgo |
|-----------|----------------|------------------|----------------|--------|-------|
| Security Cycle (Rastro) | `cores/offensive/`, `cores/validation/`, cores/engine | IMPLEMENTADO | SOFTWARE | KEEP | Bajo |
| Opportunity Engine | `cores/opportunity/`, api/routers/* | IMPLEMENTADO | SOFTWARE, EXTRA WORK | EXTEND (filtros por área) | Bajo |
| Execution Layer | `cores/execution/`, executors en `cores/opportunity/executors/` | IMPLEMENTADO | SOFTWARE, EXTRA WORK | KEEP | Bajo |
| BountyCoordinator | `cores/agents/bounty_coordinator.py` | IMPLEMENTADO | SOFTWARE | KEEP | Bajo |
| CoderAgent | `cores/autonomy/coder_agent.py` | IMPLEMENTADO | SOFTWARE | KEEP | Bajo |
| CATEYE (inteligencia operativa) | `cores/copilot/`, agentes especializados | IMPLEMENTADO | SOFTWARE | KEEP | Bajo |
| GitHub integration | `cores/personal_infrastructure/manager.py` (desarrollo objetivo) | PARCIAL | SOFTWARE | EXTEND (completo workflow) | Medio |
| CI/CD workflows | NO ENCONTRADO | N/A | SOFTWARE | ADD | Alto |
| Linters/Formatters | Config ruff + mypy en pyproject.toml | CONFIGURADO | SOFTWARE | KEEP | Bajo |
| Test execution | tests/ (448 files) | IMPLEMENTADO | SOFTWARE | KEEP | Bajo |

**Análisis SOFTWARE:**
- Bug bounty y seguridad digital (Rastro/CATEYE) están **completamente implementados** → KEEP
- Opportunity Engine está implementado pero necesita filtros para distinguir SOFTWARE vs EXTRA WORK → EXTEND
- GitHub existe como objetivo de aprendizaje pero no como workflow completo de dev → EXTEND
- CI/CD workflows NO existen → ADD (prioridad media)

### 1.2 GESTIÓN (Tareas, Proyectos, Agenda, Sesiones, Autoguardado)

| Capacidad | Archivos/Modulos | Estado Comprobado | Área Propuesta | Acción | Riesgo |
|-----------|----------------|------------------|----------------|--------|-------|
| Agenda Unificada | `cores/agenda/`, api/routers/agenda/ | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Life Management (tareas/goals) | `cores/life_management/` (referenciado en agenda) | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Capital (savings) | `cores/capital/` | IMPLEMENTADO | GESTIÓN, INVERSIÓN | KEEP | Bajo |
| Career (roadmap) | `cores/career/` (referenciado en agenda) | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Income Target | `cores/direct_work_engine/` | IMPLEMENTADO | GESTIÓN, EXTRA WORK | KEEP | Bajo |
| Daily Companion | `cores/direct_work_engine/daily_companion.py` | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Outlook Calendar | `cores/life_management/` (referenciado en agenda) | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Session persistence | `cores/session_manager.py` | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Autosave | `cores/version_backup/backup_system.py` | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Projects | `frontend/src/pages/ProjectsList.vue` | PARCIAL | GESTIÓN | EXTEND | Bajo |
| Files management | `api/routers/files.py` | IMPLEMENTADO | GESTIÓN | KEEP | Bajo |
| Notes system | NO CLARO | N/A | GESTIÓN | EVALUAR | Medio |

**Análisis GESTIÓN:**
- Agenda unificada con 8 fuentes (Life Management, Capital, Career, Income Target, Outlook, etc.) está **completamente implementada** → KEEP
- Session persistence + autosave están implementados → KEEP
- Projects existe en frontend pero backend incompleto → EXTEND
- Notes system no está claro → EVALUAR (prioridad baja)

### 1.3 INVERSIÓN (Mercados, Portfolio, IOL, IBKR, Backtesting, Paper Trading)

| Capacidad | Archivos/Modulos | Estado Comprobado | Área Propuesta | Acción | Riesgo |
|-----------|----------------|------------------|----------------|--------|-------|
| Investment Manager | `cores/investment/manager.py` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Portfolio snapshot | `api/routers/investment.py:get_portfolio` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Trading Engine | `cores/trading/`, `CopyTradingEngine` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Trading adapters | `cores/trading/adapters/` (7 adapters) | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Memecoin trading | `cores/trading/memecoin/` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| MT5 integration | `cores/trading/mt5/` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Backtesting | `cores/trading/strategies/mean_reversion.py` | PARCIAL | INVERSIÓN | EXTEND | Medio |
| Paper trading | NO SEPARADO (mezclado con real) | PARCIAL | INVERSIÓN | ADAPT (separación REAL/SIMULATION/TEST) | Alto |
| IOL integration | NO ENCONTRADO | N/A | INVERSIÓN | ADD | Alto |
| Interactive Brokers | NO ENCONTRADO | N/A | INVERSIÓN | ADD | Alto |
| Market data (Coingecko) | `cores/crypto/coingecko.py` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Polymarket | `cores/investment/adapters/polymarket_adapter.py` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |
| Binance | `cores/market_intelligence/binance_monitor.py` | IMPLEMENTADO | INVERSIÓN | KEEP | Bajo |

**Análisis INVERSIÓN:**
- Investment Manager + Portfolio + Trading Engine están **completamente implementados** → KEEP
- 7 trading adapters existentes (Cryptohawk, Toro, etc.) → KEEP
- **CRÍTICO:** Paper trading NO está separado de real trading → ADAPT (separación REAL/SIMULATION/TEST es obligatoria)
- IOL + Interactive Brokers NO existen → ADD (prioridad alta según brief)
- Backtesting existe pero parcial → EXTEND

### 1.4 EXTRA WORK (Negocios digitales, webs con IA, ecommerce, plataformas remuneradas)

| Capacidad | Archivos/Modulos | Estado Comprobado | Área Propuesta | Acción | Riesgo |
|-----------|----------------|------------------|----------------|--------|-------|
| Direct Work Engine | `cores/direct_work_engine/` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Opportunity Engine | `cores/opportunity/` | IMPLEMENTADO | EXTRA WORK | EXTEND (filtros por área) | Bajo |
| Workbank | `cores/direct_work_engine/workbank.py` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Income Experiments | `cores/income_experiments/` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Content Factory | `cores/content/` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Fiverr | `api/routers/fiverr.py` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Ecommerce | `api/routers/ecommerce.py` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| YouTube Shorts | `frontend/src/pages/YouTubeShortsFree.vue` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Meme Copy | `cores/trading/meme_copy/` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Apuestas Deportivas | `frontend/src/pages/ApuestasDeportivas.vue` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |
| Extra Work API | `api/routers/extra_work.py` | IMPLEMENTADO | EXTRA WORK | KEEP | Bajo |

**Análisis EXTRA WORK:**
- Direct Work Engine + Workbank + Income Experiments están **completamente implementados** → KEEP
- Múltiples canales específicos (Fiverr, Ecommerce, YouTube Shorts, Meme Copy, Apuestas) → KEEP
- Opportunity Engine necesita filtros para distinguir EXTRA WORK de SOFTWARE → EXTEND

---

## 2. COMPONENTES TRANSVERSALES

| Componente | Archivos/Modulos | Estado | Áreas Afectadas | Acción |
|------------|----------------|--------|------------------|--------|
| EventBus | `cores/events/event_bus.py` | IMPLEMENTADO | TODAS | KEEP |
| Health Checks | `cores/health/`, `cores/orion/health/` | IMPLEMENTADO | TODAS | KEEP |
| Scheduler | `cores/scheduler/` | IMPLEMENTADO | TODAS | KEEP |
| Credentials Vault | `cores/identity_vault.py` | IMPLEMENTADO | TODAS | KEEP |
| Agent System | `cores/agents/` | IMPLEMENTADO | TODAS | KEEP |
| COPILOT | `cores/copilot/` | IMPLEMENTADO | TODAS | KEEP |
| Database (SQLite) | `database/` | IMPLEMENTADO | TODAS | KEEP |
| API Layer | `api/` | IMPLEMENTADO | TODAS | KEEP |
| Frontend (Vue 3) | `frontend/` | IMPLEMENTADO | TODAS | KEEP |
| Tauri Desktop | `src-tauri/` | IMPLEMENTADO | TODAS | KEEP |
| Mobile WebSocket | `cores/websocket/mobile_sync.py` | IMPLEMENTADO (FASE 6.4) | TODAS | KEEP |

---

## 3. GAPS IDENTIFICADOS

### 3.1 SOFTWARE
- [ ] CI/CD workflows completos (GitHub Actions, GitLab CI, etc.)
- [ ] Linting/Formatters integrados en workflows
- [ ] GitHub PR workflow completo (review, approval, merge)
- [ ] Dependency scanning automatizado
- [ ] Secret detection en repos

### 3.2 GESTIÓN
- [ ] Projects backend completo (actualmente solo frontend)
- [ ] Notes system unificado
- [ ] File management mejorado (actualmente básico)

### 3.3 INVERSIÓN
- [ ] **CRÍTICO:** Separación REAL/SIMULATION/TEST en todo el sistema
- [ ] IOL integration (oficial docs, MCP server)
- [ ] Interactive Brokers integration (Web API, TWS API)
- [ ] Backtesting completo (fees, slippage, look-ahead bias)
- [ ] Reconciliation de órdenes (real vs simulado)
- [ ] Risk limits configurables

### 3.4 EXTRA WORK
- [ ] Opportunity Engine con filtros por área (SOFTWARE vs EXTRA WORK)
- [ ] Canales Argentina específicos (Droppinglabel, MercadoLibre ya existen, verificar Adriel Webs)
- [ ] Workflow unificado de descubrimiento → evaluación → configuración → ejecución → medición

### 3.5 TRANSVERSAL
- [ ] Global Operations Dashboard (requerido por brief)
- [ ] Universal Connector Catalog (MCP, APIs locales, etc.)
- [ ] Windows-native verification (actualmente solo Linux/WSL)

---

## 4. PRIORIDAD DE ACCIÓN

### FASE 1: Preservación y Estabilización (inmediato)
1. Verificar FASE 5-6 (ProviderDecision, MobileSync) tests
2. Verificar separación REAL/SIMULATION/TEST en trading
3. Documentar estado actual de 70+ archivos modificados

### FASE 2: GAPS Críticos (alta prioridad)
1. Separación REAL/SIMULATION/TEST en trading (CRÍTICO)
2. Opportunity Engine con filtros por área
3. Global Operations Dashboard
4. Windows-native verification

### FASE 3: Nuevas Integraciones (media prioridad)
1. IOL integration (oficial docs)
2. Interactive Brokers integration
3. CI/CD workflows para SOFTWARE
4. Universal Connector Catalog

### FASE 4: Completar Parciales (baja prioridad)
1. Projects backend
2. Backtesting completo
3. Notes system

---

## 5. RIESGOS Y DEPENDENCIAS

### Riesgos
- **ALTO:** Trading real mezclado con simulación → podría ejecutar órdenes reales accidentalmente
- **MEDIO:** Opportunity Engine sin filtros por área → usuario confunde SOFTWARE con EXTRA WORK
- **MEDIO:** Windows-native no verificado → Tauri build puede fallar en Windows real
- **BAJO:** Cambios simultáneos sin coordinación → conflictos entre Devin/Freebuff

### Dependencias
- Sistema operativo: Actualmente Linux/WSL, Windows requiere verificación
- APIs externas: IOL, IBKR requieren investigación de docs oficiales
- MCP: Investigar servidores oficiales y seguridad

---

## 6. CONCLUSIÓN

**Capacidades existentes a PRESERVAR (KEEP):**
- Toda la infraestructura transversal (EventBus, Health, Scheduler, Credentials, Agents, COPILOT, DB, API, Frontend, Tauri)
- SOFTWARE: Security Cycle, Opportunity Engine, Execution Layer, BountyCoordinator, CoderAgent, CATEYE
- GESTIÓN: Agenda unificada (8 fuentes), Session persistence, Autosave, Files management
- INVERSIÓN: Investment Manager, Portfolio, Trading Engine, 7 adapters, market data
- EXTRA WORK: Direct Work Engine, Workbank, Income Experiments, múltiples canales específicos

**Capacidades a EXTENDER (EXTEND):**
- Opportunity Engine: filtros por área (SOFTWARE vs EXTRA WORK)
- GitHub: workflow completo de dev (actualmente solo objetivo de aprendizaje)
- Backtesting: completar (fees, slippage, etc.)

**Capacidades a ADAPTAR (ADAPT):**
- Trading: separación REAL/SIMULATION/TEST (CRÍTICO)

**Capacidades a AGREGAR (ADD):**
- SOFTWARE: CI/CD workflows, dependency scanning, secret detection
- INVERSIÓN: IOL integration, Interactive Brokers integration
- TRANSVERSAL: Global Operations Dashboard, Universal Connector Catalog
- GESTIÓN: Projects backend (parcial)

**Capacidades a EVALUAR (EVALUAR):**
- GESTIÓN: Notes system

---

## 7. ROADMAP INTEGRADO PROPUESTO

### Orden de prioridad (no reescritura, evolución incremental):

1. **Preservar y estabilizar** (inmediato)
   - Verificar FASE 5-6 tests
   - Verificar separación REAL/SIMULATION/TEST
   - Documentar estado actual

2. **Adaptar críticos** (seguridad)
   - Separación REAL/SIMULATION/TEST en trading
   - Global Operations Dashboard básico

3. **Extender filtros** (usabilidad)
   - Opportunity Engine con filtros por área
   - Navegación por 4 áreas en frontend

4. **Investigar integraciones** (investigación, no implementación)
   - IOL docs oficiales
   - Interactive Brokers docs oficiales
   - MCP servers oficiales

5. **Windows-native verification** (compatibilidad)
   - Verificar Tauri build en Windows real
   - Verificar backend sidecar en Windows real

6. **Completar gaps** (funcionalidad)
   - CI/CD workflows
   - Projects backend
   - Backtesting completo

7. **IOL/IBKR implementation** (solo después de seguridad garantizada)
   - Implementar IOL
   - Implementar IBKR
   - Backtesting con separación REAL/SIMULATION/TEST

---

**NOTA:** Esta matriz es read-only. No modificar archivos sin autorización explícita.
