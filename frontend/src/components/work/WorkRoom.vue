<script setup lang="ts">
/**
 * WorkRoom — Sala de trabajo individual sobre el contrato REAL del Work Bank.
 *
 * Contrato usado (verificado contra api/routers/direct_work.py):
 *   GET  /direct-work/workbank                              → estado + items
 *   POST /direct-work/workbank/{id}/deliver/prepare         → genera paquete en disco
 *   GET  /direct-work/workbank/{id}/file/{filename}         → lee archivo del paquete
 *   PUT  /direct-work/workbank/{id}/file/{filename}         → edita archivo del paquete
 *   POST /direct-work/workbank/{id}/deliver/approve         → humano confirma envío
 *   POST /direct-work/workbank/{id}/submit                  → envío real a plataforma
 *
 * Sin endpoints ficticios: sin CRUD de evidencia/entregables (no existen),
 * sin pipeline de etapas, sin actividad de agentes inventada.
 */

import {
  AlertTriangle,
  CheckCircle,
  ChevronLeft,
  Clock,
  ExternalLink,
  FileText,
  FolderOpen,
  LayoutDashboard,
  Loader2,
  Save,
  Send,
  Zap,
  Shield,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { useNotificationsStore } from '@/stores/notifications'
import Button from '@/components/ui/Button.vue'
import CodeEditor from '@/components/ui/CodeEditor.vue'
import DiffViewer from '@/components/ui/DiffViewer.vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

interface WorkItem {
  id: string
  title: string
  platform: string
  category: string
  reward: number
  barrier_score: number
  employment_type: string
  status: string
  access_status: string
  access_requirement: string
  deliverables: string[]
  created_at: string
  ready_to_deliver: boolean
  description: string
  url: string
  payout_method: string
  payout_method_rationale: string
  started_at: string | null
  delivered_at: string | null
  human_minutes_actual: number | null
}

const route = useRoute()
const router = useRouter()
const notifications = useNotificationsStore()

const workId = route.params.id as string
const item = ref<WorkItem | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const busy = ref<string | null>(null)
const trustNote = ref<string | null>(null)
const activeTab = ref<'overview' | 'deliver' | 'files'>('overview')

// Archivos del paquete (contrato real: read/write por filename)
const fileName = ref('')
const fileContent = ref('')
/** Contenido tal como lo dejó `prepare`: la base del diff. */
const fileOriginal = ref('')
const showDiff = ref(false)
const fileLoading = ref(false)
const fileSaving = ref(false)
const fileError = ref<string | null>(null)

const stateConfig: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info'; icon: any }> = {
  discovered: { label: 'Descubierto', variant: 'info', icon: LayoutDashboard },
  preparing: { label: 'Preparando', variant: 'warning', icon: Loader2 },
  ready_to_deliver: { label: 'Listo para entregar', variant: 'success', icon: CheckCircle },
  delivered: { label: 'Entregado', variant: 'success', icon: Shield },
  needs_access: { label: 'Necesita acceso', variant: 'error', icon: AlertTriangle },
  rejected: { label: 'Rechazado', variant: 'error', icon: AlertTriangle },
  archived: { label: 'Archivado', variant: 'default', icon: LayoutDashboard },
}

const state = computed(() => stateConfig[item.value?.status || 'discovered'] || stateConfig.discovered)
const isDelivered = computed(() => item.value?.status === 'delivered')

const hours = computed(() => item.value?.human_minutes_actual || 0)
const netPerHour = computed(() => {
  const h = hours.value
  return h > 0 ? (item.value?.reward || 0) / (h / 60) : null
})

const tabs = [
  { id: 'overview', label: 'Visión general', icon: LayoutDashboard },
  { id: 'deliver', label: 'Entrega', icon: Send },
  { id: 'files', label: 'Archivos', icon: FolderOpen },
] as const

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await api.get<{ items: WorkItem[] }>('/direct-work/workbank')
    item.value = res.items?.find((i) => i.id === workId) || null
    if (!item.value) error.value = 'Ese trabajo no está en el Work Bank'
  } catch (e: any) {
    error.value = e?.message || 'No se pudo cargar el trabajo'
  } finally {
    loading.value = false
  }
}

async function prepareDelivery() {
  busy.value = 'prepare'
  try {
    const res = await api.post<{ path?: string }>(`/direct-work/workbank/${workId}/deliver/prepare`)
    notifications.success(res.path ? `Paquete preparado en: ${res.path}` : 'Paquete preparado')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error preparando entrega')
  } finally {
    busy.value = null
  }
}

