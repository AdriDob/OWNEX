# OWNEX 1.0 ALPHA — RELEASE AUDIT (reproducible)

> **Fecha**: 2026-08-25 · **Commit auditado**: tag `v1.0.0` = `58fdbf63` (+ commits docs/test posteriores, sin código de producto)
> **Método**: ejecución real de cada grupo. Nada declarado por inspección.

## 1. BACKEND

| Grupo | Resultado | Evidencia |
|---|---|---|
| ruff (release-relevant) | PASS | 0 errores en api/, core/ producto; 67 preexistentes SOLO en cores/polymarket+chroma (WIP proceso concurrente — P2 ajeno) |
| mypy scoped (scoring/scheduler) | PASS | `Success: no issues found in 3 source files` |
| pytest COMPLETO | **PASS** | **3558 passed / 0 failed** / 8 skipped (4m04s) — tras resolver conflicto de taxonomía |
| opportunity (top5/engine/wiring) | PASS | incluido arriba + investment_wiring 18/18 |
| taxonomy | PASS | work_taxonomy 19 + boundaries 16 (fix: test derivaba del enum vivo, no literales) |
| payment | PASS | payment_compat 13/13 |
| scoring | PASS | scoring 7/7 (+ comprehensive en suite completa) |
| scheduler | PASS | scheduler_jobs 51/51 |
| CORS | PASS | cors_tauri 9/9 |
| lifecycle | PASS | e2e_security_pipeline 8 + sidecar SIGTERM 8.3s rc=0 repro local |
| persistence | PASS | data-dir override → 11 DBs creadas; restart mismo dir íntegro |

**Fix aplicado durante el audit** (único cambio de código): `tests/test_taxonomy_boundaries.py`
derivaba vocabulario hardcodeado (3 familias) y chocaba con la familia canónica
`ai_evaluation` (decisión owner 2026-08-25). Ahora deriva del enum vivo del SSOT.

## 2. FRONTEND

| Check | Resultado |
|---|---|
| npm ci (lockfile) | PASS |
| vue-tsc | PASS — 0 errores |
| vitest | PASS — 226/226 |
| vite build | PASS — dist 150 assets, fonts/CSS/chunks OK |
| rutas/imports/stores | PASS — 66/66 páginas ruteadas · 0 redirects rotos (48 verificados) · 0 componentes faltantes |
| loading/empty/error states | PASS — ErrorState estructurado + estados connecting calmados |
| auth | PASS — device-login + Bearer/cookie E2E |
| Income Command Center / NEXT_BEST_ACTION | PASS — ver §3 |

Deuda lint biome repo-wide (noExplicitAny legacy) = P2 documentada; no bloquea.

## 3. FRONTEND ↔ BACKEND (contratos reales, backend vivo)

