# OWNEX RELEASE_FINAL — v7.7.7 (cierre, pendiente validación física + tag)

> Fecha: 2026-09-28 · Rama: release/win11-stable · HEAD: a0e11ac1
> Estado: **RELEASE CANDIDATE** — código cerrado, freeze vigente.
> Falta para FINAL_STABLE: validación física del owner + tag.

## 1. Versión (sin drift)

| Superficie | Valor |
|---|---|
| .VERSION.txt | 7.7.7 |
| pyproject.toml | 7.7.7 |
| package.json (raíz) | 7.7.7 |
| frontend/package.json | 7.7.7 |
| src-tauri/tauri.conf.json | 7.7.7 |
| src-tauri/Cargo.toml | 7.7.7 |
| android/app (versionCode/versionName) | 777 / 7.7.7 |
| android/wear (versionCode/versionName) | 777 / 7.7.7 (sincronizado 2026-09-28, estaba en 1/1.0) |

## 2. Evidencia runtime (2026-09-28)

| Check | Resultado |
|---|---|
| `import api.main` | OK — **1847 rutas** |
| Scheduler | **17 ciclos / 72 jobs** (incl. autopilot_kill_scale 06:45 + daily_loop_run 06:50 restaurados) |
| Contract guard | `test_frontend_api_contract` verde |
| Suites clave | contract + mission + scheduler + curated + night: **126 passed** |
| Fast suite | **103 passed, 1 skipped** (2026-09-28) |
| Ruff | limpio en todo lo tocado (5 preexistentes en archivos extendidos, verificados por stash) |
| Frontend | `vite build` OK (~13s) |
| Secrets scan | limpio (sk-/ghp-/AKIA en código) |
| EXPECTED≠PAID | limpio en todo el árbol (dinero solo vía PAID/verificación) |
| Seeds muertos | vaciados (algora/bountyboard/polar con URLs 404 verificadas) |
| Fuentes | 136 curadas (12/12 nuevas probeadas **live**) |

## 3. Fuentes económicas

- **Verificadas vivas (probe real):** 12/12 nuevas (audit-contests, DS competitions, agregadores OSS) + majors (HackerOne, Bugcrowd, Intigriti, GitHub, Kaggle).
- **UNVERIFIED por diseño:** rate UNKNOWN pasa el gate, jamás promete plata.
- **Fuera por regla:** freelance/migajas (<$15/h o entrevista), DataAnnotation (US-only).
- **Modos:** cashflow (`near_guaranteed`) y jackpot separados y visibles en PublicWork (9 modos).

## 4. Limitaciones conocidas (no bloquean)

- Twins `cores/` file↔dir sin consolidar (documentado, riesgo > beneficio).
- Frontend legacy clusters B/D/E (WorkRoom ficticio, palette muerta, conexiones) — deuda explícita.
- LAYA sin pesos (UNAVAILABLE honesto) · `opencode2` instalado, sin smoke vivo (beta, requiere `auth login`).
- Trading live bloqueado (Human Gate + unlock explícito con monto).
- P(CASH) UNKNOWN hasta 1er PAID — todos los rates son hipótesis calibrándose.

## 5. Validación física pendiente (owner)

```text
Windows: install limpio → launch → health → login → dato → restart
  → backup → restore → offline → reinstall (dato sobrevive)
Android: install → launch → login → sync → 1 approve
opencode2: auth login → 1 run real vs v1
```

## 6. Release / rollback

- **Release:** validación física OK → tag `v7.7.7-final` → MSI/artefactos desde CI.
- **Rollback:** tag anterior + `data/` + `~/.ownex` intactos (backups `vault_backup_2h`); DB SQLite versionada por archivo.
- **Post-freeze solo entra:** BUG / SECURITY / PERFORMANCE / DATA-INTEGRITY / ECONOMIC-SOURCE-UPDATE / UX-IMPROVEMENT.

## 7. Working tree

234 entradas sin commitear (múltiples flujos). **No mezclar en un commit gigante.**
Este cierre viaja separado cuando el owner lo ordene.
