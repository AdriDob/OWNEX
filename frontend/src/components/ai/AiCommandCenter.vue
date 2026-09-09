<script setup lang="ts">
/**
 * AiCommandCenter — canonical OWNEX AI interface.
 *
 * Consolidates OwnexChat + MerlinJarvis into ONE conversation:
 * - Single identity: OWNEX AI (legacy MERLIN name retired from UI)
 * - Canonical state grounding via ownexAi service (OAR provider router)
 * - Text + V1 push-to-talk voice (SpeechRecognition + speechSynthesis)
 * - Tool approval cards (fail-closed: dangerous tools need approval)
 * - Semantic legend: FACT / INFERENCE / RECOMMENDATION / UNKNOWN
 * - Persistent single conversation (localStorage)
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { Mic, MicOff, Send, Volume2, VolumeX, Trash2, ShieldAlert } from '@lucide/vue'
import {
  sendAiMessage,
  executeAiTool,
  loadHistory,
  saveHistory,
  clearHistory,
  type AiSendResult,
} from '@/services/ownexAi'
import type { AiMessage, AiToolApproval, ChatMessage, SemanticBlock } from '@/types/ownex'
import { blocksFromLabels } from '@/services/chatSemantics'
import { fetchOneAction } from '@/services/ownexData'

const emit = defineEmits<{
  answered: [messageId: number]
  approvalRequested: [approval: AiToolApproval]
}>()

const messages = ref<AiMessage[]>([])
const history = ref<ChatMessage[]>([])
const userInput = ref('')
const isProcessing = ref(false)
const isRecording = ref(false)
const recordingSecs = ref(0)
const autoSpeak = ref(false)
const voiceSupported = ref(false)
const ttsSupported = ref(false)
const pendingApproval = ref<AiToolApproval | null>(null)
const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

let recognition: any = null
let recordTimer: ReturnType<typeof setInterval> | null = null
let msgSeq = 1

const suggestedPrompts = [
  '¿Qué hago ahora?',
  '¿Por qué esta oportunidad?',
  'Compará los 3 mejores dev bounties',
  '¿Cuánto podría generar esta semana?',
  '¿Qué me falta para empezar?',
  'Preparame todo para entregar',
]

const statusText = computed(() => {
  if (isProcessing.value) return 'Procesando…'
  if (isRecording.value) return 'Escuchando…'
  return 'En línea'
})

function scrollBottom(): void {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

function pushMessage(m: AiMessage): void {
  messages.value.push(m)
  history.value.push({ role: m.role, content: m.content })
  if (history.value.length > 60) history.value = history.value.slice(-60)
  saveHistory(history.value)
  scrollBottom()
  emit('answered', m.id)
}

function tagFor(text: string): 'FACT' | 'INFERENCE' | 'RECOMMENDATION' | 'UNKNOWN' {
  const t = text.toLowerCase()
  if (t.includes('unknown') || t.includes('no hay') || t.includes('sin datos')) return 'UNKNOWN'
  if (t.startsWith('recomiendo') || t.includes('deberías') || t.includes('te sugiero')) return 'RECOMMENDATION'
  if (t.includes('probablemente') || t.includes('parece') || t.includes('estimaci')) return 'INFERENCE'
  return 'INFERENCE'
}

function toSemantics(text: string): SemanticBlock[] {
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean).slice(0, 12)
  return lines.slice(0, 6).map((line) => ({ tag: tagFor(line), text: line.slice(0, 220) }))
}

/** Map the backend's authoritative labels to display blocks; fallback kept for contract drift. */
function fromBackendSemantics(labels?: Record<'FACT' | 'INFERENCE' | 'RECOMMENDATION' | 'UNKNOWN', string[]> | null, text = ''): SemanticBlock[] {
  if (!labels) return toSemantics(text)
  const blocks = blocksFromLabels(labels)
  return blocks.length ? blocks : toSemantics(text)
}