async function markDelivered() {
  busy.value = 'approve'
  try {
    const res = await api.post<SubmitResponse>(`/direct-work/workbank/${workId}/deliver/approve`)
    const failure = submitFailure(res)
    if (failure) {
      notifications.error(failure)
      await load()
      return
    }
    notifications.success(res?.message || 'Marcado como entregado — queda en REVIEWING hasta confirmación de la plataforma')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error al entregar')
  } finally {
    busy.value = null
  }
}

/**
 * Los endpoints de envío responden HTTP 200 aunque el envío haya caído en
 * DLQ o el trust engine lo rechace. Informar "Enviado" en ese caso es
 * afirmar un envío que no ocurrió. Cada ruta usa SU campo de falla:
 *   · submit     → { success, message, last_error, status }
 *   · auto-submit→ { success, reason, status }        (sin `message`)
 *   · approve    → { status, ... }                     (no trae `success`)
 */
interface SubmitResponse {
  success?: boolean
  status?: string
  message?: string
  reason?: string
  last_error?: string | null
  attempts?: number
}

function submitFailure(res: SubmitResponse | undefined): string | null {
  if (res?.success !== false) return null
  return res.message || res.last_error || res.reason || `Envío no completado (estado: ${res.status ?? 'desconocido'})`
}

async function submitToPlatform() {
  busy.value = 'submit'
  try {
    const res = await api.post<SubmitResponse>(`/direct-work/workbank/${workId}/submit`)
    // El backend devuelve HTTP 200 aunque el envío haya caído en DLQ
    // (`success: false`). Informar "Enviado" en ese caso es afirmar un
    // envío que no ocurrió.
    const failure = submitFailure(res)
    if (failure) {
      notifications.error(failure)
      await load()
      return
    }
    notifications.success(res?.message || 'Enviado a la plataforma')
    await load()
  } catch (e: any) {
    notifications.error(e?.message || 'Error al enviar')
  } finally {
    busy.value = null
  }
}

async function tryAutoSubmit() {
  busy.value = 'auto'
  trustNote.value = null
  try {
    const res = await api.post<SubmitResponse>(`/direct-work/workbank/${workId}/auto-submit`)
    // `auto-submit` NO envía nada todavía: el executor tiene un TODO y
    // devuelve `requires_manual_action: true`. Decirlo evita que el botón
    // prometa un envío que no ocurre.
    if (res?.success === false) {
      trustNote.value = `Trust engine: ${res.reason || 'no aprobó'}`
      return
    }
    // Aunque el trust engine apruebe, hoy NO envía: el executor tiene un
    // TODO y devuelve `requires_manual_action: true`. El `reason` técnico no
    // reemplaza esa advertencia, porque "ok" no significa "enviado".
    trustNote.value = res?.reason
      ? `Trust engine: ${res.reason}. El envío real lo hacés vos (auto-submit aún no envía).`
      : 'Trust engine aprobó. El envío real lo hacés vos: auto-submit aún no envía.'
    await load()
  } catch (e: any) {
    trustNote.value = e?.message || 'No se pudo consultar al trust engine'
  } finally {
    busy.value = null
  }
}

async function openFile() {
  const name = fileName.value.trim()
  if (!name) return
  fileLoading.value = true
  fileError.value = null
  try {
    const res = await api.get<string>(`/direct-work/workbank/${workId}/file/${encodeURIComponent(name)}`)
    const content = typeof res === 'string' ? res : JSON.stringify(res, null, 2)
    fileContent.value = content
    // El original congelado es la base del diff: sin él, editar el paquete
    // es escribir a ciegas y no hay forma de ver qué se cambió antes de
    // aprobar el envío.
    fileOriginal.value = content
  } catch (e: any) {
    fileError.value = e?.message || 'No se pudo leer el archivo'
  } finally {
    fileLoading.value = false
  }
}

