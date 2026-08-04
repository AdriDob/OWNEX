<script setup lang="ts">
/**
 * ParticleField — Lightweight canvas particle animation
 * Renders 60 drifting particles using requestAnimationFrame.
 * No external dependencies (pure Canvas 2D).
 * Falls back to empty div when reduced-motion is active.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useReducedMotion } from '@/shared/composables/useReducedMotion'

const { shouldReduce } = useReducedMotion()
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animFrameId: number | null = null

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  opacity: number
  life: number
  maxLife: number
}

const PARTICLE_COUNT = 60
const particles: Particle[] = []

function initParticles(width: number, height: number) {
  particles.length = 0
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: -Math.random() * 0.4 - 0.1,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.1,
      life: 0,
      maxLife: Math.random() * 200 + 100,
    })
  }
}

function drawParticles(ctx: CanvasRenderingContext2D, width: number, height: number) {
  ctx.clearRect(0, 0, width, height)

  for (const p of particles) {
    p.life++
    p.x += p.vx
    p.y += p.vy
    p.opacity = Math.max(0, 0.4 * (1 - p.life / p.maxLife))

    ctx.fillStyle = `rgba(255, 255, 255, ${p.opacity})`
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
    ctx.fill()

    // Reset particle
    if (p.life >= p.maxLife || p.y < -10 || p.x < -10 || p.x > width + 10) {
      p.x = Math.random() * width
      p.y = height + 10
      p.vx = (Math.random() - 0.5) * 0.3
      p.vy = -Math.random() * 0.4 - 0.1
      p.size = Math.random() * 2 + 1
      p.life = 0
      p.maxLife = Math.random() * 200 + 100
    }
  }
}

function loop(ctx: CanvasRenderingContext2D, width: number, height: number) {
  drawParticles(ctx, width, height)
  animFrameId = requestAnimationFrame(() => loop(ctx, width, height))
}

function resizeCanvas() {
  if (!canvasRef.value) return
  const dpr = window.devicePixelRatio || 1
  const w = window.innerWidth
  const h = window.innerHeight
  canvasRef.value.width = w * dpr
  canvasRef.value.height = h * dpr
  canvasRef.value.style.width = w + 'px'
  canvasRef.value.style.height = h + 'px'
  const ctx = canvasRef.value.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)
  initParticles(w, h)
}

onMounted(() => {
  if (shouldReduce() || !canvasRef.value) return

  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  loop(ctx, window.innerWidth, window.innerHeight)
})

onUnmounted(() => {
  if (animFrameId !== null) cancelAnimationFrame(animFrameId)
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<template>
  <canvas
    v-if="!shouldReduce()"
    ref="canvasRef"
    class="absolute inset-0 w-full h-full pointer-events-none"
    aria-hidden="true"
  />
  <div v-else class="absolute inset-0 bg-gradient-to-b from-black to-background" aria-hidden="true" />
</template>