async function sendMessage(prefill?: string): Promise<void> {
  const text = (prefill ?? userInput.value).trim()
  if (!text || isProcessing.value) return
  userInput.value = ''
  isProcessing.value = true

  pushMessage({ id: msgSeq++, role: 'user', content: text, timestamp: new Date(), status: 'sending' })
  const typingId = msgSeq++
  messages.value.push({ id: typingId, role: 'assistant', content: '', timestamp: new Date(), status: 'typing' })
  scrollBottom()

  try {
    const { response }: AiSendResult = await sendAiMessage(text, history.value.slice(0, -1))
    messages.value = messages.value.filter((m) => m.id !== typingId)
    const content = response.response || 'Sin respuesta del proveedor. Marcado como UNKNOWN.'
    const msg: AiMessage = {
      id: msgSeq++,
      role: 'assistant',
      content,
      timestamp: new Date(),
      provider: response.provider,
      model: response.model,
      taskType: 'chat',
      semantics: fromBackendSemantics(response.semantics, content),
      status: response.status === 'ok' ? 'completed' : 'error',
    }
    pushMessage(msg)
    if (autoSpeak.value) speak(stripHtml(content))
  } catch (e: any) {
    messages.value = messages.value.filter((m) => m.id !== typingId)
    pushMessage({
      id: msgSeq++,
      role: 'assistant',
      content: `UNKNOWN — no pude consultar el estado canónico: ${e?.message ?? 'error de red'}`,
      timestamp: new Date(),
      status: 'error',
      semantics: [{ tag: 'UNKNOWN', text: 'Backend no disponible. Ningún dato inventado.' }],
    })
  } finally {
    isProcessing.value = false
    scrollBottom()
  }
}

async function askAboutAction(actionTitle: string): Promise<void> {
  await sendMessage(`¿Por qué me recomendás "${actionTitle}"? Comparala con las alternativas y decime EV, EV/hora, probabilidad y riesgo.`)
}

/** Tool execution behind approval card (fail-closed). */
async function requestToolExecution(name: string, args: Record<string, unknown>, danger: boolean, description: string): Promise<void> {
  const approval: AiToolApproval = { id: msgSeq++, name, args, danger, description }
  pendingApproval.value = approval
  emit('approvalRequested', approval)
}

async function confirmApproval(): Promise<void> {
  const ap = pendingApproval.value
  if (!ap) return
  pendingApproval.value = null
  pushMessage({ id: msgSeq++, role: 'user', content: `[Aprobado] ${ap.name}`, timestamp: new Date(), status: 'completed' })
  try {
    const res = await executeAiTool(ap.name, ap.args)
    pushMessage({
      id: msgSeq++,
      role: 'assistant',
      content: typeof res.result === 'string' ? res.result : JSON.stringify(res.result, null, 2),
      timestamp: new Date(),
      status: 'completed',
      semantics: [{ tag: 'FACT', text: `Tool ${ap.name}: ${res.status}` }],
    })
  } catch (e: any) {
    pushMessage({ id: msgSeq++, role: 'assistant', content: `UNKNOWN — falló la herramienta ${ap.name}: ${e?.message ?? e}`, timestamp: new Date(), status: 'error' })
  }
}

function cancelApproval(): void {
  pendingApproval.value = null
  pushMessage({ id: msgSeq++, role: 'assistant', content: 'Acción cancelada. Nada fue ejecutado.', timestamp: new Date(), status: 'completed' })
}

/* ── V1 voice: push-to-talk + browser TTS ── */
function detectVoice(): void {
  voiceSupported.value = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)
  ttsSupported.value = typeof window !== 'undefined' && 'speechSynthesis' in window
}

function startRecording(): void {
  if (!voiceSupported.value || isRecording.value || isProcessing.value) return
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  recognition = new SR()
  recognition.lang = 'es-ES'
  recognition.continuous = false
  recognition.interimResults = false
  recognition.onresult = (ev: any) => {
    const t = Array.from(ev.results).map((r: any) => r[0].transcript).join(' ')
    if (t.trim()) {
      userInput.value = t
      stopRecording()
      sendMessage()
    }
  }
  recognition.onerror = () => stopRecording()
  recognition.onend = () => {
    if (isRecording.value) stopRecording()
  }
  isRecording.value = true
  recordingSecs.value = 0
  recordTimer = setInterval(() => (recordingSecs.value += 1), 1000)
  try {
    recognition.start()
  } catch {
    stopRecording()
  }
}

