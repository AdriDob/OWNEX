# OWNEX 1.0 Alpha Desktop — Release Audit & Plan

> **Fecha**: 2026-08-25 · **Estado del repo**: `main @ 76149e14` + WIP concurrente (no auditado: `control.py`, `GuidedDashboard.vue`, `remote_control.rs`, `income_plan.py`)
> **Alcance**: Auditoría delta sobre la remediación 2026-08-25 (`9f4d3f45..ca1faef2`, 3 P0 + 4 P1 cerrados test-first) + forensics nuevo de UI/branding/artefactos.
> **Veredicto**: NO release-ready todavía. Este documento es diagnóstico + plan; no declara funcionalidad.

---

## 1. Arquitectura actual (verificada, vigente)

Canónica Gen3 confirmada y sin cambios desde el audit anterior:

```
Windows installer (MSI+NSIS, Tauri bundler)
  └─ OWNEX Alpha.exe (Tauri v2 WebView, productName "OWNEX Alpha", v7.0.0)
       ├─ frontend/dist (Vue 3 + TS + Vite; build fresco en CI ×2)
       ├─ sidecar ownex-backend-x86_64-pc-windows-msvc.exe (PyInstaller ONEFILE)
       │    └─ start_backend.py → uvicorn api.main:app (--port dinámico 8000-8099,
       │         OWNEX_DESKTOP=1, %LOCALAPPDATA%\OWNEX\{database,logs})
       └─ descubrimiento triple: event backend-ready → poll is_backend_ready/
          get_backend_port (gateado por BACKEND_READY) → HTTP scan fallback
```

Contratos ya cerrados con tests permanentes:
| Contrato | Test | Commit |
|---|---|---|
| CORS Tauri origins + credentials + preflight bypass | `tests/test_cors_tauri.py` (9) | `9f4d3f45` |
| Ciclo opportunity sin método fantasma, ranking honesto | `tests/test_opportunity_cycle.py` (4) | `54737192` |
| EV único (`economics.py`, Unknown ≠ 1.0, priors etiquetados) | `tests/test_economics_ssot.py` (6) | `b21c3b62` |
| Sidecar kill en Exit + health 90s real + abort puerto agotado | cargo dev+release clean | `f6f12a85` |
| Bundle guards (ONEFILE, externalBin, CSP puertos, version sync) | `tests/test_tauri_packaging.py` (9) | `f345aad5` |
| Persistencia frozen (`OWNEX_DATA_DIR`) | `tests/test_data_dir_resolution.py` (4) | `162ed759` |
| Barreras curadas en adapters | `tests/test_adapter_barrier_flags.py` (3) | `83ac9dc7` |

Suite fast: **100 passed / 1 skipped** (baseline exacta). Total recolectable: 3693.

## 2. Arquitectura objetivo

Idéntica a la canónica — **no hay re-arquitectura pendiente**. El gap es de cierre de contratos de UX (errores visibles), limpieza de capas visuales legacy, y validación física en Windows.

## 3. Inventario clasificado

### CURRENT / RELEASE CRITICAL
- `src-tauri/` completo, `OWNEX-Backend.spec`, `start_backend.py`, `api/main.py`+routers, `cores/direct_work_engine/` (+economics.py), `frontend/src` ruteado, workflows `ci/test/ownex-tauri-windows`.
- Taxonomía SSOT: 38 categorías canónicas + 4 mapeos exhaustivos testeados (19 tests).

### LEGACY (conservar hasta validación Windows)
- Gen2 PySide6 (`desktop/native/`, `ownex-alpha-windows.yml` dispatch-only, `installer/OWNEX-Desktop-Alpha.nsi`).
- Gen1 pywebview (`release.yml` dispatch-only).

### DEAD (batch post-validación — FASE 6 del plan)
- Frontend: **26 componentes huérfanos** + `pages/Dashboard.vue` + broken import `Progress` + `tauri-plugin-http` (registrado, nunca usado) + `OmegaChatNative` (huérfano con invoke fantasma incluido).
- Assets: `installer/icons/cateye.ico`, `orion.ico` (0 referencias en NSIS actual).

### ARTEFACTOS OBSOLETOS (~9 GB locales, gitignored, NO trackeados)
| Ruta | Tamaño | Estado |
|---|---|---|
| `dist/` + `build/` + binario linux sidecar | ~2.7 G | pre-fix ONEFILE → DELETE_CANDIDATE |
| `ownex-installer/` (Gen2 setups ×5 + zip) | ~6.5 G | superado → ARCHIVE OneDrive o delete |
| `ownex-tauri-artifacts/msi|nsis/*.exe|msi` (19:10/17:59) | 53 M | **PRE-FIX rotos — NO DESPLEGAR jamás** |
| `src-tauri/target/release/bundle/` Linux OMEGA | 410 M | regenerable |

