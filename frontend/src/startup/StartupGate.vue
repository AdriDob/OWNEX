<script setup lang="ts">
/**
 * StartupGate — Entry point for the cinematic startup
 *
 * Coordinates the 4-phase startup sequence:
 *   1. Splash (particle field + logo reveal)
 *   2. Transition (crossfade to dashboard)
 *   3. Dashboard (children visible)
 *   4. Complete (emits ready state)
 *
 * Usage: wrap the main app layout inside this gate.
 *
 * <StartupGate>
 *   <router-view />
 * </StartupGate>
 */
import { onMounted, provide, ref } from 'vue'
import { useReducedMotion } from '@/shared/composables/useReducedMotion'
import LogoReveal from './components/LogoReveal.vue'
import ParticleField from './components/ParticleField.vue'
import TransitionOverlay from './components/TransitionOverlay.vue'
import { usePreloadData } from './composables/usePreloadData'
import { useStartupSequence } from './composables/useStartupSequence'

const { phase, progress, run } = useStartupSequence()
const { cache: preloadCache, preload } = usePreloadData()
const { shouldReduce } = useReducedMotion()
const startupDone = ref(false)

// Provide preload cache to children
provide('preloadCache', preloadCache)

onMounted(async () => {
  await run(preload)
  startupDone.value = true
})
</script>

<template>
  <div class="relative w-full h-full">
    <!-- Splash layer (visible during loading/splash/transition) -->
    <div
      v-if="phase !== 'dashboard'"
      id="splash-layer"
      class="splash-layer"
      :class="{ 'gpu-layer': !shouldReduce() }"
    >
      <ParticleField />
      <div class="relative z-10 flex flex-col items-center">
        <LogoReveal />

        <!-- Loading indicator -->
        <div v-if="phase === 'splash'" class="mt-8 flex gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-primary/60 dot-pulse" />
          <span class="w-1.5 h-1.5 rounded-full bg-primary/60 dot-pulse" />
          <span class="w-1.5 h-1.5 rounded-full bg-primary/60 dot-pulse" />
        </div>
      </div>
    </div>

    <!-- Dashboard layer (pre-renders behind splash, becomes visible after transition) -->
    <div
      class="dashboard-layer"
      :class="{ visible: startupDone }"
    >
      <slot />
    </div>
  </div>
</template>
