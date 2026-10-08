<script setup lang="ts">
/**
 * Copilot — Consolidated page with tabs.
 * Combines: AgentCenter + MemoryPatterns + PersonalIntelligence + InsightsView
 */
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import { Bot, Brain, BookOpen, Lightbulb, Sparkles, MessageCircle } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'

const activeTab = ref('assistant')
const loading = ref(true)
const memory = ref<any>(null)
const learning = ref<any>(null)

async function fetchData() {
  loading.value = true
  try {
    // `/api/learning/progress` no existe (404 siempre, verificado contra
    // `app.openapi()['paths']`). El endpoint real es `/api/learning/dashboard`.
    //
    // La tab esperaba `learning.skills = [{ name, level }]`, un campo que
    // ningún endpoint devuelve: con el 404 caía al estado vacío
    // "Sin skills registrados" y no se distinguishía de "no hay skills"
    // porque nunca hubo dato. Se renderiza lo que `/dashboard` SÍ devuelve.
    // Ver KNOWN_DEBT #75.
    const [mRes, lRes] = await Promise.allSettled([
      api.get<any>('/api/copilot/context'),
      api.get<any>('/api/learning/dashboard'),
    ])
    if (mRes.status === 'fulfilled') memory.value = mRes.value.context
    if (lRes.status === 'fulfilled') learning.value = lRes.value
  } catch { /* silent */ }
  loading.value = false
}

const tabs = computed(() => [
  { id: 'assistant', label: 'Asistente', icon: Bot },
  { id: 'memory', label: 'Memoria', icon: Brain },
  { id: 'learning', label: 'Aprendizaje', icon: BookOpen },
  { id: 'insights', label: 'Insights', icon: Lightbulb },
])

/**
 * Lo que `/api/learning/dashboard` devuelve de verdad:
 * `{ today, totals, recent_days, pending_actions, recent_learnings, metrics }`.
 * `totals` y `metrics` salen de `RevenueLearningLoop.get_totals()`, así que
 * sus claves se leen de ahí, no de memoria.
 */
const learningRows = computed(() => {
  const d = learning.value
  if (!d) return []
  const totals = d.totals ?? {}
  const metrics = d.metrics ?? {}
  return [
    { label: 'Minutos humanos', value: `${totals.total_human_minutes ?? 0} min` },
    { label: 'Acciones registradas', value: String(totals.total_actions ?? 0) },
    { label: 'Minutos humanos / día', value: String(metrics.human_minutes_per_day ?? 0) },
    { label: 'Ingreso / hora humana', value: `$${metrics.revenue_per_human_hour ?? 0}` },
    { label: 'Revenue real acumulado', value: `$${totals.total_actual_revenue ?? 0}` },
    { label: 'Acciones pendientes', value: String(d.pending_actions ?? 0) },
    { label: 'Envíos', value: String(d.today?.submissions ?? 0) },
    { label: 'Aceptados', value: String(d.today?.accepted ?? 0) },
    { label: 'Rechazados', value: String(d.today?.rejected ?? 0) },
  ]
})

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-foreground">Copilot</h1>
      <p class="text-sm text-muted-foreground">Asistente IA, memoria, aprendizaje y recomendaciones</p>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Assistant -->
      <template #assistant>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-6 text-center">
          <Bot class="mx-auto h-12 w-12 text-primary/40" />
          <h3 class="mt-3 text-lg font-semibold text-foreground">MERLIN Assistant</h3>
          <p class="mt-1 text-sm text-muted-foreground">Tu copiloto personal de IA</p>
          <button
            class="mt-4 flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors mx-auto"
            aria-label="$Go To /Merlin" @click="$router.push('/merlin')"
          >
            <MessageCircle class="h-4 w-4" />
            Abrir MERLIN
          </button>
        </div>
      </template>

      <!-- Memory -->
      <template #memory>
        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-16 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Contexto del Sistema</h3>
            <div v-if="memory" class="space-y-2">
              <div
                v-for="(value, key) in memory"
                :key="key"
                class="flex items-center justify-between rounded-lg border border-border/20 p-3"
              >
                <span class="font-mono text-xs text-muted-foreground">{{ key }}</span>
                <span class="font-mono text-xs text-foreground">{{ typeof value === 'object' ? JSON.stringify(value).slice(0, 50) : value }}</span>
              </div>
            </div>
            <div v-else class="text-center py-8">
              <Brain class="mx-auto h-8 w-8 text-muted-foreground/40" />
              <p class="mt-2 text-sm text-muted-foreground">Sin contexto aún</p>
              <p class="mt-1 text-xs text-muted-foreground/60">OWNEX aprende de tu actividad</p>
            </div>
          </div>
        </div>
      </template>

      <!-- Learning -->
      <template #learning>
        <div class="space-y-4">
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Progreso de Aprendizaje</h3>
            <div v-if="learning" class="space-y-2">
              <div
                v-for="row in learningRows"
                :key="row.label"
                class="flex items-center justify-between rounded-lg border border-border/20 p-3"
              >
                <span class="text-sm text-muted-foreground">{{ row.label }}</span>
                <span class="font-mono text-sm text-foreground">{{ row.value }}</span>
              </div>
            </div>
            <div v-else class="text-center py-8">
              <BookOpen class="mx-auto h-8 w-8 text-muted-foreground/40" />
              <p class="mt-2 text-sm text-muted-foreground">Sin datos de aprendizaje</p>
              <p class="mt-1 text-xs text-muted-foreground/60">
                El backend no devolvió /api/learning/dashboard
              </p>
            </div>
          </div>
        </div>
      </template>

      <!-- Insights -->
      <template #insights>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-5 text-center">
          <Lightbulb class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Recomendaciones personalizadas</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Basadas en tu actividad y resultados</p>
        </div>
      </template>
    </Tabs>
  </div>
</template>
