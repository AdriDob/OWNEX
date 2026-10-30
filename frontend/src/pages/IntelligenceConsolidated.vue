<script setup lang="ts">
/**
 * Intelligence — Consolidated page with tabs.
 * Combines: IntelligenceDashboard + ConfidenceDashboard + DifferentialEngine
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Bug, Brain, Lightbulb, BarChart3, Search, Shield, Check, X, Trash2 } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'
import { confirmFinding, rejectFinding, deleteFinding } from '@/services/ownexData'

const router = useRouter()
const activeTab = ref('overview')

// Intelligence data
const findings = ref<any[]>([])
const hypotheses = ref<any[]>([])
const loading = ref(true)
const busyId = ref<number | null>(null)

async function fetchData() {
  loading.value = true
  try {
    const [fRes, hRes] = await Promise.allSettled([
      fetch('/api/findings').then(r => r.json()),
      fetch('/api/hypotheses').then(r => r.json()),
    ])
    if (fRes.status === 'fulfilled') findings.value = fRes.value.findings || []
    if (hRes.status === 'fulfilled') hypotheses.value = hRes.value.hypotheses || []
  } catch { /* silent */ }
  loading.value = false
}

const stats = computed(() => ({
  totalFindings: findings.value.length,
  confirmedFindings: findings.value.filter((f: any) => f.status === 'confirmed').length,
  pendingFindings: findings.value.filter((f: any) => f.status === 'open').length,
  totalHypotheses: hypotheses.value.length,
}))

const tabs = computed(() => [
  { id: 'overview', label: 'Resumen', icon: BarChart3 },
  { id: 'findings', label: 'Hallazgos', icon: Bug, badge: stats.value.pendingFindings || undefined },
  { id: 'hypotheses', label: 'Hipótesis', icon: Lightbulb, badge: stats.value.totalHypotheses || undefined },
  { id: 'differential', label: 'Diferencial', icon: Brain },
])

async function confirm(findingId: number) {
  busyId.value = findingId
  try {
    await confirmFinding(findingId)
    await fetchData()
  } catch (e) {
    console.error('Failed to confirm finding', e)
  } finally {
    busyId.value = null
  }
}

async function reject(findingId: number) {
  busyId.value = findingId
  try {
    await rejectFinding(findingId)
    await fetchData()
  } catch (e) {
    console.error('Failed to reject finding', e)
  } finally {
    busyId.value = null
  }
}

async function deleteFindingItem(findingId: number) {
  if (!confirm('¿Estás seguro de que quieres eliminar este finding?')) return
  busyId.value = findingId
  try {
    await deleteFinding(findingId)
    await fetchData()
  } catch (e) {
    console.error('Failed to delete finding', e)
  } finally {
    busyId.value = null
  }
}

fetchData()
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-foreground">Inteligencia</h1>
      <p class="text-sm text-muted-foreground">Findings, hipótesis y análisis de vulnerabilidades</p>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Overview -->
      <template #overview>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
            <p class="font-mono text-[10px] uppercase text-muted-foreground">Findings</p>
            <p class="mt-1 font-mono text-2xl font-bold">{{ stats.totalFindings }}</p>
          </div>
          <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
            <p class="font-mono text-[10px] uppercase text-muted-foreground">Confirmados</p>
            <p class="mt-1 font-mono text-2xl font-bold text-emerald-400">{{ stats.confirmedFindings }}</p>
          </div>
          <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
            <p class="font-mono text-[10px] uppercase text-muted-foreground">Pendientes</p>
            <p class="mt-1 font-mono text-2xl font-bold text-yellow-400">{{ stats.pendingFindings }}</p>
          </div>
          <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
            <p class="font-mono text-[10px] uppercase text-muted-foreground">Hipótesis</p>
            <p class="mt-1 font-mono text-2xl font-bold">{{ stats.totalHypotheses }}</p>
          </div>
        </div>

        <div class="mt-6 rounded-xl border border-border/30 bg-surface/50 p-5">
          <h3 class="mb-3 text-sm font-semibold text-foreground">Acciones rápidas</h3>
          <div class="flex flex-wrap gap-2">
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              aria-label="Activetab = 'Findings'" @click="activeTab = 'findings'"
            >
              <Bug class="h-3.5 w-3.5" /> Ver hallazgos
            </button>
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              aria-label="Activetab = 'Hypotheses'" @click="activeTab = 'hypotheses'"
            >
              <Lightbulb class="h-3.5 w-3.5" /> Ver hipótesis
            </button>
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              aria-label="Go To /Intelligence/Evidence" @click="router.push('/intelligence/evidence')"
            >
              <Shield class="h-3.5 w-3.5" /> Evidencia
            </button>
          </div>
        </div>
      </template>

      <!-- Findings -->
      <template #findings>
        <div v-if="findings.length === 0" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <Bug class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Sin findings aún</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Ejecutá un scan para encontrar vulnerabilidades</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="f in findings"
            :key="f.id"
            class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/50 p-4"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-foreground">{{ f.title || f.name }}</p>
              <p class="mt-1 text-xs text-muted-foreground">{{ f.severity || 'unknown' }} · {{ f.platform || '' }}</p>
            </div>
            <div class="flex items-center gap-2">
              <span
                class="rounded-full px-2 py-0.5 text-[10px] font-mono"
                :class="f.status === 'confirmed' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-yellow-500/10 text-yellow-400'"
              >
                {{ f.status }}
              </span>
              <div class="flex items-center gap-1">
                <button
                  v-if="f.status !== 'confirmed'"
                  @click="confirm(f.id)"
                  :disabled="busyId === f.id"
                  class="rounded-md p-1.5 text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-50"
                  aria-label="Confirm finding"
                >
                  <Check class="h-3.5 w-3.5" />
                </button>
                <button
                  v-if="f.status !== 'rejected'"
                  @click="reject(f.id)"
                  :disabled="busyId === f.id"
                  class="rounded-md p-1.5 text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                  aria-label="Reject finding"
                >
                  <X class="h-3.5 w-3.5" />
                </button>
                <button
                  @click="deleteFindingItem(f.id)"
                  :disabled="busyId === f.id"
                  class="rounded-md p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 disabled:opacity-50"
                  aria-label="Delete finding"
                >
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Hypotheses -->
      <template #hypotheses>
        <div v-if="hypotheses.length === 0" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <Lightbulb class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Sin hipótesis pendientes</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="h in hypotheses"
            :key="h.id"
            class="rounded-lg border border-border/30 bg-surface/50 p-4"
          >
            <p class="text-sm font-medium text-foreground">{{ h.title || h.description }}</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ h.type || 'unknown' }} · Confidence: {{ h.confidence || '?' }}%</p>
          </div>
        </div>
      </template>

      <!-- Differential -->
      <template #differential>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-6 text-center">
          <Brain class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Análisis diferencial</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Compara findings entre targets para patrones</p>
        </div>
      </template>
    </Tabs>
  </div>
</template>
