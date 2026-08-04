<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/lib/api'

interface AssistantReply {
  id: number
  request_text: string
  domain: string
  worth_it: boolean
  response: string
  suggested_action: string
}

interface VoiceCommandResult {
  success: boolean
  command_type: string
  raw_text: string
  message: string
  voice_feedback: string
  requires_confirmation: boolean
  error?: string
}

const lastReply = ref<AssistantReply | null>(null)
const lastCommand = ref<VoiceCommandResult | null>(null)
const speaking = ref(false)
const pendingConfirmation = ref(false)
let since = 0
let timer: ReturnType<typeof setInterval> | null = null

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
        // Check if this is an executable command
        if (reply.is_executable && reply.executor_action) {
          await executeVoiceCommand(reply.request_text)
        } else {
          speak(reply.response)
        }
      }
    }
  } catch {
    // backend not reachable yet; keep polling
  }
}

async function executeVoiceCommand(text: string, confirmed = false) {
  try {
    const result = await api.post<VoiceCommandResult>('/voice/commands/command', {
      text,
      confirmed,
    })
    lastCommand.value = result

    if (result.requires_confirmation) {
      pendingConfirmation.value = true
      speak(result.voice_feedback)
    } else {
      speak(result.voice_feedback)
      pendingConfirmation.value = false
    }
  } catch (error) {
    console.error('Voice command execution failed:', error)
    speak('Error al ejecutar el comando')
  }
}

async function confirmCommand() {
  if (!lastCommand.value) return
  await executeVoiceCommand(lastCommand.value.raw_text, true)
}

async function cancelCommand() {
  pendingConfirmation.value = false
  lastCommand.value = null
  speak('Comando cancelado')
}

onMounted(() => {
  timer = setInterval(poll, 2500)
  poll()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  try {
    window.speechSynthesis?.cancel()
  } catch {
    // ignore
  }
})
</script>

<template>
  <div class="voice-listener" :class="{ active: lastReply || lastCommand }">
    <div class="vl-dot" :class="{ speaking }"></div>
    <div v-if="pendingConfirmation" class="vl-content vl-confirmation">
      <span class="vl-domain">CONFIRMACIÓN</span>
      <span class="vl-text">{{ lastCommand?.voice_feedback }}</span>
      <div class="vl-actions">
        <button @click="confirmCommand" class="vl-btn vl-confirm">Confirmar</button>
        <button @click="cancelCommand" class="vl-btn vl-cancel">Cancelar</button>
      </div>
    </div>
    <div v-else-if="lastCommand" class="vl-content">
      <span class="vl-domain">{{ lastCommand.command_type }}</span>
      <span class="vl-text">{{ lastCommand.voice_feedback }}</span>
      <span v-if="speaking" class="vl-speaking">hablando...</span>
    </div>
    <div v-else-if="lastReply" class="vl-content">
      <span class="vl-domain">{{ lastReply.domain }}</span>
      <span class="vl-text">{{ lastReply.response }}</span>
      <span v-if="speaking" class="vl-speaking">hablando...</span>
    </div>
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
.vl-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.vl-content.vl-confirmation {
  gap: 8px;
}
.vl-domain {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #00d5ff;
}
.vl-domain[style*="CONFIRMACIÓN"] {
  color: #f59e0b;
}
.vl-text {
  color: #d9dbdf;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.vl-speaking { font-size: 10px; color: #00e39a; }
.vl-idle { white-space: nowrap; }
.vl-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.vl-btn {
  padding: 4px 12px;
  border-radius: 6px;
  border: none;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.vl-confirm {
  background: #00e39a;
  color: #0a0c11;
}
.vl-confirm:hover {
  background: #00c880;
}
.vl-cancel {
  background: #ef4444;
  color: white;
}
.vl-cancel:hover {
  background: #dc2626;
}

@keyframes vl-blink {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
</style>
