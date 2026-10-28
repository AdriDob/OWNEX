# Known Limitations — OWNEX 7.1.0 FINAL STABLE

> Limitaciones reales verificadas contra runtime. Nada de esto bloquea el uso
> diario. Actualizado: 2026-09-11.

## 1. Modos LITE/FULL/CAPITAL duplicados (no bloquea)

Dos motores vivos con formas distintas: `cores/modes/engine.py` (OwnexMode,
usado por `/api/modes/*` y command_center) y
`cores/financial_intelligence/mode_manager.py` (ModeValue, usado por autopilot
y settings_runtime). Ambos funcionan; ninguno es canónico. Consolidar exige
migrar consumidores de autopilot — se difiere por riesgo, no por pereza.

- Workaround: usar `/api/modes/*` como superficie principal.
- Acción futura: un motor delega al otro con tests de equivalencia.

## 2. Mobile = RC, Watch = mínimo viable (no bloquea)

Android compila (namespace `ai.rastro.app`) pero no hay validación en hardware
físico en esta sesión. WearOS expone estado/alertas/aprobación vía
`cores/wear_os` + API; no hay app nativa. Desktop Windows es la superficie
primaria; mobile/watch son consulta y aprobación.

## 3. Suite completa con drift del flujo concurrente (no bloquea)

`make test` excluye por defecto 5 suites (`test_security`, `test_vision_gateway`,
`test_scheduler`, `test_financial_hub`, `test_self_improvement`) por red/flaky o
contratos en migración por otro flujo activo. Gate de release = suite fast
100/1 + suites afectadas por cada cambio, siempre verdes.

## 4. MSI solo vía CI Windows (no bloquea)

El instalador MSI/NSIS solo se construye en runner `windows-latest`
(`ownex-tauri-windows.yml`). En Linux se valida spec ONEFILE + `cargo check`
+ smoke del sidecar. Sin firma de código (decisión): SmartScreen mostrará
advertencia en primera instalación.

## 5. Contenido MPT requiere key gratuita (no bloquea)

El pipeline Content Factory es end-to-end real (guion Ollama local + Edge TTS
+ subtítulos verificados), pero la descarga de materiales exige
`pexels_api_keys` o `coverr_api_keys` (tiers gratuitos) en
`~/projects/MoneyPrinterTurbo/config.toml`. Sin key, el aviso queda visible
en IncomeHome + `/setup/checklist` y la generación falla con mensaje explícito.

## 6. Trading e inversión en DRY_RUN (por diseño)

Nada mueve fondos reales sin configuración explícita + Human Gate. No es un
bug: es la política de seguridad del producto.

## 7. Validation Engine: revisión humana obligatoria (por diseño)

El motor de validación produce borradores con explicaciones alternativas y
penalización por incertidumbre, pero todo finding requiere revisión humana
antes de reportar. Probabilidades UNKNOWN se etiquetan, nunca se inventan.
