# OWNEX Efectos Especiales Recomendados

## 🎀 ESTRATEGIA

OWNEX tiene estilo Tesla/Jarvis: dark, tech-forward, profesional, smooth.
Los efectos deben:
- Encajar con el estilo
- Mejorar UX sin distraer
- Ser profesionales pero divertidos
- Tener buen performance

---

## 🌟 TOP 10 EFECTOS RECOMENDADOS

### 1. Ripple Click Effect (Prioridad: ALTA)

**Descripción:**
Efecto ripple (onda) al hacer click en botones/cards.

**Por qué:**
- Feedback táctil visual
- Estandar en mobile
- Profesional pero sutil
- Bajo costo de performance

**Implementación:**
```css
.ripple {
  position: relative;
  overflow: hidden;
}

.ripple::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  pointer-events: none;
  background-image: radial-gradient(circle, var(--accent-primary) 10%, transparent 10.01%);
  background-repeat: no-repeat;
  background-position: 50%;
  transform: scale(10, 10);
  opacity: 0;
  transition: transform 0.5s, opacity 1s;
}

.ripple:active::after {
  transform: scale(0, 0);
  opacity: 0.3;
  transition: 0s;
}
```

**Uso:**
- Botones primary/secondary
- Cards clickeables
- Navigation items

---

### 2. Magnetic Buttons (Prioridad: ALTA)

**Descripción:**
Botones que "atraen" el cursor cuando está cerca.

**Por qué:**
- Interactivo y moderno
- Feedback hover mejorado
- Sutil pero noticeable
- Tesla/Jarvis feel

**Implementación:**
```vue
<template>
  <button
    class="magnetic-btn"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
    :style="buttonStyle"
  >
    <span class="btn-content">Activate</span>
  </button>
</template>

<script setup>
import { ref } from 'vue'

const buttonStyle = ref({ transform: 'translate(0, 0)' })

const handleMouseMove = (e) => {
  const rect = e.target.getBoundingClientRect()
  const x = e.clientX - rect.left - rect.width / 2
  const y = e.clientY - rect.top - rect.height / 2
  buttonStyle.value.transform = `translate(${x * 0.3}px, ${y * 0.3}px)`
}

const handleMouseLeave = () => {
  buttonStyle.value.transform = 'translate(0, 0)'
}
</script>

<style scoped>
.magnetic-btn {
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.btn-content {
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
</style>
```

**Uso:**
- Botones primary en hero sections
- Call-to-action buttons
- Botones importantes

---

### 3. 3D Card Hover (Prioridad: ALTA)

**Descripción:**
Cards con efecto 3D al hover (perspectiva + rotation).

**Por qué:**
- Elegante y profesional
- Profundidad visual
- Moderno y tech-forward
- Buen para showcasing

**Implementación:**
```vue
<template>
  <div
    class="card-3d"
    @mousemove="handleMouseMove"
    @mouseleave="handleMouseLeave"
    :style="cardStyle"
  >
    <div class="card-content">
      <h3>Card Title</h3>
      <p>Card content</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const cardStyle = ref({
  transform: 'perspective(1000px) rotateX(0) rotateY(0)',
})

const handleMouseMove = (e) => {
  const rect = e.target.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const centerX = rect.width / 2
  const centerY = rect.height / 2
  const rotateX = (y - centerY) / 10
  const rotateY = (centerX - x) / 10

  cardStyle.value.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`
}

const handleMouseLeave = () => {
  cardStyle.value.transform = 'perspective(1000px) rotateX(0) rotateY(0)'
}
</script>

<style scoped>
.card-3d {
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  transform-style: preserve-3d;
}

.card-content {
  transform: translateZ(20px);
}
</style>
```

**Uso:**
- Dashboard cards
- Feature cards
- Status cards

---

### 4. Holographic Scanline (Prioridad: MEDIA)

**Descripción:**
Efecto holográfico con scanline + glitch + glow.

**Por qué:**
- Perfecto para estilo Jarvis
- Tech-forward
- Sci-fi feel
- Distintivo

**Implementación:**
```css
.holographic {
  position: relative;
  overflow: hidden;
}

.holographic::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    transparent 50%,
    rgba(0, 212, 255, 0.1) 50%,
    transparent 51%
  );
  background-size: 100% 4px;
  animation: holographicScan 2s linear infinite;
  pointer-events: none;
}

