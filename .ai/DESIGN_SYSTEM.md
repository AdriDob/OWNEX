# OWNEX DESIGN SYSTEM — Alpha 1.0

> SSOT visual del frontend. Los tokens viven en `frontend/src/design/tokens.css`
> (importado por style.css); este doc los declara y fija las reglas de uso.
> Cualquier color/spacing nuevo DEBE entrar por token, nunca hardcodeado.

## Identidad

**"Mission control financiero + autonomous operating system"** — fondo negro
profundo con ambiente azul oscuro (decisión owner 2026-08-25), tipografía
técnica, datos en tabular-nums, cero decoración sin función.

## Tipografía

| Token | Stack | Uso |
|---|---|---|
| `--font-display` | Space Grotesk → Orbitron → Segoe UI | títulos hero |
| `--font-body` | Inter → Segoe UI Variable | todo texto UI |
| `--font-mono` | JetBrains Mono (variable vendida) → Cascadia | datos, dinero, labels técnicos |

Pesos: 400/500/600/700. Dinero SIEMPRE `font-mono tabular-nums`.

## Color — familia única (directiva owner: cero rojo decorativo)

| Token semántico | Resuelve a | Uso |
|---|---|---|
| `--color-bg` / `surface` / `surface-elevated` | ownex-bg-* | fondos |
| `--color-primary` | ownex-blue #00D5FF-family | acción primaria, foco |
| `--color-accent` | #00d5ff | acentos secundarios |
| `--color-danger` | azul fuerte (familia brand) | estados de error |
| `--color-warning` / `success` / `gold` | amber/green/gold | estados |
| `--ownex-red` | reservado | SOLO estados destructivos reales |

Reglas: jamás un segundo rojo; error ≠ accent; dinero exitoso = success.

## Espaciado y radios

`--spacing-1..n` (base 4px). Radios: sm 6 · md 10 · lg 16 · xl 24 · full.
Cards = lg; inputs/botones = md; badges/pills = full.

## Componentes base (`components/ui/`)

Button · Badge · Card(+Header/Title/Content/Footer) · Input · DataTable ·
Drawer · ContextMenu · EmptyState · LoadingState · ErrorState(shared) ·
GlassCard · CommandPalette(Ctrl+K) · StatusBadge · MoneyValue(tabular-nums).

### Contratos clave

- **ErrorState**: props `title, error, action, onRetry` — variante *connecting*
  calmada automática cuando `backendStatus !== ready`. Stub de tests debe
  espejar ESTE contrato (lección MissionControl).
- **NextBestAction**: props económicas del income-plan (payoffRange,
  evPerHour, cashSpeedDays, assessmentRequired, zeroExperience) + `href`
  para acción real. Nunca inventa valores.

## Estados obligatorios por vista

loading (LoadingState) · empty (EmptyState o copy honesto) · error
(ErrorState con retry) · offline/degraded (badge de sistema + banda
parcial via allSettled). Prohibido: blanco misterioso, spinner infinito,
"0" como placeholder de desconocido.

## Datos financieros

EXPECTED y REALIZED se muestran SIEMPRE separados (IncomeHome bandas
distintas). Probabilidades desconocidas se imprimen "desconocida". Dinero
con `usd()` locale es-AR.
