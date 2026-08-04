<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/lib/api'
import { RefreshCw, CheckCircle, Clock, DollarSign, AlertCircle, ExternalLink, Filter } from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

interface Task {
  id: string
  platform: string
  platform_id: string
  title: string
  description: string
  status: string
  priority: string
  reward: number
  estimated_hours: number
  platform_url: string
  submission_url?: string
  deadline?: string
  created_at: string
  updated_at: string
  synced_at: string
}

interface Connection {
  platform: string
  connected: boolean
  last_sync: string | null
  error: string | null
  total_tasks: number
  pending_tasks: number
  in_progress_tasks: number
}

const loading = ref(true)
const error = ref('')
const tasks = ref<Task[]>([])
const connections = ref<Record<string, Connection>>({})
const dashboard = ref<any>(null)
const statusFilter = ref<string>('all')
const platformFilter = ref<string>('all')

onMounted(loadData)

async function loadData() {
  loading.value = true
  try {
    // Load dashboard summary
    const dashRes = await api.get('/task-hub/dashboard') as any
    dashboard.value = dashRes.summary

    // Load tasks
    const tasksRes = await api.get('/task-hub/tasks') as any
    tasks.value = tasksRes.tasks || []

    // Load connections
    const connRes = await api.get('/task-hub/connections') as any
    connections.value = connRes.connections || {}
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar datos'
  } finally {
    loading.value = false
  }
}

async function syncAll() {
  try {
    await api.post('/task-hub/sync', { platform: null })
    toast({
      title: 'Sincronización iniciada',
      description: 'Sincronizando todas las plataformas...',
    })
    await loadData()
  } catch (e: any) {
    toast({
      title: 'Error',
      description: e?.message || 'Error al sincronizar',
      variant: 'destructive',
    })
  }
}

async function syncPlatform(platform: string) {
  try {
    await api.post('/task-hub/sync', { platform })
    toast({
      title: 'Sincronización iniciada',
      description: `Sincronizando ${platform}...`,
    })
    await loadData()
  } catch (e: any) {
    toast({
      title: 'Error',
      description: e?.message || 'Error al sincronizar',
      variant: 'destructive',
    })
  }
}

async function updateTaskStatus(taskId: string, newStatus: string) {
  try {
    await api.post('/task-hub/tasks/update-status', {
      task_id: taskId,
      new_status: newStatus,
    })
    toast({
      title: 'Estado actualizado',
      description: `Tarea marcada como ${newStatus}`,
    })
    await loadData()
  } catch (e: any) {
    toast({
      title: 'Error',
      description: e?.message || 'Error al actualizar estado',
      variant: 'destructive',
    })
  }
}

function openUrl(url: string) {
  window.open(url, '_blank')
}

const filteredTasks = computed(() => {
  return tasks.value.filter(task => {
    if (statusFilter.value !== 'all' && task.status !== statusFilter.value) return false
    if (platformFilter.value !== 'all' && task.platform !== platformFilter.value) return false
    return true
  })
})

const statusOptions = [
  { value: 'all', label: 'Todos' },
  { value: 'pending', label: 'Pendientes' },
  { value: 'in_progress', label: 'En Progreso' },
  { value: 'submitted', label: 'Enviados' },
  { value: 'approved', label: 'Aprobados' },
]

const platformOptions = [
  { value: 'all', label: 'Todas' },
  { value: 'algora', label: 'Algora' },
  { value: 'freelancer', label: 'Freelancer' },
  { value: 'github', label: 'GitHub' },
  { value: 'outlier', label: 'Outlier' },
]

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    pending: 'bg-warning',
    in_progress: 'bg-primary',
    submitted: 'bg-intigriti',
    approved: 'bg-success',
    rejected: 'bg-destructive',
    expired: 'bg-muted',
  }
  return colors[status] || 'bg-muted'
}

const getPriorityColor = (priority: string) => {
  const colors: Record<string, string> = {
    low: 'bg-muted',
    medium: 'bg-warning',
    high: 'bg-warning',
    urgent: 'bg-destructive',
  }
  return colors[priority] || 'bg-muted'
}
</script>

