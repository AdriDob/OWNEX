<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useOwnVoice } from '@/composables/useOwnVoice'
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

const { listening, micSupported, provider, init, start, stop, speak, cancelSpeech } = useOwnVoice()

const transcript = ref('')
const textInput = ref('')
const reply = ref<AssistantReply | null>(null)
const sending = ref(false)
const speaking = ref(false)
const usedVoice = ref(false)
/** Chat mode: sends to copilot LLM instead of quick evaluator */
const chatMode = ref(false)

function toggle() {
  if (listening.value) {
    stop()
    return
  }
  transcript.value = ''
  reply.value = null
  let sent = false
  start((liveTranscript, isFinal) => {
    transcript.value = liveTranscript
    if (isFinal && !sent && liveTranscript.trim()) {
      sent = true
      send(liveTranscript)
    }
  })
}

async function send(text: string) {
  const value = text.trim()
  if (!value) return
  sending.value = true
  try {
    if (chatMode.value) {
      // Free-form conversation via copilot LLM
      const res = await api.post<{ response: string; error?: string }>('/copilot/chat', {
        message: value,
        history: [],
        task_type: 'chat',
      })
      const responseText = res.response || 'No pude procesar eso en este momento.'
      reply.value = {
        id: Date.now(),
        request_text: value,
        domain: 'conversación',
        worth_it: true,
        worth_score: 0.5,
        response: responseText,
        suggested_action: '',
      }
    } else {
      // Quick evaluation mode (existing behavior)
      reply.value = await api.post<AssistantReply>('/voice/assistant', { text: value })
    }
    usedVoice.value = true
    speaking.value = true
    const ok = await speak(reply.value.response)
    speaking.value = ok
  } catch {
    reply.value = null
  } finally {
    sending.value = false
  }
}

function submitText() {
  const value = textInput.value.trim()
  if (!value) return
  textInput.value = ''
  send(value)
}

onMounted(() => {
  init()
})

onUnmounted(() => {
  stop()
  cancelSpeech()
})
</script>

<template>
  <div class="voice-recorder">
    <div class="vr-header">
      <span class="vr-title">Asistente por Voz</span>
      <div class="flex items-center gap-2">
        <button
          class="vr-mode-toggle"
          :class="{ active: chatMode }"
          @click="chatMode = !chatMode"
          :title="chatMode ? 'Conversación libre con IA (copilot)' : 'Evaluación rápida de oportunidades'"
        >
          {{ chatMode ? '💬 MERLIN' : '⚡ Quick' }}
        </button>
        <span v-if="micSupported" class="vr-badge">
          {{ provider === 'capacitor' ? 'NATIVE MIC' : 'REALTIME' }}
        </span>
      </div>
    </div>

    <p v-if="chatMode" class="vr-chat-hint">Modo conversación — hablá libremente con MERLIN</p>

    <div v-if="!micSupported" class="vr-muted">
      Micrófono no disponible en esta vista — usá el chat de texto o Chrome móvil.
    </div>

    <template v-if="micSupported">
      <button
        class="vr-mic"
        :class="{ recording: listening }"
        @click="toggle"
      >
        <span class="vr-mic-icon">{{ listening ? '◉' : '🎙' }}</span>
      </button>

      <p class="vr-hint">{{ listening ? 'Escuchando... hablá ahora' : 'Tocá para hablar con OWNEX' }}</p>

      <p v-if="transcript" class="vr-transcript">{{ transcript }}</p>
    </template>

    <div class="vr-input-row">
      <input
        v-model="textInput"
        class="vr-input"
        type="text"
        placeholder="Escribí tu consulta..."
        @keyup.enter="submitText"
      />
      <button class="vr-send" :disabled="!textInput.trim()" @click="submitText">Enviar</button>
    </div>

    <p v-if="sending" class="vr-muted">{{ chatMode ? 'MERLIN pensando...' : 'Evaluando si vale la pena...' }}</p>

    <div v-if="reply && chatMode" class="vr-reply">
      <div class="vr-domain">
        <span class="vr-worthy ok">MERLIN</span>
        <span v-if="speaking" class="vr-speaking">🔊 hablando...</span>
      </div>
      <p class="vr-response">{{ reply.response }}</p>
      <button v-if="usedVoice" class="vr-replay" @click="speak(reply.response)">Repetir audio</button>
    </div>

    <div v-if="reply && !chatMode" class="vr-reply">
      <div class="vr-domain">
        <span class="vr-worthy" :class="reply.worth_it ? 'ok' : 'no'">
          {{ reply.worth_it ? 'Vale la pena' : 'No es prioridad' }}
        </span>
        <span class="vr-domain-label">{{ reply.domain }}</span>
        <span v-if="speaking" class="vr-speaking">🔊 hablando...</span>
      </div>
      <p class="vr-response">{{ reply.response }}</p>
      <p class="vr-action">{{ reply.suggested_action }}</p>
      <button v-if="usedVoice" class="vr-replay" @click="speak(reply.response)">Repetir audio</button>
    </div>
  </div>
