<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import type { Finding, WsEvent } from '@/types'
import { useFindingsStore } from '@/stores/findings'
import { useBountyStream } from '@/composables/useBountyStream'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { X, Video, FileText, Sparkles, CheckCircle2, XCircle, RotateCcw, AlertTriangle } from '@lucide/vue'

const props = defineProps<{ finding: Finding | null }>()
const emit = defineEmits<{ close: []; 'status-updated': [] }>()

const store = useFindingsStore()
const { onWsEvent } = useBountyStream()

const narrative = ref('')
const regenLoading = ref(false)
const actionLoading = ref<'approve' | 'discard' | 'revalidate' | null>(null)
const triageOpen = ref(false)
const videoError = ref(false)

watch(() => props.finding, (f) => {
  if (f) {
    narrative.value = ''
    triageOpen.value = false
    videoError.value = false
  }
})

const wsCleanup = onWsEvent('finding:', (e: WsEvent) => {
  if (e.payload?.id === props.finding?.id) {
    emit('status-updated')
  }
})
onUnmounted(wsCleanup)

async function handleRegen() {
  if (!props.finding) return
  regenLoading.value = true
  try {
    const res = await store.regenerateNarrative(props.finding.id)
    if (res?.narrative) narrative.value = res.narrative
  } catch {
    narrative.value = 'Error al regenerar la narrativa.'
  } finally {
    regenLoading.value = false
  }
}

async function handleAction(action: 'approve' | 'discard' | 'revalidate') {
  if (!props.finding || actionLoading.value) return
  actionLoading.value = action
  try {
    if (action === 'approve') {
      await store.submitAsReport(props.finding.id, 'hackerone')
      await store.updateStatus(props.finding.id, 'SUBMITTED')
    } else if (action === 'discard') {
      await store.updateStatus(props.finding.id, 'DISCARDED')
    } else {
      await store.updateStatus(props.finding.id, 'RE_VALIDATE')
    }
    emit('status-updated')
    emit('close')
  } catch { /* toast handled by parent */ }
  finally { actionLoading.value = null }
}

function severityVariant(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}
</script>

<template>
  <Transition name="drawer">
    <aside v-if="finding" class="fixed right-0 top-0 z-30 flex h-full w-[480px] flex-col border-l border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-border/40 px-5 py-4">
        <div class="flex items-center gap-2 min-w-0">
          <Badge :variant="severityVariant(finding.severity)" class="text-[10px] px-1.5 py-0 shrink-0">{{ finding.severity }}</Badge>
          <span class="text-sm font-semibold text-foreground truncate">{{ finding.title }}</span>
        </div>
        <button @click="emit('close')" class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-surface transition-colors">
          <X class="h-3.5 w-3.5" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto">
        <div class="space-y-5 p-5">
          <!-- Status & Metadata -->
          <div class="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>Target: <span class="text-foreground font-medium">{{ finding.target_name || `#${finding.target_id}` }}</span></span>
            <span v-if="finding.endpoint_path" class="font-mono">{{ finding.endpoint_path }}</span>
            <span v-if="finding.payout" class="text-gold font-semibold">${{ finding.payout.toLocaleString() }}</span>
          </div>

          <!-- Video Evidence Viewer -->
          <div v-if="finding.poc_path" class="space-y-1">
            <div class="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <Video class="h-3 w-3" />
              <span>Evidencia (PoC)</span>
            </div>
            <div v-if="videoError" class="flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <AlertTriangle class="h-3 w-3" />
              <span>No se pudo cargar el video</span>
            </div>
            <video
              v-else
              :src="finding.poc_path"
              controls
              class="w-full rounded-lg border border-border/40 bg-black/40"
              @error="videoError = true"
            >
              Tu navegador no soporta video.
            </video>
          </div>

          <!-- Narrative Editor -->
          <div class="space-y-1">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                <FileText class="h-3 w-3" />
                <span>Narrativa</span>
              </div>
              <Button variant="ghost" size="sm" @click="handleRegen" :disabled="regenLoading" class="text-xs">
                <Sparkles class="h-3 w-3" />
                {{ regenLoading ? 'Generando...' : 'Regenerar con IA' }}
              </Button>
            </div>
            <textarea
              v-model="narrative"
              placeholder="Describe el hallazgo... (opcional)"
              class="w-full min-h-[120px] rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20 resize-y"
            />
          </div>

          <!-- Triage Predictions -->
          <div v-if="finding.suggested_responses?.length" class="space-y-1">
            <button @click="triageOpen = !triageOpen" class="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors">
              <Sparkles class="h-3 w-3" />
              <span>Triage Predictivo ({{ finding.suggested_responses.length }})</span>
              <span class="ml-1 text-[10px]">{{ triageOpen ? '▼' : '▶' }}</span>
            </button>
            <Transition name="collapse">
              <div v-if="triageOpen" class="space-y-2 mt-2">
                <Card v-for="(sug, i) in finding.suggested_responses" :key="i" class="p-3">
                  <p class="text-xs text-foreground">{{ sug }}</p>
                </Card>
              </div>
            </Transition>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="border-t border-border/40 p-4 flex gap-2">
        <Button
          variant="default"
          class="flex-1"
          @click="handleAction('approve')"
          :loading="actionLoading === 'approve'"
        >
          <CheckCircle2 class="h-4 w-4" />
          Aprobar y Enviar
        </Button>
        <Button
          variant="secondary"
          class="flex-1"
          @click="handleAction('discard')"
          :loading="actionLoading === 'discard'"
        >
          <XCircle class="h-4 w-4" />
          Descartar
        </Button>
        <Button
          variant="ghost"
          class="flex-1"
          @click="handleAction('revalidate')"
          :loading="actionLoading === 'revalidate'"
        >
          <RotateCcw class="h-4 w-4" />
          Re-validar
        </Button>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