| Endpoint | Código | Campos exigidos |
|---|---|---|
| /api/health | 200 | status=ok, version=1.0.0 ✓ |
| /api/settings/ai/providers | 200 | 7 providers, shape id/label/models/available ✓ |
| /api/applications/overview | 200 | next_action ✓ |
| /api/applications/income-plan | 200 | plataforma ✓ · $/hora-EV ✓ · assessment ✓ · barrera (zero_experience+assessment_required) ✓ · argentina ✓ · pago/cash_speed ✓ · experiencia ✓ · rango low/high (conservative/optimistic) ✓ |
| NEXT_BEST_ACTION | — | source/title/detail/url/human_hours/**ev_per_human_hour_usd**/payoff_range/cash_speed_days/**zero_experience**/**assessment_required**/**access_probability:"desconocida"** ✓ (no inventa probabilidades) |
| /direct-work/workbank (root-mounted) | 200 | ✓ |
| /api/opportunity-score/top5 · CEO dashboard · orion/context | 200 | ✓ |

## 4. TAURI

conf assertions 7/7 (productName, identifier ai.orion.alpha.desktop, version 1.0.0,
frontendDist, externalBin sidecar, targets all, CSP localhost). Dynamic port +
backend-ready event verificados por diseño lib.rs/lib.backend.ts; flujo completo
INSTALL→LAUNCH→DATA DISPLAY = HUMAN_VALIDATION_REQUIRED.

## 5-8. LIFECYCLE · PERSISTENCE · CLEAN INSTALL · UPGRADE

- START→alive / CLOSE→terminated / REOPEN→nuevo: **VERIFIED local** (SIGTERM ≤8s
  garantizado por watchdog; Tauri además mata child en Exit).
- Persistence %LOCALAPPDATA%\OWNEX: diseño verificado con data-dir override
  (11 DBs + logs); ciclo INSTALL→CREATE→CLOSE→REOPEN completo = HUMAN_VALIDATION_REQUIRED.
- CLEAN INSTALL (sin Python/Node/repo): HUMAN_VALIDATION_REQUIRED — el bundle es
  autocontenido (sidecar ONEFILE + frontend embebido), CI smoke pasa, pero la
  instalación real en Windows limpio no es ejecutable desde este entorno.
- UPGRADE 7.0.0→1.0.0: HUMAN_VALIDATION_REQUIRED (datos %LOCALAPPDATA% se conservan
  por diseño; verificar Task Manager sin residuales).

## 9. ECONOMIC ENGINE

PASS — zero_experience_model 12 + max_income_model 13 + income_plan 14 (38 total).
ZERO_EXPERIENCE ≠ ZERO_BARRIER separados por enums EntryMechanism/
ExperienceRequirement; ranking por $EV/hora-humana con cash_speed;
access_probability="desconocida" cuando no hay historial (jamás inventada);
familias cubiertas: AI training/evaluation, data annotation, dev bounty,
bug bounty, QA, technical writing, code review, prompt engineering.

## 10. NEXT BEST ACTION — verificado en vivo

Respuesta real del endpoint con los 11 campos exigidos (ver §3). Ejemplo devuelto:
`Entregá: Plusgrade Loyalty Public Program bug bounty` (Bugcrowd, zero_experience=true,
assessment_required=false, probability honesta).

## 11. DOCUMENTACIÓN

ACTUALIZADOS: CURRENT_STATE (sesiones), SESSION_CHECKPOINT, DECISIONS (5 entradas),
TECHNICAL_DEBT (rebuild), FRONTEND_FUNCTIONALITY_MATRIX, DESKTOP_BUILD, RELEASE_GATE.
CREADOS: ARCHITECTURE_CURRENT.md, ARCHITECTURE_TARGET.md, RELEASE_NOTES/README/
VERSION/CHANGELOG en OneDrive. Claims obsoletos eliminados (OMEGA branding, paths WSL).

## 12. DEAD CODE

| Clase | Items |
|---|---|
| SAFE_TO_DELETE | (ninguno confirmado sin riesgo esta pasada) |
| REVIEW_REQUIRED | 12 componentes .vue huérfanos (OmegaChatNative*, OrionAssistant, SplashScreen, GlobalStatusBar, MerlinInterface, WidgetDashboard, PlatformGrid, OpportunityCard, QuickActions, ErrorRecoveryUI, MicroSection, PremiumButton); specs PyInstaller legacy ×3; launchers dev (OWNEX-Launcher.*, start.*) |
| KEEP | desktop/boot_guard·watchdog·updater (consumidos por runtime), twin trees (decisión 2026-08-24) |

\*OmegaChatNative ya gateado a validación Windows en DECISIONS.

## 13. RELEASE ARTIFACT

Generados POR CI desde tag v1.0.0 (58fdbf63). Commits posteriores = solo
docs/tests (sin código de producto). Hashes regenerados y verificados ×2:

```
b38f906c…d0a9c76  OWNEX Alpha_1.0.0_x64_es-ES.msi   (137 MB)
5a49d714…22209e6  OWNEX Alpha_1.0.0_x64-setup.exe   (135 MB)
```

Branding probe MSI: OWNEX Alpha ×15 · OMEGA ×0 · identifier alpha · sidecar marker.

## 14. VEREDICTO

```
RELEASE_STATUS = READY (ALPHA) — condicionado a HUMAN_VALIDATION_REQUIRED

P0: (ninguno)
P1: (ninguno)
P2: lint biome legacy (noExplicitAny) · 12 componentes huérfanos a revisar ·
    67 ruff preexistentes en polymarket/chroma (proceso concurrente)

Evidencia end-to-end ejecutada: build CI success con gates de sidecar,
contratos vivos campo-a-campo, lifecycle/persistence reproducidos localmente.
Lo único no ejecutado: install/runtime/uninstall/upgrade EN Windows real
(entorno de este audit = WSL/Linux) — checklist exacto en RELEASE_NOTES §
WINDOWS REAL VALIDATION REQUIRED.
```

Al pasar ese checklist: etiquetar `v1.0.0-alpha` final y **congelar arquitectura**.
