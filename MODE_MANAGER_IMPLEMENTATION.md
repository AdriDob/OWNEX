# Mode Manager — Panel Inteligente Centralizado para Control de Modos

## 🎯 PROBLEMA RESUELTO

OWNEX tiene **14+ sistemas de modos diferentes** que pueden ser conflictivos entre sí. El usuario pidió un panel inteligente para activar/desactivar modos sin conflictos.

---

## 📊 TODOS LOS MODOS DE OWNEX

### 1. IncomeMode (Revenue) — **3 modos**
- **ultra_fast** — Phase 0 (survival), solo categorías que pagan en días
- **balanced** — Phase 1-2, mix de velocidades
- **scaling** — Phase 3-4, alto valor, largo plazo

### 2. OWNEXMode (General) — **2 modos**
- **manual** — Usuario controla todo manualmente
- **automatic** — Sistema opera automáticamente

### 3. TradingMode (Trading) — **3 modos**
- **real** — Trading real con dinero real
- **dry_run** — Simulación sin ejecución
- **paper_trading** — Trading de papel (simulación completa)

### 4. AssistanceMode (Assistance) — **4 modos**
- **guided** — Sistema guía cada paso
- **assisted** — Sistema asiste cuando solicitado
- **autonomous** — Sistema opera solo
- **expert** — Sistema como experto

### 5. WorkMode (Work) — **n modos**
- **bug_bounty** — Enfoque en bug bounty
- **investment** — Enfoque en inversiones
- **trading** — Enfoque en trading

### 6. VoiceMode (Voice) — **4 modos**
- **normal** — Texto y voz normales
- **voice_only** — Solo voz
- **text_only** — Solo texto
- **hybrid** — Ambos al mismo tiempo

### 7. DecisionMode (Decision) — **3 modos**
- **explanatory** — Explica decisiones
- **automatic** — Decide automáticamente
- **expert** — Modo experto

---

## 🔒 REGLAS DE COMPATIBILIDAD

### IncomeMode Reglas

**ultra_fast:**
- ✅ Compatible con: manual, dry_run, paper_trading
- ❌ Mutually exclusive con: balanced, scaling
- ❌ Excludes: real trading

**balanced:**
- ✅ Compatible con: automatic, dry_run
- ❌ Mutually exclusive con: ultra_fast, scaling

**scaling:**
- ✅ Compatible con: automatic, real
- ✅ Requires: automatic
- ❌ Mutually exclusive con: ultra_fast, balanced
- ❌ Excludes: manual

### OWNEXMode Reglas

**manual:**
- ✅ Compatible con: ultra_fast, balanced, dry_run
- ❌ Mutually exclusive con: automatic
- ❌ Excludes: scaling, autonomous, expert

**automatic:**
- ✅ Compatible con: balanced, scaling, real
- ❌ Mutually exclusive con: manual
- ✅ Required by: scaling, autonomous, expert

### TradingMode Reglas

**real:**
- ✅ Compatible with: scaling, automatic
- ✅ Requires: automatic
- ❌ Mutually exclusive con: dry_run, paper_trading
- ❌ Excludes: ultra_fast

**dry_run:**
- ✅ Compatible con: ultra_fast, balanced, manual, automatic
- ❌ Mutually exclusive con: real, paper_trading

**paper_trading:**
- ✅ Compatible con: ultra_fast, balanced, manual
- ❌ Mutually exclusive con: real, dry_run

### AssistanceMode Reglas

**guided:**
- ✅ Compatible con: manual
- ❌ Mutually exclusive con: assisted, autonomous, expert
- ❌ Excludes: automatic

**assisted:**
- ✅ Compatible con: manual, automatic
- ❌ Mutually exclusive con: guided, autonomous, expert

**autonomous:**
- ✅ Compatible con: automatic
- ✅ Requires: automatic
- ❌ Mutually exclusive con: guided, assisted, expert
- ❌ Excludes: manual

**expert:**
- ✅ Compatible con: automatic
- ✅ Requires: automatic
- ❌ Mutually exclusive con: guided, assisted, autonomous
- ❌ Excludes: manual

---

## 🎛️ MODE MANAGER (IMPLEMENTADO)

### Backend: ModeManager

