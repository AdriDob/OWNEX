# Definition of Done — OWNEX Economic Operating System

> Verificado por `tests/test_economic_os.py` (17) + fast gate. Si un ítem no
> tiene evidencia citada, no está DONE.

## DONE significa

- [x] Arranca: `api.main` importa, `/api/health` 200
- [x] Conoce estado: `/api/daily-digest` + `/api/system/pc-health` + `/api/system/brave`
- [x] Conoce oportunidades: `/direct-work/recommend` ranked + `public_work` ladder
- [x] Conoce tareas: WorkBank `ready_to_deliver` + ExecutionQueue mirror
- [x] Daily Execution Plan: `POST /mission-hub/daily-loop/run` (auto A1-A2, gate A3 con evidencia)
- [x] Prioriza NET CASH/HOUR: `recommendation` EV/h + P(CASH); grants ×0.4
- [x] Prepara acciones: ladder A1 (plan) + A2 (checks reversibles)
- [x] Human Gate: HMAC single-use 600s (`safety.py`); approve/reject/edit/defer
- [x] Ejecuta permitido: A2 + A6→A7 tras approval; opencode two-phase con token
- [x] Verifica: A8 monitor + A9 payment track (ledger PENDING→PAID→NET)
- [x] Registra dinero real: Revenue Ledger PAID-only; ACCEPTED≠PAID
- [x] Distingue CASH/EXPECTED: ledger states + `paid_only_increments_real`
- [x] Actualiza P(CASH): `channel_economy()` + `identify_repeatable()` desde outcomes
- [x] Aprende: A10 (outcomes→economía) + A11 (re-rank, cut losers)
- [x] Funciona sin IA: OAR degraded + heurísticos; chat degrada honesto
- [x] Fallback: OAR failover chain pineado local-first; feeds graceful []
- [x] Backup/recovery: engine + restore + `.key.bak` + UNKNOWN heal rule
- [x] Seguridad: vault scopes, least privilege, sin secretos en repo/logs
- [x] Docs sincronizadas: `.ai/` SSOT + README + W1-W12 guide
- [x] Builds: vite + cargo check + PyInstaller ONEFILE + CI MSI/EXE
- [x] Sin duplicación nueva: solver/ladder/economics reutilizan motores
- [x] Opera post-60-días: economic-loop phases + workspace allocation diaria

## Explícitamente NO DONE (honesto)

- W1-W12 físico: PENDING USER EXECUTION (nunca PASS desde Linux)
- `core/` borrado: gateado a W1-W12 + `rg from core. == 0`
- EV/h por workspace: UNKNOWN hasta horas humanas por workspace medidas
- P(CASH) por workspace: UNKNOWN hasta calibración por workspace
- Cross-process Human Gate: fuera de 7.1.x (single-process documentado)