## 4–5. Problemas · P0

**Ningún P0 de bloqueo funcional abierto.** Los 3 P0 del audit previo están cerrados con evidencia (§1). El hallazgo "fondo rojo" se reclasifica tras forensics:

### 🔴 Rojo en pestañas — causa raíz (FASE 4, resuelta como diagnóstico)
No existe ningún componente de error que pinte fondo rojo sólido. Son **3 capas combinadas**, ninguna es un crash:

1. **Tinte rojo global permanente** — `App.vue:150` monta `JarvisBackground.vue` en TODAS las páginas; su grilla/partículas/scanline usan `#e31937` de `styles/tesla-jarvis-theme.css:12` (importado en `main.ts:9`). En superficies oscuras grandes (zona tabs/sidebar) se percibe "fondo rojizo". *Condición: siempre.*
2. **Triple fuente de verdad del rojo + tema runtime** — `design/tokens.css:25` define `--ownex-red: #00d5ff` (**cian**, artefacto de-neón mal nombrado); `themes/tesla.json` lo pisa a `#E82127` al cargar (`useThemeEngine.ts:123-125`). Resultado: todos los indicadores de error (badges de `WorkspaceTabs.vue:273-276`, dots, textos críticos) se vuelven rojo-real, con **mismatch rojo-sobre-cian** donde el fondo quedó hardcodeado (`OwnexBadge.vue:147`, `KnowledgeFeed.vue:40`). *Condición: ThemeEngine cargó (App.vue:81).*
3. **Gradientes rojo pleno en páginas legadas** — `.btn-primary/.badge-primary/.progress-fill` = gradientes `#e31937→#ff4d6a` completos (`tesla-jarvis-theme.css:45,453,556,574`) consumidos por `/mobile`, `/setup/*`, wizards. *Condición: navegar ahí.*

**Fix correcto (Prompt 2)**: consolidar a UNA definición (`--ownex-red=#E82127` en tokens.css, tema deja de pisar), migrar consumidores de `tesla-jarvis-theme.css` a tokens TESLA y desmontar `JarvisBackground` (o portarlo a tokens), eliminar archivo legacy. No es un bug de estado — es deuda de capas de branding.

## P1 (producto visible)

| # | Problema | Evidencia |
|---|---|---|
| 1 | **Dashboards tragan errores**: `services/ownexData.ts` captura TODO y devuelve defaults → backend caído se ve como “datos en cero” sin mensaje (MissionControl/GamingConsole casi nunca alcanzan su ErrorState). Viola contrato documentado en `lib/backend.ts:195` | ownexData.ts:146,196-234 |
| 2 | **Contrato roto de retry**: `ui/ErrorState` usa prop-función pero GamingConsole (:150) y Capital (:307) le pasan `@retry` → botón Reintentar no renderiza | ErrorState.vue:23-30 |
| 3 | IntelligenceDashboard: `catch { /* ignore */ }` sin error state ni retry (:28) | página queda vacía silenciosa |
| 4 | Publisher **“CATEYE”** visible en Agregar/Quitar programas (NSIS Gen2 `COMPANYNAME`, línea 11); MSI Tauri sin `publisher` definido | leak usuario final |
| 5 | Settings.vue no consume catálogo real de providers para todos los campos (hosts Ollama hardcodeados parciales en settings.ts:196) aunque `GET /providers` backend-driven existe | FASE 6 audit previo |
| 6 | Outlier/Mindrift ausentes del catálogo curado → barreras reales (assessments) no modeladas | data-curation pendiente |
| 7 | Auth sin redirect real: fallo silencioso a WelcomePage; `meta.requiresAuth` decorativo | main.ts:60-63 |

## P2
Empty states ausentes en GamingConsole (3 listas) · `capacitor.config.json appName "CATEYE"` (mobile, no bloquea Windows) · `pyproject.toml` description “OMEGA” · accesibilidad.css muerto con destructive #ff4444 (tercera definición de rojo) · coverage sin config permanente · docs drift menor.

## 6. Riesgos
1. **Deploy de artefacto obsoleto** (MSI pre-fix local de 27.5 MB parece válido) → mitigación: borrar/archivar `ownex-tauri-artifacts/` antes de taggear; fuente de verdad = CI.
2. **Proceso concurrente activo** sobre control/investment/income_plan/remote_control → no tocar; coordinar commits.
3. **Validación Windows sigue siendo manual** (host único) → checklist §11 obligatoria.
4. WebView2 runtime: instalador Tauri lo gestiona (bootstrapper), verificar en PC limpia sin internet.

