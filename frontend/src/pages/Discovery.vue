<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDiscoveryStore } from '@/stores/discovery'
import { useAuthStore } from '@/stores/auth'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'
import { AlertTriangle, CheckCircle2, Compass, ExternalLink, Globe, Layers, Loader2, RefreshCw, RotateCw, Search, XCircle, FlagArgentina } from "@lucide/vue"

const discoveryStore = useDiscoveryStore()
const userStore = useAuthStore()

const filterPlatform = ref('')
const filterSource = ref('')
const filterImported = ref<string>('')

const sourceOptions = computed(() => {
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const p of discoveryStore.programs) {
    if (!seen.has(p.source)) {
      seen.add(p.source)
      opts.push({ value: p.source, label: p.source })
    }
  }
  return opts
})

const platformOptions = computed(() => {
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const p of discoveryStore.programs) {
    if (!seen.has(p.platform)) {
      seen.add(p.platform)
      opts.push({ value: p.platform, label: p.platform })
    }
  }
  return opts
})

const filteredPrograms = computed(() => {
  let list = discoveryStore.programs
  if (filterPlatform.value) list = list.filter(p => p.platform === filterPlatform.value)
  if (filterSource.value) list = list.filter(p => p.source === filterSource.value)
  if (filterImported.value === 'true') list = list.filter(p => p.imported)
  else if (filterImported.value === 'false') list = list.filter(p => !p.imported)
  return list
})

function confidenceColor(c: number): string {
  if (c >= 80) return 'text-success'
  if (c >= 50) return 'text-warning'
  return 'text-muted-foreground'
}

function statusColor(s: string): string {
  if (s === 'active' || s === 'open') return 'text-success'
  if (s === 'inactive' || s === 'closed') return 'text-muted-foreground'
  return 'text-warning'
}

async function handleScan() {
  await discoveryStore.runScan()
}

async function handleImportAll() {
  await discoveryStore.importAll()
}

async function handleImport(program: any) {
  await discoveryStore.importProgram(program.url)
}

// Remote Job Search state
const remoteJobQuery = ref('')
const remoteJobSalaryMin = ref(0)
const remoteJobMaxTechTests = ref(1)
const remoteJobPaymentMethods = ref('')
const remoteJobResults = ref<any[]>([])
const remoteJobLoading = ref(false)
const remoteJobError = ref<string | null>(null)
const remoteJobProfile = ref<Record<string, unknown> | null>(null)

async function searchRemoteJobs() {
  remoteJobLoading.value = true
  remoteJobError.value = null
  remoteJobResults.value = []
  
  try {
    const params = new URLSearchParams({
      q: remoteJobQuery.value,
      salary_min: String(remoteJobSalaryMin.value || 0),
      max_tech_tests: String(remoteJobMaxTechTests.value),
      payment_methods: remoteJobPaymentMethods.value,
    })
    const data = await api.get<{ jobs?: any[]; error?: string }>(
      `/opportunities/remote-jobs/search?${params.toString()}`,
    )
    remoteJobResults.value = data.jobs || []
    remoteJobError.value = null
  } catch (e: any) {
    remoteJobError.value = e?.message || 'Error de conexión'
    remoteJobResults.value = []
  } finally {
    remoteJobLoading.value = false
  }
}

async function saveRemoteJob(job: any) {
  try {
    const data = await api.post<{ id?: string; status?: string }>(
      '/opportunities/remote-jobs/save',
      { job },
    )
    await discoveryStore.fetchPrograms({ limit: 100 })
    return { success: true, id: data.id, status: data.status }
  } catch (e: any) {
    remoteJobError.value = e?.message || 'Error al guardar job'
    return { success: false, error: e?.message }
  }
}

async function draftApplication(jobId: string, profile: any) {
  try {
    const data = await api.post<Record<string, unknown>>(
      `/opportunities/remote-jobs/${jobId}/draft`,
      { profile },
    )
    return { success: true, ...data }
  } catch (e: any) {
    remoteJobError.value = e?.message || 'Error al generar draft'
    return { success: false, error: e?.message }
  }
}

// Watch user token changes
watch(() => userStore.token, () => {
  if (userStore.token) {
    searchRemoteJobs()
  }
})
onMounted(async () => {
  await Promise.all([discoveryStore.fetchPrograms({ limit: 100 }), discoveryStore.fetchStats()])
  if (userStore.token) {
    try {
      const data = await api.get<{ profile?: Record<string, unknown> }>('/opportunities/profile')
      remoteJobProfile.value = data.profile ?? null
    } catch {
      remoteJobProfile.value = null
    }
  }
})
</script>

