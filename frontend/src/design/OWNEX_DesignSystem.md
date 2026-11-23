# OWNEX Design System v1.0

## Single Source of Truth para el Frontend

### 1. Color System

#### Base Colors
```
--ownex-bg-deep:      #0d0d0d;    /* Fondo principal - negro puro */
--ownex-bg-base:      #1a1a1a;    /* Paneles elevados */
--ownex-bg-surface:   #262626;    /* Tarjetas, modales */
--ownex-bg-glass:     rgba(13, 13, 13, 0.8); /* Glassmorphism */
```

#### Identity Colors (OWNEX)
```
--ownex-primary:      #7e57c2;    /* Púrpura - marca, acciones principales */
--ownex-primary-light: #a779e8;   /* Púrpura claro */
--ownex-primary-dark:  #6a1b9a;   /* Púrpura oscuro */
--ownex-white:        #ffffff;    /* Información importante, títulos */
--ownex-gray:         #bbbbbb;    /* Gris - texto auxiliar, bordes */
--ownex-gray-light:   #efefef;    /* Gris claro */
```

#### Alert States
```
--ownex-success:      #4caf50;    /* ✅ Activo / Éxito */
--ownex-success-light: #c8e6c9;   /* Verde claro */
--ownex-warning:      #f9a825;    /* ⚠️ Atención / Advertencia */
--ownex-warning-light: #fff5e5;   /* Amarillo claro */
--ownex-danger:       #e53935;    /* ❌ Error / Riesgo crítico */
--ownex-danger-light: #ffcdd2;    /* Rojo claro */
```

#### Platform Colors (referencia)
```
--ownex-hackerone:    #43a047;
--ownex-bugcrowd:     #fb8c00;
--ownex-intigriti:    #ab47bc;
--ownex-synack:       #5d6d7e;
--ownex-yeswehack:    #1976d2;
```

#### Cycle Colors (monocromo, purple = ownership)
```
--ownex-cycle-security: #F5F5F5;
--ownex-cycle-forge:    #9E9E9E;
--ownex-cycle-pulse:    #7e57c2;
--ownex-cycle-vault:    #6a1b9a;
--ownex-cycle-atlas:    #757575;
--ownex-cycle-odyssey:  #7e57c2;
```

#### Expansión de colores (Mission Control)
```
[accent="default"] { }
[accent="gold"] {
  --ownex-primary: #f5f5f5;
  --ownex-white: #1A1200;
}
```

### 2. Typography

```
--font-display: 'Space Grotesk', 'Orbitron', 'Segoe UI', ui-sans-serif, system-ui, sans-serif;
--font-body: 'Inter', 'Segoe UI Variable Text', 'Segoe UI', ui-sans-serif, system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Cascadia Code', ui-monospace, 'Consolas', monospace;

--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;

--leading-tight: 1.1;
--leading-snug: 1.375;
--leading-normal: 1.5;
--leading-relaxed: 1.625;
```

### 3. Spacing

```
--space-1:  4px;
--space-2:  8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  24px;
--space-6:  32px;
--space-8:  48px;
--space-10: 64px;
```

### 4. Layout Dimensions

```
--status-bar-height: 40px;
--sidebar-width: 280px;
--sidebar-collapsed-width: 64px;
--sidebar-mobile-width: 280px;
```

### 5. Z-Index Scale

```
--z-status-bar: 50;
--z-sidebar: 40;
--z-overlay: 60;
--z-modal: 70;
--z-toast: 80;
--z-tooltip: 90;
--z-splash: 200;
--z-command-palette: 100;
```

### 6. Density Modes

```
--density-compact: 0.75;
--density-default: 1;
--density-spacious: 1.5;
```

### 7. Focus Ring

```
--focus-ring: 0 0 0 2px rgba(126, 87, 194, 0.3), 0 0 12px rgba(126, 87, 194, 0.2);
```

### 8. Borders & Materials

