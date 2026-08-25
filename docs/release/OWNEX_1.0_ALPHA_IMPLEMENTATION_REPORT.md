# OWNEX 1.0 Alpha Desktop — Implementation Report

> **Fecha**: 2026-08-25 · **Rango**: remediación + Prompt 2 (`9f4d3f45..8d42c0d7`, 17 commits propios)
> **Entrada**: `docs/release/OWNEX_1.0_ALPHA_AUDIT.md` · **Estado**: implementación de correcciones COMPLETA salvo items marcados PENDING. **NO se declara release final** — falta validación física en Windows (PROMPT 3).

---

## 1. Cambios implementados (con razón y evidencia)

### P0 — bloqueantes funcionales
| Fix | Razón | Commit | Test |
|---|---|---|---|
| CORS Tauri: `configure_cors()` SSOT + orígenes `tauri.localhost` http/https/scheme + `OWNEX_DESKTOP=1` forzado en sidecar + bypass OPTIONS en AuthMiddleware | El bundle abría con health READY pero TODA llamada autenticada era bloqueada (ACAO:* + credentials); preflights morían 401 antes que CORS | `9f4d3f45` | `tests/test_cors_tauri.py` ×9 |
| `execute_cycle` honesto: ranking con `action_required=human_review` | `_process_opportunity` perdido en churn del árbol core/: AttributeError con candidatos reales, `[]` silencioso sin red | `54737192` | `tests/test_opportunity_cycle.py` ×4 |
| Economía SSOT `economics.py`: TaskAvailability Known/**Unknown** (unknown nunca ×1.0, warning explícito), priors cold-start etiquetados, ambos motores delegan (spy exactly-once) | Dos fórmulas EV paralelas + tabla inventada presentada como "historical data"; p(disponibilidad)=1.0 implícito sesgaba toda decisión | `b21c3b62` | `tests/test_economics_ssot.py` ×6 |

### P1 — launcher y producto
| Fix | Commit | Test |
|---|---|---|
| Sidecar muere en RunEvent::Exit (sin huérfanos tras cerrar/update); health budget real 45×2s=90s (antes ~287s "60s"); puerto agotado aborta terminal | `f6f12a85` | cargo dev+release clean |
| Guards de bundle: ONEFILE (COLLECT banned), frontendDist existe, externalBin↔triple, CSP puertos dinámicos HTTP+WS, version sync ×3 manifiestos, CI stub-guard ≥50MB | `f345aad5` | `tests/test_tauri_packaging.py` ×9 |
| Persistencia frozen: WorkBank/MarketKB honran `OWNEX_DATA_DIR` (%LOCALAPPDATA%\OWNEX) | `162ed759` | `tests/test_data_dir_resolution.py` ×4 |
| Barreras curadas: adapters usan catálogo global (join nombre-normalizado/url-domain), unknown→None documentado | `83ac9dc7` | `tests/test_adapter_barrier_flags.py` ×3 |

### Prompt 2 — UX honesta + identidad
| Fix | Commit | Test |
|---|---|---|
| **Fondo azul oscuro (directiva owner)** + rojo unificado: `--ownex-red` cian→#E82127 (tokens≡tema, muere flip post-carga), JarvisBackground a rgba(30,64,255,*) desacoplado de vars jarvis | `bfcf799d` | `tests/test_frontend_theme_consistency.py` ×4 |
| Contrato dual retry en ErrorState (prop + evento) — Reintentar renderiza en GamingConsole/Capital | `242c6466` | vue-tsc |
| Dashboards honestos: 6 feeders ownexData propagan ApiError → ErrorState alcanzable; **fleet falso de agentes eliminado** (mock prohibido) | `aab28579`+`3c5c07b1` | vue-tsc |
| Publisher OWNEX en MSI metadata + NSIS Add/Remove (muere leak CATEYE visible) | `0e2f2d0a` | JSON válido |
| Providers: P1 verificado ya resuelto (Settings consume GET /providers backend-driven) + drift guard FALLBACK==PROVIDER_CATALOG | `256e8ec0` | `tests/test_provider_catalog_sync.py` |

### Higiene
- Limpieza física **9.6GB** artefactos obsoletos — incluidos los MSI pre-fix marcados NO-DEPLOY (riesgo de deploy equivocado eliminado).
- Docs: audit forense (`docs/release/OWNEX_1.0_ALPHA_AUDIT.md`), directiva de diseño permanente + bitácoras `.ai/`.

## 2. Verificaciones ejecutadas (resultados)

```
pytest (nuevos contratos)      → 35+4+13+1 passed
scripts/dev test-fast          → 100 passed / 1 skipped (baseline exacta, estable entre sesiones)
vue-tsc --noEmit               → EXIT 0
cargo check (dev + release)    → sin warnings
ruff                           → limpio en todos los archivos tocados
git                            → 17 commits pusheados a origin/main; árbol sin WIP propio
```

## 3. Cumplimiento por sección del plan

§1 Tauri ✅ (lifecycle + guards; detección `window.__TAURI__` solo en OmegaChatNative = huérfano en dead-code batch) · §2 Discovery ✅ (triple vía ya robusta, verificada en audit) · §3 Lifecycle ✅ (start/ready/crash-error/close-kill) · §4 API client ✅ (getApiBase request-time único, verificado audit) · §5 WebSocket ✅ (dinámico vía getWsBase/wsUrl con tests existentes; cero hardcodes fuera del centralizador) · §6 Frontend ✅ para las 6 páginas principales auditadas (matriz en AUDIT §B; resto de páginas: mejora incremental pendiente) · §7 Fondo ✅ causa raíz (no síntoma): rojo solo estados, background azul oscuro · §8 Providers ✅ catálogo backend-driven + drift guard (schema de configuración por provider: PENDING) · §9 Ollama ⚠️ PARCIAL — mensaje inline "no disponible" existe en chat; **detección de modelos instalados: PENDING** · §10 API keys ⏳ PENDING auditoría de estados configured/not-configured por integración · §11 Taxonomía ✅ SSOT 38 categorías + 4 mapeos testeados (prioridades HIGH/MED/LOW: en curso por proceso concurrente sobre economics/models — NO tocado por coordinación) · §12 Scoring ✅ base honesta (acceptance histórica real, Unknown availability, cash-speed) — effective-hourly con historial: se llena al registrar payouts reales · §13 Docs ✅ · §14 Tests ✅ · §15 Calidad ✅ mock crítico eliminado; restantes documentados como PENDING (no VERIFIED).

## 4. Problemas restantes / riesgos
1. **Validación Windows física** — único gate de release. 5 escenarios definidos (AUDIT §10-12). Requiere humano en PC x64.
2. Curación Outlier/Mindrift + modelo zero-experience: **en vuelo por proceso concurrente** (WIP 18 archivos: taxonomy/global_sources/economics/models/scoring/result_based) — coordinar commit antes del tag.
3. Dead-code batch (27 archivos frontend + plugin-http + icons legacy): gateado por diseño a post-validación Windows.
4. Ollama model-detection y API-key status matrix: PENDING (Prompt 3 o siguiente sesión).
5. Riesgo residual: temas no-default siguen variando el matiz del rojo (#DC2626 etc.) — aceptado como variantes temáticas legítimas.

## 5. Qué debe probar PROMPT 3 (checklist humana, Windows x64)
1. **Instalación limpia**: MSI de CI → abrir → splash → backend healthy ≤90s → dashboard muestra datos REALES (no ceros silenciosos ni fleet falso).
2. **Segundo arranque**: cerrar (verificar en Task Manager que `ownex-backend*.exe` muere) → reabrir → datos intactos en `%LOCALAPPDATA%\OWNEX`.
3. **Puerto ocupado**: ocupar :8000 con otro servicio → OWNEX debe elegir 8001+ y el frontend descubrirlo solo.
4. **Backend caído intencional**: matar el proceso backend → dashboards deben mostrar ErrorState "Conectando/Error" CON botón Reintentar funcional (no ceros, no fleet falso, no pantalla roja genérica).
5. **Upgrade**: instalar nueva versión encima → datos previos intactos → sin sidecar viejo adoptado.
6. Visual: fondo ambiental azul oscuro en todas las páginas; rojo solo en errores/severidad; publisher "OWNEX" en Agregar/Quitar programas.

## 6. Comandos de reproducción
```bash
pytest tests/test_cors_tauri.py tests/test_opportunity_cycle.py tests/test_economics_ssot.py \
       tests/test_tauri_packaging.py tests/test_data_dir_resolution.py \
       tests/test_adapter_barrier_flags.py tests/test_frontend_theme_consistency.py \
       tests/test_provider_catalog_sync.py -q        # 36 contracts
python scripts/dev test-fast                        # 100 passed / 1 skipped
cd frontend && npx vue-tsc --noEmit && npm run build
cd src-tauri && cargo check && cargo check --release
rg -n "227, 25, 55" frontend/src/components/JarvisBackground.vue   # vacío
rg -n "COMPANYNAME|publisher" installer/*.nsi src-tauri/tauri.conf.json
```
