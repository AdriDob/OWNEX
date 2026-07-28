<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import ParticleField from '@/startup/components/ParticleField.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  done: []
}>()

type Phase = 'idle' | 'logo' | 'loading' | 'fadeout'

const phase = ref<Phase>('idle')
const progress = ref(0)
const logoRevealed = ref(false)
const loadingRevealed = ref(false)

let progressInterval: ReturnType<typeof setInterval> | null = null
let fadeTimeout: ReturnType<typeof setTimeout> | null = null
let logoRevealTimeout: ReturnType<typeof setTimeout> | null = null
let loadingRevealTimeout: ReturnType<typeof setTimeout> | null = null
let sequenceTimeout: ReturnType<typeof setTimeout> | null = null

function clearAllTimeouts() {
  if (progressInterval) clearInterval(progressInterval)
  if (fadeTimeout) clearTimeout(fadeTimeout)
  if (logoRevealTimeout) clearTimeout(logoRevealTimeout)
  if (loadingRevealTimeout) clearTimeout(loadingRevealTimeout)
  if (sequenceTimeout) clearTimeout(sequenceTimeout)
  progressInterval = null
  fadeTimeout = null
  logoRevealTimeout = null
  loadingRevealTimeout = null
  sequenceTimeout = null
}

function startSequence() {
  clearAllTimeouts()
  progress.value = 0
  logoRevealed.value = false
  loadingRevealed.value = false
  phase.value = 'logo'

  logoRevealTimeout = setTimeout(() => {
    logoRevealed.value = true
  }, 150)

  sequenceTimeout = setTimeout(() => {
    phase.value = 'loading'
    loadingRevealed.value = true
    progressInterval = setInterval(() => {
      progress.value = Math.min(progress.value + Math.random() * 3 + 0.5, 96)
    }, 200)
  }, 1000)

  fadeTimeout = setTimeout(() => {
    progress.value = 100
    if (progressInterval) clearInterval(progressInterval)
    phase.value = 'fadeout'
    emit('done')
  }, 2200)
}

function reset() {
  clearAllTimeouts()
  phase.value = 'idle'
  progress.value = 0
  logoRevealed.value = false
  loadingRevealed.value = false
}

onMounted(() => {
  if (props.visible) startSequence()
})

onUnmounted(() => {
  clearAllTimeouts()
})

watch(() => props.visible, (v) => {
  if (v) startSequence()
  else reset()
})
</script>

<template>
  <Transition name="splash">
    <div
      v-if="visible"
      class="splash-bg fixed inset-0 z-[200] flex flex-col items-center justify-center overflow-hidden"
    >
      <ParticleField />

      <div class="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div
          class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          style="{
            width: '800px',
            height: '800px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, var(--splash-glow-color) 0%, transparent 70%)',
            filter: 'blur(80px)',
          }"
        />
      </div>

      <div class="relative z-10 flex flex-col items-center">
        <div
          :class="[
            'transition-all duration-500 ease-out',
            logoRevealed ? 'scale-100 opacity-100' : 'scale-75 opacity-0',
          ]"
        >
          <svg
            width="80"
            height="80"
            viewBox="0 0 512 512"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            class="drop-shadow-lg"
            style="filter: drop-shadow(0 0 24px rgba(59, 130, 246, 0.3))"
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
              :class="{ 'animate-pulse': phase === 'loading' }"
            />
            <circle cx="256" cy="256" r="32" fill="#3b82f6" opacity="0.8">
              <animate attributeName="r" values="28;36;28" dur="2s" repeatCount="indefinite" />
            </circle>
            <circle cx="256" cy="256" r="32" fill="#3b82f6" opacity="0.3">
              <animate attributeName="r" values="32;48;32" dur="2s" repeatCount="indefinite" />
            </circle>
          </svg>
        </div>

        <div
          :class="[
            'mt-8 font-display font-bold tracking-[0.35em] text-splash-text transition-all duration-500 ease-out',
            logoRevealed ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0',
          ]"
          style="{
            fontSize: 'var(--splash-title-size)'
          }"
        >
          OWNEX
        </div>

        <div
          :class="[
            'mt-2 font-mono uppercase tracking-[0.25em] transition-all duration-400 ease-out',
            loadingRevealed ? 'opacity-100' : 'opacity-0',
          ]"
          style="{
            fontSize: 'var(--splash-subtitle-size)',
            color: 'var(--splash-text-muted)',
          }"
        >
          Personal Autonomous Work OS
        </div>

        <div
          v-if="phase === 'loading'"
          :class="[
            'mt-10 flex flex-col items-center gap-3 transition-all duration-400 ease-out',
            loadingRevealed ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4',
          ]"
        >
          <span
            class="font-mono text-xs uppercase tracking-widest"
            style="{
              color: 'var(--splash-text-muted)'
            }"
          >
            Inicializando sistemas
          </span>

          <div class="relative w-56 h-1 rounded-full overflow-hidden"
            style="{
              background: 'var(--splash-progress-bg)'
            }"
          >
            <div
              class="h-full rounded-full transition-all duration-200 ease-out"
              :style="{
                width: progress + '%',
                background: 'var(--splash-progress-bar)',
                boxShadow: '0 0 12px rgba(59, 130, 246, 0.4)',
              }"
            />
          </div>

          <span
            class="font-mono text-[10px] tabular-nums"
            style="{
              color: 'var(--splash-text-muted)'
            }"
          >
            {{ Math.round(progress) }}%
          </span>
        </div>
      </div>

      <div class="absolute bottom-0 left-0 right-0 h-px"
        style="{
          background: 'linear-gradient(90deg, transparent 0%, rgba(59, 130, 246, 0.2) 50%, transparent 100%)',
        }"
      />
    </div>
  </Transition>
</template>

<style scoped>
.splash-enter-active {
  transition: opacity 0.3s ease;
}
.splash-leave-active {
  transition: opacity 0.6s ease;
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
}
</style>