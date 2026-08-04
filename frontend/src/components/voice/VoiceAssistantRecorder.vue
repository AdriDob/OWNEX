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
  suggested_action: string
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

const listening = ref(false)
const supported = ref(false)
const transcript = ref('')
const reply = ref<AssistantReply | null>(null)
const sending = ref(false)

let recognition: SpeechRecognitionLike | null = null

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

function toggle() {
  if (listening.value) {
    recognition?.stop()
    return
  }
  recognition = getRecognition()
  if (!recognition) return
  transcript.value = ''
  reply.value = null
  listening.value = true
  recognition.onresult = (e) => {
    let text = ''
    for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
    transcript.value = text
  }
  recognition.onend = () => {
    listening.value = false
    if (transcript.value.trim()) send()
  }
  recognition.onerror = () => {
    listening.value = false
  }
  recognition.start()
}

async function send() {
  const text = transcript.value.trim()
  if (!text) return
  sending.value = true
  try {
    reply.value = await api.post<AssistantReply>('/voice/assistant', { text })
  } catch {
    reply.value = null
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  const w = window as unknown as Record<string, unknown>
  supported.value = Boolean(w.SpeechRecognition || w.webkitSpeechRecognition)
})

onUnmounted(() => {
  recognition?.stop()
})
</script>

<template>
  <div class="voice-recorder">
    <div class="vr-header">
      <span class="vr-title">Asistente por Voz</span>
      <span v-if="supported" class="vr-badge">REALTIME</span>
    </div>

    <div v-if="!supported" class="vr-muted">
      La transcripción por voz no está disponible en este navegador.
    </div>

    <template v-else>
      <button
        class="vr-mic"
        :class="{ recording: listening }"
        @click="toggle"
      >
        <span class="vr-mic-icon">{{ listening ? '◉' : '🎙' }}</span>
      </button>

      <p class="vr-hint">{{ listening ? 'Escuchando... hablá ahora' : 'Tocá para hablar con OWNEX' }}</p>

      <p v-if="transcript" class="vr-transcript">{{ transcript }}</p>
      <p v-if="sending" class="vr-muted">Evaluando si vale la pena...</p>

      <div v-if="reply" class="vr-reply">
        <div class="vr-domain">
          <span class="vr-worthy" :class="reply.worth_it ? 'ok' : 'no'">
            {{ reply.worth_it ? 'Vale la pena' : 'No es prioridad' }}
          </span>
          <span class="vr-domain-label">{{ reply.domain }}</span>
        </div>
        <p class="vr-response">{{ reply.response }}</p>
        <p class="vr-action">{{ reply.suggested_action }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.voice-recorder {
  background: #0c0e13;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  font-family: 'Inter', system-ui, sans-serif;
}
.vr-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.vr-title { font-size: 14px; font-weight: 600; color: #f5f5f4; }
.vr-badge {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: #00d5ff;
  border: 1px solid rgba(0, 213, 255, 0.35);
  border-radius: 999px;
  padding: 3px 8px;
}
.vr-mic {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: #0e1015;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.vr-mic.recording {
  border-color: #00d5ff;
  background: rgba(0, 213, 255, 0.1);
  animation: vr-pulse 1.4s ease-in-out infinite;
}
.vr-mic-icon { font-size: 22px; }
.vr-hint { font-size: 12px; color: #8b8d98; margin: 0; }
.vr-transcript {
  font-size: 13px;
  color: #d9dbdf;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 10px 12px;
  width: 100%;
  box-sizing: border-box;
  margin: 0;
}
.vr-muted { font-size: 12px; color: #8b8d98; margin: 0; }
.vr-reply {
  width: 100%;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 12px 14px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}
.vr-domain { display: flex; align-items: center; gap: 8px; }
.vr-worthy {
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  padding: 3px 9px;
}
.vr-worthy.ok { color: #00e39a; background: rgba(0, 227, 154, 0.1); }
.vr-worthy.no { color: #ff7a1a; background: rgba(255, 122, 26, 0.1); }
.vr-domain-label { font-size: 11px; color: #8b8d98; text-transform: uppercase; letter-spacing: 0.1em; }
.vr-response { font-size: 13px; color: #d9dbdf; margin: 0; line-height: 1.5; }
.vr-action { font-size: 12px; color: #00d5ff; margin: 0; }

@keyframes vr-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 213, 255, 0.25); }
  50% { box-shadow: 0 0 0 12px rgba(0, 213, 255, 0); }
}
</style>
