# FASE 1 — Auditoría UX/UI Integral

> Fecha: 2026-07-12
> Páginas auditadas: 47 (de 60+ en router)
> Componentes UI auditados: 26
> Patrones compartidos identificados: 12

---

## 1. HALLAZGOS CRÍTICOS (Impacto Alto)

### HC-1: Dos home pages — Dashboard.vue (/) vs MissionControl.vue (/mission-control)
- **Dashboard.vue** (`/`): versión anterior, usa `card-base` directo, sin QuickActions, sin activity feed
- **MissionControl.vue** (`/mission-control`): nuevo ops hub con QuickActions, status, activity, bottlenecks
- **Problema**: La ruta por defecto (`/`) redirige al Dashboard legacy. El usuario pierde el nuevo hub.
- **Solución**: Redirigir `/` → `/mission-control` o fusionar ambas páginas.

### HC-2: Sin componente Table/DataTable compartido
- Cada página que muestra datos tabulares implementa su propio HTML de tabla:
  - `MoneyRadar.vue` — grid CSS manual
  - `AttackSurface.vue` — `<table>` HTML manual
  - `TruthInspector.vue` — grid CSS manual
  - `ReportCenter.vue` — tarjetas con listas
  - `PipelineMonitor.vue` — listas manuales
  - `MemoryPatterns.vue` — tarjetas
  - `EvidenceCenter.vue` — tarjetas
  - `Connections.vue` — tarjetas + grid
- **Impacto**: Cada tabla tiene diferente markup, responsive, sorting, filtering.
- **Solución**: Crear `DataTable.vue` con sort, paginate, search, responsive.

### HC-3: Sin componente Select/Dropdown compartido
- `Settings.vue` usa `<select>` HTML nativo
- `MoneyRadar.vue` usa `<select>` nativo (líneas 136-145)
- `AttackSurface.vue` usa `<select>` nativo (línea 89)
- `Connections.vue` usa `<select>` nativo (línea 781)
- **Impacto**: Inconsistentes. El `<Input>` component existe pero `<Select>` no.
- **Solución**: Crear `Select.vue` con v-model, options, placeholder, variants.

### HC-4: Sin componente Modal/Dialog compartido
- `ReportCenter.vue` — inline modal para draft preview (líneas 210-278)
- `Connections.vue` — inline modals para platform wizard y payout wizard (líneas 652-821)
- `Settings.vue` — inline modal para onboarding wizard
- `Workflows.vue` — inline dialog para crear workflow
- **Problema**: Cada modal tiene su propia implementación (backdrop, animación, close).
- **Solución**: Crear `Modal.vue` con teleport, backdrop, transitions, sizes.

### HC-5: glass-card / glass-fintech / glass-strong — clases legacy
- `ReportCenter.vue` línea 171: `class="glass-card rounded-xl p-4"`
- `CommandPalette.vue` línea 221: `class="glass-strong rounded-xl"`
- `Connections.vue` múltiples: `class="glass-fintech rounded-xl"`
- **Problema**: `card-base` es el estándar post-RC2. Estas clases legacy sobreviven.
- **Solución**: Reemplazar con `card-base` o `<Card>` component.