## 7. Decisiones arquitectónicas vigentes
D1 ranking-honesto · D2 EV-SSOT con Unknown explícito · D3 CORS ambas ramas + flag · D4 dead-code por eliminación post-validación · Gen3 canónica única en tags `v*` · `orion_desktop`/identifier históricos NO renombrar · datos en `%LOCALAPPDATA%\OWNEX`.

## 8. Plan exacto (Prompt 2)

| Orden | Task | Archivos | Verificación |
|---|---|---|---|
| 1 | Unificar rojo: tokens.css `--ownex-red:#E82127`; temas dejan de pisar (o alinean); matar `tesla-jarvis-theme.css` migrando sus 4 consumers; JarvisBackground off/portado | tokens.css, useThemeEngine, App.vue, main.ts, 4 páginas | grep cero hits #e31937; visual smoke |
| 2 | Errores visibles: ownexData deja de tragar (propaga ApiError; defaults solo en campos opcionales) | services/ownexData.ts | dashboard caído muestra banner + retry |
| 3 | Contrato ErrorState: emitir evento `retry` Y mantener prop; fix callers | ui/ErrorState.vue, 2 páginas | botón Reintentar funciona |
| 4 | IntelligenceDashboard error state + retry | 1 página | ídem |
| 5 | Branding: NSIS COMPANYNAME→OWNEX (si Gen2 se retira, skip); añadir `bundle.publisher` en tauri.conf | nsi/tauri.conf | Panel de control |
| 6 | Settings consume GET /providers completo | settings.ts/vue | selector = catálogo backend |
| 7 | Curar Outlier/Mindrift en global_sources (flags reales de assessments) | global_sources.py | test stale-keys verde |
| 8 | Limpieza artefactos locales (~9GB) + batch dead-code (27 archivos) | git rm | build + suite verde |
| 9 | Tag `v7.1.0-alpha` → CI MSI → **validación Windows 5 escenarios** → deploy `OneDrive\Adriel\OWNEX-DESKTOP-LAUNCHER-FINAL` + SHA256SUMS | workflow/manual | checklist §11 completa |

## 9. Pruebas necesarias (nuevas)
- Test de tema: tokens vs themes no contradicen (`--ownex-red` estable post-load).
- Test contrato ErrorState (evento retry emitido).
- Test ownexData: fetch fallido → throw (no default silencioso) para endpoints críticos.
- Smoke E2E bundle: instalar en VM limpia → health → dashboard con datos → restart persistencia (manual, checklist).

## 10–12. Criterios de release (Definition of Done 1.0 Alpha)
1. Instalación limpia Windows x64: abrir → splash → backend healthy ≤90s → dashboard con datos reales (no ceros silenciosos).
2. Los 5 escenarios del launcher: limpio / 2º arranque / puerto ocupado→8001 / cierre mata backend / upgrade preserva `%LOCALAPPDATA%\OWNEX`.
3. Sin fondo rojo inexplicable: una sola fuente del rojo; errores visibles con retry funcional.
4. Suite fast ≥100/1 + nuevos tests §9 verdes; vue-tsc 0 errores; cargo ambos perfiles sin warnings.
5. MSI firmado-no-requerido pero con SHA256SUMS publicado + copia en OneDrive destino exacto.
6. Cero WIP concurrente mezclado en el tag.

## Reproducibilidad de esta auditoría
```bash
git log --oneline -8                      # pin de commits
pytest tests/test_cors_tauri.py tests/test_opportunity_cycle.py \
       tests/test_economics_ssot.py tests/test_tauri_packaging.py \
       tests/test_data_dir_resolution.py tests/test_adapter_barrier_flags.py -q   # 35 passed
python scripts/dev test-fast              # 100 passed / 1 skipped
rg -n "e31937|E82127|--ownex-red" frontend/src frontend/public/assets/branding/themes  # capas rojo
rg -n "COMPANYNAME" installer/*.nsi
du -sh dist build ownex-installer ownex-tauri-artifacts src-tauri/target/release/bundle
```

## PROMPT 2 — resumen ejecutivo de siguiente sesión
> Ejecutar tabla §8 en orden: (1) unificación del rojo con eliminación de la capa jarvis-legacy, (2) propagación honesta de errores en ownexData + contrato retry de ErrorState + IntelligenceDashboard, (3) publisher/packaging, (4) providers reales en Settings, (5) curación Outlier/Mindrift, (6) limpieza ~9GB + dead-code batch, (7) tag v7.1.0-alpha → MSI CI → validación humana Windows (5 escenarios) → deploy OneDrive. Cada item con test-first cuando aplique; no tocar WIP concurrente; no declarar release-ready hasta checklist §10-12 completa.
