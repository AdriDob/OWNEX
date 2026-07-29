<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { FileText, Download, Edit, ExternalLink, Clock, AlertTriangle, DollarSign, TrendingUp } from '@lucide/vue'
import { api } from '@/lib/api'

interface ReportCandidate {
  finding_id: number
  title: string
  severity: string
  vulnerability_type: string
  target: string
  domain: string
  program: string
  platform: string
  platform_url: string
  cvss: number
  evh: number
  confidence: number
  estimated_reward: number
  score: number
  discovered_at: string
}

interface ReportItem {
  finding_id: number
  title: string
  severity: string
  program: string
  platform: string
  submit_url: string
  estimated_reward: number
  evh: number
  file_path: string
  edited_at: string
}

interface PipelineData {
  daily: { candidates: ReportCandidate[]; count: number }
  weekly: { candidates: ReportCandidate[]; count: number }
  ready: { reports: ReportItem[]; count: number }
}

const pipeline = ref<PipelineData | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const activeTab = ref<'daily' | 'weekly' | 'ready'>('daily')

const sevColor = (sev: string) => {
  const c = sev.toLowerCase()
  if (c === 'critical') return 'text-red-400'
  if (c === 'high') return 'text-orange-400'
  if (c === 'medium') return 'text-yellow-400'
  if (c === 'low') return 'text-green-400'
  return 'text-blue-400'
}

const sevBadge = (sev: string) => {
  const c = sev.toLowerCase()
  if (c === 'critical') return 'bg-red-500/20 text-red-400'
  if (c === 'high') return 'bg-orange-500/20 text-orange-400'
  if (c === 'medium') return 'bg-yellow-500/20 text-yellow-400'
  if (c === 'low') return 'bg-green-500/20 text-green-400'
  return 'bg-blue-500/20 text-blue-400'
}

async function loadPipeline() {
  loading.value = true
  error.value = null
  try {
    const [daily, weekly, ready] = await Promise.all([
      api.get('/reports/pipeline/daily', { limit: 7 }),
      api.get('/reports/pipeline/weekly', { limit: 15 }),
      api.get('/reports/pipeline/ready'),
    ])
    pipeline.value = {
      daily: { candidates: daily.candidates || [], count: daily.count || 0 },
      weekly: { candidates: weekly.candidates || [], count: weekly.count || 0 },
      ready: { reports: ready.reports || [], count: ready.count || 0 },
    }
  } catch (e: any) {
    error.value = e.message || 'Failed to load report pipeline'
  } finally {
    loading.value = false
  }
}

async function generateReport(findingId: number) {
  try {
    const res = await api.post(`/reports/pipeline/generate/${findingId}`)
    await loadPipeline()
    return res
  } catch (e: any) {
    error.value = e.message || 'Failed to generate report'
    throw e
  }
}