### HC-6: 3+ formas de hacer inputs
1. `<Input>` component (modelValue) — Findings.vue, ReportCenter, etc.
2. `<input>` raw con Tailwind — Settings.vue (20+ inputs raw)
3. `<input>` raw con clases manuales — Connections.vue (10+ inputs raw)
4. `<input>` raw con bg-[#0a0a0a] — Connections.vue (líneas 411, 417, etc.)
- **Impacto**: Los inputs raw no tienen focus ring consistente, ni error states, ni disabled.
- **Solución**: Usar `<Input>` en todos lados.

### HC-7: Hardcoded colors rompen theming
- `IntelligenceDashboard.vue`:
  - `bg-[#1e2230]` (líneas 116, 136, 140, 144)
  - `border-[#2a2e3d]` (líneas 116, 136, 140, 144)
- `AgentCenter.vue`:
  - `bg-[#ffffff08]` (líneas 206, 229)
- **Impacto**: Cambiar de tema (ocean, sunset, light) no afecta estos colores.
- **Solución**: Usar variables CSS (`bg-surface`, `border-border`).

---

## 2. HALLAZGOS IMPORTANTES (Impacto Medio)

### HM-1: EmptyState component existe pero no se usa
- `src/components/ui/EmptyState.vue` — bien implementado con icon, title, description, action
- Pero cada página implementa su propio empty state con div manual
- **Impacto**: 20+ implementaciones duplicadas de empty states.
- **Solución**: Usar `<EmptyState>` en todas las páginas.

### HM-2: Loading/Error/Empty patterns no estandarizados
- 90% de páginas implementan:
  ```html
  <template v-if="loading"> <Skeleton /> </template>
  <template v-else-if="error"> <AlertTriangle /> + mensaje + retry </template>
  <template v-else-if="!data.length"> <EmptyState /> </template>
  <template v-else> contenido </template>
  ```
- Pero el markup varía: algunos usan `<Button>`, otros `<button>`, otros raw HTML
- **Solución**: Crear `LoadingErrorEmpty.vue` que encapsule el patrón.

### HM-3: Autofetch + polling inconsistente
- `AgentCenter.vue` — polling 3s y 5s con `setInterval`
- `MissionControl.vue` — polling 30s (?)
- Otras páginas: fetch on mount, nunca refrescan
- **Solución**: Crear `usePolling(fn, interval)` composable estándar.

### HM-4: CommandPalette limitada
- Solo busca: navegación (6 items), acciones (4 items), targets
- No busca: findings, reports, workflows, knowledge, settings, agents, config
- No acepta lenguaje natural
- No tiene fuzzy search
- **Solución**: FASE 2 completa.

### HM-5: Sin shortcuts discoverability
- `useGlobalShortcuts.ts` tiene 15 shortcuts
- Pero no hay UI para descubrirlos (command palette no los muestra)
- `ctrl+/` existe pero no hay panel de shortcuts
- **Solución**: Agregar shortcut list en CommandPalette o panel dedicado.

### HM-6: Notifications no conectadas a activity center
- `NotificationPanel.vue` existe, store existe
- Pero notifications viven aisladas del timeline, eventos, scheduler
- **Solución**: FASE 4 — unificar activity center.

### HM-7: Sidebar navegación no coincide con router
- Sidebar agrupa en: Inteligencia, Finanzas, Operaciones, Apps, Sistema
- Muchas páginas del router (37+) no están en sidebar
- Discovery: `/discovery` apunta pero no hay entrada visible (búsqueda desde sidebar)
- **Solución**: Revisar taxonomía de navegación.

---

## 3. HALLAZGOS MENORES (Impacto Bajo)

### Hm-1: Wallets.vue usa emoji como iconos (línea 65-70)
```ts
function platformIcon(platform: string) {
  if (p.includes('bank')) return '🏦'
  if (p.includes('paypal')) return '💳'
  return '💰'
}
```
- Debería usar Lucide icons como el resto del sistema.

### Hm-2: QuickActions.vue usa emoji como iconos
```ts
const iconMap = { check: '✓', file: '📄', search: '🔍', dollar: '💰', ... }
```
- Rompe consistencia de iconografía.

### Hm-3: AgentCenter.vue icons con emoji
```ts
const agentIcons = { coordinator: '🎯', research: '🔍', validator: '✅', ... }
```
- Inconsistente con el sistema de Lucide icons.

### Hm-4: DailyMode.vue sin estilos globales
- Usa `<button>` raw en lugar de `<Button>` component (línea 58-59, 121)
- Tiene estilos inline `rounded-md bg-primary px-3 py-1.5`

### Hm-5: PipelineMonitor.vue usa `prompt()` (línea 49)
- `const targetName = prompt('Target name (domain or IP):')`
- Debería ser un diálogo del sistema o modal.

### Hm-6: Settings.vue tiene 996+ líneas
- Candidato a ser dividido en componentes.
- Las tabs podrían ser componentes lazy-loaded.

### Hm-7: Connections.vue tiene 848 líneas
- Candidato a dividir en: PlatformList, PayoutWizard, SubmissionHistory.
- Tiene 2 modales inline que deberían ser `Modal.vue`.

### Hm-8: `scrollbar-thin` re-definido en NotificationPanel.vue
- Debería ser una clase global en style.css.

### Hm-9: `glass-strong` en CommandPalette
- ClassName legacy. Usar `card-base`.

---

## 4. COMPONENTES COMPARTIDOS A CREAR

Basado en la auditoría, faltan estos componentes en el design system:

| Componente | Prioridad | Usos potenciales |
|---|---|---|
| `DataTable.vue` | 🔴 Alta | 8+ páginas con tablas |
| `Modal.vue` | 🔴 Alta | 4+ páginas con modales inline |
| `Select.vue` | 🟡 Media | 5+ páginas con selects |
| `Pagination.vue` | 🟡 Media | 4+ páginas con listas paginadas |
| `Drawer.vue` | 🟡 Media | FindingDetailDrawer, paneles laterales |
| `Toast.vue` | 🟢 Baja | ya existe useToast composable |
| `PageHeader.vue` | 🟢 Baja | 90% de páginas repiten header pattern |

---

## 5. MÉTRICAS POR PÁGINA

| Página | Líneas | Usa Card | Usa Input | Estados | Issues |
|---|---|---|---|---|---|
| Dashboard.vue | 274 | card-base raw | No | L/E/E | Legacy, duplicado con MC |
| MissionControl.vue | ~350 | card-base | No | L/E/E | ✅ Bueno |
| Findings.vue | 228 | ✅ Card | raw input | L/E/E | Input raw |
| FindingDetail.vue | 216 | ✅ Card | No | L/E/E | ✅ Bueno |
| ReportCenter.vue | 430 | ✅ Card | ✅ Input | L/E/E | glass-card legacy |
| HotPaths.vue | 122 | ✅ Card | No | L/E/E | ✅ Bueno |
| OpportunityRadar.vue | 123 | ✅ Card | ✅ Input | L/E/E | ✅ Bueno |
| MoneyRadar.vue | 273 | ✅ Card | ✅ Input | L/E/E | Select raw |
| DailyMode.vue | 149 | ✅ Card | No | L/E/E | Button raw |
| Wallets.vue | 285 | ✅ Card | No | L/E/E | Emoji icons |
| Settings.vue | 996+ | card-base raw | raw inputs | ✅ Save toast | Raw inputs everywhere |
| OperationsDashboard.vue | 384 | ✅ Card | No | L/E/E | ✅ Bueno |
| AgentCenter.vue | 246 | ✅ Card | No | L/E/E | Emoji icons, hardcoded colors |
| IntelligenceDashboard.vue | 172 | ✅ Card | No | L/E/E | Hardcoded bg/border |
| EvidenceCenter.vue | 202 | ✅ Card | No | L/E/E | ✅ Bueno |
| HealthCenter.vue | ~189 | No Card | No | L/E/E | Sin Card |
| Connections.vue | 848 | ✅ Card | raw inputs | L/E/E | glass-fintech, 848 lines |
| AttackSurface.vue | 128 | ✅ Card | No | L/E/E | Select raw |
| MemoryPatterns.vue | ~204 | ✅ Card | ✅ Input | L/E/E | ✅ Bueno |
| TruthInspector.vue | ~234 | ✅ Card | No | L/E/E | ✅ Bueno |
| PipelineMonitor.vue | ~235 | ✅ Card | No | L/E/E | prompt() raw |
| Workflows.vue | ~241 | No Card | No | L/E/E | Sin Card |

L = Loading, E = Error, E = Empty

---

## 6. CONCLUSIONES Y PRIORIDADES

### Prioridad 1 (Comenzar ahora)
1. Redirigir `/` → `/mission-control` (HC-1)
2. Reemplazar glass-card/glass-fintech/glass-strong → card-base (HC-5)
3. Reemplazar inputs raw → `<Input>` en Settings y Connections (HC-6)
4. Reemplazar hardcoded colors → theme variables (HC-7)

### Prioridad 2 (Componentes faltantes)
5. Crear `Modal.vue` — reemplazar 4+ modales inline
6. Crear `Select.vue` — reemplazar 5+ selects raw
7. Crear `DataTable.vue` — estandarizar tablas

### Prioridad 3 (Patrones)
8. Usar `<EmptyState>` en todas las páginas (HM-1)
9. Estandarizar Loading/Error/Empty (HM-2)
10. Crear `usePolling()` composable (HM-3)

### Prioridad 4 (Consistencia visual)
11. Reemplazar emojis → Lucide icons (Hm-1, Hm-2, Hm-3)
12. Reemplazar button raw → Button component (Hm-4)
13. Reemplazar prompt() → Modal (Hm-5)
