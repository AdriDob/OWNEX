# OWNEX — Product Map & Concept Consolidation

> Estado verificado contra el código el **2026-10-04**. Cada fila cita `file:line`
> o un grep reproducible. Lo que no se pudo verificar está en §6.
>
> Documento hermano: [`PRODUCT_ONE_PAGE.md`](PRODUCT_ONE_PAGE.md) — el qué.
> Este es el **dónde**.

---

## 1. El loop canónico

```
                    ┌──────────────────────────────────────┐
   178 fuentes ────▶│ DISCOVER                            │  dato, no motor
   (SourceDefinition)│  normalizar · deduplicar · admitir  │
                    └──────────────┬───────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │ EVALUATE                            │
                    │  elegibilidad (barrera)             │
                    │  prioridad TÉCNICA  ─┐               │
                    │  prioridad ECONÓMICA ─┴─ NO colapsar │
                    └──────────────┬───────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │ PREPARE · EXECUTE · VERIFY          │
                    │  adapters → PolicyEngine → evidencia │
                    └──────────────┬───────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │ HUMAN GATE  ← irreversibles          │
                    └──────────────┬───────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │ DELIVER · REGISTRAR · APRENDER       │
                    │  EXPECTED → PENDING → REALIZED       │
                    └──────────────────────────────────────┘
```

Los **5 ciclos** (`cores/cycles/registry.py`) son dominios que alimentan el mismo
loop. No son productos:

| Ciclo | Prioridad | Categoría | Alimenta el loop desde |
|---|---:|---|---|
| security | 10 | `offensive` | el etapa VERIFY (targets autorizados) |
| forge | 8 | `development` | el etapa EVALUATE (dev bounties, OSS) |
| pulse | 6 | `ai_work` | el etapa EVALUATE (AI-eval, microtasks) |
| vault | 7 | `finance` | el etapa REGISTER/APRENDER (capital) |
| atlas | 5 | `intelligence` | el etapa DISCOVER (OSINT, CVE, research) |

---

## 2. Tabla de conceptos canónicos (§57)

Cada fila es un solapamiento **verificado**. `MERGE` significa: una fachada de
compatibilidad apunta al canónico; nunca dos canónicos en paralelo.

| Concepto | Implementaciones actuales (verificadas) | Reemplazo canónico | Acción |
|---|---|---|---|
| **Validation** | 4 clases compitiendo en `cores/validation/` (23 ficheros, 6.460 L): `ValidationBridge:58` (316 L), `ValidationEngine:50` (460 L), `ValidationLoopEngine:23` (282 L), `ValidationPlanner:planner.py:420` (493 L). **Medido 2026-10-04**: la API usa `ValidationLoopEngine` (6) y `ValidationBridge` (2); `ValidationEngine` y `ValidationPlanner` sólo los consumen sus tests | `ValidationService` (Planner→Executor→Analyzer→Confidence→Verdict) | **BLOQUEADO** — ver §3.2 |
| **Autonomy / ejecución autónoma** | 6 módulos, 39 ficheros: `autonomous`(2) `autonomy`(12) `autopilot`(13) `execution_queue`(4) `daily_cycle`(3) `loop`(5) | Política de ejecución (`MANUAL`/`ASSISTED`/`AUTO_REVERSIBLE`/`HUMAN_APPROVAL`) sobre `execution_queue` | **MERGE** — autonomía es **política**, no dominio |
| **"Atacar" / probar un objetivo** | 5 caminos: `offensive/`(50f) `attack/`(2f) `exploit/`(2f) `hunt/`(2f) `validation/`(23f) | **Un ataque es una acción dentro de VALIDATION**, no una entidad de negocio | **MERGE** — `attack`/`exploit`/`hunt` son fases, no dominios |
| **Evidence** | 3 módulos + 1 dentro de validation: `evidence/`(4f) `evidence_graph/`(3f) `artifacts/`(12f) `validation/evidence_builder.py` | `EvidenceBundle` (`Evidence = hechos`, `Finding = interpretación`) | **MERGE** |
| **Revenue** | 3 módulos: `revenue/` `revenue_tracker/`(5f, 2.416 L) `revenue_multiplier/`(11f) | `RevenueLedger` — `REALIZED` sólo con evidencia de pago | **MERGE** |
| **Discovery** | 2 módulos: `discovery/` (**5 L, 0 importadores**) y `discovery_engine/`(2f, 268 L) | `discovery_engine` | **REMOVE** el de 5 líneas (tumba) |
| **Financial** | `financial/` y `financial_hub/` | uno | **MERGE** |
| **Voice** | `voice/`(5f) y `voice_department/`(10f) | uno | **MERGE** |
| **Workflow** | `workflow/`(5f) y `workflows/`(3f) | uno | **MERGE** |
| **Self-healing** | 4 módulos para un concepto: `self_heal/`(4f) `self_healer/`(8f) `self_healing/`(3f) `self_repair/`(1f) + `self_update/`(2f) | `SelfHealService` | **MERGE** — 4 filas |
| **Clustering** | `clustering/` = 17 L, `Clusterer` importado **sólo por su propio `__init__`** | — | **REMOVE** (0 consumidores) |
| **Cycle categories** | Enum `CycleCategory` (`security/forge/pulse/vault/atlas` = *slugs*) vs lo que la DB guarda (`offensive/development/ai_work/finance/intelligence` = *dominios*). 2 referencias totales, ambas en `cycles/__init__.py:25,41` — **cero usos reales** | los dominios | **REMOVE** el enum (vestigial, confunde al 6º ciclo) |
| **Cycle seed** | `DEFAULT_CYCLES` (`cycles/models.py:53`) duplica `registry.py`, con el comentario *"needs to match registry.py"*. **Verificado: divergen 0/5** (prioridades y categorías idénticas) | `registry.py` genera el seed | **DE-DUPLICAR** (riesgo de mantenimiento, no bug vivo) |
| **Human Gate — 2 canónicos** | `cores/approval/gate.py:565 L` y `cores/approval/gates.py:204 L` **definen ambos `ApprovalGate` y `get_approval_gate()` con semántica distinta**. `gate.py`: `AutonomyPolicy` LITE/FULL/CAPITAL + `RiskLevel` LOW→CRITICAL + `ActionType` de 10 acciones. `gates.py`: `ApprovalLevel` AUTO→FULL_REVIEW + `ActionType` de 8 acciones. Los dos `ActionType` comparten **1** valor (`submit_report`) | `ApprovalGate` único. **Consumidor real = `gates.py`** (`api/routers/approvals.py` ×3) | **MERGE** — `gate.py` es huérfano productivo (ver abajo) |
| **Modos primary** | `AutonomyPolicy` (gate.py) define LITE/FULL/CAPITAL, pero `api/routers/settings_runtime.py:56` **re-valida la lista a mano**: `valid_modes = ["lite","full","capital"]`. El enum no es la fuente | validar contra `AutonomyPolicy` | **ISOLATE** — una sola lista |
| **Design tokens** | `design-system/MASTER.md` decía ser el SSOT con **8 tokens que no existen** en el CSS y `--color-destructive: #00d5ff` contra el `#3b82f6` real | `frontend/src/design/tokens.css` | **RESUELTO** 2026-10-04 |