async function downloadReport(findingId: number, format: 'markdown' | 'json' = 'markdown') {
  try {
    const res = await api.get(`/reports/pipeline/${findingId}/download`, { format }, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${findingId}.${format === 'markdown' ? 'md' : 'json'}`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (e: any) {
    error.value = e.message || 'Failed to download report'
  }
}

async function openSubmitUrl(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

onMounted(() => {
  loadPipeline()
  const interval = setInterval(loadPipeline, 60000)
  return () => clearInterval(interval)
})
</script>

<template>
  <div class="space-y-6 animate-in">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="font-display text-lg font-bold text-foreground">Report Pipeline</h2>
        <p class="text-xs text-muted-foreground">Findings → Reports → Manual Submit</p>
      </div>
      <button @click="loadPipeline" :disabled="loading" class="btn-ghost btn-sm flex items-center gap-1">
        <Clock class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
        Refresh
      </button>
    </div>

    <div v-if="error" class="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/30 px-3 py-2 text-xs text-destructive">
      <AlertTriangle class="h-3.5 w-3.5 shrink-0" />
      <span>{{ error }}</span>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 rounded-lg bg-surface/20 border border-border/30 p-1" role="tablist">
      <button
        @click="activeTab = 'daily'"
        :class="['px-3 py-1.5 rounded-md text-xs font-medium transition-colors', activeTab === 'daily' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground']"
        role="tab"
        :aria-selected="activeTab === 'daily'"
      >
        Top 7 Today
      </button>
      <button
        @click="activeTab = 'weekly'"
        :class="['px-3 py-1.5 rounded-md text-xs font-medium transition-colors', activeTab === 'weekly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground']"
        role="tab"
        :aria-selected="activeTab === 'weekly'"
      >
        Top 15 This Week
      </button>
      <button
        @click="activeTab = 'ready'"
        :class="['px-3 py-1.5 rounded-md text-xs font-medium transition-colors', activeTab === 'ready' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground']"
        role="tab"
        :aria-selected="activeTab === 'ready'"
      >
        Ready to Submit ({{ pipeline?.ready?.count || 0 }})
      </button>
    </div>

    <!-- Content -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent" />
    </div>

    <template v-else-if="activeTab === 'daily'">
      <ReportCandidateList
        :candidates="pipeline?.daily?.candidates || []"
        title="Top 7 Reports Ready Today"
        @generate="generateReport"
        @download="downloadReport"
        @submit="openSubmitUrl"
      />
    </template>

    <template v-else-if="activeTab === 'weekly'">
      <ReportCandidateList
        :candidates="pipeline?.weekly?.candidates || []"
        title="Top 15 Reports This Week"
        @generate="generateReport"
        @download="downloadReport"
        @submit="openSubmitUrl"
      />
    </template>

    <template v-else>
      <ReadyReportsList
        :reports="pipeline?.ready?.reports || []"
        @download="downloadReport"
        @submit="openSubmitUrl"
      />
    </template>
  </div>
</template>

<script lang="ts">
// Child components defined inline for simplicity
import { defineComponent, h } from 'vue'
import { FileText, Download, Edit, ExternalLink, DollarSign, TrendingUp, Clock, AlertTriangle } from '@lucide/vue'

const ReportCandidateList = defineComponent({
  props: {
    candidates: { type: Array, default: () => [] },
    title: { type: String, default: '' },
  },
  emits: ['generate', 'download', 'submit'],
  setup(props, { emit }) {
    const handleGenerate = async (id: number) => {
      await emit('generate', id)
    }
    return () => h('div', { class: 'space-y-3' }, [
      props.candidates.length === 0
        ? h('div', { class: 'text-center py-8 text-muted-foreground text-sm' }, 'No eligible findings yet. Run scans to discover vulnerabilities.')
        : props.candidates.map((c: any) => h('div', {
          key: c.finding_id,
          class: 'panel rounded-xl p-4 space-y-3'
        }, [
          h('div', { class: 'flex items-start justify-between gap-3' }, [
            h('div', { class: 'flex-1 min-w-0' }, [
              h('div', { class: 'flex items-center gap-2 flex-wrap' }, [
                h('h3', { class: 'font-medium text-sm truncate' }, c.title),
                h('span', { class: `px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${sevBadge(c.severity)}` }, c.severity.toUpperCase()),
                h('span', { class: 'px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-400' }, c.platform),
              ]),
              h('div', { class: 'flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap' }, [
                h('span', { class: 'flex items-center gap-1' }, [h(DollarSign, { class: 'h-3 w-3' }), `$${c.estimated_reward.toLocaleString()}`]),
                h('span', { class: 'flex items-center gap-1' }, [h(TrendingUp, { class: 'h-3 w-3' }), `$${c.evh}/hr EVH`]),
                h('span', { class: 'flex items-center gap-1' }, [h(Clock, { class: 'h-3 w-3' }), `${(c.confidence * 100).toFixed(0)}% conf`]),
                h('span', { class: 'flex items-center gap-1' }, [h(FileText, { class: 'h-3 w-3' }), c.vulnerability_type]),
              ]),
            ]),
            h('div', { class: 'flex items-center gap-1 shrink-0' }, [
              h('button', {
                onClick: () => handleGenerate(c.finding_id),
                class: 'btn-primary btn-xs flex items-center gap-1 px-2 py-1',
                title: 'Generate Report'
              }, [h(FileText, { class: 'h-3 w-3' }), ' Generate']),
            ]),
          ]),
        ])),
    ])
  },
})

const ReadyReportsList = defineComponent({
  props: {
    reports: { type: Array, default: () => [] },
  },
  emits: ['download', 'submit'],
  setup(props, { emit }) {
    return () => h('div', { class: 'space-y-3' }, [
      props.reports.length === 0
        ? h('div', { class: 'text-center py-8 text-muted-foreground text-sm' }, 'No reports ready. Generate and edit reports from the Daily/Weekly tabs.')
        : props.reports.map((r: any) => h('div', {
          key: r.finding_id,
          class: 'panel rounded-xl p-4 space-y-3 border-success/30'
        }, [
          h('div', { class: 'flex items-start justify-between gap-3' }, [
            h('div', { class: 'flex-1 min-w-0' }, [
              h('div', { class: 'flex items-center gap-2 flex-wrap' }, [
                h('h3', { class: 'font-medium text-sm truncate' }, r.title),
                h('span', { class: `px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${sevBadge(r.severity)}` }, r.severity.toUpperCase()),
                h('span', { class: 'px-1.5 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-400' }, r.platform),
              ]),
              h('div', { class: 'flex items-center gap-3 mt-1 text-xs text-muted-foreground flex-wrap' }, [
                h('span', { class: 'flex items-center gap-1' }, [h(DollarSign, { class: 'h-3 w-3' }), `$${r.estimated_reward.toLocaleString()}`]),
                h('span', { class: 'flex items-center gap-1' }, [h(TrendingUp, { class: 'h-3 w-3' }), `$${r.evh}/hr`]),
                h('span', { class: 'flex items-center gap-1' }, [h(Clock, { class: 'h-3 w-3' }), `Edited: ${new Date(r.edited_at).toLocaleString()}`]),
              ]),
            ]),
            h('div', { class: 'flex items-center gap-1 shrink-0' }, [
              h('button', {
                onClick: () => emit('download', r.finding_id, 'markdown'),
                class: 'btn-ghost btn-xs flex items-center gap-1 px-2 py-1',
                title: 'Download Markdown'
              }, [h(Download, { class: 'h-3 w-3' }), ' MD']),
              h('button', {
                onClick: () => emit('download', r.finding_id, 'json'),
                class: 'btn-ghost btn-xs flex items-center gap-1 px-2 py-1',
                title: 'Download JSON'
              }, [h(Download, { class: 'h-3 w-3' }), ' JSON']),
              h('a', {
                href: r.submit_url,
                target: '_blank',
                rel: 'noopener noreferrer',
                class: 'btn-primary btn-xs flex items-center gap-1 px-2 py-1',
                title: 'Submit Manually on Platform'
              }, [h(ExternalLink, { class: 'h-3 w-3' }), ' Submit']),
            ]),
          ]),
        ])),
    ])
  },
})

// Severity helpers (duplicate for inline components)
const sevBadge = (sev: string) => {
  const c = sev.toLowerCase()
  if (c === 'critical') return 'bg-red-500/20 text-red-400'
  if (c === 'high') return 'bg-orange-500/20 text-orange-400'
  if (c === 'medium') return 'bg-yellow-500/20 text-yellow-400'
  if (c === 'low') return 'bg-green-500/20 text-green-400'
  return 'bg-blue-500/20 text-blue-400'
}
</script>

<style scoped>
.panel {
  background: rgba(24, 24, 27, 0.3);
  border: 1px solid rgba(39, 39, 42, 0.8);
}
.btn-primary {
  background: #2563eb;
  color: white;
}
.btn-primary:hover {
  background: #3b82f6;
}
.btn-ghost {
  background: transparent;
  border: 1px solid rgba(39, 39, 42, 0.8);
}
.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.05);
}
.btn-xs {
  padding: 0.25rem 0.5rem;
  font-size: 10px;
  font-family: ui-monospace, monospace;
}
</style>