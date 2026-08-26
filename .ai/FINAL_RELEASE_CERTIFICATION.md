# FINAL RELEASE CERTIFICATION — OWNEX Alpha 1.0.1

> **Fecha**: 2026-08-26 · **Commit**: e9a295dc · **Tag CI**: v1.0.1-alpha-rc2 (build en curso)
> **Método**: solo evidencia ejecutada. Clasificación: PASS / PASS-WITH-LIMITATION / MANUAL VERIFIED / NOT APPLICABLE / FAIL.

## Gates automatizados

| Área | Clasificación | Evidencia |
|---|---|---|
| Backend tests | **PASS** | 3880 passed / 0 failed / 18 skipped documentados / 2 xfailed |
| Frontend typecheck | **PASS** | vue-tsc exit 0 |
| Frontend tests | **PASS** | vitest 226/226 |
| Frontend build | **PASS** | vite build OK (11.6s) |
| Lint tocados | **PASS** | ruff 0 errores; global ~2897 pre-existentes = P2 backlog |
| Economic integrity | **PASS** | EXPECTED≠PENDING≠PAID por proyección de estado; dinero solo en PAID (E2E) |
| Execution Queue | **PASS** | Mirror WorkBank↔Queue↔Pago cerrado, idempotente, 8/8 tests + sweep 29/29 |
| Device identity tri-surface | **PASS** | /api/device/* + ownex-device-id compartido |
| Mobile unificada | **PASS** | MobileApp.vue tokens Tesla, offline queue honesta, Watch tab |
| Watch contract + cliente | **PASS-WITH-LIMITATION** | Backend 4/4 200; MainActivity.java existe; APK física = manual |
| Security scan | **PASS** | 0 secretos hardcodeados (patrones sk-/AKIA/api_key); CSP loopback-only; vault para credenciales |
| OAR budget | **PASS** | daily_budget_usd=0.0 default (§12); paid tiers exigen config explícita |
| Persistence %LOCALAPPDATA% | **PASS** | user_data_dir() frozen-aware + guards 4 tests |
| Sidecar lifecycle | **PASS** (código) | RunEvent::Exit kill + port-abort + health poll; guards packaging 9 |
| Launcher Win11+WSL | **PASS** (WSL lado) | start/stop verificados E2E UI 200+API 200; .ps1 lado Windows = manual |
| CI artifacts MSI+NSIS | **MANUAL VERIFIED** pendiente | rc2 en curso; instalación limpia/upgrade/soak24h requieren máquina Windows |

## Release blockers

**None identified** en lo automatizable desde este host.

## REQUIRES HUMAN VALIDATION (no falseable)

1. Instalación limpia Windows 11 (MSI/NSIS rc2)
2. Upgrade sobre versión previa con datos
3. Shutdown sin huérfanos en Windows real
4. Soak 24h
5. APK Android + Wear en dispositivo/emulador
6. Launchers .ps1 ejecutados desde PowerShell real

## Known limitations (reales)

- Playwright E2E tri-surface cross-device → 1.1 (suites por-superficie cubiertas)
- Push VAPID emisor backend → 1.1 (handler SW listo)
- Sync apply/conflict entrante → corte siguiente (snapshot productivo hoy)
- Lint global histórico → P2
- Cuotas de providers gratuitos = UNKNOWN por diseño (nunca "unlimited")

## Veredicto

**RC** — Release Candidate. Todos los gates automatizables PASS.
`STABLE` solo tras validación física Windows (checklist arriba).
