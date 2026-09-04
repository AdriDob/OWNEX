<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  done: []
}>()

type Phase = 'intro' | 'logo' | 'video' | 'content' | 'fadeout'

const phase = ref<Phase>('intro')
const progress = ref(0)
const logoScale = ref(0.82)
const logoOpacity = ref(0)
const contentOpacity = ref(0)
const particleIntensity = ref(0)
const isPlayingVideo = ref(true)
const loadingDots = ref('')
const currentTime = ref('')

// System checks for OWNEX Boot Sequence
const systemChecks = ref([
  { name: 'Backend', status: 'pending' as 'pending' | 'checking' | 'complete' | 'error' },
  { name: 'Providers', status: 'pending' },
  { name: 'Scheduler', status: 'pending' },
  { name: 'Database', status: 'pending' },
  { name: 'Mission Control', status: 'pending' },
  { name: 'Memory', status: 'pending' },
  { name: 'Agents', status: 'pending' },
])

let progressInterval: ReturnType<typeof setInterval> | null = null
let videoInterval: ReturnType<typeof setTimeout> | null = null
let particleAnimationId: number | null = null
let systemCheckInterval: ReturnType<typeof setInterval> | null = null

// OWNEX System Checks
async function runSystemChecks() {
  const checkOrder = [0, 1, 2, 3, 4, 5, 6]

  for (const idx of checkOrder) {
    systemChecks.value[idx].status = 'checking'
    await new Promise((resolve) => setTimeout(resolve, 260 + Math.random() * 360))

    const isHealthy = Math.random() > 0.08
    systemChecks.value[idx].status = isHealthy ? 'complete' : 'error'
    if (!isHealthy) {
      console.warn(`[ARRANQUE] ${systemChecks.value[idx].name} verificación fallida`)
    }
  }
}

// Subtle white/blue particle field (Tesla-minimal, not neon)
interface Particle {
  id: number
  x: number
  y: number
  vx: number
  vy: number
  life: number
  size: number
  opacity: number
  color: string
}

const particles = ref<Particle[]>([])

function initParticles() {
  particles.value = []
  for (let i = 0; i < 32; i++) {
    particles.value.push({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      vx: (Math.random() - 0.5) * 0.16,
      vy: (Math.random() - 0.5) * 0.16,
      life: Math.random() * 100 + 60,
      size: Math.random() * 1.6 + 0.4,
      opacity: Math.random() * 0.35 + 0.1,
      color: Math.random() > 0.6 ? 'rgba(0, 213, 255, 0.5)' : 'rgba(255, 255, 255, 0.4)',
    })
  }
  startParticleAnimation()
}

function startParticleAnimation() {
  const animate = () => {
    particles.value.forEach((particle) => {
      particle.x += particle.vx
      particle.y += particle.vy
      particle.life--
      particle.opacity = Math.max(0, particle.opacity - 0.004)

      if (particle.x < 0 || particle.x > 100) particle.vx *= -0.8
      if (particle.y < 0 || particle.y > 100) particle.vy *= -0.8

      if (particle.life <= 0) {
        particle.x = Math.random() * 100
        particle.y = Math.random() * 100
        particle.vx = (Math.random() - 0.5) * 0.4
        particle.vy = (Math.random() - 0.5) * 0.4
        particle.life = Math.random() * 200 + 100
        particle.opacity = Math.random() * 0.5 + 0.1
      }
    })
    particleAnimationId = requestAnimationFrame(animate)
  }
  animate()
}

function stopParticles() {
  if (particleAnimationId) {
    cancelAnimationFrame(particleAnimationId)
    particleAnimationId = null
  }
}

// Video background simulation
let videoCurrentTime = 0
const VIDEO_DURATION = 16

function startVideoPlayback() {
  isPlayingVideo.value = true
  videoPlayback()
}

function videoPlayback() {
  if (!isPlayingVideo.value) return

  videoInterval = setTimeout(() => {
    videoCurrentTime += 0.016
    if (videoCurrentTime < VIDEO_DURATION) {
      videoPlayback()
    } else {
      isPlayingVideo.value = false
      phase.value = 'content'
      setTimeout(() => {
        contentOpacity.value = 1
      }, 800)
    }
  }, 16)
}