</template>

<style scoped>
.voice-recorder {
  background: var(--ownex-bg-base);
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
.vr-title { font-size: 14px; font-weight: 600; color: var(--ownex-bg-surface); }
.vr-badge {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--ownex-accent);
  border: 1px solid rgba(0, 213, 255, 0.35);
  border-radius: 999px;
  padding: 3px 8px;
}
.vr-mode-toggle {
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  padding: 3px 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: transparent;
  color: var(--ownex-text-secondary);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.vr-mode-toggle.active {
  color: var(--ownex-green);
  border-color: rgba(0, 227, 154, 0.4);
  background: rgba(0, 227, 154, 0.08);
}
.vr-chat-hint {
  font-size: 11px;
  color: var(--ownex-green);
  margin: -4px 0 0;
}
.vr-mic {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: var(--ownex-bg-base);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.vr-mic.recording {
  border-color: var(--ownex-accent);
  background: rgba(0, 213, 255, 0.1);
  animation: vr-pulse 1.4s ease-in-out infinite;
}
.vr-mic-icon { font-size: 22px; }
.vr-hint { font-size: 12px; color: var(--ownex-text-secondary); margin: 0; }
.vr-transcript {
  font-size: 13px;
  color: var(--ownex-text-secondary);
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 10px 12px;
  width: 100%;
  box-sizing: border-box;
  margin: 0;
}
.vr-muted { font-size: 12px; color: var(--ownex-text-secondary); margin: 0; }
.vr-input-row {
  display: flex;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
}
.vr-input {
  flex: 1;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 10px 12px;
  color: var(--ownex-text-secondary);
  font-size: 13px;
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
}
.vr-input:focus { border-color: rgba(0, 213, 255, 0.5); }
.vr-send {
  background: var(--ownex-accent);
  color: var(--ownex-bg-base);
  border: none;
  border-radius: 10px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.vr-send:disabled { opacity: 0.4; cursor: default; }
.vr-reply {
  width: 100%;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 12px 14px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}
.vr-domain { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.vr-worthy {
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  padding: 3px 9px;
}
.vr-worthy.ok { color: var(--ownex-green); background: rgba(0, 227, 154, 0.1); }
.vr-worthy.no { color: var(--ownex-accent); background: rgba(255, 122, 26, 0.1); }
.vr-domain-label { font-size: 11px; color: var(--ownex-text-secondary); text-transform: uppercase; letter-spacing: 0.1em; }
.vr-speaking { font-size: 11px; color: var(--ownex-green); }
.vr-response { font-size: 13px; color: var(--ownex-text-secondary); margin: 0; line-height: 1.5; }
.vr-action { font-size: 12px; color: var(--ownex-accent); margin: 0; }
.vr-replay {
  background: transparent;
  border: 1px solid rgba(0, 213, 255, 0.35);
  color: var(--ownex-accent);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 11px;
  cursor: pointer;
  align-self: flex-start;
}

@keyframes vr-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 213, 255, 0.25); }
  50% { box-shadow: 0 0 0 12px rgba(0, 213, 255, 0); }
}
</style>