---

## 3. Residuo verificado (candidato a borrado — **no** borrado)

| Fichero | Tamaño | Evidencia |
|---|---:|---|
| `cores/discovery/__init__.py` | 5 L | sólo docstring, **0 importadores** |
| `cores/clustering/` | 17 L | `Clusterer` sólo se importa desde su propio `__init__` |
| `frontend/src/styles/accessibility.css` | 4 hex fuera del SSOT | **no está muerto**: `.skip-nav` se usa en 1 `.vue` y sólo ese fichero lo define → está **no importado** (`KNOWN_DEBT #47`) |

**Por qué no se borran aquí:** "Delete Don't Comment" aplica, pero borrar exige
análisis de dependencias y el árbol tiene otro flujo escribiendo. Se registran;
se borran en la fase de deprecación.

---

### 3.1 Huérfano verificado: `cores/approval/gate.py`

| | |
|---|---|
| Tamaño | 565 L |
| Consumidores de producción | **0** — `grep` de `approval.gate` fuera del propio fichero: nada |
| Único consumidor | `tests/test_approval_gate.py:7` |
| Lo que sí usa la API | `cores/approval/gates.py` (204 L), vía `api/routers/approvals.py` ×3 |
| Lo que dice `.ai/` | `FINAL_RELEASE_AUDIT_2026.md:46,276` señala **`gates.py`** como canónico — coincide con el código |

**Lo grave no es el tamaño: es que ambos se llaman `ApprovalGate` y ambos
exponen `get_approval_gate()`.** Un import equivocado resuelve en silencio a la
política equivocada. `gate.py` tiene los 3 modos del producto (LITE/FULL/CAPITAL)
y una taxonomía de riesgo de 4 niveles que `gates.py` no tiene — no es un
duplicado, es **media política perdida**.

**Por qué NO se borra:** `test_approval_gate.py` lo cubre y pasa. Borrarlo rompe
un test verde. **Por qué NO se arregla acá:** decidir cuál de las dos politicas
gana es una decisión de producto (¿el gate canónico tiene niveles de riesgo? ¿tiene
los modos?), no una limpieza. Se registra como `KNOWN_DEBT #49`.

### 3.2 MERGE de Validation: bloqueado por migración en curso (2026-10-04)

El merge de las 4 clases se **midió** pero **no se ejecutó**, por una razón
concreta y verificada:

