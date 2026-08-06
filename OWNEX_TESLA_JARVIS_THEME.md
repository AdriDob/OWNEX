# OWNEX Tesla/Jarvis Theme — UI Dark Profesional con Animaciones

## 🎀 VISIÓN

OWNEX ahora tiene una UI unificada estilo Tesla/Jarvis:
- **Dark** — Fondos oscuros profesionales
- **Tech-forward** — Acentos rojo Tesla y azul Jarvis
- **Smooth** — Animaciones fluidas y elegantes
- **Professional** — Diseño minimalista y limpio
- **Modern** — Efectos glass, glow, gradient

---

## 🎨 PALETA DE COLORES

### Primary Colors (Tesla/Jarvis Dark)

**Backgrounds:**
- `--bg-primary: #0a0a0a` — Negro puro
- `--bg-secondary: #111111` — Gris muy oscuro
- `--bg-tertiary: #1a1a1a` — Gris oscuro
- `--bg-elevated: #222222` — Gris medio
- `--bg-hover: #2a2a2a` — Gris hover

**Accents:**
- `--accent-primary: #e31937` — Tesla Red
- `--accent-secondary: #00d4ff` — Jarvis Blue
- `--accent-tertiary: #00ff88` — Success Green
- `--accent-warning: #ffaa00` — Warning Orange
- `--accent-error: #ff3366` — Error Red

**Text:**
- `--text-primary: #ffffff` — Blanco puro
- `--text-secondary: #b0b0b0` — Gris claro
- `--text-tertiary: #707070` — Gris medio
- `--text-muted: #505050` — Gris oscuro

**Borders:**
- `--border-primary: #333333` — Gris oscuro
- `--border-secondary: #444444` — Gris medio
- `--border-accent: var(--accent-primary)` — Tesla Red
- `--border-success: var(--accent-tertiary)` — Success Green
- `--border-warning: var(--accent-warning)` — Warning Orange
- `--border-error: var(--accent-error)` — Error Red

---

## ✨ EFECTOS ESPECIALES

### Glow Effects

**Primary Glow:**
```css
--glow-primary: 0 0 20px rgba(227, 25, 55, 0.5);
```

**Secondary Glow:**
```css
--glow-secondary: 0 0 20px rgba(0, 212, 255, 0.5);
```

**Success Glow:**
```css
--glow-success: 0 0 20px rgba(0, 255, 136, 0.5);
```

**Warning Glow:**
```css
--glow-warning: 0 0 20px rgba(255, 170, 0, 0.5);
```

**Error Glow:**
```css
--glow-error: 0 0 20px rgba(255, 51, 102, 0.5);
```

### Glass Effect

```css
--glass-bg: rgba(26, 26, 26, 0.8);
--glass-border: rgba(255, 255, 255, 0.1);
--glass-blur: 20px;
```

### Gradients

**Primary Gradient:**
```css
--gradient-primary: linear-gradient(135deg, var(--accent-primary) 0%, #ff4d6a 100%);
```

**Secondary Gradient:**
```css
--gradient-secondary: linear-gradient(135deg, var(--accent-secondary) 0%, #00aaff 100%);
```

**Success Gradient:**
```css
--gradient-success: linear-gradient(135deg, var(--accent-tertiary) 0%, #00cc66 100%);
```

**Dark Gradient:**
```css
--gradient-dark: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
```

---

## 🎬 SISTEMA DE ANIMACIONES

### Tipos de Animaciones

**Fade:**
- `fade_in` — Opacidad 0 → 1
- `fade_out` — Opacidad 1 → 0

**Slide:**
- `slide_in_left` — Desliza desde izquierda
- `slide_in_right` — Desliza desde derecha
- `slide_in_up` — Desliza desde abajo
- `slide_in_down` — Desliza desde arriba
- `slide_out_left` — Desliza hacia izquierda
- `slide_out_right` — Desliza hacia derecha
- `slide_out_up` — Desliza hacia arriba
- `slide_out_down` — Desliza hacia abajo

**Scale:**
- `scale_in` — Escala 0.8 → 1
- `scale_out` — Escala 1 → 0.8

**Effects:**
- `pulse` — Pulso de opacidad
- `glow` — Pulso de glow
- `shimmer` — Shimmer effect
- `glitch` — Glitch effect (para errores)
- `spin` — Rotación continua
- `bounce` — Rebote
- `shake` — Vibración
- `float` — Flotación suave
- `drift` — Deriva horizontal
- `wave` — Movimiento de onda
- `ripple` — Efecto ripple
- `explode` — Explosión
- `implode` — Implosión

### Duraciones

- `INSTANT: 0ms`
- `FAST: 150ms`
- `NORMAL: 300ms`
- `SLOW: 500ms`
- `VERY_SLOW: 1000ms`

### Easing Functions

- `LINEAR` — Lineal
- `EASE_IN` — Aceleración
- `EASE_OUT` — Desaceleración
- `EASE_IN_OUT` — Aceleración + desaceleración
- `EASE_QUAD_IN` — Cuadrática aceleración
- `EASE_QUAD_OUT` — Cuadrática desaceleración
- `EASE_QUAD_IN_OUT` — Cuadrática aceleración + desaceleración
- `EASE_CUBIC_IN` — Cúbica aceleración
- `EASE_CUBIC_OUT` — Cúbica desaceleración
- `EASE_CUBIC_IN_OUT` — Cúbica aceleración + desaceleración
- `EASE_ELASTIC_OUT` — Elástico con rebote
- `EASE_BACK_OUT` — Back con rebote

---

## 🌟 JARVIS BACKGROUND

**Componente animado estilo Jarvis:**

**Características:**
- Grid overlay animado (Tesla red)
- 50 partículas flotantes (Tesla red)
- Scanline vertical animado
- Vignette effect
- Mouse tracking (opcional)

