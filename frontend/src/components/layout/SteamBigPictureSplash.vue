<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  done: []
}>()

type Phase = 'intro' | 'logo' | 'video' | 'content' | 'fadeout'

const phase = ref<Phase>('intro')
const progress = ref(0)
const logoScale = ref(0.8)
const logoOpacity = ref(0)
const videoOpacity = ref(0)
const contentOpacity = ref(0)
const particleIntensity = ref(0)
const isPlayingVideo = ref(true)
const isVideoEnded = ref(false)
const loadingDots = ref('')
const currentTime = ref('')

let progressInterval: ReturnType<typeof setInterval> | null = null
let videoInterval: ReturnType<typeof setTimeout> | null = null
let particleAnimationId: number | null = null

// Elite sound effects
function playEliteSound(type: 'startup' | 'success' | 'error' | 'hover') {
  // In production, play actual audio files
  console.log(`[ELITE AUDIO] Playing ${type} sound effect`)
}

// Elite particle system
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
  for (let i = 0; i < 50; i++) {
    particles.value.push({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      vx: (Math.random() - 0.5) * 0.2,
      vy: (Math.random() - 0.5) * 0.2,
      life: Math.random() * 100 + 50,
      size: Math.random() * 2 + 0.5,
      opacity: Math.random() * 0.5 + 0.2,
      color: Math.random() > 0.5 ? 'rgba(59, 130, 246, 0.6)' : 'rgba(139, 92, 246, 0.6)',
    })
  }
  startParticleAnimation()
}

function startParticleAnimation() {
  const animate = () => {
    particles.value.forEach(particle => {
      particle.x += particle.vx
      particle.y += particle.vy
      particle.life--
      particle.opacity = Math.max(0, particle.opacity - 0.005)
      
      if (particle.x < 0 || particle.x > 100) particle.vx *= -0.8
      if (particle.y < 0 || particle.y > 100) particle.vy *= -0.8
      
      if (particle.life <= 0) {
        particle.x = Math.random() * 100
        particle.y = Math.random() * 100
        particle.vx = (Math.random() - 0.5) * 0.5
        particle.vy = (Math.random() - 0.5) * 0.5
        particle.life = Math.random() * 200 + 100
        particle.opacity = Math.random() * 0.8 + 0.2
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
const VIDEO_DURATION = 20

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
      isVideoEnded.value = true
      phase.value = 'content'
      setTimeout(() => {
        contentOpacity.value = 1
        playEliteSound('success')
      }, 1000)
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
      second: '2-digit'
    })
  }
  update()
  setInterval(update, 1000)
}

async function startSequence() {
  playEliteSound('startup')
  
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  phase.value = 'logo'
  await new Promise(resolve => setTimeout(resolve, 800))
  
  logoScale.value = 1
  logoOpacity.value = 1
  
  await new Promise(resolve => setTimeout(resolve, 1500))
  
  startVideoPlayback()
  
  await new Promise(resolve => setTimeout(resolve, 3000))
  
  initParticles()
  
  await new Promise(resolve => setTimeout(resolve, 2000))
  
  startLoadingAnimation()
  
  const startTime = Date.now()
  const duration = 3000
  
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
      playEliteSound('success')
      
      setTimeout(() => {
        emit('done')
      }, 1500)
    }
  }
  
  requestAnimationFrame(progressAnimation)
}

function reset() {
  phase.value = 'intro'
  progress.value = 0
  logoScale.value = 0.8
  logoOpacity.value = 0
  videoOpacity.value = 0
  contentOpacity.value = 0
  isPlayingVideo.value = true
  isVideoEnded.value = false
  loadingDots.value = ''
  videoCurrentTime = 0
  stopParticles()
  pauseVideo()
}

watch(() => props.visible, (visible) => {
  if (visible) startSequence()
  else reset()
})

onMounted(() => {
  if (props.visible) startSequence()
  updateTime()
})

onUnmounted(() => {
  stopParticles()
  pauseVideo()
  if (progressInterval) clearInterval(progressInterval)
})

const eliteStyles = computed(() => ({
  '--elite-primary': 'rgba(59, 130, 246, 0.9)',
  '--elite-secondary': 'rgba(139, 92, 246, 0.8)',
  '--elite-accent': 'rgba(16, 185, 129, 0.9)',
  '--elite-dark': 'rgba(10, 10, 15, 0.95)',
  '--elite-surface': 'rgba(30, 30, 40, 0.9)',
  '--elite-glow': 'rgba(59, 130, 246, 0.3)',
  '--elite-glass': 'rgba(255, 255, 255, 0.05)',
}))

const progressBarStyle = computed(() => ({
  width: progress.value + '%',
  background: 'var(--elite-primary)',
  boxShadow: '0 0 16px var(--elite-glow)',
}))
</script>