function stopRecording(): void {
  try {
    recognition?.stop()
  } catch { /* noop */ }
  recognition = null
  if (recordTimer) clearInterval(recordTimer)
  recordTimer = null
  isRecording.value = false
  recordingSecs.value = 0
}

function stripHtml(s: string): string {
  return s.replace(/<[^>]*>/g, '')
}

function speak(text: string): void {
  if (!ttsSupported.value || !autoSpeak.value) return
  try {
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text.slice(0, 500))
    u.lang = 'es-ES'
    u.rate = 0.95
    window.speechSynthesis.speak(u)
  } catch { /* noop */ }
}

function toggleSpeak(): void {
  autoSpeak.value = !autoSpeak.value
  if (!autoSpeak.value) {
    try {
      window.speechSynthesis.cancel()
    } catch { /* noop */ }
  }
}

function clearConversation(): void {
  messages.value = []
  history.value = []
  clearHistory()
}

function fmtTime(d: Date): string {
  return new Date(d).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function onKeydown(e: KeyboardEvent): void {
  if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
    e.preventDefault()
    if (isRecording.value) stopRecording()
    else startRecording()
  }
  if (e.key === 'Escape' && pendingApproval.value) cancelApproval()
}

onMounted(() => {
  detectVoice()
  const saved = loadHistory()
  history.value = saved
  window.addEventListener('keydown', onKeydown)
  inputEl.value?.focus()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  stopRecording()
  try {
    window.speechSynthesis.cancel()
  } catch { /* noop */ }
})

defineExpose({ sendMessage, askAboutAction, requestToolExecution })
</script>