**Efectos:**
- Grid se mueve lentamente (20s loop)
- Partículas flotan aleatoriamente
- Scanline recorre pantalla cada 8s
- Vignette oscurece bordes

---

## 🎨 COMPONENTES UI

### Utility Classes

**Animaciones:**
```css
.animate-fade-in
.animate-fade-out
.animate-slide-in-left
.animate-slide-in-right
.animate-slide-in-up
.animate-slide-in-down
.animate-scale-in
.animate-scale-out
.animate-pulse
.animate-glow
.animate-shimmer
.animate-glitch
.animate-spin
.animate-bounce
.animate-shake
.animate-float
.animate-drift
```

**Glass Effect:**
```css
.glass
```

**Gradient Text:**
```css
.gradient-text
```

**Glow Effects:**
```css
.glow-primary
.glow-secondary
.glow-success
.glow-warning
.glow-error
```

### Button Styles

**Primary Button:**
```css
.btn-primary
```
- Background: Tesla Red gradient
- Hover: Lift + glow
- Transition: 150ms

**Secondary Button:**
```css
.btn-secondary
```
- Background: Elevated gray
- Border: Primary border
- Hover: Border change

### Card Styles

```css
.card
```
- Background: Secondary
- Border: Primary
- Hover: Border change + shadow increase
- Transition: 300ms

### Input Styles

```css
.input
```
- Background: Tertiary
- Border: Primary
- Focus: Tesla Red border + glow
- Transition: 150ms

### Status Indicators

```css
.status-online  /* Green glow */
.status-offline /* Gray */
.status-warning /* Orange glow */
.status-error   /* Red glow */
```

### Loading Spinner

```css
.spinner
```
- Border: Primary
- Border-top: Tesla Red
- Animation: Spin 1s infinite

### Progress Bar

```css
.progress-bar
.progress-fill
```
- Background: Tertiary
- Fill: Tesla Red gradient
- Transition: 300ms
- Glow effect

### Badge

```css
.badge
.badge-primary
.badge-secondary
.badge-success
.badge-warning
.badge-error
```

---

## 🚀 CÓMO USAR

### 1. Aplicar Tema

**Ya está importado en main.ts:**
```typescript
import './styles/tesla-jarvis-theme.css'
```

### 2. Usar Variables CSS

```css
.my-component {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  box-shadow: var(--shadow-md);
}
```

### 3. Aplicar Animaciones

```vue
<template>
  <div class="card animate-fade-in">
    <h1 class="gradient-text">OWNEX</h1>
  </div>
</template>
```

### 4. Usar Jarvis Background

```vue
<template>
  <div class="flex h-screen w-screen">
    <JarvisBackground />
    <YourContent />
  </div>
</template>

<script setup>
import JarvisBackground from '@/components/JarvisBackground.vue'
</script>
```

### 5. Usar Sistema de Animaciones

```typescript
import { getAnimation, getAnimationCss } from '@/utils/animations'

// Get animation config
const anim = getAnimation('pulse')

// Get CSS string
const css = getAnimationCss('pulse')
// Returns: "pulse 2s ease-in-out infinite 0s 1 normal forwards"
```

---

## 💎 EJEMPLOS DE UI

### Dashboard Card

```vue
<template>
  <div class="card animate-fade-in glass">
    <h2 class="gradient-text">Revenue</h2>
    <div class="progress-bar">
      <div class="progress-fill" style="width: 75%"></div>
    </div>
    <button class="btn-primary">View Details</button>
  </div>
</template>
```

### Status Indicator

```vue
<template>
  <div class="flex items-center gap-2">
    <div class="w-2 h-2 rounded-full status-online animate-pulse"></div>
    <span class="text-secondary">Online</span>
  </div>
</template>
```

### Glowing Button

```vue
<template>
  <button class="btn-primary glow-primary animate-glow">
    Activate
  </button>
</template>
```

### Alert with Glitch

```vue
<template>
  <div class="card border-error animate-glitch">
    <h3 class="text-error">Error Detected</h3>
    <p class="text-secondary">System failure detected</p>
  </div>
</template>
```

---

## 🎯 ESTRATEGIA DE IMPLEMENTACIÓN

### Fase 1: Tema Base (Completado)
- ✅ Tesla/Jarvis color palette
- ✅ CSS variables
- ✅ Utility classes
- ✅ Animations system
- ✅ Jarvis background

### Fase 2: Migración de Componentes (Próximo)
- Migrar cards existentes al nuevo tema
- Migrar buttons al nuevo tema
- Migrar inputs al nuevo tema
- Migrar badges al nuevo tema
- Aplicar animaciones a transiciones

### Fase 3: Componentes Específicos (Próximo)
- Crear componentes Tesla-styled
- Crear componentes Jarvis-styled
- Animaciones específicas por sección
- Efectos de hover y focus mejorados

### Fase 4: Refinamiento (Próximo)
- Ajustar tiempos de animación
- Optimizar performance
- Acessibility checks
- Responsive design

---

## 💎 CONCLUSIÓN

**OWNEX ahora tiene:**
- ✅ Tema Tesla/Jarvis dark profesional
- ✅ Paleta de colores unificada
- ✅ Sistema de animaciones completo
- ✅ Jarvis background animado
- ✅ Utility classes reutilizables
- ✅ Efectos glow, glass, gradient
- ✅ Transiciones suaves

**La UI es:**
- Dark — Fondos oscuros profesionales
- Tech-forward — Acentos Tesla Red y Jarvis Blue
- Smooth — Animaciones fluidas y elegantes
- Professional — Diseño minimalista y limpio
- Modern — Efectos glass, glow, gradient

**Estilo Jarvis/Tesla logrado.**