```
--glass-bg:       var(--ownex-bg-glass);
--glass-border:   1px solid var(--ownex-bg-glass-border);
--glass-blur:     backdrop-filter: blur(20px) saturate(180%);
--glass-blur-webkit: -webkit-backdrop-filter: blur(20px) saturate(180%);

--mica-bg:        rgba(8, 8, 8, 0.9);
--mica-border:    1px solid rgba(255, 255, 255, 0.06);
```

### 9. Elevation Shadows

```
--shadow-sm:  0 1px 3px rgba(0, 0, 0, 0.4);
--shadow-md:  0 4px 12px rgba(0, 0, 0, 0.5);
--shadow-lg:  0 8px 32px rgba(0, 0, 0, 0.6);
--shadow-glow: 0 0 24px rgba(255, 255, 255, 0.06);
```

### 10. Radius & Transitions

```
--radius-sm:  6px;
--radius-md:  10px;
--radius-lg:  16px;
--radius-xl:  24px;
--radius-full: 9999px;

--transition-fast:  120ms ease-out;
--transition-base:  200ms ease-out;
--transition-slow:  350ms ease-out;

--spring-snappy:    stiffness 200 damping 20 mass 0.5;
--spring-gentle:    stiffness 120 damping 14 mass 1;
--spring-bouncy:    stiffness 100 damping 8  mass 1;
--spring-liquid:    stiffness 80  damping 12 mass 1.2;
--spring-stiff:     stiffness 300 damping 30 mass 0.8;
--spring-loading:   stiffness 150 damping 18 mass 1;
```

## 📋 11. Layout Variants

### Dark Mode (default)
```
[data-theme="dark"] {
  --ownex-bg-deep: #0d0d0d;
  --ownex-bg-base: #1a1a1a;
  --ownex-bg-surface: #262626;
}
```

### Light Mode
```
[data-theme="light"] {
  --ownex-bg-deep: #fafafa;
  --ownex-bg-base: #ffffff;
  --ownex-bg-surface: #f5f5f5;
  --ownex-primary: #7e57c2;
  --ownex-white: #1a1a1a;
}
```

### Cycle Active Variant
```
[data-cycle="security"]   { --cycle-color: var(--ownex-cycle-security) }
[data-cycle="forge"]      { --cycle-color: var(--ownex-cycle-forge) }
[data-cycle="pulse"]      { --cycle-color: var(--ownex-cycle-pulse) }
[data-cycle="vault"]      { --cycle-color: var(--ownex-cycle-vault) }
[data-cycle="atlas"]      { --cycle-color: var(--ownex-cycle-atlas) }
[data-cycle="odyssey"]    { --cycle-color: var(--ownex-cycle-odyssey) }
```

## 🛠️ 12. Component Specifications

### Button Component
```vue
<button class="btn btn--primary" :class="[variant, sizeClass]">
  <slot />
</button>
```

Variants: `primary`, `secondary`, `success`, `warning`, `danger`, `ghost`
Sizes: `xs`, `sm`, `md`, `lg`, `icon`
States: `default`, `hover`, `active`, `disabled`, `loading`

### Input Component
```vue
<input :class="[inputClass, sizeClass]" :placeholder="placeholder" />
```

States: `default`, `focus`, `error`, `disabled`
Sizes: `xs`, `sm`, `md`, `lg`

### Table Component
```vue
<table class="ownex-table">
  <thead>
    <tr>
      <th>Columna</th>
    </tr>
  </thead>
  <tbody>
    <tr v-for="item in data" :key="item.id">
      <td>{{ item.valor }}</td>
    </tr>
  </tbody>
</table>
```

States: `default`, `loading`, `empty`, `error`

### Badge Component
```vue
<span class="badge badge--primary" :class="[variant]">{{ texto }}</span>
```

Variants: `primary`, `success`, `warning`, `danger`, `neutral`

### Status Badge
```vue
<status-badge :status="status" :size="size" />
```

States: `online`, `offline`, `warning`, `critical`, `pending`, `verified`

## 📱 13. App Shell Structure

