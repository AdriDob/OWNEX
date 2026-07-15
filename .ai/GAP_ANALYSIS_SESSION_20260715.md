# GAP ANALYSIS — 15 Julio 2026

> Principal Engineer Audit de toda la sesión: Offensive Intelligence v3, Research, Architecture.
> Revenue Rule aplicada a cada recomendación. Evidencia de fuentes reales.

---

## 1. OFFENSIVE INTELLIGENCE v3 — Solo IDOR Reasoner implementado

### Estado actual
- Pipeline tiene 8 steps (relationships → reasoners → contradictions → triager → planner → curiosity → ownership → prioritize)
- Pero `_discover_reasoners()` solo carga `IDORReasoner`
- El Planner, Curiosity, Contradictions y Triager existen para 5 tipos (IDOR, SSRF, Auth Bypass, XSS, SQLi) pero los **reasoners** solo para IDOR

### Comparativa
| Producto | Stars | Capacidad |
|---|---|---|
| Nuclei (ProjectDiscovery) | 29.3k | 12,000+ templates, Go, ejecuta real |
| sqlmap | ~10k | 5 técnicas, 40+ DBs, explotación real |
| Burp Suite | Estándar industria | Proxy + Scanner + Extensions |
| **ORION Offensive** | — | Análisis puro, 1 reasoner, sin HTTP |

### GAP: Reasoners faltantes
| Reasoner | Impacto | Código ya existe para planner/curiosity/contradictions | Prioridad |
|---|---|---|---|
| SSRFReasoner | Alto — SSRF es top-5 bug bounty | Sí (planner 9 steps, curiosity 4, contradictions listos) | ✅ Hoy |
| AuthBypassReasoner | Alto — OAuth/JWT/Session | Sí (planner 8 steps, curiosity 4) | ✅ Hoy |
| XSSReasoner | Alto — reflejado/stored/DOM | Sí (planner 6 steps, curiosity 2) | ✅ Hoy |
| SQLiReasoner | Alto — clásico | Sí (planner 6 steps, curiosity 2) | ✅ Hoy |
| GraphQLReasoner | Medio — creciendo rápido | No (no hay templates) | Post-v3 |
| OAuthReasoner | Medio | No | Post-v3 |

### Revenue Impact de construir reasoners faltantes
- 4 reasoners nuevos = 4x más tipos de vulnerabilidad detectados
- Sin costo de diseño (planner/curiosity/contradictions ya existen)
- ROI: **Alto inmediato** — 4 reasoners ≈ 4-8 horas de implementación

---

## 2. CRÍTICO: ORION nunca hace peticiones HTTP reales

### Estado actual
- `OffensiveEngine.analyze_endpoint()` recibe dicts de endpoints
- Jamás envía un request HTTP
- No puede verificar si un endpoint existe, responde, o es vulnerable

### Gap vs industria
- Nuclei envía requests reales y matchea respuestas
- sqlmap envía payloads y analiza respuestas
- ZAP escanea activamente con spiders
- Burp Intercepta tráfico real

### Recomendación
- NO construir un HTTP engine propio (re-inventar la rueda)
- Construir un **NucleiAdapter** que convierta hypotheses → templates Nuclei
- El adapter ejecuta `nuclei -t generated_template.yaml -u target`
- ORION proporciona la inteligencia (qué testear, por qué), Nuclei ejecuta
- Similar: sqlmapAdapter para SQLi, BurpAdapter para import/export

### ROI
- Impacto: **Transformacional** — ORION pasa de analítico a operacional
- Complejidad: Media (wrapper sobre CLI binarios)
- Tiempo: 1-2 días para NucleiAdapter
- Dependencia: nuclei binary (Go, single binary)

---

## 3. API DESIGN FLAW — POST /analyze usa query params

### Estado actual
```python
@router.post("/analyze")
def analyze_endpoint(
    path: str = Query(...),
    method: str = Query("GET"),
    params: str = Query("{}"),
    ...
```

### Problema
- POST con query params viola convención REST
- `params` es un JSON string en query param (debe escaparse, máximo URL length)
- El endpoint `/analyze/batch` SÍ usa body correctamente (list[dict])

### Fix requerido
- Mover a Pydantic request body model
- Mantener compatibilidad con `/analyze/batch` (ya usa body)
- Revenue impact: Bajo individualmente, pero es calidad profesional

---

## 4. FEEDBACK LOOP FALTANTE — Offensive no aprende

### Estado actual
- `FeedbackTuner` existe en `core/validation/` y está conectado en `api/main.py`
- Pero **no está conectado al pipeline ofensivo**
- Cuando una hypothesis se confirma o rechaza, el reasoner no ajusta sus pesos

### Qué falta
- `IDORReasoner._keyword_score()` usa pesos fijos
- `OBJECT_REFERENCE_KEYWORDS` dict con scores hardcodeados
- Sin feedback loop, el reasoner no puede mejorar con experiencia real

### Fix
- Conectar `FeedbackTuner.accumulate()` y `FeedbackTuner.apply_adjustments()` al pipeline ofensivo
- Los reasoners deben exponer sus pesos para que FeedbackTuner los ajuste
- Revenue Impact: **Alto** — cada confirmación/rechazo mejora la precisión futura

