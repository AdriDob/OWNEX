<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  DollarSign,
  Play,
  Pause,
  Square,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  Zap,
  Shield,
  Eye,
} from 'lucide-vue'
import { api } from '@/lib/api'

// ── Types ──

interface WorkerStatus {
  state: string
  running: boolean
  goal: Record<string, unknown> | null
  work_item_count: number
  active_phases: string[]
}

interface WorkItem {
  id: string
  title: string
  phase: string
  state: string
  platform: string
  category: string
  estimated_reward_usd: number
  expected_value_usd_per_hour: number
  acceptance_probability: number
  human_action_required: boolean
  human_action_description: string
  error: string | null
  artifacts: string[]
  checkpoints: number
}

interface WorkerMetrics {
  cycles_completed: number
  work_completed: number
  work_failed: number
  total_revenue_usd: number
  avg_ev_usd_per_hour: number
  session_cost_usd: number
  circuit_breakers: Record<string, unknown>
}

interface AuditEntry {
  timestamp: string
  action: string
  workflow_id: string
  details: Record<string, unknown>
  level: string
}

// ── State ──

const status = ref<WorkerStatus | null>(null)
const metrics = ref<WorkerMetrics | null>(null)
const workItems = ref<WorkItem[]>([])
const auditEntries = ref<AuditEntry[]>([])
const loading = ref(true)
const actionLoading = ref<string | null>(null)
const expandedItem = ref<string | null>(null)
const showAudit = ref(false)
const refreshInterval = ref<number | null>(null)

// ── API calls ──

async function fetchAll() {
  try {
    const [sRes, mRes, wRes, aRes] = await Promise.allSettled([
      api.get<WorkerStatus>('/worker/status'),
      api.get<WorkerMetrics>('/worker/metrics'),
      api.get<{ items: WorkItem[] }>('/worker/work-items'),
      api.get<{ entries: AuditEntry[] }>('/worker/audit?limit=30'),
    ])
    if (sRes.status === 'fulfilled') status.value = sRes.value
    if (mRes.status === 'fulfilled') metrics.value = mRes.value
    if (wRes.status === 'fulfilled') workItems.value = wRes.value.items || []
    if (aRes.status === 'fulfilled') auditEntries.value = aRes.value.entries || []
  } catch {
    /* silent */
  }
  loading.value = false
}

async function workerAction(action: string) {
  actionLoading.value = action
  try {
    await api.post(`/worker/${action}`)
    await fetchAll()
  } catch (e) {
    console.warn(`[WorkerControl] ${action} failed:`, e)
  }
  actionLoading.value = null
}

async function approveWork(workId: string) {
  actionLoading.value = workId
  try {
    await api.post(`/worker/work-items/${workId}/approve`)
    await fetchAll()
  } catch (e) {
    console.warn('[WorkerControl] approve failed:', e)
  }
  actionLoading.value = null
}

async function rejectWork(workId: string) {
  actionLoading.value = workId
  try {
    await api.post(`/worker/work-items/${workId}/reject?reason=Rejected+from+UI`)
    await fetchAll()
  } catch (e) {
    console.warn('[WorkerControl] reject failed:', e)
  }
  actionLoading.value = null
}

// ── Formatting helpers ──

function stateColor(state: string) {
  switch (state) {
    case 'running': return 'text-emerald-400 bg-emerald-400/10'
    case 'paused': return 'text-amber-400 bg-amber-400/10'
    case 'stopped': return 'text-zinc-400 bg-zinc-400/10'
    case 'error': return 'text-red-400 bg-red-400/10'
    default: return 'text-zinc-400 bg-zinc-400/10'
  }
}

function phaseColor(phase: string) {
  const map: Record<string, string> = {
    discover: 'text-blue-400',
    evaluate: 'text-violet-400',
    select: 'text-amber-400',
    prepare: 'text-cyan-400',
    execute: 'text-emerald-400',
    validate: 'text-orange-400',
    deliver: 'text-green-400',
    learn: 'text-pink-400',
  }
  return map[phase] || 'text-zinc-400'
}

function formatUsd(n: number) {
  if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '$' + (n / 1_000).toFixed(1) + 'k'
  return '$' + (n || 0).toFixed(2)
}

