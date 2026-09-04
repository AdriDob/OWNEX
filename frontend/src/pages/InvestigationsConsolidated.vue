<script setup lang="ts">
/**
 * Investigations — Consolidated page with tabs.
 * Combines: InvestigationCenter + InvestigationDetail
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Eye, ArrowLeft, RefreshCw, Calendar, Shield, Target } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'

const router = useRouter()
const activeTab = ref('list')
const loading = ref(true)
const investigations = ref<any[]>([])
const selectedId = ref<string | null>(null)
const detail = ref<any>(null)

async function fetchData() {
  loading.value = true
  try {
    const res = await fetch('/api/investigations')
    const data = await res.json()
    investigations.value = data.investigations || []
  } catch { /* silent */ }
  loading.value = false
}

async function loadDetail(id: string) {
  selectedId.value = id
  activeTab.value = 'detail'
  try {
    const res = await fetch(`/api/investigations/${id}`)
    detail.value = await res.json()
  } catch { /* silent */ }
}

function goBack() {
  selectedId.value = null
  detail.value = null
  activeTab.value = 'list'
}

const tabs = computed(() => [
  { id: 'list', label: 'Lista', icon: Search, badge: investigations.value.length || undefined },
  { id: 'detail', label: 'Detalle', icon: Eye, disabled: !selectedId },
])

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: '2-digit' })
}

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-background p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Investigaciones</h1>
        <p class="text-sm text-muted-foreground">Investigaciones activas y historial</p>
      </div>
      <button
        class="flex items-center gap-1.5 rounded-lg border border-border/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        @click="fetchData"
      >
        <RefreshCw class="h-3 w-3" /> Refresh
      </button>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- List -->
      <template #list>
        <div v-if="loading" class="space-y-3">
          <div v-for="i in 5" :key="i" class="h-16 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else-if="investigations.length === 0" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <Search class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Sin investigaciones</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Las investigaciones se crean desde findings</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="inv in investigations"
            :key="inv.id"
            class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/50 p-4 transition-colors hover:border-primary/30 cursor-pointer"
            @click="loadDetail(inv.id)"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-foreground">{{ inv.title || inv.name }}</p>
              <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <Calendar class="h-3 w-3" />
                <span>{{ formatDate(inv.created_at) }}</span>
                <span>·</span>
                <span>{{ inv.status || 'active' }}</span>
              </div>
            </div>
            <Eye class="h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      </template>

      <!-- Detail -->
      <template #detail>
        <div v-if="!detail" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <Eye class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Seleccioná una investigación</p>
        </div>
        <div v-else class="space-y-4">
          <button
            class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            @click="goBack"
          >
            <ArrowLeft class="h-3 w-3" /> Volver a lista
          </button>

          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h2 class="text-lg font-semibold text-foreground">{{ detail.title || detail.name }}</h2>
            <p class="mt-1 text-xs text-muted-foreground">{{ detail.description || 'No description' }}</p>
          </div>

          <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div class="rounded-lg border border-border/20 p-3">
              <p class="text-[10px] font-mono text-muted-foreground">Status</p>
              <p class="mt-1 text-sm font-medium text-foreground">{{ detail.status || 'active' }}</p>
            </div>
            <div class="rounded-lg border border-border/20 p-3">
              <p class="text-[10px] font-mono text-muted-foreground">Findings</p>
              <p class="mt-1 text-sm font-medium text-foreground">{{ detail.findings?.length || 0 }}</p>
            </div>
            <div class="rounded-lg border border-border/20 p-3">
              <p class="text-[10px] font-mono text-muted-foreground">Evidence</p>
              <p class="mt-1 text-sm font-medium text-foreground">{{ detail.evidence?.length || 0 }}</p>
            </div>
          </div>
        </div>
      </template>
    </Tabs>
  </div>
</template>
