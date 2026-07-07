<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import {
  ListTodo, Plus, Trash2, Play, CheckCircle2, Clock, AlertTriangle,
  Loader2, RefreshCw, ArrowUp, ArrowDown, XCircle, Pause,
} from '@lucide/vue'

interface Task {
  id: string
  title: string
  description?: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'in_progress' | 'waiting' | 'completed'
  created_at?: string
  updated_at?: string
}

type StatusFilter = 'all' | 'pending' | 'in_progress' | 'waiting' | 'completed'

const loading = ref(true)
const error = ref('')
const tasks = ref<Task[]>([])
const statusFilter = ref<StatusFilter>('all')

const showForm = ref(false)
const newTitle = ref('')
const newDescription = ref('')
const newPriority = ref<Task['priority']>('medium')
const saving = ref(false)
const formError = ref('')

const priorityColors: Record<string, string> = {
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  critical: 'bg-destructive/10 text-destructive border-destructive/20',
}

const statusColors: Record<string, 'default' | 'info' | 'warning' | 'success'> = {
  pending: 'default',
  in_progress: 'info',
  waiting: 'warning',
  completed: 'success',
}

const filteredTasks = computed(() => {
  if (statusFilter.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === statusFilter.value)
})

const statusLabels = ['all', 'pending', 'in_progress', 'waiting', 'completed'] as const

const statusCount = computed(() => {
  const counts: Record<string, number> = { all: tasks.value.length }
  for (const s of statusLabels) if (s !== 'all') counts[s] = tasks.value.filter(t => t.status === s).length
  return counts
})

const doughnutLabels = computed(() => statusLabels.filter(s => s !== 'all'))
const doughnutData = computed(() => doughnutLabels.value.map(s => statusCount.value[s] || 0))

const priorityLabels = ['low', 'medium', 'high', 'critical']
const priorityData = computed(() => priorityLabels.map(p => tasks.value.filter(t => t.priority === p).length))

async function loadTasks() {
  loading.value = true
  error.value = ''
  try {
    const params = statusFilter.value !== 'all' ? { status: statusFilter.value } : undefined
    const res = await api.get<{ tasks: Task[] }>('/system/tasks', params as any)
    tasks.value = res.tasks || []
  } catch (e: any) {
    error.value = e.message || 'Failed to load tasks'
  } finally {
    loading.value = false
  }
}

async function createTask() {
  if (!newTitle.value.trim()) {
    formError.value = 'Title is required'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    await api.post('/system/tasks', {
      title: newTitle.value,
      description: newDescription.value,
      priority: newPriority.value,
    })
    newTitle.value = ''
    newDescription.value = ''
    newPriority.value = 'medium'
    showForm.value = false
    await loadTasks()
  } catch (e: any) {
    formError.value = e.message || 'Failed to create task'
  } finally {
    saving.value = false
  }
}

async function updateTaskStatus(id: string, status: Task['status']) {
  try {
    await api.patch(`/system/tasks/${id}`, { status })
    const task = tasks.value.find(t => t.id === id)
    if (task) task.status = status
  } catch { /* ignore */ }
}

async function updateTaskPriority(id: string, priority: Task['priority']) {
  try {
    await api.patch(`/system/tasks/${id}`, { priority })
    const task = tasks.value.find(t => t.id === id)
    if (task) task.priority = priority
  } catch { /* ignore */ }
}

async function deleteTask(id: string) {
  try {
    await api.delete(`/system/tasks/${id}`)
    tasks.value = tasks.value.filter(t => t.id !== id)
  } catch { /* ignore */ }
}

function onFilterChange(filter: StatusFilter) {
  statusFilter.value = filter
  loadTasks()
}

