# OWNEX DESIGN SYSTEM — SSOT Reference

> **Single Source of Truth:** `.ai/OWNEX_DESIGN_SYSTEM.md` (v1.0)
> Los tokens viven en `frontend/src/design/tokens.css` (importado por style.css).
> Cualquier color/spacing nuevo DEBE entrar por token, nunca hardcodeado.

---

## Resumen Rápido (Alpha 1.0)

### Identidad
**"Mission control financiero + autonomous operating system"** — fondo negro profundo, tipografía técnica, datos en tabular-nums, cero decoración sin función.

### Paleta (Cero rojo decorativo — directiva owner 2026-08-25)

| Token semántico | Valor | Uso |
|---|---|---|
| `--color-bg` / `surface` / `surface-elevated` | `ownex-bg-*` | fondos |
| `--color-primary` | `ownex-blue #3B82F6` | acción primaria, foco |
| `--color-accent` | `#00d5ff` | acentos secundarios (cyan legacy) |
| `--color-danger` | azul fuerte (`ownex-blue`) | estados de error |
| `--color-warning` / `success` / `gold` | amber/green/gold | estados |
| `--ownex-red` | reservado | SOLO estados destructivos reales |

**Regla:** jamás un segundo rojo; error ≠ accent; dinero exitoso = success.

### Tipografía
- `--font-display`: Space Grotesk → Orbitron → Segoe UI (títulos hero)
- `--font-body`: Inter → Segoe UI Variable (todo texto UI)
- `--font-mono`: JetBrains Mono → Cascadia (datos, dinero, labels técnicos)

### Espaciado y Radios
`--spacing-1..n` (base 4px). Radios: sm 6 · md 10 · lg 16 · xl 24 · full.
Cards = lg; inputs/botones = md; badges/pills = full.

### Componentes base (`components/ui/`)
Button · Badge · Card(+Header/Title/Content/Footer) · Input · DataTable ·
Drawer · ContextMenu · EmptyState · LoadingState · ErrorState(shared) ·
GlassCard · CommandPalette(Ctrl+K) · StatusBadge · MoneyValue(tabular-nums).

### Contratos clave
- **ErrorState**: props `title, error, action, onRetry` — variante *connecting* calmada cuando `backendStatus !== ready`.
- **NextBestAction**: props económicas (payoffRange, evPerHour, cashSpeedDays, assessmentRequired, zeroExperience) + `href` para acción real. Nunca inventa valores.

### Estados obligatorios por vista
loading (LoadingState) · empty (EmptyState o copy honesto) · error (ErrorState con retry) · offline/degraded (badge + banda parcial via allSettled).
**Prohibido:** blanco misterioso, spinner infinito, "0" como placeholder de desconocido.

### Datos financieros
EXPECTED y REALIZED SIEMPRE separados (IncomeHome bandas distintas). Probabilidades desconocidas = "desconocida". Dinero con `usd()` locale es-AR.

---

## Para el detalle completo (tokens, layout, componentes, desktop, android, splash)
👉 **Leer `.ai/OWNEX_DESIGN_SYSTEM.md`** — es el documento canónico v1.0.