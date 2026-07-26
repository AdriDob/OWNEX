<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'done': []
}>()

const phase = ref<'logo' | 'loading' | 'fadeout'>('logo')

onMounted(() => {
  if (!props.visible) return
  phase.value = 'logo'
  setTimeout(() => { phase.value = 'loading' }, 800)
  setTimeout(() => { phase.value = 'fadeout' }, 1800)
  setTimeout(() => { emit('done') }, 2400)
})
</script>

<template>
  <Transition name="splash">
    <div
      v-if="visible"
      class="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-background"
    >
      <!-- OWNEX Logo -->
      <div :class="['transition-all duration-700 ease-out', phase === 'logo' ? 'scale-75 opacity-0' : 'scale-100 opacity-100']">
        <svg
          width="72"
          height="72"
          viewBox="0 0 512 512"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Outer ring -->
          <circle cx="256" cy="256" r="200" stroke="#3b82f6" stroke-width="12" opacity="0.15" />
          <!-- Orbit -->
          <ellipse cx="256" cy="256" rx="180" ry="80" stroke="#3b82f6" stroke-width="2" opacity="0.3" transform="rotate(-30 256 256)">
            <animateTransform attributeName="transform" type="rotate" from="-30 256 256" to="330 256 256" dur="12s" repeatCount="indefinite" />
          </ellipse>
          <ellipse cx="256" cy="256" rx="180" ry="80" stroke="#3b82f6" stroke-width="1" opacity="0.15" transform="rotate(30 256 256)">
            <animateTransform attributeName="transform" type="rotate" from="30 256 256" to="390 256 256" dur="15s" repeatCount="indefinite" />
          </ellipse>
          <!-- Core hexagon -->
          <polygon
            points="256,96 376,156 376,356 256,416 136,356 136,156"
            stroke="#3b82f6"
            stroke-width="6"
            fill="rgba(59, 130, 246, 0.05)"
            :class="phase === 'loading' ? 'animate-pulse' : ''"
          />
          <!-- Inner core -->
          <circle cx="256" cy="256" r="32" fill="#3b82f6" opacity="0.8">
            <animate attributeName="r" values="28;36;28" dur="2s" repeatCount="indefinite" />
          </circle>
          <circle cx="256" cy="256" r="32" fill="#3b82f6" opacity="0.3">
            <animate attributeName="r" values="32;48;32" dur="2s" repeatCount="indefinite" />
          </circle>
        </svg>
      </div>

      <!-- OWNEX text -->
      <div
        :class="[
          'mt-6 font-display text-3xl font-bold tracking-[0.3em] text-foreground transition-all duration-700 ease-out',
          phase === 'logo' ? 'translate-y-4 opacity-0' : 'translate-y-0 opacity-100',
        ]"
      >
        OWNEX
      </div>
      <div
        :class="[
          'mt-1 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/40 transition-all duration-700 delay-200',
          phase === 'loading' ? 'opacity-100' : 'opacity-0',
        ]"
      >
        Personal Autonomous Work OS
      </div>

      <!-- Loading dots -->
      <div v-if="phase === 'loading'" class="mt-8 flex gap-2">
        <span class="h-1.5 w-1.5 rounded-full bg-primary opacity-60 animate-bounce" style="animation-delay: 0s" />
        <span class="h-1.5 w-1.5 rounded-full bg-primary opacity-60 animate-bounce" style="animation-delay: 0.15s" />
        <span class="h-1.5 w-1.5 rounded-full bg-primary opacity-60 animate-bounce" style="animation-delay: 0.3s" />
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.splash-enter-active { transition: opacity 0.3s ease; }
.splash-leave-active { transition: opacity 0.4s ease; }
.splash-enter-from, .splash-leave-to { opacity: 0; }
</style>
