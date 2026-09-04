<script setup lang="ts">
/**
 * WorkRoom — Sala de trabajo individual.
 * Muestra progreso, archivos, actividad de agentes, evidencia, acciones.
 * Se abre desde WorkQueue, IncomeHome, o Command Palette.
 */

import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Clock,
  Code,
  Copy,
  Download,
  Edit2,
  ExternalLink,
  FileText,
  FolderOpen,
  Globe,
  Hash,
  LayoutDashboard,
  Lightbulb,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Paperclip,
  Play,
  Plus,
  Save,
  Search,
  Send,
  Shield,
  Trash2,
  Upload,
  UserRound,
  X,
  Zap,
} from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { useNotificationsStore } from '@/stores/notifications'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import MetricCard from '@/components/ui/MetricCard.vue'

interface WorkItem {
  id: string
  title: string
  platform: string
  category: string
  state: WorkState
  reward_range: { low: number; high: number }
  estimated_hours: number
  human_hours: number
  progress_pct: number
  current_stage: string
  stages: WorkStage[]
  files: WorkFile[]
  agent_activity: AgentActivity[]
  evidence: EvidenceItem[]
  deliverables: DeliverableItem[]
  url?: string
  assessment_required: boolean
  zero_experience: boolean
  zero_barrier: boolean
  cash_speed_days: number
  acceptance_probability: number
  ev_per_human_hour: number
  created_at: string
  updated_at: string
}

type WorkState = 'discovered' | 'preparing' | 'ready_to_deliver' | 'delivered' | 'needs_access' | 'rejected' | 'archived'

interface WorkStage {
  name: string
  status: 'completed' | 'active' | 'pending' | 'blocked'
  started_at?: string
  completed_at?: string
  agent?: string
  details?: string
}

interface WorkFile {
  name: string
  path: string
  type: 'source' | 'evidence' | 'report' | 'deliverable'
  size: number
  modified_at: string
}

interface AgentActivity {
  timestamp: string
  agent: string
  action: string
  details?: string
  status: 'success' | 'working' | 'failed'
}

interface EvidenceItem {
  id: string
  type: 'poc' | 'screenshot' | 'log' | 'request' | 'response'
  title: string
  description: string
  file_path?: string
  verified: boolean
}

interface DeliverableItem {
  id: string
  name: string
  type: 'report' | 'patch' | 'proposal' | 'walkthrough'
  status: 'draft' | 'ready' | 'submitted' | 'accepted'
  file_path?: string
}

const route = useRoute()
const router = useRouter()
const notifications = useNotificationsStore()

const workId = route.params.id as string
const work = ref<WorkItem | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<'overview' | 'files' | 'activity' | 'evidence' | 'deliverables'>('overview')
const submitting = ref(false)

// Edit modes
const editMode = ref<'overview' | 'files' | 'evidence' | 'deliverables' | null>(null)
const editForm = ref<Record<string, any>>({})
const saving = ref(false)

const stateConfig: Record<WorkState, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info'; icon: any }> = {
  discovered: { label: 'Descubierto', variant: 'info', icon: Lightbulb },
  preparing: { label: 'Preparando', variant: 'warning', icon: Loader2 },
  ready_to_deliver: { label: 'Listo para entregar', variant: 'success', icon: CheckCircle },
  delivered: { label: 'Entregado', variant: 'success', icon: Shield },
  needs_access: { label: 'Necesita acceso', variant: 'error', icon: AlertTriangle },
  rejected: { label: 'Rechazado', variant: 'error', icon: X },
  archived: { label: 'Archivado', variant: 'default', icon: Hash },
}

const tabs = [
  { id: 'overview', label: 'Visión general', icon: LayoutDashboard },
  { id: 'files', label: 'Archivos', icon: FolderOpen },
  { id: 'activity', label: 'Actividad', icon: Bot },
  { id: 'evidence', label: 'Evidencia', icon: Shield },
  { id: 'deliverables', label: 'Entregables', icon: FileText },
] as const

const fileInputRef = ref<HTMLInputElement | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await api.get<WorkItem>(`/direct-work/workbank/${workId}`)
    work.value = res
  } catch (e: any) {
    error.value = e?.message || 'No se pudo cargar el trabajo'
  } finally {
    loading.value = false
  }
}

async function markDelivered() {
  if (!work.value) return
  try {
    await api.post(`/direct-work/workbank/${workId}/deliver/approve`)
    notifications.success('Marcado como entregado')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error al entregar')
  }
}