async function saveFile() {
  const name = fileName.value.trim()
  if (!name) return
  fileSaving.value = true
  fileError.value = null
  try {
    await api.put(`/direct-work/workbank/${workId}/file/${encodeURIComponent(name)}`, { content: fileContent.value })
    fileOriginal.value = fileContent.value
    notifications.success('Archivo guardado en el paquete')
  } catch (e: any) {
    fileError.value = e?.message || 'No se pudo guardar'
  } finally {
    fileSaving.value = false
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-AR', { hour12: false, day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div class="flex items-start gap-3">
        <Button variant="ghost" size="sm" aria-label="Volver" @click="router.back()">
          <ChevronLeft class="h-4 w-4" />
        </Button>
        <div>
          <h1 class="text-lg font-semibold text-foreground sm:text-xl">
            {{ item?.title || 'Sala de trabajo' }}
          </h1>
          <p class="mt-0.5 font-mono text-[11px] text-muted-foreground">
            {{ workId }} · {{ item?.platform || '—' }}
          </p>
        </div>
      </div>
      <div v-if="item" class="flex items-center gap-2">
        <Badge :variant="state.variant">
          <component :is="state.icon" class="mr-1 h-3 w-3" />{{ state.label }}
        </Badge>
      </div>
    </div>

    <Skeleton v-if="loading" class="h-40" />
    <div v-else-if="error" class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
      {{ error }}
    </div>

    <template v-else-if="item">
      <!-- Tabs -->
      <div class="flex gap-1 border-b border-border/40">
        <button
          v-for="t in tabs"
          :key="t.id"
          :aria-pressed="activeTab === t.id"
          class="flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs transition-colors"
          :class="activeTab === t.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
          @click="activeTab = t.id"
        >
          <component :is="t.icon" class="h-3.5 w-3.5" />{{ t.label }}
        </button>
      </div>

      <!-- OVERVIEW -->
      <div v-if="activeTab === 'overview'" class="space-y-4">
        <Card class="p-4">
          <h2 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Qué es</h2>
          <p class="mt-2 whitespace-pre-wrap text-sm text-foreground">{{ item.description || 'Sin descripción.' }}</p>
          <a
            v-if="item.url"
            :href="item.url"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-3 inline-flex items-center gap-1 text-xs text-primary hover:underline"
          >
            <ExternalLink class="h-3 w-3" /> Abrir en {{ item.platform }}
          </a>
        </Card>

        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card class="p-3">
            <p class="text-[9px] uppercase text-muted-foreground">Recompensa</p>
            <p class="mt-1 font-mono text-base font-semibold text-foreground">${{ Math.round(item.reward || 0) }}</p>
          </Card>
          <Card class="p-3">
            <p class="text-[9px] uppercase text-muted-foreground">Neto/hora</p>
            <p class="mt-1 font-mono text-base font-semibold text-foreground">
              {{ netPerHour != null ? `$${Math.round(netPerHour)}` : '—' }}
            </p>
            <p class="text-[9px] text-muted-foreground">{{ hours }} min humanos</p>
          </Card>
          <Card class="p-3">
            <p class="text-[9px] uppercase text-muted-foreground">Barrera</p>
            <p class="mt-1 font-mono text-base font-semibold text-foreground">{{ Math.round(item.barrier_score || 0) }}</p>
          </Card>
          <Card class="p-3">
            <p class="text-[9px] uppercase text-muted-foreground">Pago</p>
            <p class="mt-1 font-mono text-sm font-semibold text-foreground">{{ item.payout_method || 'UNKNOWN' }}</p>
          </Card>
        </div>

        <Card class="p-4">
          <h2 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Tiempos</h2>
          <dl class="mt-2 grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
            <div><dt class="text-muted-foreground">Creado</dt><dd class="font-mono">{{ formatTime(item.created_at) }}</dd></div>
            <div><dt class="text-muted-foreground">Iniciado</dt><dd class="font-mono">{{ formatTime(item.started_at) }}</dd></div>
            <div><dt class="text-muted-foreground">Entregado</dt><dd class="font-mono">{{ formatTime(item.delivered_at) }}</dd></div>
          </dl>
        </Card>

        <div v-if="item.access_status !== 'public' || item.access_requirement" class="rounded-lg border border-warning/50 bg-warning/10 p-3 text-xs text-foreground">
          <span class="font-semibold">Requiere acceso:</span> {{ item.access_requirement || item.access_status }}
        </div>
      </div>

      <!-- DELIVER -->
      <div v-else-if="activeTab === 'deliver'" class="space-y-4">
        <Card class="p-4">
          <h2 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Paquete de entrega</h2>
          <p class="mt-2 text-xs text-muted-foreground">
            <span class="font-mono text-[10px]">1 · prepare</span> genera el paquete en disco ·
            <span class="font-mono text-[10px]">2 · edita</span> los archivos en la pestaña Archivos ·
            <span class="font-mono text-[10px]">3 · approve</span> registra el envío (queda en REVIEWING, no es pago).
          </p>
          <div class="mt-3 flex flex-wrap gap-2">
            <Button :disabled="busy === 'prepare'" @click="prepareDelivery">
              <Loader2 v-if="busy === 'prepare'" class="mr-1 h-3.5 w-3.5 animate-spin" />
              <FileText v-else class="mr-1 h-3.5 w-3.5" /> Preparar paquete
            </Button>
            <Button
              variant="outline"
              :disabled="busy === 'approve' || isDelivered || !item.ready_to_deliver"
              @click="markDelivered"
            >
              <CheckCircle v-if="busy !== 'approve'" class="mr-1 h-3.5 w-3.5" />
              {{ isDelivered ? 'Ya entregado' : 'Marcar entregado' }}
            </Button>
            <Button
              variant="outline"
              :disabled="busy === 'submit' || !item.ready_to_deliver"
              title="Envío real a la plataforma (idempotente, con retry y DLQ)"
              @click="submitToPlatform"
            >
              <Send class="mr-1 h-3.5 w-3.5" /> Enviar a plataforma
            </Button>
            <Button
              variant="ghost"
              :disabled="busy === 'auto' || !item.ready_to_deliver"
              title="Consulta al trust engine: si aprueba, prepara el envío. Si rechaza, te dice POR QUÉ."
              @click="tryAutoSubmit"
            >
              <Zap class="mr-1 h-3.5 w-3.5" /> Auto (trust engine)
            </Button>
          </div>
          <p v-if="trustNote" class="mt-2 text-[11px] text-muted-foreground" data-testid="trust-note">
            {{ trustNote }}
          </p>
          <p v-if="!item.ready_to_deliver" class="mt-2 text-[11px] text-muted-foreground">
            <AlertTriangle class="mr-1 inline h-3 w-3" />No está listo: primero prepará el paquete.
          </p>
        </Card>

        <Card v-if="item.deliverables?.length" class="p-4">
          <h2 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Entregables declarados</h2>
          <ul class="mt-2 space-y-1 text-xs text-foreground">
            <li v-for="(d, i) in item.deliverables" :key="i">· {{ d }}</li>
          </ul>
        </Card>
      </div>

      <!-- FILES -->
      <div v-else class="space-y-3">
        <Card class="p-4">
          <h2 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Archivo del paquete</h2>
          <p class="mt-1 text-[11px] text-muted-foreground">
            Lectura y edición directa del paquete generado por <span class="font-mono">prepare</span> (README.md, proposal.md, work.md).
          </p>
          <div class="mt-3 flex gap-2">
            <input
              v-model="fileName"
              placeholder="README.md"
              class="flex-1 rounded-md border border-border/50 bg-background px-3 py-1.5 font-mono text-xs text-foreground"
            />
            <Button variant="outline" :disabled="fileLoading || !fileName" @click="openFile">
              <Loader2 v-if="fileLoading" class="mr-1 h-3.5 w-3.5 animate-spin" />
              <FolderOpen v-else class="mr-1 h-3.5 w-3.5" /> Abrir
            </Button>
            <Button :disabled="fileSaving || !fileName" @click="saveFile">
              <Loader2 v-if="fileSaving" class="mr-1 h-3.5 w-3.5 animate-spin" />
              <Save v-else class="mr-1 h-3.5 w-3.5" /> Guardar
            </Button>
          </div>
          <p v-if="fileError" class="mt-2 text-[11px] text-destructive">{{ fileError }}</p>
          <!-- Editor real: el deliverable de un bounty es código (diff del PR,
               PoC, test). Un textarea no da números de línea, Tab que
               indenta, ni resaltado — y en seguridad cada línea cuenta. -->
          <CodeEditor
            v-model="fileContent"
            :language="fileName"
            :min-height="'18rem'"
            :max-height="'34rem'"
            class="mt-3"
          />

          <!-- Diff contra el original congelado. Un bounty se judgea por el
               diff: sin esto, aprobar el envío es aprobar a ciegas. -->
          <div v-if="fileOriginal" class="mt-3">
            <button
              type="button"
              class="text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              @click="showDiff = !showDiff"
            >
              {{ showDiff ? 'Ocultar cambios' : 'Ver cambios' }}
            </button>
            <DiffViewer
              v-if="showDiff"
              :original="fileOriginal"
              :modified="fileContent"
              :filename="fileName"
              class="mt-2"
            />
          </div>
        </Card>
        <p class="flex items-center gap-1 text-[10px] text-muted-foreground">
          <Clock class="h-3 w-3" /> Cada guardado es un write al disco del paquete: la entrega final la confirmás vos.
        </p>
      </div>
    </template>
  </div>
</template>
