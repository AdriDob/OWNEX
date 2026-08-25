# OWNEX Alpha Desktop 1.0.0 — RELEASE GATE

> **Fecha**: 2026-08-25 · **Tag**: `v1.0.0` (58fdbf63) · **CI run**: [32795255916](https://github.com/AdriDob/OWNEX/actions/runs/32795255916) (success)
> **Entorno de build**: WSL/Linux + runners Windows de CI. **Instalación/runtime en Windows real: PENDIENTE** (checklist en RELEASE_NOTES §WINDOWS REAL VALIDATION REQUIRED).

## Artifacts (OneDrive `Adriel\OWNEX-DESKTOP-LAUNCHER-FINAL\`)

| Artifact | Tamaño | SHA256 |
|---|---|---|
| `OWNEX Alpha_1.0.0_x64_es-ES.msi` | 137,4 MB | `b38f906c5ccf7fba8639b809651057afb33cd663a85ebd6a680560c60d0a9c76` |
| `OWNEX Alpha_1.0.0_x64-setup.exe` (NSIS) | 135,2 MB | `5a49d714dcf45e5439cd6275cc6f76767c73828c688ce4d190613623c22209e6` |

## Matriz del Gate

| Área | Estado | Evidencia | Artifact/Fuente |
|---|---|---|---|
| Frontend build | VERIFIED | npm ci limpio → vue-tsc 0 err → vitest 226/226 → vite build OK; dist sin hardcodes :8000 (grep ×0); 150 assets | frontend/dist @ 58fdbf63 |
| Frontend runtime | PARTIAL | SPA sirve y flujos E2E API verificados contra backend vivo en Linux; render visual real = WebView2 pendiente | E2E smoke 11/11 |
| Backend standalone | VERIFIED | entrypoint probado: --port/--host/--data-dir/--log-level; health 4,5s; DB schema completo en data-dir; SIGTERM limpio 8,3s rc=0; restart mismo data-dir OK | src-tauri/binaries/start_backend.py |
| Backend exe Windows | PARTIAL | CI gate: sidecar ≥50MB + runtime smoke /api/health en runner ANTES de empaquetar (pasó); ejecución directa del .exe en PC usuario pendiente | CI run 32795255916 job log |
| Tauri bundle | VERIFIED | branding OWNEX Alpha ×15 / OMEGA ×0; identifier ai.orion.alpha.desktop; sidecar marker; version 1.0.0 en conf+Cargo+lock | probes sobre MSI descargado |
| Installer (install) | NOT VERIFIED | requiere Windows real | — |
| Uninstaller | NOT VERIFIED | idem (comportamiento de datos documentado: conserva %LOCALAPPDATA%\OWNEX) | README.txt |
| Lifecycle (start/close/restart) | PARTIAL | SIGTERM/watchdog verificado localmente (8,3s rc=0); orquestación Tauri→sidecar en Windows real pendiente | repro local |
| Database | VERIFIED | schema completo creado en data-dir override (11 DBs: cateye/memory/vault/pulse/odyssey/forge/atlas/aegis/orion_core/knowledge_graph/recovery) | /tmp sidecar-test |
| Persistence | VERIFIED (local) | datos íntegros tras restart en mismo data-dir; en Windows: misma ruta %LOCALAPPDATA%\OWNEX por código | repro local |
| AI providers | VERIFIED (API) | catálogo dinámico 200; PUT config aplica a registry vivo; tests Settings 10/10 | settings_ai.py |
| Providers reales (Ollama/keys) | NOT VERIFIED | requiere entorno con Ollama/keys del usuario | — |
| Opportunity Engine | VERIFIED (API) | targets/target/{id}/endpoints?target_id 200 live; hypotheses POST→attack_queue wired | E2E smoke |
| Direct Work Engine | VERIFIED (API) | direct-work/status·workbank 200 (root-mounted fix) | E2E smoke |
| WebSocket | PARTIAL | wsUrl resuelve puerto dinámico (lib/backend.ts); upgrade real vía WebView2 pendiente | código + tsc |
| Security | VERIFIED | 0 secretos en dist/docs/release; .env gitignored y fuera de specs; creds de adapters efímeras por-request; tokens solo como NOMBRES localStorage | sweep Fase 10 |
| Documentation | VERIFIED | README.txt/VERSION/CHANGELOG/RELEASE_NOTES/SHA256SUMS en destino; este gate en repo | OneDrive folder |
| Restart (sin huérfanos) | VERIFIED (local) / PARTIAL (Win) | watchdog ≤8s garantiza salida; verificación Task Manager en Windows pendiente | repro + lib.rs kill-on-exit |
| Clean install | NOT VERIFIED | requiere Windows real | — |

## Veredicto

**RELEASE READY (ALPHA) — condicionado a WINDOWS REAL VALIDATION REQUIRED.**

Bloqueos P0: **0** · P1 críticos: **0**
Lo único que separa este gate de "VERIFIED" completo son las pruebas que
físicamente requieren una sesión gráfica Windows (install/runtime/uninstall/
restart en máquina real). Todo lo verificable desde el pipeline de build está
verificado con evidencia citada.
