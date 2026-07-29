<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { Activity, FileText, Play, Plus, RefreshCw, Workflow, CheckCircle2, XCircle, Clock, Loader2 } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

interface WorkflowTemplate {
  file: string
  name: string
  description: string
  steps: { id: string; type: string }[]
}

interface WorkflowRun {
  id: string
  template_name: string
  target: string
  status: string
  steps: { id: string; type: string; params: Record<string, any> }[]
  results: { step_id: string; status: string; output: any; error: string | null }[]
  created_at: string
  updated_at: string
}

const { toast } = useToast()
const templates = ref<WorkflowTemplate[]>([])
const runs = ref<WorkflowRun[]>([])
const loading = ref(true)
const creating = ref<string | null>(null)
const targetInput = ref('')
const selectedTemplate = ref<string | null>(null)
const showNewDialog = ref(false)
const activeTab = ref<'templates' | 'runs'>('templates')

const tabData = computed(() => activeTab.value === 'templates' ? templates.value : runs.value)
const tabLabel = computed(() => activeTab.value === 'templates' ? 'Plantillas' : 'Ejecuciones')

async function fetchAll() {
  loading.value = true
  try {
    const [tRes, rRes] = await Promise.all([
      fetch('/api/core/workflows/templates'),
      fetch('/api/core/workflows/runs'),
    ])
    if (tRes.ok) {
      const d = await tRes.json()
      templates.value = d.templates || []
    }
    if (rRes.ok) {
      const d = await rRes.json()
      runs.value = d.runs || []
    }
  } catch {
    toast.error('Error', 'No se pudieron cargar workflows')
  } finally {
    loading.value = false
  }
}

async function createRun(templateFile: string) {
  creating.value = templateFile
  try {
    const res = await fetch('/api/core/workflows/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template_file: templateFile, target: targetInput.value }),
    })
    if (res.ok) {
      toast.success('Workflow', 'Ejecución creada')
      targetInput.value = ''
      selectedTemplate.value = null
      showNewDialog.value = false
      await fetchAll()
      activeTab.value = 'runs'
    } else {
      const err = await res.json()
      toast.error('Error', err.error || 'No se pudo crear')
    }
  } catch {
    toast.error('Error', 'Error de conexión')
  } finally {
    creating.value = null
  }
}

function statusBadgeVariant(s: string): 'success' | 'warning' | 'info' | 'destructive' | 'outline' {
  const m: Record<string, 'success' | 'warning' | 'info' | 'destructive' | 'outline'> = { completed: 'success', running: 'warning', pending: 'info', failed: 'destructive', cancelled: 'outline' }
  return m[s] || 'outline'
}

function statusIcon(s: string) {
  const m: Record<string, any> = { completed: CheckCircle2, running: Loader2, pending: Clock, failed: XCircle, cancelled: XCircle }
  return m[s] || Clock
}

onMounted(fetchAll)
</script>