---

## 5. ASYNC BATCH PROCESSING — analyze_batch es secuencial

### Estado actual
```python
def analyze_batch(self, endpoints: list[dict]) -> list[ReasonerResult]:
    self.set_context(endpoints)
    results = [self.analyze_endpoint(ep) for ep in endpoints]  # secuencial!
```

### Problema
- Para 100 endpoints, 100 llamadas secuenciales
- Cada analyze_endpoint ejecuta 8 steps (relationships, reasoners, contradictions, etc.)
- Sin paralelismo, sin timeout, sin progreso

### Fix
- Usar `concurrent.futures.ThreadPoolExecutor` o `asyncio.gather`
- Timeout por endpoint (30s default)
- Reportar progreso parcial
- Revenue Impact: Medio — mejora UX pero no revenue directamente

---

## 6. CAPABILITY REGISTRY INCOMPLETO

### Estado actual
- Solo registra `analyze_endpoint` y `generate_hypothesis`

### Capacidades faltantes
- `generate_investigation_plan`
- `curiosity_explore`
- `build_ownership_graph`
- `triager_simulate`
- `batch_analyze`
- `analyze_collection`

### Impacto
- Bajo hoy (capacidades se usan directamente vía API), pero impide descubrimiento automático

---

## 7. FINANCE ARCHITECTURE — Postponer vs Offensive

### Análisis Revenue Rule
5 preguntas:
1. **¿Aumenta detección?** No — finanzas no detectan vulnerabilidades
2. **¿Aumenta aceptación?** No
3. **¿Aumenta automatización?** Sí — automatizar gestión de ingresos
4. **¿Aumenta velocidad?** Sí — consolidar patrimonio
5. **¿Aumenta ROI?** Sí — optimizar capital para bug bounty (equipo, tools, VPS, APIs)

### Decisión
- Finance architecture es **válida** pero **SECUNDARIA**
- La prioridad #1 es Offensive Intelligence (genera revenue)
- Finance es prioridad #2 (gestiona/optimiza el revenue generado)
- Revenue Ready (Task Queue item 1-5) debe completarse antes de Finance

### Timing
- Offensive v3 + reasoners faltantes: próxima semana
- HTTP testing (NucleiAdapter): próxima semana
- Frontend de Offensive: próxima semana
- Finance architecture: post Offensive v3 completo

---

## 8. SIN FRONTEND PARA OFFENSIVE

### Estado actual
- Frontend Vue 3 existe para otros módulos
- No hay vistas para: attack surface graph, hypothesis review, investigation plans, curiosity questions, ownership graph

### Recomendación
- NO construir frontend ahora
- Priorizar reasoners y HTTP testing primero
- Frontend después de que el backend genere resultados reales

---

## 9. COMPARATIVA OPEN SOURCE — Dónde debe integrar ORION

| Categoría | Mejor OSS | ORION debe |
|---|---|---|
| Vulnerability scanning | **Nuclei** (29k★) | Generar templates, no reemplazar |
| SQL injection | **sqlmap** (10k★) | Generar comandos sqlmap |
| Web proxy | **Caido** / Burp Suite | Importar tráfico desde Caido |
| Subdomain recon | **Subfinder** (10k★) | Consumir output |
| HTTP probing | **httpx** (7k★) | Consumir output |
| Fuzzing | **FFUF** (12k★) | Generar wordlists + comandos |
| Crypto trading | **Freqtrade** (30k★) | Conectar como adapter |
| Backtesting | **VectorBT** (5k★) | Consumir resultados |
| Quant engine | **NautilusTrader** (3k★) | Integrar como adapter |
| AI Finance | **FinGPT** (20k★) | ORION COPILOT + FinGPT |
| Workflow | **n8n** (50k★) | ORION Runtime ya existe |

### Principio
ORION no compite con estas herramientas.
ORION las **orquesta** — proporciona la inteligencia, ellas ejecutan.

---

## PRIORIDADES CORREGIDAS (Post-Audit)

| # | Tarea | Impacto | Esfuerzo | Revenue |
|---|---|---|---|---|
| 1 | SSRFReasoner + AuthBypassReasoner + XSSReasoner + SQLiReasoner | 🟢 Alto | 4-6h | 🟢 Directo |
| 2 | Fix API POST /analyze body | 🟡 Medio | 30min | 🟢 Profesional |
| 3 | Conectar FeedbackTuner → Offensive | 🟢 Alto | 2h | 🟢 Directo |
| 4 | Async batch processing | 🟡 Medio | 1h | 🟡 Indirecto |
| 5 | NucleiAdapter (hypotheses → templates) | 🟢 Alto | 1-2d | 🟢 Directo |
| 6 | Frontend Offensive views | 🟡 Medio | 2-3d | 🟡 Indirecto |
| 7 | Finance architecture | 🟡 Medio | 3-5d | 🟡 Indirecto |

**Decisión**: Procedo con items 1-4 hoy. Items 5-7 son próximos sprints.
