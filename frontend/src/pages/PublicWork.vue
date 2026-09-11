<script setup lang="ts">
/**
 * PublicWork — escalera de trabajo público ETAPA 0→4.
 * Capa de presentación sobre POST /direct-work/recommend: agrupa por peldaño
 * (rung). Sin motor de ranking propio: misma inteligencia, otra superficie.
 */
import { computed, onMounted, ref } from 'vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import { fetchPublicWork, type DirectWorkRanked } from '@/services/ownexData'

const RUNGS = [
  { id: 'oss_validation', label: 'Etapa 0 · Validación OSS' },
  { id: 'beginner', label: 'Principiante' },
  { id: 'intermediate', label: 'Intermedio' },
  { id: 'advanced', label: 'Avanzado' },
  { id: 'expert', label: 'Experto' },
] as const

const MODES = ['secure_plus_upside', 'secure_income', 'balanced', 'fast_income', 'max_success', 'max_income'] as const

const mode = ref<string>('secure_plus_upside')
const ranked = ref<DirectWorkRanked[]>([])
const loading = ref(true)
const error = ref('')

const pct = (n: number | null | undefined): string => (n != null ? `${Math.round(n * 100)}%` : '—')
const usd = (n: number | null | undefined): string => (n != null ? `$${Math.round(n).toLocaleString('es-AR')}` : '—')
const evh = (r: DirectWorkRanked): string => {
  const v = r.htroi?.usd_per_hour
  return v != null ? `${usd(v)}/h` : '—'
}
const pcash = (r: DirectWorkRanked): string => {
  if (r.p_cash == null) return 'UNKNOWN'
  return `${pct(r.p_cash)} (${r.p_cash_band || 'UNKNOWN'})`
}

const grouped = computed(() => {
  const by: Record<string, DirectWorkRanked[]> = {}
  for (const r of ranked.value) {
    const key = r.public_work?.rung || 'beginner'
    ;(by[key] ||= []).push(r)
  }
  return by
})

const rungGoal = (id: string): string => {
  const first = (grouped.value[id] || [])[0]
  return first?.public_work?.rung_goal_es || ''
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    ranked.value = await fetchPublicWork(mode.value, 30)
  } catch (e: any) {
    error.value = e?.message || 'Error cargando Public Work'
  } finally {
    loading.value = false
  }
}

function reload(m: string): void {
  mode.value = m
  void load()
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-4 p-4 sm:space-y-6 sm:p-6">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-foreground sm:text-2xl">Public Work</h1>
        <p class="mt-1 text-xs text-muted-foreground sm:text-sm">
          Sin experiencia → contribución pública → PR merged → primer bounty → reputación.
          Mismo ranking de siempre, agrupado en rampa.
        </p>
      </div>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="m in MODES"
          :key="m"
          :aria-pressed="mode === m"
          class="rounded-md border px-2.5 py-1 font-mono text-[11px]"
          :class="mode === m ? 'border-primary bg-primary/10 text-primary' : 'border-border/40 text-muted-foreground'"
          @click="reload(m)"
        >
          {{ m }}
        </button>
      </div>
    </header>

    <div v-if="loading" class="py-20 text-center text-sm text-muted-foreground">Cargando escalera…</div>
    <div v-else-if="error" class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
      {{ error }}
    </div>

    <template v-else>
      <section v-for="rung in RUNGS" :key="rung.id">
        <div class="mb-2 flex items-baseline gap-2">
          <h2 class="text-base font-semibold text-foreground">{{ rung.label }}</h2>
          <span class="text-xs text-muted-foreground">{{ rungGoal(rung.id) }}</span>
          <span class="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
            {{ (grouped[rung.id] || []).length }}
          </span>
        </div>

        <p v-if="!(grouped[rung.id] || []).length" class="mb-4 text-xs text-muted-foreground">
          Sin oportunidades en este peldaño con el modo actual.
        </p>

        <div class="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <OwnexCard v-for="r in (grouped[rung.id] || []).slice(0, 3)" :key="r.opportunity.id" class="p-4">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-foreground">{{ r.opportunity.title }}</p>
                <p class="font-mono text-[11px] text-muted-foreground">
                  {{ r.opportunity.platform }} · {{ r.opportunity.category }} · {{ usd(r.opportunity.payment) }}
                </p>
              </div>
              <span class="shrink-0 font-mono text-lg font-bold tabular-nums text-primary">#{{ r.rank }}</span>
            </div>

            <div class="mt-2 grid grid-cols-4 gap-1 text-center">
              <div><p class="font-mono text-[9px] uppercase text-muted-foreground">Fit</p><p class="font-mono text-sm font-semibold">{{ pct(r.compatibility_score) }}</p></div>
              <div><p class="font-mono text-[9px] uppercase text-muted-foreground">EV/h</p><p class="font-mono text-sm font-semibold">{{ evh(r) }}</p></div>
              <div><p class="font-mono text-[9px] uppercase text-muted-foreground">P(CASH)</p><p class="font-mono text-sm font-semibold">{{ pcash(r) }}</p></div>
              <div><p class="font-mono text-[9px] uppercase text-muted-foreground">Acept.</p><p class="font-mono text-sm font-semibold">{{ pct(r.acceptance_probability) }}</p></div>
            </div>

            <div v-if="r.public_work" class="mt-2 rounded-md border border-border/30 bg-surface/30 p-2">
              <p class="font-mono text-[10px] font-semibold uppercase text-muted-foreground">Validación pública</p>
              <ul class="mt-1 space-y-0.5">
                <li v-for="(c, i) in r.public_work.checks" :key="i" class="text-[11px] text-foreground/90">✓ {{ c }}</li>
              </ul>
              <p class="mt-1 font-mono text-[11px] font-semibold text-success">Lo que demuestra: {{ r.public_work.proof }}</p>
            </div>

            <p v-if="r.opportunity.url" class="mt-2 truncate font-mono text-[11px]">
              <a :href="r.opportunity.url" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">Abrir oportunidad →</a>
            </p>
          </OwnexCard>
        </div>
      </section>
    </template>
  </div>
</template>