async function prepareDelivery() {
  if (!work.value) return
  try {
    submitting.value = true
    const res = await api.post(`/direct-work/workbank/${workId}/deliver/prepare`)
    notifications.success(`Paquete preparado en: ${res.path}`)
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error preparando entrega')
  } finally {
    submitting.value = false
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('es-AR', { hour12: false, day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatDuration(hours: number): string {
  if (hours < 1) return `${Math.round(hours * 60)}m`
  return `${Math.floor(hours)}h ${Math.round((hours % 1) * 60)}m`
}

function getStageIcon(status: string) {
  switch (status) {
    case 'completed': return CheckCircle
    case 'active': return Loader2
    case 'blocked': return AlertTriangle
    default: return Hash
  }
}

onMounted(load)

watch(() => route.params.id, (newId) => {
  if (newId !== workId) {
    load()
  }
})

// Edit functions
function startEdit(tab: 'overview' | 'files' | 'evidence' | 'deliverables') {
  editMode.value = tab
  if (work.value) {
    editForm.value = {
      title: work.value.title,
      description: work.value.description,
      estimated_hours: work.value.estimated_hours,
      human_hours: work.value.human_hours,
      cash_speed_days: work.value.cash_speed_days,
    }
  }
}

function cancelEdit() {
  editMode.value = null
  editForm.value = {}
}

async function saveEdit() {
  if (!work.value) return
  saving.value = true
  try {
    await api.put(`/direct-work/workbank/${workId}`, editForm.value)
    notifications.success('Cambios guardados')
    await load()
    editMode.value = null
  } catch (e: any) {
    notifications.error(e?.message || 'Error guardando cambios')
  } finally {
    saving.value = false
  }
}

// Stage editing
const editingStage = ref<string | null>(null)
const stageEditForm = ref<{ name: string; status: string; details: string }>({ name: '', status: 'pending', details: '' })

function startEditStage(stage: WorkStage) {
  editingStage.value = stage.name
  stageEditForm.value = {
    name: stage.name,
    status: stage.status,
    details: stage.details || '',
  }
}

function cancelEditStage() {
  editingStage.value = null
  stageEditForm.value = { name: '', status: 'pending', details: '' }
}

async function saveStageEdit() {
  if (!work.value || !editingStage.value) return
  const stageIndex = work.value.stages.findIndex(s => s.name === editingStage.value)
  if (stageIndex === -1) return

  work.value.stages[stageIndex] = {
    ...work.value.stages[stageIndex],
    name: stageEditForm.value.name,
    status: stageEditForm.value.status as any,
    details: stageEditForm.value.details,
  }

  try {
    await api.put(`/direct-work/workbank/${workId}`, {
      stages: work.value.stages,
    })
    notifications.success('Etapa actualizada')
    await load()
    editingStage.value = null
  } catch (e: any) {
    notifications.error(e?.message || 'Error actualizando etapa')
  }
}

// File actions
async function uploadFile(file: File, type: WorkFile['type']) {
  if (!work.value) return
  const form = new FormData()
  form.append('file', file)
  form.append('type', type)
  try {
    const res = await api.post(`/direct-work/workbank/${workId}/files`, { file, type })
    notifications.success('Archivo subido')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error subiendo archivo')
  }
}

async function deleteFile(filePath: string) {
  if (!work.value) return
  try {
    await api.delete(`/direct-work/workbank/${workId}/files`, { data: { path: filePath } })
    notifications.success('Archivo eliminado')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error eliminando archivo')
  }
}

// Evidence actions
async function addEvidence(evidence: Partial<EvidenceItem>) {
  if (!work.value) return
  try {
    await api.post(`/direct-work/workbank/${workId}/evidence`, evidence)
    notifications.success('Evidencia agregada')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error agregando evidencia')
  }
}

async function toggleEvidenceVerified(evidence: EvidenceItem) {
  if (!work.value) return
  const evIndex = work.value.evidence.findIndex(e => e.id === evidence.id)
  if (evIndex === -1) return

  work.value.evidence[evIndex] = { ...evidence, verified: !evidence.verified }

  try {
    await api.put(`/direct-work/workbank/${workId}/evidence/${evidence.id}`, { verified: !evidence.verified })
    notifications.success('Evidencia actualizada')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error actualizando evidencia')
  }
}

async function deleteEvidence(evidence: EvidenceItem) {
  if (!work.value) return
  try {
    await api.delete(`/direct-work/workbank/${workId}/evidence/${evidence.id}`)
    notifications.success('Evidencia eliminada')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error eliminando evidencia')
  }
}

// Deliverable actions
async function addDeliverable(deliverable: Partial<DeliverableItem>) {
  if (!work.value) return
  try {
    await api.post(`/direct-work/workbank/${workId}/deliverables`, deliverable)
    notifications.success('Entregable agregado')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error agregando entregable')
  }
}

async function updateDeliverableStatus(deliverable: DeliverableItem, status: DeliverableItem['status']) {
  if (!work.value) return
  const delIndex = work.value.deliverables.findIndex(d => d.id === deliverable.id)
  if (delIndex === -1) return

  work.value.deliverables[delIndex] = { ...deliverable, status }

  try {
    await api.put(`/direct-work/workbank/${workId}/deliverables/${deliverable.id}`, { status })
    notifications.success('Estado actualizado')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error actualizando entregable')
  }
}

async function deleteDeliverable(deliverable: DeliverableItem) {
  if (!work.value) return
  try {
    await api.delete(`/direct-work/workbank/${workId}/deliverables/${deliverable.id}`)
    notifications.success('Entregable eliminado')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error eliminando entregable')
  }
}

function triggerFileUpload(type: string) {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

function handleFileUpload(event: Event, type: string) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    uploadFile(input.files[0], type as WorkFile['type'])
  }
}
</script>

<template>
  <div class="flex h-full w-full flex-col bg-background">
    <!-- Header -->
    <header class="flex items-center gap-4 border-b border-border/30 px-6 py-4 bg-surface/30 backdrop-blur-sm">
      <button @click="$emit('close')" class="p-2 hover:bg-muted/30 rounded-lg transition-colors" title="Cerrar">
        <ChevronLeft class="h-5 w-5" />
      </button>

      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-3 flex-wrap">
          <h1 class="text-lg font-semibold truncate">{{ work?.title || 'Cargando…' }}</h1>
          <span v-if="work" :class="['badge', `badge-${stateConfig[work.state].variant}`]" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium">
            <component :is="stateConfig[work.state].icon" class="h-3 w-3" />
            {{ stateConfig[work.state].label }}
          </span>
          <span v-if="work?.assessment_required" class="badge badge-warning text-[9px]">Assessment requerido</span>
          <span v-if="work?.zero_experience" class="badge badge-success text-[9px]">Zero Experience</span>
          <span v-if="work?.zero_barrier" class="badge badge-info text-[9px]">Zero Barrier</span>
        </div>
        <p v-if="work" class="text-sm text-muted-foreground truncate">{{ work.platform }} · {{ work.category }} · {{ work.id }}</p>
      </div>

      <div class="flex items-center gap-2">
        <button v-if="work?.url" @click="window.open(work.url, '_blank')" class="p-2 hover:bg-muted/30 rounded-lg" title="Abrir en plataforma">
          <ExternalLink class="h-4 w-4" />
        </button>
        <button v-if="work?.state === 'ready_to_deliver' && !submitting" @click="prepareDelivery" class="btn-primary px-3 py-1.5 text-sm" :disabled="submitting">
          <Upload class="h-4 w-4 mr-1" v-if="!submitting" />
          <Loader2 class="h-4 w-4 mr-1 animate-spin" v-else />
          {{ submitting ? 'Preparando…' : 'Preparar entrega' }}
        </button>
        <button v-if="work?.state === 'ready_to_deliver'" @click="markDelivered" class="btn-success px-3 py-1.5 text-sm">
          <CheckCircle class="h-4 w-4 mr-1" /> Entregado
        </button>
      </div>
    </header>

    <!-- Loading / Error -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <Loader2 class="h-8 w-8 animate-spin text-primary" />
    </div>
    <div v-else-if="error" class="flex-1 flex items-center justify-center text-destructive">
      <AlertTriangle class="h-6 w-6 mr-2" /> {{ error }}
    </div>

    <!-- Content -->
    <div v-else-if="work" class="flex-1 flex overflow-hidden">
      <!-- Sidebar Tabs -->
      <aside class="w-48 border-r border-border/30 bg-surface/30 flex flex-col">
        <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'flex w-full items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
              activeTab === tab.id
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:bg-muted/30 hover:text-foreground',
            ]"
          >
            <component :is="tab.icon" class="h-4 w-4 shrink-0" />
            {{ tab.label }}
          </button>
        </nav>
        <div class="p-3 border-t border-border/30">
          <div class="space-y-2 text-xs">
            <div class="flex justify-between">
              <span class="text-muted-foreground">Valor</span>
              <span class="font-mono tabular-nums text-success">${{ work.reward_range.low }}–${{ work.reward_range.high }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Probabilidad</span>
              <span class="font-mono tabular-nums">{{ Math.round(work.acceptance_probability * 100) }}%</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">EV/h humano</span>
              <span class="font-mono tabular-nums text-success">${{ work.ev_per_human_hour }}/h</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Cash speed</span>
              <span class="font-mono">{{ work.cash_speed_days }} días</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Progreso</span>
              <span class="font-mono tabular-nums">{{ work.progress_pct }}%</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- Overview Tab -->
        <div v-if="activeTab === 'overview'" class="space-y-6 animate-in">
          <!-- Progress Bar -->
          <div class="rounded-lg border border-border/30 bg-surface/30 p-5">
            <div class="flex items-center justify-between mb-3">
              <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Progreso del pipeline</p>
              <span class="font-mono text-sm font-bold">{{ work.progress_pct }}%</span>
            </div>
            <div class="h-2 bg-muted rounded-full overflow-hidden">
              <div class="h-full bg-primary transition-all duration-500" :style="{ width: work.progress_pct + '%' }" />
            </div>
            <div class="mt-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>Iniciado: {{ formatTime(work.created_at) }}</span>
              <span>Actualizado: {{ formatTime(work.updated_at) }}</span>
            </div>
          </div>

          <!-- Stages Pipeline -->
          <div class="rounded-lg border border-border/30 bg-surface/30 p-5">
            <div class="flex items-center justify-between mb-4">
              <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Etapas</p>
              <div class="flex items-center gap-2">
                <button v-if="editMode !== 'overview'" @click="startEdit('overview')" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                  <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar
                </button>
                <button v-if="editMode === 'overview'" @click="saveEdit" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                  <Save class="h-3.5 w-3.5 mr-1" /> Guardar
                </button>
                <button v-if="editMode === 'overview'" @click="cancelEdit" class="btn-secondary px-3 py-1.5 text-sm">
                  <X class="h-3.5 w-3.5 mr-1" /> Cancelar
                </button>
              </div>
            </div>

            <div v-if="editMode === 'overview'">
              <div class="space-y-4">
                <div>
                  <label class="block text-xs font-medium text-muted-foreground mb-1">Título</label>
                  <Input v-model="editForm.title" placeholder="Título del trabajo" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-muted-foreground mb-1">Descripción</label>
                  <textarea v-model="editForm.description" class="w-full rounded-lg border border-border/30 bg-background/60 px-3 py-1.5 font-mono text-xs outline-none focus:border-primary/60" rows="3" placeholder="Descripción del trabajo..."></textarea>
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-medium text-muted-foreground mb-1">Horas estimadas</label>
                    <Input v-model.number="editForm.estimated_hours" type="number" step="0.5" min="0" placeholder="0" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-muted-foreground mb-1">Horas humanas</label>
                    <Input v-model.number="editForm.human_hours" type="number" step="0.5" min="0" placeholder="0" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-muted-foreground mb-1">Velocidad cobro (días)</label>
                    <Input v-model.number="editForm.cash_speed_days" type="number" step="1" min="0" placeholder="0" />
                  </div>
                </div>
              </div>
            </div>
            <div v-else>
              <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-4">Etapas</p>
              <div class="space-y-3">
                <div
                  v-for="(stage, i) in work.stages"
                  :key="stage.name"
                  class="flex items-center gap-4 group relative"
                >
                  <div class="relative flex items-center" :style="{ zIndex: 10 - i }">
                    <div class="w-8 h-8 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors"
                      :class="[
                        stage.status === 'completed' ? 'bg-success border-success' :
                        stage.status === 'active' ? 'bg-primary border-primary animate-pulse' :
                        stage.status === 'blocked' ? 'bg-destructive border-destructive' :
                        'bg-muted border-border'
                      ]"
                    >
                      <component :is="getStageIcon(stage.status)" class="h-4 w-4"
                        :class="stage.status === 'completed' ? 'text-background' : 'text-foreground'" />
                    </div>
                    <div v-if="i < work.stages.length - 1" class="absolute left-3 top-8 bottom-8 w-0.5 bg-border" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span v-if="editingStage === stage.name">
                        <Input v-model="stageEditForm.name" class="w-40 text-sm font-mono" />
                      </span>
                      <span v-else class="font-mono text-sm font-medium">{{ stage.name }}</span>
                      <span class="badge badge-xs" :class="[
                        stage.status === 'completed' ? 'badge-success' :
                        stage.status === 'active' ? 'badge-primary' :
                        stage.status === 'blocked' ? 'badge-destructive' :
                        'badge-muted'
                      ]">{{ stage.status }}</span>
                      <span v-if="stage.agent" class="text-[10px] text-muted-foreground">via {{ stage.agent }}</span>
                    </div>
                    <div class="text-right shrink-0 w-48">
                      <p v-if="stage.started_at" class="text-[10px] text-muted-foreground">Iniciado: {{ formatTime(stage.started_at) }}</p>
                      <p v-if="stage.completed_at" class="text-[10px] text-success">Completado: {{ formatTime(stage.completed_at) }}</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <button v-if="editingStage !== stage.name" @click="startEditStage(stage)" class="p-1.5 hover:bg-muted/30 rounded" title="Editar etapa">
                      <Edit2 class="h-3.5 w-3.5" />
                    </button>
                    <button v-if="editingStage === stage.name" @click="saveStageEdit" class="p-1.5 hover:bg-muted/30 rounded" title="Guardar">
                      <Save class="h-3.5 w-3.5" />
                    </button>
                    <button v-if="editingStage === stage.name" @click="cancelEditStage" class="p-1.5 hover:bg-muted/30 rounded" title="Cancelar">
                      <X class="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div v-if="editingStage === stage.name" class="absolute left-0 right-0 top-full mt-2 p-4 bg-surface border border-border/30 rounded-lg shadow-lg z-10 animate-in">
                    <div class="space-y-3">
                      <div>
                        <label class="block text-xs font-medium text-muted-foreground mb-1">Nombre</label>
                        <Input v-model="stageEditForm.name" placeholder="Nombre de la etapa" />
                      </div>
                      <div>
                        <label class="block text-xs font-medium text-muted-foreground mb-1">Estado</label>
                        <Select v-model="stageEditForm.status" :options="[
                          { value: 'pending', label: 'Pendiente' },
                          { value: 'active', label: 'Activa' },
                          { value: 'completed', label: 'Completada' },
                          { value: 'blocked', label: 'Bloqueada' },
                        ]" placeholder="Estado" />
                      </div>
                      <div>
                        <label class="block text-xs font-medium text-muted-foreground mb-1">Detalles</label>
                        <textarea v-model="stageEditForm.details" class="w-full rounded-lg border border-border/30 bg-background/60 px-3 py-1.5 font-mono text-xs outline-none focus:border-primary/60" rows="2" placeholder="Detalles..."></textarea>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          <!-- Key Metrics -->
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <MetricCard label="Tiempo estimado" :value="formatDuration(work.estimated_hours)" icon="Clock" />
            <MetricCard label="Tiempo humano" :value="formatDuration(work.human_hours)" icon="UserRound" />
            <MetricCard label="Velocidad cobro" :value="`${work.cash_speed_days} días`" icon="Zap" variant="warning" />
            <MetricCard label="EV/hora humana" :value="`$${work.ev_per_human_hour}/h`" icon="CircleDollarSign" variant="success" />
          </div>
        </div>

        <!-- Files Tab -->
        <div v-if="activeTab === 'files'" class="space-y-4 animate-in">
          <div class="flex items-center justify-between">
            <h3 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Archivos del workspace</h3>
            <div class="flex items-center gap-2">
              <span class="badge badge-muted">{{ work.files.length }}</span>
              <button v-if="editMode !== 'files'" @click="startEdit('files')" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar
              </button>
              <button v-if="editMode === 'files'" @click="saveEdit" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Save class="h-3.5 w-3.5 mr-1" /> Guardar
              </button>
              <button v-if="editMode === 'files'" @click="cancelEdit" class="btn-secondary px-3 py-1.5 text-sm">
                <X class="h-3.5 w-3.5 mr-1" /> Cancelar
              </button>
            </div>
          </div>

          <div v-if="editMode === 'files'" class="p-4 bg-muted/30 rounded-lg border border-border/30 mb-4 space-y-3">
            <div class="flex items-center gap-2">
              <label class="text-xs font-medium text-muted-foreground">Subir archivo</label>
              <input type="file" ref="fileInputRef" class="hidden" @change="handleFileUpload($event, 'source')" />
              <button @click="triggerFileUpload('source')" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Upload class="h-3.5 w-3.5 mr-1" /> Subir archivo
              </button>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-1">Tipo</label>
                <Select v-model="editForm.fileType" :options="[
                  { value: 'source', label: 'Código fuente' },
                  { value: 'evidence', label: 'Evidencia' },
                  { value: 'report', label: 'Reporte' },
                  { value: 'deliverable', label: 'Entregable' },
                ]" placeholder="Tipo" />
              </div>
            </div>
          </div>

          <div v-if="editMode !== 'files'" class="p-4 bg-muted/30 rounded-lg border border-border/30 mb-4 space-y-3">
            <button @click="startEdit('files')" class="btn-primary w-full py-1.5 text-sm" :disabled="saving">
              <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar archivos
            </button>
          </div>

          <div class="rounded-lg border border-border/30 bg-surface/30 divide-y divide-border/30">
            <div v-for="file in work.files" :key="file.path" class="flex items-center gap-4 px-4 py-3 hover:bg-muted/20 transition-colors">
              <div class="w-10 h-10 rounded-lg bg-muted/50 flex items-center justify-center shrink-0">
                <FileText class="h-5 w-5 text-muted-foreground" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-mono text-sm truncate">{{ file.name }}</p>
                <p class="text-[11px] text-muted-foreground">{{ file.path }} · {{ (file.size / 1024).toFixed(1) }} KB</p>
              </div>
              <div class="flex items-center gap-2">
                <span class="badge badge-xs" :class="[
                  file.type === 'source' ? 'badge-primary' :
                  file.type === 'evidence' ? 'badge-warning' :
                  file.type === 'report' ? 'badge-success' :
                  'badge-info'
                ]">{{ file.type }}</span>
                <button class="p-1.5 hover:bg-muted/30 rounded" title="Copiar ruta">
                  <Copy class="h-3.5 w-3.5" />
                </button>
                <button class="p-1.5 hover:bg-muted/30 rounded" title="Descargar">
                  <Download class="h-3.5 w-3.5" />
                </button>
                <button class="p-1.5 hover:bg-muted/30 rounded text-destructive" title="Eliminar" @click="deleteFile(file.path)">
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            <div v-if="!work.files.length" class="p-8 text-center text-muted-foreground">
              <FolderOpen class="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p>Sin archivos. OWNEX prepara el workspace al iniciar.</p>
            </div>
          </div>

        <!-- Activity Tab -->
        <div v-if="activeTab === 'activity'" class="space-y-4 animate-in">
          <div class="flex items-center justify-between">
            <h3 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Actividad de agentes</h3>
            <span class="badge badge-muted">{{ work.agent_activity.length }}</span>
          </div>
          <div class="rounded-lg border border-border/30 bg-surface/30 divide-y divide-border/30">
            <div v-for="(activity, i) in work.agent_activity" :key="i" class="flex items-start gap-4 px-4 py-3 hover:bg-muted/20 transition-colors">
              <div class="relative shrink-0">
                <div class="w-2 h-2 rounded-full mt-2"
                  :class="activity.status === 'success' ? 'bg-success' : activity.status === 'working' ? 'bg-primary animate-pulse' : 'bg-destructive'" />
                <div v-if="i < work.agent_activity.length - 1" class="absolute left-0.5 top-4 bottom-0 w-0.5 bg-border" />
              </div>
              <div class="flex-1 min-w-0 pt-1">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-medium">{{ activity.agent }}</span>
                  <span class="text-[10px] text-muted-foreground">{{ formatTime(activity.timestamp) }}</span>
                  <span class="badge badge-xs" :class="[
                    activity.status === 'success' ? 'badge-success' :
                    activity.status === 'working' ? 'badge-primary' :
                    'badge-destructive'
                  ]">{{ activity.status }}</span>
                </div>
                <p class="mt-1 text-sm text-foreground">{{ activity.action }}</p>
                <p v-if="activity.details" class="text-[11px] text-muted-foreground mt-0.5">{{ activity.details }}</p>
              </div>
            </div>
            <div v-if="!work.agent_activity.length" class="p-8 text-center text-muted-foreground">
              <Bot class="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p>Sin actividad registrada aún.</p>
            </div>
          </div>
        </div>

        <!-- Evidence Tab -->
        <div v-if="activeTab === 'evidence'" class="space-y-4 animate-in">
          <div class="flex items-center justify-between">
            <h3 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Evidencia</h3>
            <div class="flex items-center gap-2">
              <span class="badge badge-muted">{{ work.evidence.length }}</span>
              <button v-if="editMode !== 'evidence'" @click="startEdit('evidence')" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar
              </button>
              <button v-if="editMode === 'evidence'" @click="saveEdit" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Save class="h-3.5 w-3.5 mr-1" /> Guardar
              </button>
              <button v-if="editMode === 'evidence'" @click="cancelEdit" class="btn-secondary px-3 py-1.5 text-sm">
                <X class="h-3.5 w-3.5 mr-1" /> Cancelar
              </button>
            </div>
          </div>

          <div v-if="editMode === 'evidence'" class="p-4 bg-muted/30 rounded-lg border border-border/30 mb-4 space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-1">Título</label>
                <Input v-model="editForm.evidenceTitle" placeholder="Título de la evidencia" />
              </div>
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-1">Tipo</label>
                <Select v-model="editForm.evidenceType" :options="[
                  { value: 'poc', label: 'PoC' },
                  { value: 'screenshot', label: 'Captura' },
                  { value: 'log', label: 'Log' },
                  { value: 'request', label: 'Request' },
                  { value: 'response', label: 'Response' },
                ]" placeholder="Tipo" />
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-medium text-muted-foreground mb-1">Descripción</label>
                <textarea v-model="editForm.evidenceDescription" class="w-full rounded-lg border border-border/30 bg-background/60 px-3 py-1.5 font-mono text-xs outline-none focus:border-primary/60" rows="2" placeholder="Descripción..."></textarea>
              </div>
            </div>
            <div class="flex gap-2">
              <button @click="addEvidence({ title: editForm.evidenceTitle, type: editForm.evidenceType, description: editForm.evidenceDescription, verified: false })" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving || !editForm.evidenceTitle">
                <Plus class="h-3.5 w-3.5 mr-1" /> Agregar
              </button>
            </div>
          </div>

          <div v-if="editMode !== 'evidence'" class="p-4 bg-muted/30 rounded-lg border border-border/30 mb-4">
            <button @click="startEdit('evidence')" class="btn-primary w-full py-1.5 text-sm" :disabled="saving">
              <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar evidencia
            </button>
          </div>

          <div class="rounded-lg border border-border/30 bg-surface/30 divide-y divide-border/30">
            <div v-for="ev in work.evidence" :key="ev.id" class="flex items-start gap-4 px-4 py-3 hover:bg-muted/20 transition-colors">
              <div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                :class="ev.verified ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'">
                <Shield class="h-5 w-5" :class="ev.verified ? 'text-success' : 'text-warning'" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-medium">{{ ev.title }}</span>
                  <span class="badge badge-xs" :class="[
                    ev.type === 'poc' ? 'badge-destructive' :
                    ev.type === 'screenshot' ? 'badge-primary' :
                    ev.type === 'log' ? 'badge-muted' :
                    'badge-warning'
                  ]">{{ ev.type }}</span>
                  <span v-if="ev.verified" class="badge badge-xs badge-success">Verificada</span>
                </div>
                <p class="text-sm text-muted-foreground mt-1">{{ ev.description }}</p>
                <button v-if="ev.file_path" class="mt-2 text-sm text-primary hover:underline font-mono" @click="navigator.clipboard.writeText(ev.file_path!)">
                  Copiar ruta: {{ ev.file_path }}
                </button>
              </div>
              <div class="flex items-center gap-2">
                <button class="p-1.5 hover:bg-muted/30 rounded" :class="ev.verified ? 'text-success' : 'text-warning'" @click="toggleEvidenceVerified(ev)" title="{{ ev.verified ? 'Marcar no verificada' : 'Marcar verificada' }}">
                  <Shield class="h-3.5 w-3.5" :class="ev.verified ? 'text-success' : 'text-warning'" />
                </button>
                <button class="p-1.5 hover:bg-muted/30 rounded text-destructive" @click="deleteEvidence(ev)" title="Eliminar">
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            <div v-if="!work.evidence.length" class="p-8 text-center text-muted-foreground">
              <Shield class="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p>Sin evidencia. Se genera durante validación.</p>
            </div>
          </div>
            </div>
            <div v-if="!work.evidence.length" class="p-8 text-center text-muted-foreground">
              <Shield class="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p>Sin evidencia. Se genera durante validación.</p>
            </div>
          </div>
        </div>

        <!-- Deliverables Tab -->
        <div v-if="activeTab === 'deliverables'" class="space-y-4 animate-in">
          <div class="flex items-center justify-between">
            <h3 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Entregables</h3>
            <div class="flex items-center gap-2">
              <span class="badge badge-muted">{{ work.deliverables.length }}</span>
              <button v-if="editMode !== 'deliverables'" @click="startEdit('deliverables')" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar
              </button>
              <button v-if="editMode === 'deliverables'" @click="saveEdit" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving">
                <Save class="h-3.5 w-3.5 mr-1" /> Guardar
              </button>
              <button v-if="editMode === 'deliverables'" @click="cancelEdit" class="btn-secondary px-3 py-1.5 text-sm">
                <X class="h-3.5 w-3.5 mr-1" /> Cancelar
              </button>
            </div>
          </div>

          <div v-if="editMode === 'deliverables'" class="p-4 bg-muted/30 rounded-lg border border-border/30 mb-4 space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-1">Nombre</label>
                <Input v-model="editForm.deliverableName" placeholder="Nombre del entregable" />
              </div>
              <div>
                <label class="block text-xs font-medium text-muted-foreground mb-1">Tipo</label>
                <Select v-model="editForm.deliverableType" :options="[
                  { value: 'report', label: 'Reporte' },
                  { value: 'patch', label: 'Patch' },
                  { value: 'proposal', label: 'Propuesta' },
                  { value: 'walkthrough', label: 'Walkthrough' },
                ]" placeholder="Tipo" />
              </div>
            </div>
            <div class="flex gap-2">
              <button @click="addDeliverable({ name: editForm.deliverableName, type: editForm.deliverableType, status: 'draft' })" class="btn-primary px-3 py-1.5 text-sm" :disabled="saving || !editForm.deliverableName">
                <Plus class="h-3.5 w-3.5 mr-1" /> Agregar
              </button>
            </div>
          </div>

          <div v-if="editMode !== 'deliverables'" class="p-4 bg-muted/30 rounded-lg border border-border/30 mb-4">
            <button @click="startEdit('deliverables')" class="btn-primary w-full py-1.5 text-sm" :disabled="saving">
              <Edit2 class="h-3.5 w-3.5 mr-1" /> Editar entregables
            </button>
          </div>

          <div class="rounded-lg border border-border/30 bg-surface/30 divide-y divide-border/30">
            <div v-for="del in work.deliverables" :key="del.id" class="flex items-center gap-4 px-4 py-3 hover:bg-muted/20 transition-colors">
              <div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                :class="del.status === 'accepted' ? 'bg-success/10 text-success' : del.status === 'submitted' ? 'bg-primary/10 text-primary' : 'bg-muted/10 text-muted-foreground'">
                <FileText class="h-5 w-5" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-sm font-medium">{{ del.name }}</span>
                  <span class="badge badge-xs" :class="[
                    del.type === 'report' ? 'badge-primary' :
                    del.type === 'patch' ? 'badge-success' :
                    del.type === 'proposal' ? 'badge-warning' :
                    'badge-info'
                  ]">{{ del.type }}</span>
                  <span class="badge badge-xs" :class="[
                    del.status === 'accepted' ? 'badge-success' :
                    del.status === 'submitted' ? 'badge-primary' :
                    del.status === 'ready' ? 'badge-warning' :
                    'badge-muted'
                  ]">{{ del.status }}</span>
                </div>
                <button v-if="del.file_path" class="mt-2 text-sm text-primary hover:underline font-mono" @click="navigator.clipboard.writeText(del.file_path)">
                  Copiar ruta: {{ del.file_path }}
                </button>
              </div>
              <button v-if="del.status === 'ready'" @click="markDelivered" class="btn-primary px-3 py-1.5 text-sm shrink-0">
                <CheckCircle class="h-4 w-4 mr-1" /> Entregar
              </button>
              <button class="p-1.5 hover:bg-muted/30 rounded" @click="updateDeliverableStatus(del, 'submitted')" title="Marcar como enviado">
                <Send class="h-3.5 w-3.5" />
              </button>
              <button class="p-1.5 hover:bg-muted/30 rounded text-destructive" @click="deleteDeliverable(del)" title="Eliminar">
                <Trash2 class="h-3.5 w-3.5" />
              </button>
            </div>
            <div v-if="!work.deliverables.length" class="p-8 text-center text-muted-foreground">
              <FileText class="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p>Sin entregables. Se crean al preparar la entrega.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.625rem;
  font-family: var(--font-mono);
  font-weight: 500;
}
.badge-primary { background: var(--color-primary); color: var(--color-primary-foreground); opacity: 0.15; }
.badge-success { background: var(--color-success); color: var(--color-success); opacity: 0.15; }
.badge-warning { background: var(--color-warning); color: var(--color-warning); opacity: 0.15; }
.badge-destructive { background: var(--color-destructive); color: var(--color-destructive); opacity: 0.15; }
.badge-info { background: var(--ownex-danger); color: var(--ownex-danger); opacity: 0.15; }
.badge-muted { background: var(--color-muted); color: var(--color-muted-foreground); }
.badge-xs { padding: 0.125rem 0.375rem; font-size: 0.5625rem; }
.btn-primary { border-radius: 0.5rem; background: var(--color-primary); color: var(--color-primary-foreground); font-weight: 500; transition: opacity 0.2s; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.4; }
.btn-success { border-radius: 0.5rem; background: var(--color-success); color: var(--color-success-foreground); font-weight: 500; transition: opacity 0.2s; }
.btn-success:hover { opacity: 0.9; }
</style>