<script setup lang="ts">
/**
 * Reports — Consolidated page with tabs.
 * Combines: ReportQueue + ReportCenter + ReportHistory
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { FileText, Clock, History, Plus, Send, Eye } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'

const router = useRouter()
const activeTab = ref('queue')

interface Report {
  id: string
  title: string
  platform: string
  status: 'draft' | 'review' | 'submitted' | 'accepted' | 'rejected'
  severity: string
  created_at: string
  updated_at: string
}

const reports = ref<Report[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function fetchReports() {
  loading.value = true
  try {
    const res = await fetch('/api/reports')
    const data = await res.json()
    reports.value = data.reports || []
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const queueReports = computed(() => reports.value.filter(r => r.status === 'draft' || r.status === 'review'))
const submittedReports = computed(() => reports.value.filter(r => r.status === 'submitted'))
const historyReports = computed(() => reports.value.filter(r => r.status === 'accepted' || r.status === 'rejected'))

const tabs = computed(() => [
  { id: 'queue', label: 'Cola', icon: Clock, badge: queueReports.value.length || undefined },
  { id: 'center', label: 'Centro', icon: FileText, badge: submittedReports.value.length || undefined },
  { id: 'history', label: 'Historial', icon: History },
])

function statusColor(status: string) {
  const colors: Record<string, string> = {
    draft: 'bg-muted text-muted-foreground',
    review: 'bg-yellow-500/10 text-yellow-400',
    submitted: 'bg-blue-500/10 text-blue-400',
    accepted: 'bg-emerald-500/10 text-emerald-400',
    rejected: 'bg-red-500/10 text-red-400',
  }
  return colors[status] || 'bg-muted'
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: 'short' })
}

fetchReports()
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Reportes</h1>
        <p class="text-sm text-muted-foreground">Gestioná tus reportes de vulnerabilidades</p>
      </div>
      <button
        class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        @click="router.push('/reports/new')"
      >
        <Plus class="h-4 w-4" />
        Nuevo Reporte
      </button>
    </div>

    <!-- Tabs -->
    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Queue Tab -->
      <template #queue>
        <div v-if="loading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-20 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else-if="queueReports.length === 0" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <FileText class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">No hay reportes pendientes</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Los reportes se generan al confirmar findings</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="report in queueReports"
            :key="report.id"
            class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/50 p-4 transition-colors hover:border-primary/30 cursor-pointer"
            @click="router.push(`/reports/${report.id}`)"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-foreground">{{ report.title }}</p>
              <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span>{{ report.platform }}</span>
                <span>·</span>
                <span>{{ formatDate(report.updated_at) }}</span>
              </div>
            </div>
            <span :class="['rounded-full px-2 py-0.5 text-[10px] font-mono', statusColor(report.status)]">
              {{ report.status }}
            </span>
          </div>
        </div>
      </template>

      <!-- Center Tab -->
      <template #center>
        <div v-if="submittedReports.length === 0" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <Send class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">No hay reportes enviados</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Enviá reportes desde la cola para verlos acá</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="report in submittedReports"
            :key="report.id"
            class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/50 p-4 transition-colors hover:border-primary/30 cursor-pointer"
            @click="router.push(`/reports/${report.id}`)"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-foreground">{{ report.title }}</p>
              <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span>{{ report.platform }}</span>
                <span>·</span>
                <span>{{ formatDate(report.updated_at) }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span :class="['rounded-full px-2 py-0.5 text-[10px] font-mono', statusColor(report.status)]">
                {{ report.status }}
              </span>
              <Eye class="h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </div>
      </template>

      <!-- History Tab -->
      <template #history>
        <div v-if="historyReports.length === 0" class="rounded-xl border border-dashed border-border/30 p-8 text-center">
          <History class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Sin historial aún</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Aparecerán acá los reportes aceptados y rechazados</p>
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="report in historyReports"
            :key="report.id"
            class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/50 p-4 transition-colors hover:border-primary/30 cursor-pointer"
            @click="router.push(`/reports/${report.id}`)"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-foreground">{{ report.title }}</p>
              <div class="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                <span>{{ report.platform }}</span>
                <span>·</span>
                <span>{{ formatDate(report.updated_at) }}</span>
              </div>
            </div>
            <span :class="['rounded-full px-2 py-0.5 text-[10px] font-mono', statusColor(report.status)]">
              {{ report.status }}
            </span>
          </div>
        </div>
      </template>
    </Tabs>
  </div>
</template>
