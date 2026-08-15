<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { RefreshCw, CalendarDays, Mail, CheckCircle2, XCircle, Clock, AlertTriangle, ListTodo } from '@lucide/vue'
import {
  getOutlookStatus,
  getOutlookAgenda,
  getOutlookTodo,
  getOutlookTasks,
  syncOutlookCalendar,
  type OutlookStatus,
  type OutlookAgenda,
  type OutlookEvent,
  type OutlookTodoData,
  type OutlookSyncTask,
  type OutlookSyncSummary,
  type OutlookTodoSyncSummary,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref<string | null>(null)
const status = ref<OutlookStatus | null>(null)
const agenda = ref<OutlookAgenda | null>(null)
const todo = ref<OutlookTodoData | null>(null)
const tasks = ref<OutlookSyncTask[]>([])
const syncing = ref(false)
const syncResult = ref<OutlookSyncSummary | null>(null)
const syncTodoResult = ref<OutlookTodoSyncSummary | null>(null)
const syncError = ref<string | null>(null)

const isConfigured = computed(() => status.value?.configured === true)
const isConnected = computed(() => status.value?.connected === true)

function formatDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [s, a, td, t] = await Promise.allSettled([
      getOutlookStatus(),
      getOutlookAgenda(),
      getOutlookTodo(),
      getOutlookTasks(),
    ])
    if (s.status === 'fulfilled') status.value = s.value.data
    if (a.status === 'fulfilled') agenda.value = a.value.data
    if (td.status === 'fulfilled') todo.value = td.value.data
    if (t.status === 'fulfilled') tasks.value = t.value.data.tasks ?? []
  } catch (e: any) {
    error.value = e?.message ?? 'Error cargando integración Outlook'
  } finally {
    loading.value = false
  }
}

