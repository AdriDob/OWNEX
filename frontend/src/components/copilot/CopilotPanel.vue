<script setup lang="ts">
import { ref, computed, nextTick, watch, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { assistantStreamChat } from '@/lib/api'
import { X, Send, Bot, User, Loader2, Sparkles, FileText, Activity, Eye } from '@lucide/vue'
import ScrollArea from '@/components/ui/ScrollArea.vue'
import Button from '@/components/ui/Button.vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const route = useRoute()
const messages = ref<Array<{ role: string; content: string }>>([])
const input = ref('')
const loading = ref(false)
const abortController = ref<AbortController | null>(null)
const chatEnd = ref<HTMLDivElement | null>(null)

const isFindingsRoute = computed(() => route.path.startsWith('/findings'))
const isMissionControl = computed(() => route.path.startsWith('/mission-control') || route.path.startsWith('/legacy'))

const systemContext = computed(() => {
  if (isFindingsRoute.value) return 'Eres un asistente de redacción de reportes de seguridad. Ayuda al operador a redactar reportes claros y profesionales para plataformas de bug bounty.'
  if (isMissionControl.value) return 'Eres un analista de operaciones de seguridad. Ayuda al operador a entender el estado del sistema, priorizar objetivos y optimizar el pipeline.'
  return 'Eres CATEYE Copilot, un asistente de operaciones de bug bounty. Responde preguntas sobre el sistema, hallazgos y recomendaciones.'
})

const suggestions = computed(() => {
  if (isFindingsRoute.value) return ['Redactá un reporte para este hallazgo', '¿Qué severidad debería asignar?', '¿Cómo describir el impacto?']
  if (isMissionControl.value) return ['Resumí el estado actual', '¿Cuál es la mejor oportunidad?', '¿Qué debo hacer ahora?']
  return ['¿Cómo va el pipeline?', 'Mostrame las métricas', '¿Qué hay de nuevo?']
})

const modeLabel = computed(() => {
  if (isFindingsRoute.value) return 'Reportes'
  if (isMissionControl.value) return 'Ops'
  return 'General'
})

watch(() => props.open, (o) => {
  if (o && messages.value.length === 0) {
    messages.value = [{ role: 'assistant', content: `Soy CATEYE Copilot (${modeLabel.value}). ¿En qué puedo ayudarte?` }]
  }
})

function appendToken(token: string) {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content += token
  } else {
    messages.value.push({ role: 'assistant', content: token })
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true

  abortController.value = new AbortController()
  try {
    await assistantStreamChat(
      text,
      messages.value.slice(-10),
      appendToken,
      systemContext.value,
      abortController.value.signal,
    )
  } catch (e: any) {
    if (e?.name === 'AbortError') return
    messages.value.push({ role: 'assistant', content: 'Error al conectar con CATEYE. Intentá de nuevo.' })
  } finally {
    loading.value = false
    abortController.value = null
  }
}

function stopStreaming() {
  abortController.value?.abort()
  loading.value = false
}

function sendSuggestion(text: string) {
  input.value = text
  send()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  if (e.key === 'Escape') { if (loading.value) stopStreaming(); else emit('close') }
}

watch(() => messages.value.length, async () => {
  await nextTick()
  chatEnd.value?.scrollIntoView({ behavior: 'smooth' })
})
</script>

<template>
  <Transition name="panel">
    <aside v-if="open" class="fixed right-0 top-0 z-40 flex h-full w-80 flex-col border-l border-border/50 bg-background/95 backdrop-blur-xl shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-border/40 px-4 py-3 scanline">
        <div class="flex items-center gap-2">
          <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 ring-1 ring-primary/20">
            <Eye class="h-3.5 w-3.5 text-primary" />
          </div>
          <span class="font-mono text-sm font-bold tracking-wide text-foreground">CATEYE</span>
          <span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">{{ modeLabel }}</span>
        </div>
        <button @click="emit('close')" class="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-surface transition-colors">
          <X class="h-3.5 w-3.5" />
        </button>
      </div>

      <!-- Suggestions -->
      <div v-if="messages.length <= 1" class="px-4 pt-3 space-y-1.5">
        <p class="font-mono text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">Sugerencias</p>
        <button v-for="(s, i) in suggestions" :key="i"
          @click="sendSuggestion(s)"
          class="w-full text-left rounded-lg border border-border/30 px-3 py-2 font-mono text-xs text-muted-foreground hover:bg-surface hover:text-foreground transition-colors"
        >{{ s }}</button>
      </div>

      <ScrollArea class="flex-1 px-4 py-4">
        <div class="space-y-4">
          <div v-for="(msg, i) in messages" :key="i"
            :class="['flex gap-3 animate-in', msg.role === 'user' ? 'justify-end' : 'justify-start']"
          >
            <div :class="['max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed', msg.role === 'user' ? 'bg-primary/15 text-foreground' : 'glass-terminal text-muted-foreground']">
              <p class="whitespace-pre-wrap font-mono text-xs leading-relaxed">{{ msg.content }}</p>
            </div>
          </div>

          <div v-if="loading" class="flex items-center gap-2 text-muted-foreground text-sm animate-in">
            <Loader2 class="h-3.5 w-3.5 animate-spin" />
            <span class="font-mono text-xs">Procesando...</span>
          </div>

          <div ref="chatEnd" />
        </div>
      </ScrollArea>

      <div class="border-t border-border/40 p-3">
        <div class="flex gap-2">
          <input
            v-model="input"
            @keydown="handleKeydown"
            placeholder="Consultar a CATEYE..."
            class="flex-1 rounded-lg border border-border/60 bg-surface/50 px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
            :disabled="loading"
          />
          <Button v-if="!loading" size="icon" @click="send" :disabled="!input.trim()">
            <Send class="h-4 w-4" />
          </Button>
          <Button v-else variant="destructive" size="icon" @click="stopStreaming">
            <X class="h-4 w-4" />
          </Button>
        </div>
        <p class="mt-1.5 font-mono text-[10px] text-muted-foreground/50 text-center">Ctrl+B toggle · Esc parar</p>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.panel-enter-active, .panel-leave-active { transition: transform 0.2s ease, opacity 0.2s ease; }
.panel-enter-from, .panel-leave-to { transform: translateX(100%); opacity: 0; }
</style>