function pauseVideo() {
  isPlayingVideo.value = false
  if (videoInterval) {
    clearTimeout(videoInterval)
    videoInterval = null
  }
}

function startLoadingAnimation() {
  const dots = ['', '.', '..', '...']
  let index = 0
  progressInterval = setInterval(() => {
    loadingDots.value = dots[index % dots.length]
    index++
    if (progress.value >= 100 && progressInterval) {
      clearInterval(progressInterval)
      progressInterval = null
    }
  }, 300)
}

function updateTime() {
  const update = () => {
    const now = new Date()
    currentTime.value = now.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }
  update()
  setInterval(update, 1000)
}

async function startSequence() {
  await new Promise((resolve) => setTimeout(resolve, 1200))

  phase.value = 'logo'
  await new Promise((resolve) => setTimeout(resolve, 700))

  logoScale.value = 1
  logoOpacity.value = 1

  await new Promise((resolve) => setTimeout(resolve, 1600))

  startVideoPlayback()

  await new Promise((resolve) => setTimeout(resolve, 2600))

  initParticles()

  await new Promise((resolve) => setTimeout(resolve, 1800))

  await runSystemChecks()

  startLoadingAnimation()

  const startTime = Date.now()
  const duration = 2600

  function progressAnimation() {
    const elapsed = Date.now() - startTime
    const percentage = Math.min((elapsed / duration) * 100, 100)
    progress.value = percentage

    if (percentage < 100) {
      requestAnimationFrame(progressAnimation)
    } else {
      pauseVideo()
      stopParticles()
      phase.value = 'fadeout'
      setTimeout(() => {
        emit('done')
      }, 1400)
    }
  }

  requestAnimationFrame(progressAnimation)
}

function reset() {
  phase.value = 'intro'
  progress.value = 0
  logoScale.value = 0.82
  logoOpacity.value = 0
  contentOpacity.value = 0
  isPlayingVideo.value = true
  loadingDots.value = ''
  videoCurrentTime = 0
  systemChecks.value.forEach((check) => (check.status = 'pending'))
  stopParticles()
  pauseVideo()
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) startSequence()
    else reset()
  },
)

onMounted(() => {
  if (props.visible) startSequence()
  updateTime()
})

onUnmounted(() => {
  stopParticles()
  pauseVideo()
  if (progressInterval) clearInterval(progressInterval)
})

const ownexTheme = computed(() => ({
  '--ownex-bg': 'var(--ownex-bg-base)',
  '--ownex-surface': 'var(--ownex-bg-base)',
  '--ownex-white': 'var(--ownex-text-primary)',
  '--ownex-muted': 'var(--ownex-text-secondary)',
  '--ownex-cyan': 'var(--ownex-accent)',
  '--ownex-blue': 'var(--ownex-accent)',
  '--ownex-line': 'rgba(255, 255, 255, 0.08)',
  '--ownex-glow': 'rgba(0, 213, 255, 0.22)',
}))

const progressBarStyle = computed(() => ({
  width: progress.value + '%',
  background: 'linear-gradient(90deg, var(--ownex-cyan), var(--ownex-blue))',
  boxShadow: '0 0 14px var(--ownex-glow)',
}))
</script>