async function runSync() {
  syncing.value = true
  syncError.value = null
  syncResult.value = null
  syncTodoResult.value = null
  try {
    const res = await syncOutlookCalendar()
    syncResult.value = res.data.summary
    syncTodoResult.value = res.data.todo
    await loadAll()
  } catch (e: any) {
    syncError.value = e?.message ?? 'Error ejecutando sync'
  } finally {
    syncing.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">Outlook &amp; To Do</h1>
        <p class="text-muted-foreground text-sm">
          Calendario y Microsoft To Do sincronizados con las tareas de OWNEX
        </p>
      </div>
      <Button :disabled="syncing || !isConfigured" @click="runSync">
        <RefreshCw :class="syncing ? 'animate-spin' : ''" class="mr-2 h-4 w-4" />
        {{ syncing ? 'Sincronizando…' : 'Sync ahora' }}
      </Button>
    </div>

    <p v-if="error" class="text-sm text-accent">{{ error }}</p>

    <!-- Estado -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-2">
            <CalendarDays class="h-5 w-5 text-primary" />
            <span class="text-sm text-muted-foreground">Configuración</span>
          </div>
          <div class="mt-2">
            <Skeleton v-if="loading" class="h-5 w-24" />
            <Badge v-else :variant="isConfigured ? 'success' : 'default'">
              {{ isConfigured ? 'Configurado' : 'No configurado' }}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-2">
            <CheckCircle2 class="h-5 w-5 text-success" />
            <span class="text-sm text-muted-foreground">Conexión Graph API</span>
          </div>
          <div class="mt-2">
            <Skeleton v-if="loading" class="h-5 w-24" />
            <template v-else>
              <Badge :variant="isConnected ? 'success' : 'destructive'">
                {{ isConnected ? 'Conectado' : 'Desconectado' }}
              </Badge>
              <p v-if="status?.user" class="mt-1 text-xs text-muted-foreground">{{ status.user }}</p>
            </template>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent class="p-4">
          <div class="flex items-center gap-2">
            <Mail class="h-5 w-5 text-warning" />
            <span class="text-sm text-muted-foreground">No leídos</span>
          </div>
          <div class="mt-2 text-2xl font-bold">
            <Skeleton v-if="loading" class="h-6 w-12" />
            <template v-else>{{ agenda?.unread ?? '—' }}</template>
          </div>
        </CardContent>
      </Card>
    </div>

    <p v-if="!isConfigured" class="flex items-center gap-2 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm">
      <AlertTriangle class="h-4 w-4 text-warning" />
      La integración no está configurada. Agregá
      <code class="rounded bg-muted px-1">CATEYE_OUTLOOK_CLIENT_ID</code>,
      <code class="rounded bg-muted px-1">CATEYE_OUTLOOK_CLIENT_SECRET</code>,
      <code class="rounded bg-muted px-1">CATEYE_OUTLOOK_TENANT_ID</code>
      y opcionalmente <code class="rounded bg-muted px-1">CATEYE_OUTLOOK_NOTIFICATION_TO</code> en <code class="rounded bg-muted px-1">.env</code>.
    </p>

    <!-- Resultado del sync -->
    <div v-if="syncResult" class="rounded-md border border-success/30 bg-success/10 p-3 text-sm">
      Sync de calendario:
      <span class="font-semibold">{{ syncResult.created }}</span> creados ·
      <span class="font-semibold">{{ syncResult.updated }}</span> actualizados ·
      <span class="font-semibold">{{ syncResult.deleted }}</span> eliminados
      <span v-if="syncResult.errors"> · <span class="font-semibold text-accent">{{ syncResult.errors }}</span> errores</span>
      <template v-if="syncTodoResult">
        <span class="mx-2 text-muted-foreground">|</span>
        To Do:
        <span class="font-semibold">{{ syncTodoResult.todo_created }}</span> creados ·
        <span class="font-semibold">{{ syncTodoResult.todo_updated }}</span> actualizados ·
        <span class="font-semibold">{{ syncTodoResult.todo_deleted }}</span> eliminados
        <span v-if="syncTodoResult.todo_errors"> · <span class="font-semibold text-accent">{{ syncTodoResult.todo_errors }}</span> errores</span>
      </template>
    </div>
    <p v-if="syncError" class="text-sm text-accent">{{ syncError }}</p>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <!-- Agenda -->
      <Card>
        <CardHeader>
          <CardTitle>Próximos eventos</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton v-if="loading" class="h-24 w-full" />
          <p v-else-if="!agenda?.events?.length" class="text-sm text-muted-foreground">Sin eventos próximos.</p>
          <ul v-else class="divide-y divide-border">
            <li v-for="ev in agenda.events" :key="ev.id" class="flex items-start gap-3 py-2">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ ev.subject }}</p>
                <p class="text-xs text-muted-foreground">{{ formatDate(ev.start) }} → {{ formatDate(ev.end) }}</p>
                <p v-if="ev.location" class="text-xs text-muted-foreground">{{ ev.location }}</p>
              </div>
              <Badge v-if="ev.is_online" variant="default">online</Badge>
            </li>
          </ul>
        </CardContent>
      </Card>

      <!-- Microsoft To Do -->
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2">
            <ListTodo class="h-4 w-4 text-primary" />Microsoft To Do
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton v-if="loading" class="h-24 w-full" />
          <p v-else-if="!todo?.lists?.length" class="text-sm text-muted-foreground">
            Sin listas de To Do. Ejecutá "Sync ahora" para crear la lista
            <code class="rounded bg-muted px-1">OWNEX</code> y volcar ahí las tareas.
          </p>
          <ul v-else class="divide-y divide-border">
            <li v-for="tt in todo.tasks" :key="tt.id" class="flex items-center gap-3 py-2">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ tt.title }}</p>
                <p class="text-xs text-muted-foreground">
                  <Clock class="mr-1 inline h-3 w-3" />{{ formatDate(tt.due_date) }}
                  <span class="ml-2">{{ tt.list_name }}</span>
                </p>
              </div>
              <Badge v-if="tt.status === 'completed'" variant="success">completada</Badge>
              <Badge v-else variant="default">{{ tt.status }}</Badge>
            </li>
          </ul>
        </CardContent>
      </Card>

      <!-- Tasks locales -->
      <Card>
        <CardHeader>
          <CardTitle>Tareas con fecha (sync)</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton v-if="loading" class="h-24 w-full" />
          <p v-else-if="!tasks.length" class="text-sm text-muted-foreground">
            No hay tareas con fecha. Creá una task con <code class="rounded bg-muted px-1">due_date</code>
            en <code class="rounded bg-muted px-1">POST /api/operations/tasks</code> para que aparezca en el calendario y en To Do.
          </p>
          <ul v-else class="divide-y divide-border">
            <li v-for="t in tasks" :key="t.id" class="flex items-center gap-3 py-2">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">{{ t.title }}</p>
                <p class="text-xs text-muted-foreground">
                  <Clock class="mr-1 inline h-3 w-3" />{{ formatDate(t.due_date) }}
                </p>
              </div>
              <div class="flex flex-col items-end gap-1">
                <Badge :variant="t.synced_to_calendar ? 'success' : 'default'">
                  {{ t.synced_to_calendar ? 'Calendario' : 'Cal. pendiente' }}
                </Badge>
                <Badge :variant="t.synced_to_todo ? 'success' : 'default'">
                  {{ t.synced_to_todo ? 'To Do' : 'To Do pendiente' }}
                </Badge>
              </div>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  </div>
</template>