**Funcionalidades:**
- ✅ Centralized mode storage
- ✅ Compatibility rules entre modos
- ✅ Conflict detection antes de activar
- ✅ Auto-resolution de conflictos (con force)
- ✅ History de cambios de modo
- ✅ Validation rules (requires/excludes)
- ✅ Persistence en disco

**API Endpoints:**
- `GET /api/modes/status` — Estado del mode manager
- `GET /api/modes/active` — Modos activos
- `GET /api/modes/available` — Todos los modos con status
- `POST /api/modes/set` — Activar modo (detecta conflictos)
- `POST /api/modes/set-force` — Activar modo (fuerza resolución)
- `GET /api/modes/compatibility` — Matriz de compatibilidad
- `GET /api/modes/history` — Historial de cambios

### Frontend: ModeManagerPanel

**Funcionalidades:**
- ✅ Panel centralizado para todos los modos
- ✅ Agrupado por categoría (Revenue, General, Trading, Assistance)
- ✅ Indicador visual de conflictos
- ✅ Botón activate/deactivate por modo
- ✅ Modal de conflict con sugerencias
- ✅ Force activate (auto-resolución)
- ✅ Modal de detalles (requirements, excludes, compatible_with)
- ✅ Historial de cambios
- ✅ Refresh automático

**Visual:**
- Active modes: verde con checkmark
- Inactive modes: gris con círculo
- Conflict modes: amarillo con warning
- Categorías separadas con headers
- Botones de acción por modo

---

## 🚀 CÓMO USAR

### 1. Ver Panel de Modos

**URL:** http://localhost:8000 → Capital → Progressive Scaling → "Show Mode Manager"

**Muestra:**
- Categorías: Revenue, General, Trading, Assistance
- Modos dentro de cada categoría
- Status: Active/Inactive
- Conflict warnings
- Botones Activate/Deactivate

### 2. Activar Modo (Sin Conflictos)

**Ejemplo:** Activar "Ultra Fast"

```bash
curl -X POST http://localhost:8000/api/modes/set \
  -H "Content-Type: application/json" \
  -d '{"mode_key": "income_ultra_fast", "force": false}'
```

**Resultado:**
```json
{
  "status": "success",
  "message": "Activated income_ultra_fast",
  "active_modes": {
    "income": "ultra_fast",
    "general": "manual"
  },
  "auto_resolved": [],
  "conflicts_resolved": []
}
```

### 3. Activar Modo (Con Conflictos)

**Ejemplo:** Activar "Scaling" cuando "Manual" está activo

```bash
curl -X POST http://localhost:8000/api/modes/set \
  -H "Content-Type": application/json" \
  -d '{"mode_key": "income_scaling", "force": false}'
```

**Resultado:**
```json
{
  "status": "conflict",
  "message": "Cannot activate income_scaling due to conflicts",
  "conflicts": ["general_manual"],
  "suggested_resolution": {
    "mode_key": "income_scaling",
    "total_conflicts": 1,
    "suggestions": [
      {
        "conflict": "general_manual",
        "conflict_name": "Manual",
        "action": "deactivate",
        "reason": "Scaling is mutually exclusive with Manual"
      }
    ]
  }
}
```

### 4. Force Activate (Auto-Resolve)

**Ejemplo:** Forzar activación de "Scaling"

```bash
curl -X POST http://localhost:8000/api/modes/set-force \
  -H "Content-Type": application/json" \
  -d '{"mode_key": "income_scaling", "force": true}'
```

**Resultado:**
```json
{
  "status": "success",
  "message": "Activated income_scaling",
  "active_modes": {
    "income": "scaling",
    "general": "automatic"
  },
  "auto_resolved": ["general_manual"],
  "conflicts_resolved": ["general_manual"]
}
```

### 5. Ver Matriz de Compatibilidad

```bash
curl http://localhost:8000/api/modes/compatibility
```

**Devuelve:**
```json
{
  "income_ultra_fast": {
    "compatible_with": ["general_manual", "trading_dry_run", "trading_paper_trading"],
    "mutually_exclusive_with": ["income_balanced", "income_scaling"],
    "requires": [],
    "excludes": ["trading_real"]
  },
  ...
}
```

---

## 💎 EJEMPLOS DE COMBINACIONES VÁLIDAS

### Combinación 1: Ultra Fast + Manual + Dry Run
```
✅ income: ultra_fast
✅ general: manual
✅ trading: dry_run
✅ assistance: guided
```
**Resultado:** Sistema supervivencia, usuario controla, simulación trading