<template>
  <div class="p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-white mb-2">Task Hub</h1>
        <p class="text-muted-foreground">Tareas unificadas de todas las plataformas</p>
      </div>
      <Button @click="syncAll">
        <RefreshCw class="w-4 h-4 mr-2" />
        Sincronizar Todo
      </Button>
    </div>

    <LoadingState v-if="loading" />
    <div v-else-if="error" class="text-destructive">{{ error }}</div>

    <div v-else class="space-y-6">
      <!-- Dashboard Summary -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent class="p-4">
            <div class="text-2xl font-bold text-white">{{ dashboard?.total_tasks || 0 }}</div>
            <div class="text-sm text-muted-foreground">Total Tareas</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <div class="text-2xl font-bold text-warning">{{ dashboard?.pending || 0 }}</div>
            <div class="text-sm text-muted-foreground">Pendientes</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <div class="text-2xl font-bold text-primary">{{ dashboard?.in_progress || 0 }}</div>
            <div class="text-sm text-muted-foreground">En Progreso</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="p-4">
            <div class="text-2xl font-bold text-success">${{ dashboard?.total_potential_reward?.toFixed(2) || 0 }}</div>
            <div class="text-sm text-muted-foreground">Recompensa Potencial</div>
          </CardContent>
        </Card>
      </div>

      <!-- Platform Connections -->
      <Card>
        <CardHeader>
          <CardTitle class="text-white">Conexiones de Plataforma</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div
              v-for="(conn, platform) in connections"
              :key="platform"
              class="bg-surface border border-border rounded-lg p-4"
            >
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-lg font-semibold text-white capitalize">{{ platform }}</h3>
                <div :class="['w-3 h-3 rounded-full', conn.connected ? 'bg-success' : 'bg-destructive']" />
              </div>
              <div class="text-sm text-muted-foreground mb-2">
                {{ conn.connected ? 'Conectado' : 'No conectado' }}
              </div>
              <div v-if="conn.error" class="text-sm text-destructive mb-2">{{ conn.error }}</div>
              <div class="text-sm text-foreground/80">
                Tareas: {{ conn.total_tasks }} ({{ conn.pending_tasks }} pendientes)
              </div>
              <Button
                variant="outline"
                size="sm"
                class="mt-2 w-full"
                @click="syncPlatform(platform)"
              >
                <RefreshCw class="w-4 h-4 mr-2" />
                Sync
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Filters -->
      <div class="flex gap-4">
        <select
          v-model="statusFilter"
          class="bg-surface border border-border rounded px-3 py-2 text-white"
        >
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <select
          v-model="platformFilter"
          class="bg-surface border border-border rounded px-3 py-2 text-white"
        >
          <option v-for="opt in platformOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>

      <!-- Tasks List -->
      <div class="space-y-4">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          class="bg-surface border border-border rounded-lg p-4"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <Badge :class="getStatusColor(task.status)" class="text-white">
                  {{ task.status }}
                </Badge>
                <Badge :class="getPriorityColor(task.priority)" class="text-white">
                  {{ task.priority }}
                </Badge>
                <Badge variant="outline" class="capitalize">
                  {{ task.platform }}
                </Badge>
              </div>
              <h3 class="text-lg font-semibold text-white mb-2">{{ task.title }}</h3>
              <p class="text-foreground/80 mb-3">{{ task.description }}</p>
              <div class="flex items-center gap-4 text-sm text-muted-foreground">
                <div class="flex items-center gap-1">
                  <DollarSign class="w-4 h-4" />
                  ${{ task.reward }}
                </div>
                <div class="flex items-center gap-1">
                  <Clock class="w-4 h-4" />
                  {{ task.estimated_hours }}h
                </div>
              </div>
            </div>
            <div class="flex flex-col gap-2 ml-4">
              <Button
                variant="outline"
                size="sm"
                @click="openUrl(task.platform_url)"
              >
                <ExternalLink class="w-4 h-4 mr-2" />
                Abrir
              </Button>
              <Button
                v-if="task.status === 'pending'"
                variant="default"
                size="sm"
                @click="updateTaskStatus(task.id, 'in_progress')"
              >
                <CheckCircle class="w-4 h-4 mr-2" />
                Aceptar
              </Button>
              <Button
                v-if="task.status === 'in_progress'"
                variant="default"
                size="sm"
                @click="updateTaskStatus(task.id, 'submitted')"
              >
                <CheckCircle class="w-4 h-4 mr-2" />
                Enviar
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
