<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart } from '@/components/charts'
import { Image, AlertTriangle, RefreshCw, X, Maximize2, Shield, Eye, EyeOff, List, ExternalLink, Search } from '@lucide/vue'

interface ScreenshotBlock {
  selector?: string
  type?: string
  content?: string
  visible?: boolean
}

interface ScreenshotItem {
  id: number
  title: string
  vulnerability_type: string
  endpoint: string
  severity: string
  roi_score: number
  visual_blocks: ScreenshotBlock[]
  screenshot_path?: string
  thumbnail_path?: string
  created_at: string
}

const screenshots = ref<ScreenshotItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const selectedScreenshot = ref<ScreenshotItem | null>(null)
const showModal = ref(false)

async function fetchScreenshots() {
  try {
    const res = await api.get<{ items: ScreenshotItem[]; total: number }>('/screenshots')
    screenshots.value = res.items || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar capturas'
  } finally {
    loading.value = false
  }
}

onMounted(fetchScreenshots)

const filtered = computed(() => {
  if (!search.value) return screenshots.value
  const q = search.value.toLowerCase()
  return screenshots.value.filter(s =>
    s.title?.toLowerCase().includes(q) ||
    s.vulnerability_type?.toLowerCase().includes(q) ||
    s.endpoint?.toLowerCase().includes(q)
  )
})

function severityColor(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev?.toLowerCase()] || 'default'
}

const severityChartData = computed(() => {
  const counts: Record<string, number> = {}
  for (const s of screenshots.value) {
    const sev = s.severity?.toLowerCase() || 'unknown'
    counts[sev] = (counts[sev] || 0) + 1
  }
  const order = ['critical', 'high', 'medium', 'low', 'info']
  const labels: string[] = []
  const data: number[] = []
  for (const key of order) {
    if (counts[key]) { labels.push(key.charAt(0).toUpperCase() + key.slice(1)); data.push(counts[key]) }
  }
  for (const [k, v] of Object.entries(counts)) {
    if (!order.includes(k)) { labels.push(k); data.push(v) }
  }
  return { labels, data }
})

