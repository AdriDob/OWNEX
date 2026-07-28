<script setup lang="ts">
/**
 * LogoReveal — OWNEX logo with SVG stroke-draw animation
 * Uses framer-motion/dom spring to animate scale + opacity.
 * The SVG paths draw in (stroke-dashoffset → 0) for the premium feel.
 */
import { ref, onMounted } from 'vue'
import { animate } from 'motion'

const logoLoaded = ref(false)

onMounted(() => {
  // Logo container entrance (scale + opacity)
  const control = animate(
    '#logo-reveal',
    { scale: [0.8, 1], opacity: [0, 1] },
    { type: 'spring', stiffness: 120, damping: 14, duration: 0.6 },
  )
  control.then(() => {
    logoLoaded.value = true
  })
})
</script>

<template>
  <div
    id="logo-reveal"
    class="flex flex-col items-center"
  >
    <!-- Logo SVG with stroke-draw -->
    <svg
      width="72"
      height="72"
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <!-- Outer ring (subtle) -->
      <circle
        cx="256" cy="256" r="200"
        stroke="currentColor" stroke-width="12"
        opacity="0.15"
        class="text-primary"
      />
      <!-- Hexagon core — stroke-draw animation -->
      <polygon
        points="256,96 376,156 376,356 256,416 136,356 136,156"
        stroke="currentColor"
        stroke-width="6"
        fill="rgba(59, 130, 246, 0.05)"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="text-primary"
        :class="{ 'animate-pulse': logoLoaded }"
        stroke-dasharray="800"
        stroke-dashoffset="800"
        style="animation: logo-draw 1.2s ease-out 0.3s forwards"
      />
      <!-- Inner glow core -->
      <circle cx="256" cy="256" r="32" fill="currentColor" opacity="0.8" class="text-primary">
        <animate attributeName="r" values="28;36;28" dur="2s" repeatCount="indefinite" />
      </circle>
      <circle cx="256" cy="256" r="32" fill="currentColor" opacity="0.3" class="text-primary">
        <animate attributeName="r" values="32;48;32" dur="2s" repeatCount="indefinite" />
      </circle>
    </svg>

    <!-- OWNEX text -->
    <div class="mt-6 font-display text-3xl font-bold tracking-[0.3em]">
      <span class="text-primary">OWN</span><span class="text-foreground">EX</span>
    </div>
    <div class="mt-1 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/40">
      Personal Autonomous Work OS
    </div>
  </div>
</template>