<template>
  <Transition name="splash">
    <div
      v-if="visible"
      class="splash-bg fixed inset-0 z-[200] flex flex-col items-center justify-center overflow-hidden"
    >
      <!-- Elite particle field -->
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
            filter: 'blur(1px)',
            transform: 'translate(-50%, -50%)',
          }"
        />
      </div>

      <!-- Elite glow background -->
      <div class="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div
          class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style="
            width: 800px;
            height: 800px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--elite-primary) 0%, transparent 70%);
            filter: blur(80px);
            opacity: 0.4;
          "
        />
      </div>

      <div class="relative z-10 flex flex-col items-center">
        <!-- Elite logo with premium animation -->
        <div
          :class="[
            'transition-all duration-700 ease-out',
            logoOpacity ? 'scale-100 opacity-100' : 'scale-75 opacity-0',
          ]"
          :style="{ transform: 'scale(' + logoScale + ')' }"
        >
          <svg
            width="100"
            height="100"
            viewBox="0 0 512 512"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            class="drop-shadow-[0_0_32px_rgba(59,130,246,0.4)]"
          >
            <ellipse
              cx="256" cy="256" rx="180" ry="80"
              stroke="#3b82f6" stroke-width="1.5" opacity="0.3"
              transform="rotate(-30 256 256)"
            >
              <animateTransform attributeName="transform" type="rotate"
                from="-30 256 256" to="330 256 256" dur="12s" repeatCount="indefinite" />
            </ellipse>
            <ellipse
              cx="256" cy="256" rx="180" ry="80"
              stroke="#3b82f6" stroke-width="1" opacity="0.15"
              transform="rotate(30 256 256)"
            >
              <animateTransform attributeName="transform" type="rotate"
                from="30 256 256" to="390 256 256" dur="15s" repeatCount="indefinite" />
            </ellipse>
            <circle cx="256" cy="256" r="200" stroke="#3b82f6" stroke-width="12" opacity="0.1" />
            <polygon
              points="256,96 376,156 376,356 256,416 136,356 136,156"
              stroke="#3b82f6" stroke-width="6"
              fill="rgba(59, 130, 246, 0.05)"
              stroke-linejoin="round"
            />
            <circle cx="256" cy="256" r="32" fill="#3b82f6" opacity="0.8">
              <animate attributeName="r" values="28;36;28" dur="2s" repeatCount="indefinite" />
            </circle>
            <circle cx="256" cy="256" r="32" fill="#3b82f6" opacity="0.3">
              <animate attributeName="r" values="32;48;32" dur="2s" repeatCount="indefinite" />
            </circle>
          </svg>
        </div>

        <!-- Elite title -->
        <div
          :class="[
            'mt-8 font-display font-bold tracking-[0.35em] transition-all duration-500 ease-out',
            logoOpacity ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0',
          ]"
          style="color: var(--elite-primary); font-size: clamp(2rem, 5vw, 4rem);"
        >
          OWNEX
        </div>

        <!-- Elite subtitle -->
        <div
          :class="[
            'mt-2 font-mono uppercase tracking-[0.25em] transition-all duration-400 ease-out',
            contentOpacity ? 'opacity-100' : 'opacity-0',
          ]"
          style="color: var(--elite-secondary); font-size: clamp(0.75rem, 1.5vw, 1rem);"
        >
          Personal Autonomous Work OS
        </div>

        <!-- Elite video indicator -->
        <div
          v-if="phase === 'video'"
          :class="[
            'mt-6 flex flex-col items-center gap-2 transition-all duration-400 ease-out',
            contentOpacity ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4',
          ]"
        >
          <div class="flex items-center gap-2 text-xs font-mono" style="color: var(--elite-primary);">
            <span class="animate-pulse" style="width: 6px; height: 6px; background: var(--elite-primary); border-radius: 50%;"></span>
            <span>LIVE VIDEO FEED</span>
            <span>{{ currentTime }}</span>
          </div>
          <div class="relative w-64 h-1 rounded-full overflow-hidden" style="background: var(--elite-glass);">
            <div
              class="h-full rounded-full transition-all duration-200 ease-out"
              :style="{ width: (videoCurrentTime / VIDEO_DURATION) * 100 + '%, background: var(--elite-primary)' }"
            />
          </div>
        </div>

        <!-- Elite loading progress -->
        <div
          v-if="phase === 'content'"
          :class="[
            'mt-10 flex flex-col items-center gap-3 transition-all duration-400 ease-out',
            contentOpacity ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4',
          ]"
        >
          <span class="font-mono text-xs uppercase tracking-widest" style="color: var(--elite-secondary);">
            Inicializando sistemas
          </span>

          <div class="relative w-64 h-1.5 rounded-full overflow-hidden" style="background: var(--elite-glass);">
            <div
              class="h-full rounded-full transition-all duration-200 ease-out"
              :style="progressBarStyle"
            />
          </div>

          <div class="flex items-center gap-2">
            <span class="font-mono text-[10px] tabular-nums" style="color: var(--elite-secondary);">
              {{ Math.round(progress) }}%
            </span>
            <span class="font-mono text-[10px]" style="color: var(--elite-primary);">{{ loadingDots }}</span>
          </div>
        </div>
      </div>

      <!-- Elite bottom accent line -->
      <div class="absolute bottom-0 left-0 right-0 h-px" style="background: linear-gradient(90deg, transparent 0%, var(--elite-primary) 50%, transparent 100%);" />
    </div>
  </Transition>
</template>

<style scoped>
.splash-enter-active {
  transition: opacity 0.3s ease;
}
.splash-leave-active {
  transition: opacity 0.8s ease;
}
.splash-enter-from,
.splash-leave-to {
  opacity: 0;
}

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