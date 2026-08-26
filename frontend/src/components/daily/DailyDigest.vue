<script setup lang="ts">
/**
 * Daily Digest — THE single card that answers "what matters today?" (§43, §90).
 * Máximo 5 decisiones ordenadas por dinero. Una acción principal. Cero ruido.
 */
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import { fetchDailyDigest, type DailyDigestState } from '@/services/ownexData'

const digest = ref<DailyDigestState | null>(null)
const loading = ref(true)

const usd = (n: number | undefined | null): string =>
  `$${Math.round(n ?? 0).toLocaleString('es-AR')}`

const typeIcon = computed(() => ({
  opportunity: '🎯',
  execution_review: '⚙️',
  security_finding: '🛡️',
}))

async function load(): Promise<void> {
  loading.value = true
  try {
    digest.value = await fetchDailyDigest()
  } catch {
    /* degradación silenciosa — la página no se rompe si el endpoint falla */
  }
  loading.value = false
}

onMounted(load)
</script>

<template>
  <Card v-if="digest && digest.decisions.length" class="space-y-4 p-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">
        ⚡ Qué importa hoy
      </p>
      <Badge variant="default">{{ digest.counts.pending_decisions }} pendientes</Badge>
    </div>

    <!-- Best Action (THE ONE) -->
    <div
      v-if="digest.best_action"
      class="rounded-lg border border-gold/30 bg-gold/5 p-4"
    >
      <p class="font-mono text-[10px] uppercase tracking-wider text-gold">🔥 Mejor movimiento</p>
      <p class="mt-1 text-sm font-semibold leading-snug">{{ digest.best_action.title }}</p>
      <div class="mt-2 flex items-center gap-3 font-mono text-sm tabular-nums">
        <span v-if="digest.best_action.reward" class="font-semibold text-success">
          {{ usd(digest.best_action.reward) }}
        </span>
        <span class="text-xs text-muted-foreground">{{ digest.best_action.platform || '' }}</span>
        <a
          :href="digest.best_action.url || '#'"
          class="ml-auto rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90"
        >
          {{ digest.best_action.action }}
        </a>
      </div>
    </div>

    <!-- Rest of decisions -->
    <div v-if="digest.decisions.length > 1" class="space-y-1">
      <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Siguiente</p>
      <div
        v-for="(d, i) in digest.decisions.slice(1)"
        :key="i"
        class="flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-surface/40"
      >
        <div class="flex items-center gap-2 min-w-0">
          <span class="shrink-0">{{ typeIcon[d.type] || '📋' }}</span>
          <span class="line-clamp-1 text-sm">{{ d.title }}</span>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <span v-if="d.reward" class="font-mono text-xs tabular-nums text-success">{{ usd(d.reward) }}</span>
          <Badge variant="default" class="text-[9px] uppercase">{{ d.type.replace('_', ' ') }}</Badge>
        </div>
      </div>
    </div>

    <!-- Money summary strip -->
    <div class="grid grid-cols-3 gap-2 rounded-lg border border-border/20 p-3">
      <div class="text-center">
        <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Targets listos</p>
        <p class="font-mono text-base font-semibold tabular-nums">{{ digest.money.ready_to_deliver }}</p>
      </div>
      <div class="text-center">
        <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Públicos</p>
        <p class="font-mono text-base font-semibold tabular-nums">{{ digest.money.public_ready }}</p>
      </div>
      <div class="text-center">
        <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Potencial</p>
        <p class="font-mono text-base font-semibold tabular-nums">{{ usd(digest.money.total_potential_usd) }}</p>
      </div>
    </div>
  </Card>

  <!-- Empty state -->
  <Card v-else-if="!loading" class="space-y-2 p-5 text-center">
    <p class="text-sm text-muted-foreground">Sin decisiones pendientes</p>
    <p class="text-xs text-muted-foreground/60">El sistema está corriendo. Las oportunidades aparecerán acá cuando el scanner las encuentre.</p>
  </Card>
</template>
