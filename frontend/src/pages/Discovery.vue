<script setup lang="ts">
import {
  AlertTriangle,
  CheckCircle2,
  Compass,
  ExternalLink,
  Globe,
  Layers,
  Loader2,
  RefreshCw,
  RotateCw,
  Search,
  XCircle,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useDiscoveryStore } from '@/stores/discovery'

const store = useDiscoveryStore()

const filterPlatform = ref('')
const filterSource = ref('')
const filterImported = ref<string>('')

const sourceOptions = computed(() => {
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const p of store.programs) {
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
  for (const p of store.programs) {
    if (!seen.has(p.platform)) {
      seen.add(p.platform)
      opts.push({ value: p.platform, label: p.platform })
    }
  }
  return opts
})

const filteredPrograms = computed(() => {
  let list = store.programs
  if (filterPlatform.value) list = list.filter((p) => p.platform === filterPlatform.value)
  if (filterSource.value) list = list.filter((p) => p.source === filterSource.value)
  if (filterImported.value === 'true') list = list.filter((p) => p.imported)
  else if (filterImported.value === 'false') list = list.filter((p) => !p.imported)
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
  await store.runScan()
}

async function handleImportAll() {
  await store.importAll()
}

async function handleImport(program: any) {
  await store.importProgram(program.url)
}

onMounted(async () => {
  await Promise.all([store.fetchPrograms({ limit: 100 }), store.fetchStats()])
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
        <Button variant="outline" size="sm" :disabled="store.scanning" @click="handleScan">
          <Loader2 v-if="store.scanning" class="h-3.5 w-3.5 animate-spin" />
          <Search v-else class="h-3.5 w-3.5" />
          Scan
        </Button>
        <Button variant="outline" size="sm" @click="handleImportAll">
          <RefreshCw class="h-3.5 w-3.5" />
          Import All
        </Button>
      </div>
    </div>

    <template v-if="store.loading && store.programs.length === 0">
      <Skeleton class="h-24 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="store.error && store.programs.length === 0">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-8 w-8 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">{{ store.error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="store.fetchPrograms({ limit: 100 })">
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
          <p class="font-display text-xl font-bold text-foreground">{{ store.totalDiscovered }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <CheckCircle2 class="h-3 w-3 text-success" />
            <p class="font-mono text-[9px] uppercase text-success tracking-wider">Importados</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ store.importedCount }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <Layers class="h-3 w-3 text-info" />
            <p class="font-mono text-[9px] uppercase text-info tracking-wider">Plataformas</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ store.platforms.length }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <Search class="h-3 w-3 text-muted-foreground" />
            <p class="font-mono text-[9px] uppercase text-muted-foreground tracking-wider">Fuentes</p>
          </div>
          <p class="font-display text-xl font-bold text-foreground">{{ Object.keys(store.stats?.by_source ?? {}).length }}</p>
        </Card>
      </div>

      <!-- Monitor Status -->
      <div v-if="store.monitorStatus" class="rounded-xl border border-border/30 bg-surface/20 p-4">
        <div class="flex items-center justify-between mb-2">
          <p class="font-mono text-xs font-semibold text-foreground">Monitor Status</p>
          <Badge
            variant="outline"
            class="text-[9px]"
            :class="store.monitorStatus?.status === 'active' ? 'text-success' : 'text-muted-foreground'"
          >
            {{ store.monitorStatus?.status || 'inactive' }}
          </Badge>
        </div>
        <div v-if="store.monitorStatus?.last_scan" class="font-mono text-[9px] text-muted-foreground">
          Último scan: {{ new Date(store.monitorStatus.last_scan).toLocaleString('es-AR') }}
        </div>
        <div v-if="store.monitorStatus?.next_scan" class="font-mono text-[9px] text-muted-foreground">
          Próximo scan: {{ new Date(store.monitorStatus.next_scan).toLocaleString('es-AR') }}
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
                <span v-if="p.rewards_range" :class="statusColor(p.status)">
                  Rewards: {{ p.rewards_range }}
                </span>
                <span v-if="p.max_payout">
                  Max: ${{ p.max_payout.toLocaleString() }}
                </span>
                <span :class="confidenceColor(p.confidence)">
                  Confianza: {{ p.confidence }}%
                </span>
                <span v-if="p.technologies?.length">
                  Tech: {{ p.technologies.join(', ') }}
                </span>
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
    </template>
  </div>
</template>