function formatPct(n: number) {
  return ((n || 0) * 100).toFixed(0) + '%'
}

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts
  }
}

function toggleExpand(id: string) {
  expandedItem.value = expandedItem.value === id ? null : id
}

// ── Lifecycle ──

onMounted(() => {
  fetchAll()
  refreshInterval.value = window.setInterval(fetchAll, 15_000)
})

onUnmounted(() => {
  if (refreshInterval.value) clearInterval(refreshInterval.value)
})
</script>

<template>
  <div class="min-h-screen bg-background p-6">
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="font-display text-xl font-bold tracking-tight text-foreground">WorkerCore Control</h1>
        <p class="mt-1 font-mono text-xs text-muted-foreground">Autonomous work orchestrator — DISCOVER→EVALUATE→SELECT→PREPARE→EXECUTE→VALIDATE→DELIVER→LEARN</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="fetchAll"
          class="rounded-lg border border-border/50 bg-surface/50 px-3 py-1.5 font-mono text-xs text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
        >
          <RotateCcw class="mr-1 inline h-3 w-3" />Refresh
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex h-64 items-center justify-center">
      <div class="text-center">
        <Cpu class="mx-auto h-8 w-8 animate-pulse text-primary" />
        <p class="mt-2 font-mono text-xs text-muted-foreground">Loading worker status…</p>
      </div>
    </div>

    <template v-else>
      <!-- Status + Controls -->
      <div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <!-- Status Card -->
        <div class="rounded-xl border border-border/50 bg-surface/30 p-4">
          <div class="mb-3 flex items-center gap-2">
            <Activity class="h-4 w-4 text-muted-foreground" />
            <span class="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Status</span>
          </div>
          <div class="flex items-center gap-3">
            <span
              :class="[
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-xs font-semibold',
                stateColor(status?.state || 'unknown'),
              ]"
            >
              <span class="h-1.5 w-1.5 rounded-full bg-current" :class="status?.running ? 'animate-pulse' : ''" />
              {{ (status?.state || 'unknown').toUpperCase() }}
            </span>
          </div>
          <div class="mt-3 space-y-1.5">
            <div class="flex justify-between font-mono text-[11px]">
              <span class="text-muted-foreground">Active items</span>
              <span class="text-foreground">{{ status?.work_item_count || 0 }}</span>
            </div>
            <div class="flex justify-between font-mono text-[11px]">
              <span class="text-muted-foreground">Active phases</span>
              <span class="text-foreground">{{ status?.active_phases?.length || 0 }}</span>
            </div>
          </div>
        </div>

        <!-- Controls Card -->
        <div class="rounded-xl border border-border/50 bg-surface/30 p-4">
          <div class="mb-3 flex items-center gap-2">
            <Zap class="h-4 w-4 text-muted-foreground" />
            <span class="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Controls</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-if="!status?.running"
              @click="workerAction('start')"
              :disabled="actionLoading === 'start'"
              class="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/15 px-3 py-1.5 font-mono text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-500/25 disabled:opacity-50"
            >
              <Play class="h-3 w-3" />Start
            </button>
            <button
              v-if="status?.running"
              @click="workerAction('pause')"
              :disabled="actionLoading === 'pause'"
              class="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/15 px-3 py-1.5 font-mono text-xs font-medium text-amber-400 transition-colors hover:bg-amber-500/25 disabled:opacity-50"
            >
              <Pause class="h-3 w-3" />Pause
            </button>
            <button
              v-if="status?.state === 'paused'"
              @click="workerAction('resume')"
              :disabled="actionLoading === 'resume'"
              class="inline-flex items-center gap-1.5 rounded-lg bg-blue-500/15 px-3 py-1.5 font-mono text-xs font-medium text-blue-400 transition-colors hover:bg-blue-500/25 disabled:opacity-50"
            >
              <Play class="h-3 w-3" />Resume
            </button>
            <button
              v-if="status?.running || status?.state === 'paused'"
              @click="workerAction('stop')"
              :disabled="actionLoading === 'stop'"
              class="inline-flex items-center gap-1.5 rounded-lg bg-red-500/15 px-3 py-1.5 font-mono text-xs font-medium text-red-400 transition-colors hover:bg-red-500/25 disabled:opacity-50"
            >
              <Square class="h-3 w-3" />Stop
            </button>
          </div>
        </div>

        <!-- Metrics Card -->
        <div class="rounded-xl border border-border/50 bg-surface/30 p-4">
          <div class="mb-3 flex items-center gap-2">
            <DollarSign class="h-4 w-4 text-muted-foreground" />
            <span class="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Metrics</span>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <p class="font-mono text-[9px] uppercase text-muted-foreground">Cycles</p>
              <p class="font-mono text-sm font-bold text-foreground">{{ metrics?.cycles_completed || 0 }}</p>
            </div>
            <div>
              <p class="font-mono text-[9px] uppercase text-muted-foreground">Completed</p>
              <p class="font-mono text-sm font-bold text-emerald-400">{{ metrics?.work_completed || 0 }}</p>
            </div>
            <div>
              <p class="font-mono text-[9px] uppercase text-muted-foreground">Failed</p>
              <p class="font-mono text-sm font-bold text-red-400">{{ metrics?.work_failed || 0 }}</p>
            </div>
            <div>
              <p class="font-mono text-[9px] uppercase text-muted-foreground">Revenue</p>
              <p class="font-mono text-sm font-bold text-primary">{{ formatUsd(metrics?.total_revenue_usd || 0) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Work Items -->
      <div class="mb-6">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Cpu class="h-4 w-4 text-muted-foreground" />
            <span class="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">Work Items</span>
            <span class="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-[10px] font-bold text-primary">{{ workItems.length }}</span>
          </div>
          <button
            @click="showAudit = !showAudit"
            class="flex items-center gap-1 rounded-lg border border-border/50 bg-surface/50 px-2.5 py-1 font-mono text-[10px] text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
          >
            <Eye class="h-3 w-3" />
            {{ showAudit ? 'Hide Audit' : 'Show Audit' }}
          </button>
        </div>

        <!-- Empty state -->
        <div
          v-if="workItems.length === 0"
          class="rounded-xl border border-border/30 bg-surface/20 p-8 text-center"
        >
          <Cpu class="mx-auto h-10 w-10 text-muted-foreground/30" />
          <p class="mt-3 font-mono text-sm text-muted-foreground">No work items yet</p>
          <p class="mt-1 font-mono text-[11px] text-muted-foreground/60">Start the worker to begin discovering opportunities</p>
        </div>

        <!-- Work items list -->
        <div v-else class="space-y-2">
          <div
            v-for="item in workItems"
            :key="item.id"
            class="rounded-xl border border-border/50 bg-surface/30 transition-colors hover:bg-surface/50"
          >
            <!-- Item header -->
            <div
              @click="toggleExpand(item.id)"
              class="flex cursor-pointer items-center gap-3 px-4 py-3"
            >
              <component
                :is="expandedItem === item.id ? ChevronDown : ChevronRight"
                class="h-4 w-4 shrink-0 text-muted-foreground"
              />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="truncate font-mono text-sm font-medium text-foreground">{{ item.title || item.id }}</span>
                  <span
                    v-if="item.human_action_required"
                    class="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 font-mono text-[9px] font-bold text-amber-400"
                  >
                    <AlertTriangle class="h-2.5 w-2.5" />APPROVAL NEEDED
                  </span>
                </div>
                <div class="mt-1 flex items-center gap-3 font-mono text-[10px] text-muted-foreground">
                  <span :class="phaseColor(item.phase)">{{ item.phase?.toUpperCase() }}</span>
                  <span>{{ item.platform || '—' }}</span>
                  <span>{{ item.category || '—' }}</span>
                </div>
              </div>
              <div class="flex items-center gap-4 text-right">
                <div>
                  <p class="font-mono text-xs font-bold text-primary">{{ formatUsd(item.estimated_reward_usd) }}</p>
                  <p class="font-mono text-[9px] text-muted-foreground">{{ formatPct(item.acceptance_probability) }} prob</p>
                </div>
                <div v-if="item.human_action_required" class="flex gap-1">
                  <button
                    @click.stop="approveWork(item.id)"
                    :disabled="actionLoading === item.id"
                    class="rounded-lg bg-emerald-500/15 p-1.5 text-emerald-400 transition-colors hover:bg-emerald-500/25 disabled:opacity-50"
                    title="Approve"
                  >
                    <ThumbsUp class="h-3.5 w-3.5" />
                  </button>
                  <button
                    @click.stop="rejectWork(item.id)"
                    :disabled="actionLoading === item.id"
                    class="rounded-lg bg-red-500/15 p-1.5 text-red-400 transition-colors hover:bg-red-500/25 disabled:opacity-50"
                    title="Reject"
                  >
                    <ThumbsDown class="h-3.5 w-3.5" />
                  </button>
                </div>
                <span
                  v-else
                  :class="[
                    'rounded-full px-2 py-0.5 font-mono text-[9px] font-semibold',
                    item.state === 'completed' ? 'bg-emerald-500/10 text-emerald-400' :
                    item.state === 'failed' ? 'bg-red-500/10 text-red-400' :
                    item.state === 'executing' ? 'bg-blue-500/10 text-blue-400' :
                    'bg-zinc-500/10 text-zinc-400',
                  ]"
                >
                  {{ item.state?.toUpperCase() }}
                </span>
              </div>
            </div>

            <!-- Expanded details -->
            <div
              v-if="expandedItem === item.id"
              class="border-t border-border/30 px-4 py-3"
            >
              <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div>
                  <p class="font-mono text-[9px] uppercase text-muted-foreground">EV/Hour</p>
                  <p class="font-mono text-xs font-medium text-foreground">{{ formatUsd(item.expected_value_usd_per_hour) }}</p>
                </div>
                <div>
                  <p class="font-mono text-[9px] uppercase text-muted-foreground">Checkpoints</p>
                  <p class="font-mono text-xs font-medium text-foreground">{{ item.checkpoints }}</p>
                </div>
                <div>
                  <p class="font-mono text-[9px] uppercase text-muted-foreground">Artifacts</p>
                  <p class="font-mono text-xs font-medium text-foreground">{{ item.artifacts?.length || 0 }}</p>
                </div>
                <div v-if="item.error">
                  <p class="font-mono text-[9px] uppercase text-red-400">Error</p>
                  <p class="font-mono text-xs text-red-400">{{ item.error }}</p>
                </div>
              </div>
              <div v-if="item.human_action_description" class="mt-3 rounded-lg bg-amber-500/5 border border-amber-500/20 px-3 py-2">
                <p class="font-mono text-[10px] text-amber-400">{{ item.human_action_description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Audit Trail -->
      <div v-if="showAudit">
        <div class="mb-3 flex items-center gap-2">
          <Shield class="h-4 w-4 text-muted-foreground" />
          <span class="font-mono text-xs font-bold uppercase tracking-wider text-muted-foreground">Audit Trail</span>
          <span class="rounded-full bg-zinc-500/10 px-2 py-0.5 font-mono text-[10px] text-zinc-400">{{ auditEntries.length }}</span>
        </div>
        <div class="rounded-xl border border-border/50 bg-surface/30 overflow-hidden">
          <div
            v-for="(entry, i) in auditEntries"
            :key="i"
            :class="[
              'flex items-center gap-3 px-4 py-2.5 font-mono text-[11px]',
              i < auditEntries.length - 1 ? 'border-b border-border/20' : '',
            ]"
          >
            <Clock class="h-3 w-3 shrink-0 text-muted-foreground/50" />
            <span class="w-20 shrink-0 text-muted-foreground">{{ formatTime(entry.timestamp) }}</span>
            <span
              :class="[
                'shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold',
                entry.level === 'error' ? 'bg-red-500/10 text-red-400' :
                entry.level === 'warning' ? 'bg-amber-500/10 text-amber-400' :
                'bg-zinc-500/10 text-zinc-400',
              ]"
            >
              {{ entry.action }}
            </span>
            <span class="flex-1 truncate text-muted-foreground">{{ entry.workflow_id || '—' }}</span>
          </div>
          <div
            v-if="auditEntries.length === 0"
            class="px-4 py-6 text-center font-mono text-xs text-muted-foreground/50"
          >
            No audit entries yet
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