`cores/validation/` tiene **5 ficheros modificados sin commitear** en este
momento (231 líneas añadidas) — `confidence.py`, `models.py`, `promoter.py`,
`economic_scorer.py`, `evidence_builder.py`. Es una migración de
`ConfidenceScorer.calculate()` para el piloto LAYA:

```
calculate(results, validation, endpoint_signals, llm_boost=0.0,
          uncertainty_penalty=0.0, laya_signal=None) -> ConfidenceScore
```

Su consecuencia medible: **11 tests rojos** en `test_validation_engine.py` y
`test_validation_bridge.py` (`TypeError: missing 2 required positional
arguments`), que los tests de la API **no cubren** — `make test-fast` sigue en
**103/1**.

**Por qué NO se ejecuta el merge ahora:**

| Razón | Consecuencia si se ignora |
|---|---|
| `cores/validation/` está en migración activa | el merge colisiona con trabajo sin commitear |
| Los 11 rojos son de esa migración, no del solapamiento | no puedo distinguir "mi fallo" de "su fallo" ⇒ cualquier diagnóstico es suposición |
| El otro flujo todavía no actualizó sus tests | un rojo más sería imposible de atribuir |

**Qué hay que hacer antes de intentarlo** (en este orden):

1. El otro flujo commitea su migración LAYA y pone sus 11 tests en verde.
2. `make test` (no `test-fast`) para tener el conteo real de la suite completa.
3. Sólo entonces: medir el blast radius de cada clase con
   `graft callers <symbol> --depth 2` y decidir el orden del merge.

**Regla permanente:** *un merge es correcto cuando los tests del módulo están
verdes y el módulo no tiene trabajo sin commitear. Mientras haya reds de otro
cambio en el mismo módulo, tocarlo es trabajar a ciegas.*

## 4. Lo que **no** es un producto

§6 del megaprompt, aplicado. Ninguno de estos existe como producto separado y
ninguno debe ganar su propio loop:

```
Security · AI · Web3 · Open Source · Cloud/DevOps · Research · Grants · Trading
```

Todos son **dominios** (el nivel de `category` en `cycles/registry.py`) o
**source types** (una `SourceDefinition` más su adapter). Los que quedaron
fuera por decisión explícita del owner:

| Carril | Estado | Razón |
|---|---|---|
| Fiverr / freelance genérico | **HARD-EXCLUDED** (`_HARD_EXCLUDED`, sin override por HTTP) | owner: "no quiero trabajar en fiverr ni en freelance" (2026-10-01) |
| Workana | `EXCLUDED` | no hay bolsa pública |
| Mercor, Mindrift | **RETIRADOS** | interview + Stripe no cubre AR / requisitos de doctorado |
| Turing | no implementado | anti-bot; un adapter que devuelve 0 es peor que ninguno |

---

## 5. Reglas que este mapa protege

1. **Un concepto = un módulo canónico.** Duplicado = deuda, no capacidad.
2. **Técnico ≠ económico.** `technical_priority` y `economic_priority` no se colapsan.
3. **`EXPECTED ≠ REALIZED`.** `PAID` es la única caja.
4. **`UNKNOWN ≠ 0`.** Sin dato, la métrica es `UNKNOWN` — no un número.
5. **AI interpreta; la realidad confirma.** La IA no confirma un hallazgo por sí sola.
6. **Una acción consequential es humana.** El sistema la prepara y se detiene.
7. **Una fuente es dato, no un motor.** 178 fuentes, 0 módulos por fuente.
8. **Autonomía es política, no dominio.**

---

## 6. UNKNOWN REGISTER (§65)

No verificado — **no** se afirma en ningún sitio de este documento:

| # | UNKNOWN | Por qué |
|---|---|---|
| 1 | Cuántos de los 194 módulos de `cores/` tienen consumidor real | Requiere análisis de dependencia por módulo; `graft callers --depth all` por cada uno |
| 8 | Por qué `ValidationEngine` y `ValidationPlanner` no tienen consumidor de producción | ¿legado, o API que falta? Afecta si el merge es `REMOVE` o `DEPRECATE`. Medido: sólo sus tests los importan |
| 2 | Route count real | ~1.850 según `DECISIONS` 2026-09-30, sin re-medir |
| 3 | Conteo de la suite completa | Sólo medido `make test-fast` = 103/1. El histórico registra 85 rojos post-cierre |
| 4 | Cuántos de los 44 `--x` sin definir son intencionales | `KNOWN_DEBT #48` — triage var por var |
| 5 | Estado real de licencia MIT vs Proprietary | Decisión legal, no técnica |
| 6 | `agent-tree` (§33 del megaprompt) | Sin referencia verificable. **No inventar** |
| 7 | Si el enum `CycleCategory` quedó muerto o se serializa en la DB | 0 usos en código, pero la columna podría existir |