<template>
  <div class="space-y-6 animate-in">
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <Compass class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">PROGRAM DISCOVERY</span>
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Program Discovery</h1>
        <p class="text-xs text-muted-foreground">Descubrimiento y monitoreo de programas bug bounty</p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" :disabled="discoveryStore.scanning" @click="handleScan">
          <Loader2 v-if="discoveryStore.scanning" class="h-3.5 w-3.5 animate-spin" />
          <Search v-else class="h-3.5 w-3.5" />
          Scan
        </Button>
        <Button variant="outline" size="sm" @click="handleImportAll">
          <RefreshCw class="h-3.5 w-3.5" />
          Import All
        </Button>
      </div>
    </div>

    <template v-if="discoveryStore.loading && discoveryStore.programs.length === 0">
      <Skeleton class="h-24 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="discoveryStore.error && discoveryStore.programs.length === 0">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-8 w-8 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">{{ discoveryStore.error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="discoveryStore.fetchPrograms({ limit: 100 })">
          <RotateCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else>
      <!-- Stats -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <Globe class="h-3 w-3 text-primary" />
            <p class="font-mono text-[9px] uppercase text-primary tracking-wider">Descubiertos</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ discoveryStore.totalDiscovered }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <CheckCircle2 class="h-3 w-3 text-success" />
            <p class="font-mono text-[9px] uppercase text-success tracking-wider">Importados</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ discoveryStore.importedCount }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <Layers class="h-3 w-3 text-info" />
            <p class="font-mono text-[9px] uppercase text-info tracking-wider">Plataformas</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ discoveryStore.platforms.length }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <Search class="h-3 w-3 text-muted-foreground" />
            <p class="font-mono text-[9px] uppercase text-muted-foreground tracking-wider">Fuentes</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ Object.keys(discoveryStore.stats?.by_source ?? {}).length }}</p>
        </Card>
      </div>

      <!-- Monitor Status -->
      <div v-if="discoveryStore.monitorStatus" class="rounded-xl border border-border/30 bg-surface/20 p-4">
        <div class="flex items-center justify-between mb-2">
          <p class="font-mono text-xs font-semibold text-foreground">Monitor Status</p>
          <Badge
            variant="outline"
            class="text-[9px]"
            :class="discoveryStore.monitorStatus?.status === 'active' ? 'text-success' : 'text-muted-foreground'"
          >
            {{ discoveryStore.monitorStatus?.status || 'inactive' }}
          </Badge>
        </div>
        <div v-if="discoveryStore.monitorStatus?.last_scan" class="font-mono text-[9px] text-muted-foreground">
          Último scan: {{ new Date(discoveryStore.monitorStatus.last_scan).toLocaleString('es-AR') }}
        </div>
        <div v-if="discoveryStore.monitorStatus?.next_scan" class="font-mono text-[9px] text-muted-foreground">
          Próximo scan: {{ new Date(discoveryStore.monitorStatus.next_scan).toLocaleString('es-AR') }}
        </div>
      </div>

      <!-- Filters -->
      <div class="flex flex-wrap items-center gap-3">
        <select
          v-model="filterPlatform"
          class="rounded-lg border border-border/30 bg-surface/20 px-3 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary/50"
        >
          <option value="">Todas las plataformas</option>
          <option v-for="opt in platformOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <select
          v-model="filterSource"
          class="rounded-lg border border-border/30 bg-surface/20 px-3 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary/50"
        >
          <option value="">Todas las fuentes</option>
          <option v-for="opt in sourceOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <select
          v-model="filterImported"
          class="rounded-lg border border-border/30 bg-surface/20 px-3 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary/50"
        >
          <option value="">Todos</option>
          <option value="true">Importados</option>
          <option value="false">No importados</option>
        </select>
        <span class="font-mono text-[9px] text-muted-foreground">{{ filteredPrograms.length }} programas</span>
      </div>

      <!-- Remote Job Search -->
      <div v-if="userStore.token" class="rounded-xl border border-border/30 bg-surface/20 p-4 mb-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-mono text-xs text-foreground">Búsqueda de Jobs Remotos</h3>
          <button class="text-[10px] text-primary underline underline-offset-2" @click="searchRemoteJobs">
            Buscar
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="text-[9px] text-muted-foreground">Query</label>
            <input
              v-model="remoteJobQuery"
              type="text"
              class="w-full rounded-lg border border-border/30 bg-surface/20 px-2 py-1 font-mono text-xs text-foreground outline-none focus:border-primary/50"
              placeholder="Desarrollo, QA, soporte..."
            />
          </div>
          <div>
            <label class="text-[9px] text-muted-foreground">Salario min (USD)</label>
            <input
              v-model.number="remoteJobSalaryMin"
              type="number"
              class="w-full rounded-lg border border-border/30 bg-surface/20 px-2 py-1 font-mono text-xs text-foreground outline-none focus:border-primary/50"
              min="0"
              placeholder="0"
            />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="text-[9px] text-muted-foreground">Máx tests tech</label>
            <input
              v-model="remoteJobMaxTechTests"
              type="number"
              class="w-full rounded-lg border border-border/30 bg-surface/20 px-2 py-1 font-mono text-xs text-foreground outline-none focus:border-primary/50"
              min="0"
              max="10"
              value="1"
            />
          </div>
          <div>
            <label class="text-[9px] text-muted-foreground">Payment methods</label>
            <input
              v-model="remoteJobPaymentMethods"
              type="text"
              class="w-full rounded-lg border border-border/30 bg-surface/20 px-2 py-1 font-mono text-xs text-foreground outline-none focus:border-primary/50"
              placeholder="payoneer, wise, paypal"
            />
          </div>
        </div>
        <div v-if="remoteJobLoading" class="text-muted-foreground text-[9px]">Buscando...</div>
        <div v-else-if="remoteJobError" class="text-destructive text-[9px] mt-2">{{ remoteJobError }}</div>
      </div>

      <!-- Programs List -->
      <div v-if="filteredPrograms.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-8 text-center">
        <Compass class="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
        <p class="font-mono text-xs text-muted-foreground">No se encontraron programas</p>
      </div>

      <div class="space-y-2">
        <div
          v-for="(p, i) in filteredPrograms"
          :key="`${p.platform}-${p.name}-${i}`"
          class="rounded-xl border border-border/30 bg-surface/20 p-3"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-medium text-foreground truncate">{{ p.name }}</span>
                <Badge variant="outline" class="text-[9px]">{{ p.platform }}</Badge>
                <Badge variant="outline" class="text-[9px]">{{ p.source }}</Badge>
              </div>
              <p v-if="p.description" class="mt-1 font-mono text-[9px] text-muted-foreground line-clamp-2">{{ p.description }}</p>
              <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[9px] text-muted-foreground">
                <span v-if="p.rewards_range" :class="statusColor(p.status)">Rewards: {{ p.rewards_range }}</span>
                <span v-if="p.max_payout">Max: ${{ p.max_payout.toLocaleString() }}</span>
                <span :class="confidenceColor(p.confidence)">Confianza: {{ p.confidence }}%</span>
                <span v-if="p.technologies?.length">Tech: {{ p.technologies.join(', ') }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <Badge
                variant="outline"
                class="text-[9px]"
                :class="p.imported ? 'text-success' : 'text-warning'"
              >
                {{ p.imported ? 'Importado' : 'Pendiente' }}
              </Badge>
              <Button
                v-if="!p.imported"
                variant="ghost"
                size="sm"
                @click="handleImport(p)"
              >
                <ExternalLink class="h-3 w-3" />
              </Button>
            </div>
          </div>
          <div v-if="p.import_error" class="mt-1 font-mono text-[9px] text-destructive/80">
            Error: {{ p.import_error }}
          </div>
          <div class="mt-1.5 font-mono text-[9px] text-muted-foreground/60">
            Descubierto: {{ new Date(p.discovered_at).toLocaleString('es-AR') }}
          </div>
        </div>
      </div>

      <!-- Remote Jobs Results -->
      <template v-if="remoteJobResults.length > 0 && userStore.token">
        <div class="rounded-xl border border-border/30 bg-surface/20 p-4 mt-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-mono text-xs text-foreground">Jobs Remotos Encontrados</h3>
            <span class="text-[9px] text-muted-foreground">{{ remoteJobResults.length }} resultados</span>
          </div>
          <div class="space-y-2 max-h-80 overflow-y-auto">
            <div
              v-for="(job, jidx) in remoteJobResults"
              :key="`remote-${jidx}`"
              class="rounded-xl border border-border/30 bg-surface/20 p-3 text-[9px]"
            >
              <div class="flex items-center gap-2 mb-1">
                <span class="font-medium truncate">{{ job.title || 'Sin título' }}</span>
                <Badge
                  variant="outline"
                  class="text-[9px]"
                  :class="job.argentina_ok ? 'text-success' : 'text-destructive'"
                >
                  {{ job.argentina_ok ? 'AR' : 'No AR' }}
                </Badge>
              </div>
              <p v-if="job.company" class="text-[10px] truncate">{{ job.company }}</p>
              <p v-if="job.location" class="text-[9px] text-muted-foreground truncate">{{ job.location }}</p>
              <p v-if="job.salary_min" class="text-[9px]">$ {{ job.salary_min.toLocaleString() }} USD/mes</p>
              <p v-if="job.language" class="text-[9px] text-muted-foreground">Idioma: {{ job.language }}</p>
              <p v-if="job.remote" class="text-[9px] text-success">Remoto</p>
              <div class="mt-1 flex gap-2">
                <button
                  class="text-[10px] text-primary underline"
                  @click="saveRemoteJob(job)"
                >
                  Guardar en Work Bank
                </button>
                <button
                  v-if="remoteJobProfile"
                  class="text-[10px] text-primary underline"
                  @click="draftApplication(job.id, remoteJobProfile)"
                >
                  Draft Application
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
