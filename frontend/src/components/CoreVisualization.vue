<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useThemeEngine } from '@/composables/useThemeEngine'

const { currentTheme } = useThemeEngine()

const modules = [
  { id: 'opportunity', name: 'Opportunity Engine', icon: '🎯', angle: 0, distance: 140 },
  { id: 'automation', name: 'Automation', icon: '⚙️', angle: 45, distance: 140 },
  { id: 'ai', name: 'AI', icon: '🧠', angle: 90, distance: 140 },
  { id: 'investment', name: 'Investment', icon: '📈', angle: 135, distance: 140 },
  { id: 'revenue', name: 'Revenue', icon: '💰', angle: 180, distance: 140 },
  { id: 'knowledge', name: 'Knowledge', icon: '📚', angle: 225, distance: 140 },
  { id: 'security', name: 'Security', icon: '🛡️', angle: 270, distance: 140 },
  { id: 'memory', name: 'Memory', icon: '🧮', angle: 315, distance: 140 },
  { id: 'devtools', name: 'Dev Tools', icon: '🛠️', angle: 360, distance: 140 },
]

let animationId: number | null = null
const rotationSpeed = 0.3
const particleCount = 40
const particles = ref<Array<{ x: number; y: number; size: number; opacity: number; speed: number }>>([])

const canvasRef = ref<HTMLCanvasElement | null>(null)
const ctxRef = ref<CanvasRenderingContext2D | null>(null)

function initParticles() {
  const canvas = canvasRef.value
  if (!canvas) return
  const width = canvas.width
  const height = canvas.height
  particles.value = Array.from({ length: particleCount }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    size: Math.random() * 2 + 0.5,
    opacity: Math.random() * 0.3 + 0.05,
    speed: Math.random() * 0.3 + 0.1
  }))
}

function animate() {
  const canvas = canvasRef.value
  const ctx = ctxRef.value
  if (!canvas || !ctx) return

  const width = canvas.width
  const height = canvas.height
  const centerX = width / 2
  const centerY = height / 2

  ctx.clearRect(0, 0, width, height)

  // Draw particles
  const theme = currentTheme.value
  const particleColor = theme?.visualization.particleColor || 'rgba(255, 255, 255, 0.08)'

  particles.value.forEach(p => {
    p.y -= p.speed
    if (p.y < 0) {
      p.y = height
      p.x = Math.random() * width
    }
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
    ctx.fillStyle = particleColor
    ctx.globalAlpha = p.opacity
    ctx.fill()
  })
  ctx.globalAlpha = 1

  // Draw orbits and modules
  const orbitColor = theme?.visualization.orbitColor || 'rgba(255, 255, 255, 0.15)'
  const coreColor = theme?.visualization.coreColor || '#E82127'
  const coreGlow = theme?.visualization.coreGlow || 'rgba(232, 33, 39, 0.4)'
  const trailLength = theme?.visualization.trailLength || 20
  const gravityCenter = theme?.visualization.gravityCenter

  // Draw orbit rings
  modules.forEach(m => {
    ctx.beginPath()
    ctx.arc(centerX, centerY, m.distance, 0, Math.PI * 2)
    ctx.strokeStyle = orbitColor
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    ctx.stroke()
    ctx.setLineDash([])
  })

  // Draw trails if enabled
  if (trailLength > 10) {
    modules.forEach(m => {
      const angle = (m.angle * Math.PI) / 180
      for (let i = 1; i <= trailLength; i += 4) {
        const trailAngle = angle - (i * 0.02)
        const tx = centerX + Math.cos(trailAngle) * m.distance
        const ty = centerY + Math.sin(trailAngle) * m.distance
        ctx.beginPath()
        ctx.arc(tx, ty, Math.max(1, 3 - i / 10), 0, Math.PI * 2)
        ctx.fillStyle = orbitColor.replace('0.15', String(0.15 * (1 - i / trailLength)))
        ctx.fill()
      }
    })
  }

  // Draw core glow
  const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 60)
  gradient.addColorStop(0, coreGlow.replace('0.4', '0.3'))
  gradient.addColorStop(0.5, coreGlow.replace('0.4', '0.1'))
  gradient.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.beginPath()
  ctx.arc(centerX, centerY, 60, 0, Math.PI * 2)
  ctx.fillStyle = gradient
  ctx.fill()

  // Draw core
  ctx.beginPath()
  ctx.arc(centerX, centerY, 24, 0, Math.PI * 2)
  const coreGradient = ctx.createRadialGradient(centerX - 4, centerY - 4, 0, centerX, centerY, 24)
  coreGradient.addColorStop(0, '#FFFFFF')
  coreGradient.addColorStop(0.5, coreColor)
  coreGradient.addColorStop(1, coreColor)
  ctx.fillStyle = coreGradient
  ctx.fill()

  // Core ring
  ctx.beginPath()
  ctx.arc(centerX, centerY, 28, 0, Math.PI * 2)
  ctx.strokeStyle = coreColor
  ctx.lineWidth = 2
  ctx.stroke()

  // Draw modules
  modules.forEach(m => {
    const angle = (m.angle * Math.PI) / 180
    const x = centerX + Math.cos(angle) * m.distance
    const y = centerY + Math.sin(angle) * m.distance

    // Module background
    ctx.beginPath()
    ctx.arc(x, y, 36, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(10, 10, 15, 0.9)'
    ctx.fill()
    ctx.strokeStyle = orbitColor
    ctx.lineWidth = 1
    ctx.stroke()

    // Module icon
    ctx.font = '20px system-ui'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(m.icon, x, y - 4)

    // Module name
    ctx.font = '10px "JetBrains Mono", monospace'
    ctx.fillStyle = '#F5F5F5'
    ctx.fillText(m.name, x, y + 22)
  })

  // Rotate modules
  modules.forEach(m => {
    m.angle = (m.angle + rotationSpeed) % 360
  })

  animationId = requestAnimationFrame(animate)
}

function handleResize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const container = canvas.parentElement
  if (!container) return
  const rect = container.getBoundingClientRect()
  canvas.width = rect.width
  canvas.height = rect.height
  initParticles()
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  ctxRef.value = canvas.getContext('2d')
  handleResize()
  window.addEventListener('resize', handleResize)
  animate()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (animationId) cancelAnimationFrame(animationId)
})

const coreStyle = computed(() => {
  const theme = currentTheme.value
  return {
    '--core-color': theme?.visualization.coreColor || '#E82127',
    '--core-glow': theme?.visualization.coreGlow || 'rgba(232, 33, 39, 0.4)',
  }
})
</script>

<template>
  <div class="core-visualization relative w-full h-full min-h-[400px]">
    <canvas
      ref="canvasRef"
      class="absolute inset-0 w-full h-full"
      aria-hidden="true"
    />
    <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div
        class="absolute w-12 h-12 rounded-full"
        :style="coreStyle"
      >
        <div class="w-full h-full rounded-full bg-[var(--core-color)] opacity-90" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.core-visualization {
  background: var(--ownex-bg-deep);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.core-visualization::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(31, 31, 31, 0.3) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31, 31, 31, 0.3) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .core-visualization canvas {
    display: none;
  }
}
</style>