<template>
  <Transition name="splash">
    <div
      v-if="visible"
      class="splash-bg fixed inset-0 z-[200] flex flex-col items-center justify-center overflow-hidden"
      :style="ownexTheme"
      style="background: var(--ownex-bg-base)"
    >
      <!-- Subtle white/blue particle field -->
      <div class="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div
          v-for="p in particles"
          :key="p.id"
          class="absolute rounded-full pointer-events-none"
          :style="{
            left: p.x + '%',
            top: p.y + '%',
            width: p.size + 'px',
            height: p.size + 'px',
            background: p.color,
            opacity: p.opacity,
            transform: 'translate(-50%, -50%)',
          }"
        />
      </div>

      <!-- Soft blue ambient glow (Tesla-minimal) -->
      <div class="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div
          class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style="
            width: 720px;
            height: 720px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(0, 213, 255, 0.12) 0%, transparent 65%);
            filter: blur(70px);
            opacity: 0.55;
          "
        />
      </div>

      <div class="relative z-10 flex flex-col items-center">
        <!-- ═══ OWNEX APERTURE NEXUS MARK ═══ -->
        <div
          class="logo-wrap"
          :class="logoOpacity ? 'logo-visible' : ''"
          :style="{ transform: 'scale(' + logoScale + ')' }"
        >
          <svg
            width="150"
            height="150"
            viewBox="0 0 512 512"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="nexusGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="var(--ownex-text-primary)" />
                <stop offset="55%" stop-color="var(--ownex-text-primary)" />
                <stop offset="100%" stop-color="var(--ownex-accent)" />
              </linearGradient>
            </defs>

            <!-- Outer octagonal ring (draws in) -->
            <polygon
              class="draw-ring"
              points="436,256 383.3,128.7 256,76 128.7,128.7 76,256 128.7,383.3 256,436 383.3,383.3"
              stroke="url(#nexusGrad)"
              stroke-width="6"
              fill="none"
              stroke-linejoin="round"
              opacity="0.9"
            >
              <animateTransform attributeName="transform" type="rotate"
                from="0 256 256" to="360 256 256" dur="36s" repeatCount="indefinite" />
            </polygon>

            <!-- Second counter-rotating ring -->
            <polygon
              class="draw-ring slow"
              points="436,256 383.3,128.7 256,76 128.7,128.7 76,256 128.7,383.3 256,436 383.3,383.3"
              stroke="var(--ownex-accent)"
              stroke-width="1.5"
              fill="none"
              stroke-linejoin="round"
              opacity="0.35"
              transform="scale(0.9) translate(28,28)"
            >
              <animateTransform attributeName="transform" type="rotate"
                from="360 256 256" to="0 256 256" dur="60s" repeatCount="indefinite" />
            </polygon>

            <!-- X of conic rays from the core -->
            <line class="draw-x" x1="196" y1="196" x2="316" y2="316" stroke="var(--ownex-text-primary)" stroke-width="10" stroke-linecap="round" opacity="0.85" />
            <line class="draw-x" x1="316" y1="196" x2="196" y2="316" stroke="var(--ownex-text-primary)" stroke-width="10" stroke-linecap="round" opacity="0.85" />

            <!-- Central square node -->
            <rect x="244" y="244" width="24" height="24" rx="3" fill="var(--ownex-accent)">
              <animate attributeName="opacity" values="1;0.45;1" dur="2.2s" repeatCount="indefinite" />
            </rect>

            <!-- Ray breaking the ring (top-right) -->
            <line class="draw-break" x1="383.3" y1="128.7" x2="404" y2="108" stroke="var(--ownex-accent)" stroke-width="6" stroke-linecap="round" />

            <!-- Pulse halo -->
            <circle cx="256" cy="256" r="150" stroke="var(--ownex-accent)" stroke-width="1" fill="none" opacity="0.25">
              <animate attributeName="r" values="140;172;140" dur="3s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.25;0.02;0.25" dur="3s" repeatCount="indefinite" />
            </circle>
          </svg>
        </div>

        <!-- OWNEX wordmark -->
        <div
          class="ownex-title"
          :class="logoOpacity ? 'title-visible' : ''"
        >
          OWNEX
        </div>

        <!-- Subtitle -->
        <div
          class="ownex-subtitle"
          :class="contentOpacity ? 'subtitle-visible' : ''"
        >
          PERSONAL AUTONOMOUS OPERATING SYSTEM
        </div>

        <!-- Live feed indicator -->
        <div
          v-if="phase === 'video'"
          class="mt-6 flex flex-col items-center gap-2 transition-all duration-400 ease-out"
          :class="contentOpacity ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'"
        >
          <div class="flex items-center gap-2 text-xs font-mono" style="color: var(--ownex-muted);">
            <span class="boot-dot"></span>
            <span class="tracking-[0.2em]">INICIALIZANDO</span>
            <span>{{ currentTime }}</span>
          </div>
          <div class="relative w-64 h-px overflow-hidden" style="background: var(--ownex-line);">
            <div
              class="h-full transition-all duration-200 ease-out"
              :style="{ width: (videoCurrentTime / VIDEO_DURATION) * 100 + '%, background: linear-gradient(90deg, var(--ownex-cyan), var(--ownex-blue))' }"
            />
          </div>
        </div>

        <!-- System checks -->
        <div
          v-if="phase === 'content'"
          class="mt-10 flex flex-col items-center gap-4 transition-all duration-400 ease-out"
          :class="contentOpacity ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'"
        >
          <span class="font-mono text-[10px] uppercase tracking-[0.3em]" style="color: var(--ownex-muted);">
            System Check
          </span>

          <div class="flex flex-col gap-2 w-64">
            <div
              v-for="check in systemChecks"
              :key="check.name"
              class="flex items-center justify-between text-[11px] font-mono"
              style="color: var(--ownex-muted);"
            >
              <span>{{ check.name }}</span>
              <span v-if="check.status === 'pending'">●</span>
              <span v-else-if="check.status === 'checking'" class="animate-pulse" style="color: var(--ownex-cyan);">◉</span>
              <span v-else-if="check.status === 'complete'" style="color: var(--ownex-white);">✓</span>
              <span v-else-if="check.status === 'error'" style="color: var(--ownex-blue);">✗</span>
            </div>
          </div>

          <div class="relative w-64 h-[3px] rounded-full overflow-hidden" style="background: var(--ownex-line);">
            <div class="h-full rounded-full transition-all duration-200 ease-out" :style="progressBarStyle" />
          </div>

          <div class="flex items-center gap-2">
            <span class="font-mono text-[10px] tabular-nums" style="color: var(--ownex-muted);">
              {{ Math.round(progress) }}%
            </span>
            <span class="font-mono text-[10px]" style="color: var(--ownex-cyan);">{{ loadingDots }}</span>
          </div>
        </div>
      </div>

      <!-- Bottom accent line -->
      <div class="absolute bottom-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, var(--ownex-cyan) 50%, transparent 100%);" />
    </div>
  </Transition>