onMounted(loadTasks)
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading">
      <div class="space-y-4">
        <Skeleton class="h-6 w-56" />
        <div class="flex gap-2"><Skeleton v-for="i in 4" :key="i" class="h-8 w-20 rounded-lg" /></div>
        <Skeleton v-for="i in 3" :key="i" class="h-16 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error loading tasks</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="loadTasks">
          <RefreshCw class="h-3.5 w-3.5" /> Retry
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between animate-in">
        <div class="space-y-1 min-w-0">
          <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">Operations</p>
          <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Task Queue</h1>
          <p class="text-xs text-muted-foreground">{{ tasks.length }} tasks</p>
        </div>
        <Button @click="showForm = !showForm" variant="default" size="sm" class="shrink-0">
          <Plus class="h-4 w-4" /> New Task
        </Button>
      </div>

      <div v-if="showForm" class="animate-in glass-fintech rounded-xl p-4 space-y-3">
        <p class="text-xs font-semibold text-foreground">Create New Task</p>
        <input
          v-model="newTitle"
          placeholder="Task title"
          class="w-full rounded-lg border border-border/60 bg-[#0a0a0a]/60 px-3 py-2 text-xs text-foreground"
        />
        <textarea
          v-model="newDescription"
          placeholder="Description (optional)"
          rows="2"
          class="w-full rounded-lg border border-border/60 bg-[#0a0a0a]/60 px-3 py-2 text-xs text-foreground resize-none"
        />
        <div class="flex items-center gap-3">
          <select
            v-model="newPriority"
            class="rounded-lg border border-border/60 bg-[#0a0a0a]/60 px-3 py-2 text-xs text-foreground"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <div v-if="formError" class="text-[10px] text-destructive">{{ formError }}</div>
        </div>
        <div class="flex gap-2">
          <Button size="sm" :disabled="saving" @click="createTask">
            <Loader2 v-if="saving" class="h-3 w-3 animate-spin" />
            <CheckCircle2 v-else class="h-3 w-3" />
            {{ saving ? 'Creating...' : 'Create' }}
          </Button>
          <Button variant="ghost" size="sm" @click="showForm = false">Cancel</Button>
        </div>
      </div>

      <div class="flex gap-1 border-b border-border/30 animate-in">
        <button
          v-for="s in statusLabels" :key="s"
          @click="onFilterChange(s)"
          :class="[
            'px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5',
            statusFilter === s ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
          ]"
        >
          {{ s === 'all' ? 'All' : s.replace('_', ' ') }}
          <span class="text-[9px] text-muted-foreground">({{ statusCount[s] }})</span>
        </button>
      </div>

      <div v-if="tasks.length === 0" class="flex flex-col items-center py-16 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <ListTodo class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No tasks yet</p>
        <p class="mt-1 text-xs text-muted-foreground">Create your first task to get started</p>
        <Button variant="outline" size="sm" class="mt-4" @click="showForm = true">
          <Plus class="h-3.5 w-3.5" /> Create Task
        </Button>
      </div>

      <div v-else class="grid gap-6 lg:grid-cols-3 animate-in">
        <div class="lg:col-span-2 space-y-2">
          <div
            v-for="task in filteredTasks" :key="task.id"
            class="glass-fintech rounded-xl p-4 transition-all hover:border-primary/20"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <p class="text-sm font-semibold text-foreground truncate">{{ task.title }}</p>
                  <Badge :variant="statusColors[task.status]" class="text-[8px]">{{ task.status.replace('_', ' ') }}</Badge>
                </div>
                <p v-if="task.description" class="mt-0.5 text-xs text-muted-foreground line-clamp-2">{{ task.description }}</p>
                <div class="mt-2 flex items-center gap-2 text-[9px] text-muted-foreground">
                  <Clock class="h-3 w-3" />
                  {{ task.created_at ? new Date(task.created_at).toLocaleDateString() : '—' }}
                  <span v-if="task.updated_at">· updated {{ new Date(task.updated_at).toLocaleDateString() }}</span>
                </div>
              </div>
              <div class="flex items-center gap-2 ml-3">
                <span :class="['rounded-md border px-2 py-0.5 text-[9px] font-semibold', priorityColors[task.priority]]">
                  {{ task.priority }}
                </span>
                <button
                  v-if="task.status !== 'completed'"
                  @click="updateTaskStatus(task.id, 'completed')"
                  class="text-muted-foreground hover:text-success transition-colors"
                  title="Complete"
                >
                  <CheckCircle2 class="h-3.5 w-3.5" />
                </button>
                <button
                  @click="deleteTask(task.id)"
                  class="text-muted-foreground hover:text-destructive transition-colors"
                  title="Delete"
                >
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div class="mt-3 flex gap-2 flex-wrap">
              <template v-if="task.status !== 'in_progress' && task.status !== 'completed'">
                <Button variant="outline" size="sm" class="text-[9px]" @click="updateTaskStatus(task.id, 'in_progress')">
                  <Play class="h-3 w-3" /> Start
                </Button>
              </template>
              <template v-if="task.status !== 'waiting' && task.status !== 'completed'">
                <Button variant="ghost" size="sm" class="text-[9px]" @click="updateTaskStatus(task.id, 'waiting')">
                  <Pause class="h-3 w-3" /> Wait
                </Button>
              </template>
              <div class="flex gap-1 ml-auto">
                <button
                  v-if="task.priority !== 'low'"
                  @click="updateTaskPriority(task.id, task.priority === 'critical' ? 'high' : task.priority === 'high' ? 'medium' : 'low')"
                  class="rounded-md border border-border/40 px-1.5 py-0.5 text-[8px] text-muted-foreground hover:text-foreground"
                >
                  <ArrowDown class="h-2.5 w-2.5 inline" /> Priority
                </button>
                <button
                  v-if="task.priority !== 'critical'"
                  @click="updateTaskPriority(task.id, task.priority === 'low' ? 'medium' : task.priority === 'medium' ? 'high' : 'critical')"
                  class="rounded-md border border-border/40 px-1.5 py-0.5 text-[8px] text-muted-foreground hover:text-foreground"
                >
                  <ArrowUp class="h-2.5 w-2.5 inline" /> Priority
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <Card class="p-4 animate-in space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <ListTodo class="h-3.5 w-3.5 text-primary" />
              Status Distribution
            </h3>
            <DoughnutChart
              v-if="doughnutData.some(d => d > 0)"
              :labels="doughnutLabels.map(l => l.replace('_', ' '))"
              :data="doughnutData"
              :height="200"
              :cutout="'65%'"
            />
            <div v-else class="py-6 text-center text-[10px] text-muted-foreground">No data</div>
          </Card>

          <Card class="p-4 animate-in space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <AlertTriangle class="h-3.5 w-3.5 text-primary" />
              Priority Breakdown
            </h3>
            <BarChart
              v-if="priorityData.some(d => d > 0)"
              :labels="priorityLabels"
              :datasets="[{ label: 'Tasks', data: priorityData }]"
              :height="200"
              :show-legend="false"
              y-label="Count"
            />
            <div v-else class="py-6 text-center text-[10px] text-muted-foreground">No data</div>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>
