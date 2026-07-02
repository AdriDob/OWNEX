<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { DoughnutChart } from '@/components/charts'
import {
  Search, AlertTriangle, RefreshCw, Plus, Trash2,
  Activity, PauseCircle, CheckCircle2, XCircle,
} from '@lucide/vue'

interface Investigation {
  id: number
  name: string
  target_id: number
  target_name: string
  status: 'active' | 'paused' | 'completed' | 'abandoned'
  findings_count: number
  created_at: string
  updated_at: string
}

type StatusTab = 'all' | 'active' | 'paused' | 'completed' | 'abandoned'

const investigations = ref<Investigation[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<StatusTab>('all')
const search = ref('')
const showCreate = ref(false)
const newName = ref('')
const newTargetId = ref<number | null>(null)
const creating = ref(false)

const statusConfig: Record<string, { icon: any; color: string; label: string }> = {
  active: { icon: Activity, color: 'text-success', label: 'Activa' },
  paused: { icon: PauseCircle, color: 'text-warning', label: 'Pausada' },
  completed: { icon: CheckCircle2, color: 'text-primary', label: 'Completada' },
  abandoned: { icon: XCircle, color: 'text-destructive', label: 'Abandonada' },
}

const statusBadge: Record<string, 'success' | 'warning' | 'info' | 'destructive'> = {
  active: 'success',
  paused: 'warning',
  completed: 'info',
  abandoned: 'destructive',
}

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, string | number | boolean | undefined | null> = { limit: 100 }
    if (activeTab.value !== 'all') params.status = activeTab.value
    const res = await api.get<{ items: Investigation[]; total: number }>('/investigations', params)
    investigations.value = res.items || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar investigaciones'
  }
  finally { loading.value = false }
}

async function createInvestigation() {
  if (!newName.value || !newTargetId.value) return
  creating.value = true
  try {
    await api.post('/investigations', { name: newName.value, target_id: newTargetId.value })
    newName.value = ''
    newTargetId.value = null
    showCreate.value = false
    await fetchData()
  } catch { /* ignore */ }
  finally { creating.value = false }
}

async function deleteInvestigation(id: number) {
  try {
    await api.delete(`/investigations/${id}`)
    investigations.value = investigations.value.filter(i => i.id !== id)
  } catch { /* ignore */ }
}

function tabChanged(tab: StatusTab) {
  activeTab.value = tab
  fetchData()
}

onMounted(fetchData)

const filtered = computed(() => {
  let result = investigations.value
  const q = search.value.toLowerCase()
  if (q) {
    result = result.filter(i =>
      i.name.toLowerCase().includes(q) ||
      i.target_name?.toLowerCase().includes(q)
    )
  }
  return result
})

const statusCounts = computed(() => {
  const counts: Record<string, number> = { active: 0, paused: 0, completed: 0, abandoned: 0 }
  for (const inv of investigations.value) {
    counts[inv.status] = (counts[inv.status] || 0) + 1
  }
  return counts
})

const chartLabels = computed(() => ['Active', 'Paused', 'Completed', 'Abandoned'])
const chartData = computed(() => [
  statusCounts.value.active || 0,
  statusCounts.value.paused || 0,
  statusCounts.value.completed || 0,
  statusCounts.value.abandoned || 0,
])

const tabs: { key: StatusTab; label: string }[] = [
  { key: 'all', label: 'Todas' },
  { key: 'active', label: 'Activas' },
  { key: 'paused', label: 'Pausadas' },
  { key: 'completed', label: 'Completadas' },
  { key: 'abandoned', label: 'Abandonadas' },
]
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Investigations</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Investigation Center</h1>
      <p class="text-sm text-muted-foreground">Gestioná tus investigaciones activas</p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-10 rounded-xl" />
      <Skeleton class="h-52 rounded-xl" />
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 6" :key="i" class="h-32 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error al cargar investigaciones</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="investigations.length === 0 && activeTab === 'all'">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Activity class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay investigaciones</p>
        <p class="mt-1 text-xs text-muted-foreground">Creá una nueva investigación para comenzar</p>
        <Button size="sm" class="mt-4 gap-2" @click="showCreate = true">
          <Plus class="h-3.5 w-3.5" /> Nueva Investigación
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-wrap items-center justify-between gap-3 animate-in">
        <div class="flex items-center gap-2 border-b border-border/40">
          <button v-for="tab in tabs" :key="tab.key"
            @click="tabChanged(tab.key)"
            :class="['px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px', activeTab === tab.key ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
          >
            {{ tab.label }}
            <span v-if="tab.key !== 'all'" class="ml-1 text-[10px] opacity-60">({{ statusCounts[tab.key] || 0 }})</span>
          </button>
        </div>
        <Button size="sm" class="gap-2" @click="showCreate = !showCreate">
          <Plus class="h-3.5 w-3.5" /> Nueva
        </Button>
      </div>

      <Transition name="fade">
        <Card v-if="showCreate" class="p-4 animate-in">
          <div class="flex flex-wrap items-end gap-3">
            <div class="flex-1 min-w-[200px]">
              <p class="text-[10px] font-semibold text-muted-foreground mb-1">Nombre</p>
              <input v-model="newName" placeholder="Nombre de la investigación"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
              />
            </div>
            <div class="w-32">
              <p class="text-[10px] font-semibold text-muted-foreground mb-1">Target ID</p>
              <input v-model.number="newTargetId" type="number" placeholder="ID"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
              />
            </div>
            <Button :disabled="creating || !newName || !newTargetId" @click="createInvestigation" class="gap-2">
              <Plus class="h-3.5 w-3.5" />
              {{ creating ? 'Creando...' : 'Crear' }}
            </Button>
          </div>
        </Card>
      </Transition>

      <div class="relative max-w-md animate-in">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input v-model="search" placeholder="Buscar investigaciones..."
          class="w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
        />
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <DoughnutChart
            :labels="chartLabels"
            :data="chartData"
            :height="180"
            :showLegend="true"
          />
        </div>
      </Card>

      <div v-if="filtered.length === 0" class="py-12 text-center text-sm text-muted-foreground">
        {{ search ? 'Sin resultados para la búsqueda' : 'No hay investigaciones en este estado' }}
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Card v-for="(inv, i) in filtered" :key="inv.id" class="p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold text-foreground truncate">{{ inv.name }}</h3>
              <p class="text-[10px] text-muted-foreground mt-0.5">{{ inv.target_name || `Target #${inv.target_id}` }}</p>
            </div>
            <Badge :variant="statusBadge[inv.status] || 'default'" class="shrink-0 text-[10px]">
              {{ statusConfig[inv.status]?.label || inv.status }}
            </Badge>
          </div>
          <div class="flex items-center justify-between mb-3 text-[10px] text-muted-foreground">
            <span>{{ inv.findings_count }} hallazgos</span>
            <span>{{ new Date(inv.updated_at || inv.created_at).toLocaleDateString() }}</span>
          </div>
          <div class="flex items-center gap-2">
            <component :is="statusConfig[inv.status]?.icon" class="h-3.5 w-3.5" :class="statusConfig[inv.status]?.color" />
            <span class="text-[10px]" :class="statusConfig[inv.status]?.color || 'text-muted-foreground'">{{ statusConfig[inv.status]?.label || inv.status }}</span>
            <button @click="deleteInvestigation(inv.id)"
              class="ml-auto text-muted-foreground hover:text-destructive transition-colors"
              title="Eliminar investigación"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        </Card>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