</template>

<style scoped>
.splash-bg {
  background: var(--ownex-bg-base);
}

/* ── Logo draw-in animation ── */
.logo-wrap {
  opacity: 0;
  transform: scale(0.82);
  transition: opacity 0.8s ease, transform 0.9s cubic-bezier(0.16, 1, 0.3, 1);
  filter: drop-shadow(0 0 26px var(--ownex-glow));
}
.logo-wrap.logo-visible {
  opacity: 1;
}

.draw-ring {
  stroke-dasharray: 1500;
  stroke-dashoffset: 1500;
  animation: ring-draw 2.2s cubic-bezier(0.6, 0, 0.2, 1) forwards;
}
.draw-ring.slow {
  animation-duration: 3s;
  animation-delay: 0.4s;
}
@keyframes ring-draw {
  to { stroke-dashoffset: 0; }
}

.draw-x {
  stroke-dasharray: 260;
  stroke-dashoffset: 260;
  animation: x-draw 1.1s cubic-bezier(0.6, 0, 0.2, 1) 0.7s forwards;
}
@keyframes x-draw {
  to { stroke-dashoffset: 0; }
}

.draw-break {
  stroke-dasharray: 60;
  stroke-dashoffset: 60;
  animation: break-draw 0.6s ease-out 2.1s forwards;
}
@keyframes break-draw {
  to { stroke-dashoffset: 0; }
}

/* ── Wordmark ── */
.ownex-title {
  margin-top: 34px;
  font-family: 'Space Grotesk', 'Inter', sans-serif;
  font-weight: 700;
  letter-spacing: 0.32em;
  color: var(--ownex-text-primary);
  font-size: clamp(2rem, 5vw, 3.4rem);
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.7s ease, transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
  text-shadow: 0 0 40px rgba(0, 213, 255, 0.25);
}
.ownex-title.title-visible {
  opacity: 1;
  transform: translateY(0);
}

.ownex-subtitle {
  margin-top: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: clamp(0.65rem, 1.3vw, 0.85rem);
  letter-spacing: 0.34em;
  color: var(--ownex-text-secondary);
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.7s ease 0.3s, transform 0.7s ease 0.3s;
}
.ownex-subtitle.subtitle-visible {
  opacity: 1;
  transform: translateY(0);
}

.boot-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ownex-accent);
  animation: boot-pulse 1.4s ease-in-out infinite;
}
@keyframes boot-pulse {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}

/* ── Splash transitions ── */
.splash-enter-active { transition: opacity 0.3s ease; }
.splash-leave-active { transition: opacity 0.8s ease; }
.splash-enter-from,
.splash-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .splash-enter-active,
  .splash-leave-active {
    transition: none;
  }
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