<template>
  <section class="flex h-full min-h-0 flex-col rounded-xl border border-border/40 bg-background" aria-label="AI Command Center">
    <header class="flex items-center gap-3 border-b border-border/30 px-4 py-3">
      <div class="flex h-9 w-9 items-center justify-center rounded-lg border border-border/40 bg-surface text-sm font-bold" aria-hidden="true">O</div>
      <div class="min-w-0 flex-1">
        <h2 class="truncate text-sm font-semibold tracking-wide">OWNEX AI</h2>
        <p class="truncate font-mono text-[11px] text-muted-foreground">{{ statusText }}</p>
      </div>
      <button class="rounded-lg border border-border/40 p-2 text-muted-foreground hover:text-foreground" :title="autoSpeak ? 'Silenciar voz' : 'Activar voz'" @click="toggleSpeak">
        <Volume2 v-if="autoSpeak" class="h-4 w-4" />
        <VolumeX v-else class="h-4 w-4" />
      </button>
      <button class="rounded-lg border border-border/40 p-2 text-muted-foreground hover:text-foreground" title="Limpiar conversación" @click="clearConversation">
        <Trash2 class="h-4 w-4" />
      </button>
    </header>

    <div ref="messagesEl" class="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4" role="log" aria-live="polite">
      <div v-if="messages.length === 0" class="mx-auto max-w-md py-8 text-center">
        <p class="text-base font-medium">¿Qué hacemos ahora?</p>
        <p class="mt-1 text-sm text-muted-foreground">Preguntá con datos reales. Marco lo desconocido como UNKNOWN.</p>
        <div class="mt-4 flex flex-wrap justify-center gap-2">
          <button v-for="p in suggestedPrompts" :key="p" class="rounded-full border border-border/40 px-3 py-1.5 text-xs hover:border-foreground/40 hover:text-foreground" @click="sendMessage(p)">{{ p }}</button>
        </div>
        <div class="mt-4 flex justify-center gap-2 font-mono text-[10px] text-muted-foreground" aria-label="Leyenda semántica">
          <span class="rounded border border-border/40 px-1.5 py-0.5">FACT</span>
          <span class="rounded border border-border/40 px-1.5 py-0.5">INFERENCE</span>
          <span class="rounded border border-border/40 px-1.5 py-0.5">RECOMMENDATION</span>
          <span class="rounded border border-border/40 px-1.5 py-0.5">UNKNOWN</span>
        </div>
      </div>

      <article v-for="m in messages" :key="m.id" class="flex gap-3" :class="m.role === 'user' ? 'flex-row-reverse' : ''">
        <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border/40 bg-surface text-xs font-bold" aria-hidden="true">{{ m.role === 'user' ? 'Tú' : 'O' }}</div>
        <div class="min-w-0 max-w-[85%]">
          <p class="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            {{ m.role === 'user' ? 'Vos' : 'OWNEX AI' }} · {{ fmtTime(m.timestamp) }}
            <span v-if="m.provider"> · {{ m.provider }}{{ m.model ? `/${m.model}` : '' }}</span>
          </p>
          <div v-if="m.status === 'typing'" class="flex gap-1 py-2" aria-label="Escribiendo"><span class="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground" /><span class="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground" /><span class="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground" /></div>
          <p v-else class="whitespace-pre-wrap break-words text-sm leading-relaxed">{{ m.content }}</p>
          <div v-if="m.semantics?.length" class="mt-2 space-y-1">
            <p v-for="(s, i) in m.semantics" :key="i" class="flex gap-2 text-xs">
              <span class="shrink-0 rounded border border-border/40 px-1 font-mono text-[9px]">{{ s.tag }}</span>
              <span class="text-muted-foreground">{{ s.text }}</span>
            </p>
          </div>
        </div>
      </article>
    </div>

    <div v-if="isRecording" class="mx-4 mb-2 flex items-center justify-center gap-3 rounded-lg border border-border/40 px-3 py-2" role="status">
      <span class="h-2 w-2 animate-pulse rounded-full bg-foreground" />
      <span class="font-mono text-xs">Grabando… {{ recordingSecs }}s</span>
      <button class="rounded-md bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground" @click="stopRecording">Detener</button>
    </div>

    <div class="border-t border-border/30 px-4 py-3">
      <div class="flex gap-2">
        <textarea
          ref="inputEl"
          v-model="userInput"
          rows="1"
          :placeholder="isRecording ? 'Grabando voz…' : 'Preguntá con datos reales… (Ctrl+Espacio = voz)'"
          class="min-h-11 flex-1 resize-none rounded-lg border border-border/40 bg-surface px-3 py-2.5 text-sm outline-none placeholder:text-muted-foreground focus:border-foreground/40"
          @keydown.enter.exact.prevent="sendMessage()"
        />
        <button
          v-if="voiceSupported"
          class="rounded-lg border border-border/40 p-2.5 text-muted-foreground hover:text-foreground"
          :class="isRecording ? 'border-foreground/50 text-foreground' : ''"
          :title="isRecording ? 'Detener grabación' : 'Push-to-talk (Ctrl+Espacio)'"
          @click="isRecording ? stopRecording() : startRecording()"
        >
          <MicOff v-if="isRecording" class="h-4 w-4" />
          <Mic v-else class="h-4 w-4" />
        </button>
        <button
          class="rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-40"
          :disabled="(!userInput.trim() && !isRecording) || isProcessing"
          @click="sendMessage()"
          aria-label="Enviar"
        >
          <Send class="h-4 w-4" />
        </button>
      </div>
      <p class="mt-1.5 text-center font-mono text-[10px] text-muted-foreground">Enter = enviar · Ctrl+Espacio = voz · Esc = cancelar aprobación</p>
    </div>

    <div v-if="pendingApproval" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" @click.self="cancelApproval" role="dialog" aria-modal="true" aria-label="Aprobación requerida">
      <div class="w-full max-w-md rounded-xl border border-border/40 bg-background p-5">
        <p class="flex items-center gap-2 text-sm font-semibold"><ShieldAlert class="h-4 w-4" /> Acción crítica — requiere aprobación</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ pendingApproval.description }}</p>
        <pre class="mt-3 max-h-48 overflow-auto rounded-lg border border-border/30 bg-surface p-3 font-mono text-[11px]">{{ JSON.stringify(pendingApproval.args, null, 2) }}</pre>
        <div class="mt-4 flex justify-end gap-2">
          <button class="rounded-lg border border-border/40 px-4 py-2 text-sm" @click="cancelApproval">Cancelar</button>
          <button class="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground" @click="confirmApproval">Aprobar y ejecutar</button>
        </div>
      </div>
    </div>
  </section>
</template>