function openDetail(item: ScreenshotItem) {
  selectedScreenshot.value = item
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  selectedScreenshot.value = null
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Evidence</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Screenshot Center</h1>
      <p class="text-sm text-muted-foreground">Visual evidence browser for vulnerability screenshots</p>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 6" :key="i" class="h-40 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">No se pudieron cargar las capturas</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" size="sm" @click="loading = true; fetchScreenshots()">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </Card>
    </template>

    <template v-else-if="screenshots.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Image class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay capturas disponibles</p>
        <p class="mt-1 text-xs text-muted-foreground">Las capturas aparecerán aquí cuando se generen desde hallazgos validados</p>
      </div>
    </template>

    <template v-else>
      <div class="flex items-center justify-between flex-wrap gap-2 animate-in">
        <div class="relative max-w-xs">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input v-model="search" placeholder="Buscar capturas..."
            class="w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
          />
        </div>
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
          <List class="h-3.5 w-3.5" />
          <span>{{ filtered.length }} de {{ screenshots.length }}</span>
        </div>
      </div>

      <div v-if="severityChartData.labels.length" class="animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Shield class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Screenshots by Severity</p>
          </div>
          <BarChart
            :labels="severityChartData.labels"
            :datasets="[{
              label: 'Count',
              data: severityChartData.data,
              backgroundColor: ['#E82127', '#D97706', '#A16207', '#16A34A', '#ffffff'],
            }]"
            :height="200"
            :showLegend="false"
            yLabel="Count"
          />
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card v-for="s in filtered" :key="s.id"
          class="p-0 overflow-hidden cursor-pointer transition-all hover:border-primary/40 animate-in group"
          @click="openDetail(s)"
        >
          <div class="aspect-video bg-surface/30 flex items-center justify-center relative">
            <div v-if="s.thumbnail_path" class="w-full h-full">
              <img :src="s.thumbnail_path" :alt="s.title" class="w-full h-full object-cover" />
            </div>
            <div v-else class="flex flex-col items-center gap-1 text-muted-foreground">
              <Image class="h-8 w-8 text-muted-foreground/30" />
              <span class="text-[10px]">No preview</span>
            </div>
            <div class="absolute top-2 right-2 flex gap-1">
              <Badge :variant="severityColor(s.severity)" class="text-[9px] px-1.5 py-0">{{ s.severity }}</Badge>
            </div>
            <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-center justify-center">
              <Maximize2 class="h-6 w-6 text-white/0 group-hover:text-white/80 transition-all" />
            </div>
          </div>
          <div class="p-3 space-y-2">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0 flex-1">
                <p class="text-xs font-semibold text-foreground truncate">{{ s.title }}</p>
                <p class="text-[10px] text-muted-foreground truncate">{{ s.vulnerability_type }}</p>
              </div>
            </div>
            <div class="flex items-center justify-between text-[10px]">
              <span class="text-muted-foreground truncate max-w-[140px]">{{ s.endpoint }}</span>
              <span class="font-semibold tabular-nums" :class="s.roi_score >= 70 ? 'text-success' : s.roi_score >= 40 ? 'text-warning' : 'text-muted-foreground'">
                ROI {{ s.roi_score }}%
              </span>
            </div>
            <div v-if="s.visual_blocks?.length" class="flex flex-wrap gap-1">
              <Badge v-for="(b, i) in s.visual_blocks.slice(0, 3)" :key="i" variant="outline" class="text-[9px] px-1 py-0">
                {{ b.type || b.selector || 'block' }}
              </Badge>
              <span v-if="s.visual_blocks.length > 3" class="text-[9px] text-muted-foreground">+{{ s.visual_blocks.length - 3 }}</span>
            </div>
          </div>
        </Card>
      </div>

      <div v-if="filtered.length === 0 && screenshots.length > 0" class="py-12 text-center text-sm text-muted-foreground">
        No se encontraron capturas con "{{ search }}"
      </div>

      <Transition name="modal">
        <div v-if="showModal && selectedScreenshot" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click="closeModal">
          <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeModal" />
          <div class="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border/40 bg-surface shadow-2xl animate-in" @click.stop>
            <div class="sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-border/40 bg-surface/90 backdrop-blur-sm px-4 sm:px-6 py-4">
              <div class="flex items-center gap-3">
                <h2 class="text-base font-semibold text-foreground">{{ selectedScreenshot.title }}</h2>
                <Badge :variant="severityColor(selectedScreenshot.severity)">{{ selectedScreenshot.severity }}</Badge>
              </div>
              <button @click="closeModal" class="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface hover:text-foreground transition-colors">
                <X class="h-4 w-4" />
              </button>
            </div>
            <div class="p-6 space-y-4">
              <div v-if="selectedScreenshot.screenshot_path" class="rounded-xl overflow-hidden border border-border/30">
                <img :src="selectedScreenshot.screenshot_path" :alt="selectedScreenshot.title" class="w-full" />
              </div>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Vulnerability</p>
                  <p class="mt-0.5 text-foreground font-semibold">{{ selectedScreenshot.vulnerability_type }}</p>
                </div>
                <div>
                  <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Endpoint</p>
                  <p class="mt-0.5 text-foreground font-mono text-xs break-all">{{ selectedScreenshot.endpoint }}</p>
                </div>
                <div>
                  <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">ROI Score</p>
                  <p class="mt-0.5 font-bold" :class="selectedScreenshot.roi_score >= 70 ? 'text-success' : selectedScreenshot.roi_score >= 40 ? 'text-warning' : 'text-foreground'">
                    {{ selectedScreenshot.roi_score }}%
                  </p>
                </div>
                <div>
                  <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Created</p>
                  <p class="mt-0.5 text-muted-foreground text-xs">{{ new Date(selectedScreenshot.created_at).toLocaleString() }}</p>
                </div>
              </div>
              <div v-if="selectedScreenshot.visual_blocks?.length">
                <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2">Visual Blocks ({{ selectedScreenshot.visual_blocks.length }})</p>
                <div class="space-y-2">
                  <div v-for="(b, i) in selectedScreenshot.visual_blocks" :key="i"
                    class="rounded-lg border border-border/30 bg-surface/20 p-3"
                  >
                    <div class="flex items-center gap-2 text-xs">
                      <span class="font-semibold text-foreground">{{ b.type || 'Block' }}</span>
                      <span v-if="b.selector" class="font-mono text-[10px] text-muted-foreground">{{ b.selector }}</span>
                      <Badge v-if="b.visible !== undefined" :variant="b.visible ? 'success' : 'default'" class="text-[9px] px-1.5 py-0">
                        {{ b.visible ? 'Visible' : 'Hidden' }}
                      </Badge>
                    </div>
                    <p v-if="b.content" class="mt-1 text-xs text-muted-foreground">{{ b.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </template>
  </div>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
