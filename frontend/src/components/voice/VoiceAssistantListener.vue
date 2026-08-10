<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/lib/api'

interface AssistantReply {
  id: number
  request_text: string
  domain: string
  worth_it: boolean
  worth_score: number
  response: string
  reasoning?: string[]
  suggested_action: string
  created_at?: string
}

interface RecognitionResult {
  0: { transcript: string }
}
interface RecognitionEvent {
  results: RecognitionResult[] & { length: number }
}
interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((e: RecognitionEvent) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
  start: () => void
  stop: () => void
}

const lastReply = ref<AssistantReply | null>(null)
const speaking = ref(false)
const listening = ref(false)
const micSupported = ref(false)
const lastError = ref('')
let since = 0
let timer: ReturnType<typeof setInterval> | null = null
let recognition: SpeechRecognitionLike | null = null
let micTranscript = ''

function speak(text: string) {
  try {
    const synth = window.speechSynthesis
    if (!synth) return
    synth.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'es-ES'
    const voice = synth.getVoices().find(v => v.lang.startsWith('es'))
    if (voice) utterance.voice = voice
    utterance.rate = 1.05
    speaking.value = true
    utterance.onend = () => { speaking.value = false }
    synth.speak(utterance)
  } catch {
    speaking.value = false
  }
}

async function poll() {
  try {
    const data = await api.get<{ replies: AssistantReply[] }>('/voice/assistant/replies', {
      since: String(since),
    })
    for (const reply of data.replies) {
      if (reply.id > since) {
        since = reply.id
        lastReply.value = reply
        speak(reply.response)
      }
    }
  } catch {
    // backend not reachable yet; keep polling
  }
}

function getRecognition(): SpeechRecognitionLike | null {
  const w = window as unknown as Record<string, unknown>
  const Ctor = (w.SpeechRecognition || w.webkitSpeechRecognition) as
    | (new () => SpeechRecognitionLike)
    | undefined
  if (!Ctor) return null
  const rec = new Ctor()
  rec.lang = 'es-ES'
  rec.interimResults = true
  rec.continuous = false
  return rec
}

function toggleMic() {
  if (listening.value) {
    recognition?.stop()
    return
  }
  recognition = getRecognition()
  if (!recognition) return
  lastError.value = ''
  listening.value = true
  micTranscript = ''
  recognition.onresult = (e) => {
    let text = ''
    for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
    micTranscript = text
  }
  recognition.onend = () => {
    listening.value = false
    const text = micTranscript.trim()
    if (text) askAssistant(text)
  }
  recognition.onerror = () => {
    listening.value = false
  }
  recognition.start()
}

async function askAssistant(text: string) {
  try {
    const reply = await api.post<AssistantReply>('/voice/assistant', { text })
    lastReply.value = reply
    speak(reply.response)
  } catch {
    lastError.value = 'No pude hablar con OWNEX (¿backend caído?).'
  }
}

onMounted(() => {
  timer = setInterval(poll, 2500)
  poll()
  const w = window as unknown as Record<string, unknown>
  micSupported.value = Boolean(w.SpeechRecognition || w.webkitSpeechRecognition)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  recognition?.stop()
  try {
    window.speechSynthesis?.cancel()
  } catch {
    // ignore
  }
})
</script>

<template>
  <div class="voice-listener" :class="{ active: lastReply || speaking || listening }">
    <div class="vl-dot" :class="{ speaking, listening }"></div>
    <button v-if="micSupported" class="vl-mic" :class="{ recording: listening }" @click="toggleMic">
      {{ listening ? '■' : '🎙' }}
    </button>
    <div v-if="lastReply" class="vl-content">
      <span class="vl-domain">{{ lastReply.domain }}</span>
      <span class="vl-text">{{ lastReply.response || lastReply.request_text }}</span>
      <span v-if="speaking" class="vl-speaking">hablando...</span>
      <span v-else-if="listening" class="vl-speaking">escuchando...</span>
    </div>
    <span v-else-if="lastError" class="vl-text vl-error">{{ lastError }}</span>
    <span v-else class="vl-idle">Voz ALPHA lista</span>
  </div>
</template>

<style scoped>
.voice-listener {
  position: fixed;
  bottom: 18px;
  right: 18px;
  z-index: 90;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(10, 12, 17, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #8b8d98;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 12px;
  max-width: 400px;
  backdrop-filter: blur(10px);
}
.voice-listener.active { border-color: rgba(0, 213, 255, 0.3); }
.vl-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #5e6272;
  flex-shrink: 0;
}
.vl-dot.speaking {
  background: #00e39a;
  animation: vl-blink 1s ease-in-out infinite;
}
.vl-dot.listening {
  background: #00d5ff;
  animation: vl-blink 1s ease-in-out infinite;
}
.vl-mic {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: #0e1015;
  color: #d9dbdf;
  cursor: pointer;
  font-size: 14px;
  flex-shrink: 0;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.vl-mic.recording {
  border-color: #00d5ff;
  background: rgba(0, 213, 255, 0.12);
}
.vl-mic:hover { border-color: rgba(0, 213, 255, 0.5); }
.vl-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.vl-domain {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #00d5ff;
}
.vl-text {
  color: #d9dbdf;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.vl-error { color: #ff7a1a; }
.vl-speaking { font-size: 10px; color: #00e39a; }
.vl-idle { white-space: nowrap; }

@keyframes vl-blink {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
</style>