<template>
  <div class="p-6 space-y-6 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
          <Workflow class="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight text-foreground">Workflows</h1>
          <p class="text-xs text-muted-foreground">Automatizaciones basadas en plantillas YAML</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button size="sm" variant="outline" @click="fetchAll">
          <RefreshCw class="h-3.5 w-3.5" /> Actualizar
        </Button>
        <Button size="sm" @click="showNewDialog = true">
          <Play class="h-3.5 w-3.5" /> Nueva ejecución
        </Button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 border-b border-border/20">
      <button v-for="tab in [{id:'templates',label:'Plantillas'},{id:'runs',label:'Ejecuciones'}]" :key="tab.id"
        @click="activeTab = tab.id as any"
        class="px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-wider transition-colors border-b-2 -mb-[1px]"
        :class="activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'"
      >
        {{ tab.label }}
        <span class="ml-1.5 text-[9px] opacity-50">{{ tab.id === 'templates' ? templates.length : runs.length }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 3" :key="i" class="h-20 rounded-xl" />
    </div>

    <!-- Templates tab -->
    <template v-else-if="activeTab === 'templates'">
      <div v-if="templates.length === 0" class="text-center py-12 text-muted-foreground">
        <FileText class="h-8 w-8 mx-auto mb-2 opacity-40" />
        <p class="font-mono text-xs">No hay plantillas disponibles</p>
      </div>
      <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="t in templates" :key="t.file"
          class="rounded-xl border border-border/30 bg-surface/30 p-4 hover:border-primary/30 transition-colors"
        >
          <div class="flex items-start justify-between mb-2">
            <h3 class="font-medium text-sm text-foreground">{{ t.name }}</h3>
            <Badge variant="outline" class="font-mono text-[9px]">{{ t.steps.length }} pasos</Badge>
          </div>
          <p class="text-xs text-muted-foreground mb-3 line-clamp-2">{{ t.description }}</p>
          <div class="flex flex-wrap gap-1 mb-3">
            <Badge v-for="s in t.steps" :key="s.id" variant="info" class="font-mono text-[8px]">{{ s.type }}</Badge>
          </div>
          <Button size="sm" variant="outline" class="w-full text-xs" @click="selectedTemplate = t.file; targetInput = ''; showNewDialog = true">
            <Play class="h-3 w-3 mr-1" /> Ejecutar
          </Button>
        </div>
      </div>
    </template>

    <!-- Runs tab -->
    <template v-else>
      <div v-if="runs.length === 0" class="text-center py-12 text-muted-foreground">
        <Activity class="h-8 w-8 mx-auto mb-2 opacity-40" />
        <p class="font-mono text-xs">No hay ejecuciones aún</p>
      </div>
      <div v-else class="space-y-2">
        <div v-for="r in runs" :key="r.id"
          class="rounded-xl border border-border/30 bg-surface/30 p-4"
        >
          <div class="flex items-start justify-between mb-2">
            <div>
              <h3 class="font-medium text-sm text-foreground">{{ r.template_name }}</h3>
              <p class="font-mono text-[10px] text-muted-foreground">{{ r.id }} · {{ new Date(r.created_at).toLocaleString() }}</p>
            </div>
            <Badge :variant="statusBadgeVariant(r.status)" class="font-mono text-[9px]">
              <component :is="statusIcon(r.status)" :class="r.status === 'running' ? 'animate-spin' : ''" class="h-2.5 w-2.5 mr-1" />
              {{ r.status }}
            </Badge>
          </div>
          <div v-if="r.target" class="mb-2">
            <Badge variant="outline" class="font-mono text-[9px]">Target: {{ r.target }}</Badge>
          </div>
          <div class="flex flex-wrap gap-1">
            <div v-for="res in r.results" :key="res.step_id"
              class="flex items-center gap-1 font-mono text-[9px] px-2 py-0.5 rounded-md"
              :class="res.status === 'completed' ? 'bg-success/10 text-success' : res.status === 'failed' ? 'bg-destructive/10 text-destructive' : 'bg-muted/20 text-muted-foreground'"
            >
              <component :is="statusIcon(res.status)" class="h-2.5 w-2.5" />
              {{ res.step_id }}
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- New run dialog -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showNewDialog" class="fixed inset-0 z-[100] flex items-center justify-center p-4" @click.self="showNewDialog = false">
          <div class="fixed inset-0 bg-black/70 backdrop-blur-sm" />
          <div class="relative w-full max-w-md card-base rounded-2xl border border-border/50 overflow-hidden">
            <div class="px-5 py-4 border-b border-border/20">
              <h2 class="font-bold text-sm text-foreground">Nueva ejecución</h2>
              <p class="text-xs text-muted-foreground">Seleccioná una plantilla y definí el target</p>
            </div>
            <div class="px-5 py-4 space-y-4">
              <div>
                <label class="mb-1 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Plantilla</label>
                <select v-model="selectedTemplate" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3 py-2 font-mono text-sm text-foreground">
                  <option value="" disabled>Seleccionar plantilla</option>
                  <option v-for="t in templates" :key="t.file" :value="t.file">{{ t.name }}</option>
                </select>
              </div>
              <div>
                <label class="mb-1 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Target (opcional)</label>
                <input v-model="targetInput" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3 py-2 font-mono text-sm text-foreground" placeholder="ej: example.com" />
              </div>
            </div>
            <div class="flex justify-end gap-2 px-5 py-3 border-t border-border/20">
              <Button variant="ghost" size="sm" @click="showNewDialog = false">Cancelar</Button>
              <Button size="sm" :disabled="!selectedTemplate" :loading="creating !== null" @click="selectedTemplate && createRun(selectedTemplate)">
                <Play class="h-3.5 w-3.5" /> Ejecutar
              </Button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