### Desktop Layout

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────────┐  ┌────────────────────────────────┐ │
│  │  SIDEBAR    │  │  TITLEBAR + SEARCH + ACTIONS      │ │
│  │  (collapsible)         │  │  [avatar, notifications, settings]│ │
│  ├─────────────────────────────────────────────────────┤ │
│  │  MAIN CONTENT              │  │  ┌────────────────────┐ │ │
│  │  └────────────────────┐  │  │  PAGE CONTENT      │ │ │
│  │  WORKSPACE AREA        │  │  └────────────────────┘ │ │
│  │                       │  │                       │ │ │
│  │  ┌────────────────┐ │  │                       │ │ │
│  │  │ SIDEBAR NAV    │ │  │  [router-view]      │ │ │
│  │  │ (collapsed)    │ │  │                       │ │ │
│  │  └────────────────┘ │  │                       │ │ │
│  └────────────────────┘ └─────────────────────────────┘ │
│  └─────────────────────────────────────────────────────┘ │
│                    FOOTER (optional)                        │
└─────────────────────────────────────────────────────────────┘
```

### Sidebar States

#### Expanded (default)
```
width: 280px
Contains: full nav items, cycle logos, badge counts, section titles
```

#### Collapsed
```
width: 64px
Contains: icons only, no text labels
Toggle: bottom-center floating button
```

### Topbar (ModernNavbar)

```
├─ Left: Brand (OWNEX Alpha + O-ring mark)
├─ Center: Search bar ("Buscar targets, hallazgos, reportes...")
├─ Right: Actions
   ├─ MERLIN (navigate to /merlin)
   ├─ Discovery (navigate to /targets/discovery)
   ├─ Hallazgos (navigate to /intelligence/findings)
   ├─ Reportes (navigate to /reports/queue)
   ├─ Capital (navigate to /capital)
   ├─ Configuración (navigate to settings)
```

### Footer (AppFooter)

```
Contiene: enlaces rápidos, versión, política de privacidad
```

## 🎯 14. Implementation Priority

### FASE 1.1: Design Tokens (HECHO)
- [x] `src/design/tokens.css` consolidado
- [x] Custom properties definidos

### FASE 1.2: App Shell (EN PROGRESO)
- [ ] AppLayout.vue con sidebar colapsable
- [ ] ModernNavbar con brand, search, actions
- [ ] TitleBar con controles de ventana (solo Tauri)
- [ ] StatusBar con indicadores de sistema
- [ ] AppFooter minimal

### FASE 1.3: Component Library Base
- [ ] OwnexBadge.vue (cycle counts, status)
- [ ] StatusBadge.vue (online/offline/warning/critical)
- [ ] ThemeToggle.vue (dark/light switch)
- [ ] LoadingSkeleton.vue (placeholder states)

### FASE 1.4: Integration
- [ ] Conectar tokens CSS con Tailwind config
- [ ] Aplicar classes a componentes existentes
- [ ] Verificar consistencia visual en todas las pantallas

## 📸 15. Capturas de Referencia

Pending: ejecutar aplicación y capturar screenshots de cada estado (expanded/collapsed theme).

## 🔧 16. Debug & Troubleshooting

### Problemas Comunes

1. **Tokens no aplicándose**: Verificar que `tailwind.config.ts` incluya `content: []` con los archivos correctos.

2. **Sidebar no colapsando**: Revisar el evento `update:modelValue` en `AppLayout.vue`.

3. **Tema no cambiando**: Verificar el `data-theme` attribute en `<html>` y el watch en `App.vue`.

4. **Transiciones saltando**: Asegurar `Transition` component con `mode="out-in"` consistente.

### Comandos de Verificación

```
# Verificar tokens compilados
grep -rn "var(--ownex-" frontend/src/ | head -20

# Verificar sidebar state
cat src/components/layout/AppLayout.vue | grep -A5 "collapsed"

# Verificar theme toggle
grep -rn "data-theme" frontend/src/ | head -10

# Verificar sidebar width en CSS
grep -A3 "ownex-sidebar--collapsed" frontend/src/assets/css/app.css || echo "No CSS file, checking Tailwind"
```