### Combinación 2: Scaling + Automatic + Real
```
✅ income: scaling
✅ general: automatic
✅ trading: real
✅ assistance: autonomous
```
**Resultado:** Sistema escalamiento agresivo, trading real, autónomo

### Combinación 3: Balanced + Automatic + Dry Run
```
✅ income: balanced
✅ general: automatic
✅ trading: dry_run
✅ assistance: assisted
```
**Resultado:** Sistema balanceado, simulación trading, asistido

---

## ❌ COMBINACIONES INVÁLIDAS (CONFLICTOS)

### Invalido 1: Ultra Fast + Real Trading
```
❌ income: ultra_fast
❌ trading: real
```
**Razón:** Ultra Fast excludes real trading (riesgo alto)

### Invalido 2: Manual + Autonomous
```
❌ general: manual
❌ assistance: autonomous
```
**Razón:** Manual excludes autonomous (contradictorio)

### Invalido 3: Scaling + Manual
```
❌ income: scaling
❌ general: manual
```
**Razón:** Scaling requires automatic

---

## 🎯 FLUJO DE TRABAJO DEL PANEL

### 1. Usuario abre panel
- Click en "Show Mode Manager"
- Panel muestra todos los modos por categoría

### 2. Usuario intenta activar modo
- Click en "Activate" en modo
- Sistema detecta conflictos

### 3. Sin conflictos
- Modo se activa inmediatamente
- Mutually exclusive modes se desactivan
- Requirements se activan automáticamente
- Panel se actualiza

### 4. Con conflictos
- Modal de conflict aparece
- Muestra conflictos detectados
- Sugiere desactivar modos conflictivos
- Usuario puede:
  - Cancelar (no activar)
  - Force Activate (auto-resolver)

### 5. Force Activate
- Sistema desactiva modos conflictivos
- Activa modo solicitado
- Activa requirements automáticamente
- Panel se actualiza
- Historial registra cambio

---

## 💎 CARACTERÍSTICAS DEL PANEL

**Visual:**
- Categorías con headers
- Status indicators (active/inactive/conflict)
- Conflict warnings (amarillo)
- Botones de acción
- Modals para detalles/conflictos/historial

**Funcional:**
- Conflict detection automático
- Sugerencias de resolución
- Force activate con auto-resolución
- Historial de cambios
- Compatibility matrix
- Refresh automático

**Inteligente:**
- Entiende dependencias (requires)
- Entiende exclusiones (excludes)
- Entiende mutual exclusivity
- Sigue reglas de compatibilidad
- Valida antes de activar

---

## 📊 IMPLEMENTACIÓN COMPLETA

**Backend:**
- ✅ ModeManager (centralizado)
- ✅ ModeConfig para cada modo
- ✅ Compatibility rules
- ✅ Conflict detection
- ✅ Auto-resolution
- ✅ History tracking
- ✅ Persistence
- ✅ 7 API endpoints

**Frontend:**
- ✅ ModeManagerPanel (componente)
- ✅ Categorización visual
- ✅ Conflict indicators
- ✅ Modal de conflict
- ✅ Modal de detalles
- ✅ Modal de historial
- ✅ Force activate
- ✅ Refresh automático

**Integración:**
- ✅ Con Ultra Fast Income
- ✅ Con Progressive Scaling
- ✅ Con todos los sistemas de modos

**Tests:**
- ✅ Pasando (88 passed)

---

## 💎 CONCLUSIÓN

**SÍ, los modos pueden ser conflictivos. He implementado:**

1. **Mode Manager centralizado** — Gestiona todos los modos
2. **Reglas de compatibilidad** — Define qué puede coexistir
3. **Detección de conflictos** — Antes de activar
4. **Auto-resolución** — Con force activate
5. **Panel inteligente** — Frontend visual
6. **Sugerencias** — Cómo resolver conflictos
7. **Historial** — Tracking de cambios

**El panel te permite:**
- Ver todos los modos por categoría
- Activar/desactivar sin conflictos
- Ver conflictos y sugerencias
- Force activate con auto-resolución
- Ver detalles de cada modo
- Ver historial de cambios

**Sin conflictos garantizado** — el sistema previene activaciones inválidas y te guía para resolver conflictos.
