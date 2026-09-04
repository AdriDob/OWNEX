<script setup lang="ts">
/**
 * MissionControlView — The main Mission Control page
 *
 * Replaces the old setup guide with a real-time system readiness dashboard.
 * Features:
 *   - System Readiness Score (ProgressRing)
 *   - "Prepare OWNEX" button (big CTA)
 *   - Real-time service check grid
 *   - Auto-detection on mount
 *   - WebSocket live updates
 */
import { onMounted, onUnmounted } from 'vue'
import GlassPanel from '@/shared/components/GlassPanel.vue'
import SkeletonCard from '@/shared/components/SkeletonCard.vue'
import { useReducedMotion } from '@/shared/composables/useReducedMotion'
import { useSpringAnimation } from '@/shared/composables/useSpringAnimation'
import PrepareButton from './components/PrepareButton.vue'
import ReadinessMeter from './components/ReadinessMeter.vue'
import ServiceGrid from './components/ServiceGrid.vue'
import { useReadinessStore } from './stores/readinessStore'

const readiness = useReadinessStore()
const { shouldReduce } = useReducedMotion()
const { animateSpring } = useSpringAnimation()

onMounted(() => {
  // Connect for live updates + run initial scan
  readiness.connectWS()
  readiness.startScan()

  // Animate page title entrance
  if (!shouldReduce()) {
    animateSpring(
      '#mc-title',
      { opacity: [0, 1], transform: ['translateY(-12px)', 'translateY(0)'] },
      { duration: 0.5 },
    )
  }
})

onUnmounted(() => {
  readiness.disconnectWS()
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-8 space-y-8">
    <!-- Header -->
    <div id="mc-title" class="space-y-1">
      <h1 class="text-2xl font-bold text-foreground tracking-tight">Mission Control</h1>
      <p class="text-sm text-muted-foreground">
        Centro de comando de OWNEX — estado del sistema, herramientas y configuración
      </p>
    </div>

    <!-- Readiness Score + Prepare Button -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Score ring -->
      <GlassPanel variant="default" padding="lg" class="flex items-center justify-center">
        <ReadinessMeter
          :score="readiness.score"
          :is-ready="readiness.isReady"
          :is-preparing="readiness.isPreparing"
        />
      </GlassPanel>

      <!-- Prepare button + specs -->
      <GlassPanel variant="default" padding="lg" class="lg:col-span-2 flex flex-col items-center justify-center gap-4">
        <PrepareButton
          :phase="readiness.phase"
          :score="readiness.score"
          @prepare="readiness.prepare()"
          @cancel="readiness.cancelPrepare()"
          @rescan="readiness.startScan()"
        />

        <!-- System specs mini display -->
        <div v-if="readiness.specs.os" class="flex gap-4 text-xs text-muted-foreground mt-2">
          <span>{{ readiness.specs.os }}</span>
          <span class="text-border-light">|</span>
          <span>{{ readiness.specs.ram_gb }} GB RAM</span>
          <span class="text-border-light">|</span>
          <span>{{ readiness.specs.disk_free_gb }} GB libres</span>
        </div>
      </GlassPanel>
    </div>

    <!-- Service checks grid -->
    <div>
      <h2 class="text-lg font-semibold text-foreground mb-3">Servicios detectados</h2>
      <ServiceGrid :checks="readiness.checks" />
    </div>

    <!-- Manual instructions -->
    <GlassPanel variant="light" padding="md" class="space-y-2">
      <h3 class="text-sm font-semibold text-muted-foreground uppercase tracking-wider">¿Qué hace "Prepare OWNEX"?</h3>
      <ul class="text-xs text-muted-foreground space-y-1 list-disc list-inside">
        <li>Detecta e instala herramientas faltantes (Docker, Ollama, FFUF, Nuclei, etc.)</li>
        <li>Configura FCC Proxy, OpenCode y Hermes automáticamente</li>
        <li>Verifica que todos los servicios respondan correctamente</li>
        <li>Muestra el puntaje de readiness en tiempo real</li>
      </ul>
    </GlassPanel>
  </div>
</template>