.holographic::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(0, 212, 255, 0.1),
    transparent
  );
  animation: holographicGlitch 0.3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes holographicScan {
  0% {
    background-position: 0 0;
  }
  100% {
    background-position: 0 4px;
  }
}

@keyframes holographicGlitch {
  0%, 100% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}
```

**Uso:**
- Critical alerts
- Status indicators
- Loading states
- Hero elements

---

### 5. Success Confetti (Prioridad: MEDIA)

**Descripción:**
Explosión de confeti al completar tareas con éxito.

**Por qué:**
- Feedback positivo claro
- Celebratorio pero profesional
- Morale booster
- Tech feel (partículas digitales)

**Implementación:**
```vue
<template>
  <div v-if="showConfetti" class="confetti-container">
    <div
      v-for="i in 50"
      :key="i"
      class="confetti-particle"
      :style="confettiStyle(i)"
    ></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const showConfetti = ref(false)

const confettiStyle = (index) => {
  const colors = ['#e31937', '#00d4ff', '#00ff88', '#ffaa00']
  const color = colors[Math.floor(Math.random() * colors.length)]
  const x = Math.random() * 100
  const y = Math.random() * 100
  const duration = Math.random() * 2 + 1
  const delay = Math.random() * 0.5

  return {
    left: `${x}%`,
    top: `${y}%`,
    backgroundColor: color,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`,
  }
}

const triggerConfetti = () => {
  showConfetti.value = true
  setTimeout(() => {
    showConfetti.value = false
  }, 3000)
}
</script>

<style scoped>
.confetti-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9999;
}

.confetti-particle {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  animation: confettiFall var(--animationDuration) ease-out forwards;
  animation-delay: var(--animation-delay);
}

@keyframes confettiFall {
  0% {
    transform: translateY(-100vh) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(100vh) rotate(720deg);
    opacity: 0;
  }
}
</style>
```

**Uso:**
- Completar tareas importantes
- Login exitoso
- Guardar cambios
- Activar features

---

### 6. Error Shake (Prioridad: MEDIA)

**Descripción:**
Vibración/shake en elementos con error.

**Por qué:**
- Feedback negativo claro
- Alert visual instantáneo
- Sutil pero noticeable
- Standard UX pattern

**Implementación:**
```css
.error-shake {
  animation: errorShake 0.5s ease-in-out;
}

@keyframes errorShake {
  0%, 100% {
    transform: translateX(0);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: translateX(-5px);
  }
  20%, 40%, 60%, 80% {
    transform: translateX(5px);
  }
}
```

**Uso:**
- Form validation errors
- API errors
- Failed operations
- Invalid inputs

---

### 7. Cursor Trail (Prioridad: BAJA)

**Descripción:**
Estela de partículas que sigue el cursor.

**Por qué:**
- Tech feel
- Interactivo
- Sutil
- Customizable

**Implementación:**
```vue
<template>
  <div class="cursor-trail">
    <div
      v-for="(point, i) in trailPoints"
      :key="i"
      class="trail-point"
      :style="trailStyle(point, i)"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const trailPoints = ref([])
const maxPoints = 20

const handleMouseMove = (e) => {
  trailPoints.value.unshift({ x: e.clientX, y: e.clientY })
  if (trailPoints.value.length > maxPoints) {
    trailPoints.value.pop()
  }
}

const trailStyle = (point, index) => {
  const opacity = 1 - (index / maxPoints)
  const size = 6 - (index / maxPoints) * 4
  return {
    left: `${point.x}px`,
    top: `${point.y}px`,
    width: `${size}px`,
    height: `${size}px`,
    opacity,
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
})
</script>

<style scoped>
.cursor-trail {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 9998;
}

.trail-point {
  position: absolute;
  background: var(--accent-primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--accent-primary);
  transform: translate(-50%, -50%);
  transition: opacity 0.1s ease;
}
</style>
```

**Uso:**
- Global (toda la app)
- Hero sections
- Landing pages

---

### 8. Morphing Gradients (Prioridad: BAJA)

**Descripción:**
Gradientes que cambian suavemente de color.

**Por qué:**
- Animación suave
- Elegante
- Profesional
- Bajo performance cost

**Implementación:**
```css
.morphing-gradient {
  background: linear-gradient(
    45deg,
    var(--accent-primary),
    var(--accent-secondary),
    var(--accent-tertiary),
    var(--accent-primary)
  );
  background-size: 400% 400%;
  animation: morphGradient 10s ease infinite;
}

@keyframes morphGradient {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}
```

**Uso:**
- Hero backgrounds
- Accent backgrounds
- Button gradients
- Card backgrounds

---

### 9. Sound Effects (Prioridad: OPCIONAL)

**Descripción:**
Sonidos de UI (click, hover, success, error).

**Por qué:**
- Feedback auditivo
- Más inmersivo
- Aumenta percepción de calidad
- Toggleable (no intrusivo)

**Implementación:**
```typescript
// sound-effects.ts
export const playSound = (type: 'click' | 'hover' | 'success' | 'error') => {
  const audio = new Audio()

  switch (type) {
    case 'click':
      audio.src = '/sounds/click.mp3'
      break
    case 'hover':
      audio.src = '/sounds/hover.mp3'
      break
    case 'success':
      audio.src = '/sounds/success.mp3'
      break
    case 'error':
      audio.src = '/sounds/error.mp3'
      break
  }

  audio.volume = 0.3
  audio.play().catch(() => {
    // Ignore autoplay errors
  })
}
```

**Uso:**
- Botones click
- Hover en elementos importantes
- Success/feedback moments
- Toggle en settings

---

### 10. Parallax Layers (Prioridad: BAJA)

**Descripción:**
Múltiples capas que se mueven a diferentes velocidades.

**Por qué:**
- Profundidad visual
- Premium feel
- Tech-forward
- Smooth

**Implementación:**
```vue
<template>
  <div class="parallax-container" @mousemove="handleMouseMove">
    <div class="parallax-layer layer-1" :style="layer1Style"></div>
    <div class="parallax-layer layer-2" :style="layer2Style"></div>
    <div class="parallax-layer layer-3" :style="layer3Style"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const layer1Style = ref({ transform: 'translate(0, 0)' })
const layer2Style = ref({ transform: 'translate(0, 0)' })
const layer3Style = ref({ transform: 'translate(0, 0)' })

const handleMouseMove = (e) => {
  const x = (e.clientX / window.innerWidth - 0.5) * 20
  const y = (e.clientY / window.innerHeight - 0.5) * 20

  layer1Style.value.transform = `translate(${x * 0.5}px, ${y * 0.5}px)`
  layer2Style.value.transform = `translate(${x * 1}px, ${y * 1}px)`
  layer3Style.value.transform = `translate(${x * 2}px, ${y * 2}px)`
}
</script>

<style scoped>
.parallax-container {
  position: relative;
  overflow: hidden;
}

.parallax-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transition: transform 0.3s ease-out;
}

.layer-1 {
  z-index: 1;
}

.layer-2 {
  z-index: 2;
}

.layer-3 {
  z-index: 3;
}
</style>
```

**Uso:**
- Hero sections
- Dashboard backgrounds
- Feature showcases

---

## 🎯 PRIORIDADES DE IMPLEMENTACIÓN

### Fase 1: Inmediato (Alta Prioridad)
1. ✅ Ripple Click Effect
2. ✅ Magnetic Buttons
3. ✅ 3D Card Hover
4. ✅ Error Shake

### Fase 2: Corto Plazo (Media Prioridad)
5. ✅ Holographic Scanline
6. ✅ Success Confetti
7. ✅ Morphing Gradients

### Fase 3: Largo Plazo (Baja Prioridad / Opcional)
8. ⚡ Cursor Trail
9. ⚡ Sound Effects (con toggle)
10. ⚡ Parallax Layers

---

## 💎 RECOMENDACIÓN FINAL

**Implementar primero:**
1. **Ripple Click Effect** — Feedback básico pero efectivo
2. **Magnetic Buttons** — Interactivo y moderno
3. **3D Card Hover** — Elegante y profesional
4. **Error Shake** — Feedback de error claro

**Luego:**
5. **Holographic Scanline** — Jarvis style
6. **Success Confetti** — Feedback positivo
7. **Morphing Gradients** — Animación suave

**Opcional (si hay tiempo):**
8. **Cursor Trail** — Tech feel
9. **Sound Effects** — Con toggle en settings
10. **Parallax Layers** — Profundidad visual

**Estos efectos encajan perfectamente con el estilo Tesla/Jarvis y mejoran la UX sin distraer.**
