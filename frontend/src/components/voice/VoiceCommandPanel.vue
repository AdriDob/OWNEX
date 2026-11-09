<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Mic, MicOff, Volume2, VolumeX, Settings as SettingsIcon } from '@lucide/vue'
import { useOwnVoice } from '@/composables/useOwnVoice'

const voice = useOwnVoice()

const isListening = ref(false)
const isProcessing = ref(false)
const volume = ref(80)
const isMuted = ref(false)
const lastCommand = ref('')
const transcript = ref('')

let recognition: SpeechRecognition | null = null

// MediaRecorder fallback: the browser records a clip and the backend transcribes it
// (needed on Capacitor/Android WebView, where Web Speech is unavailable).
let recorder: MediaRecorder | null = null
let chunks: Blob[] = []
const lastResult = ref('')
const recorderSupported =
  typeof MediaRecorder !== 'undefined' && typeof navigator !== 'undefined' && !!navigator.mediaDevices

onMounted(() => {
  initSpeechRecognition()
  void voice.init()
})

onUnmounted(() => {
  if (recognition) {
    recognition.stop()
  }
})

function initSpeechRecognition() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    console.warn('Speech recognition not supported')
    return
  }

  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  recognition = new SpeechRecognition()
  recognition.continuous = false
  recognition.interimResults = true
  recognition.lang = 'es-ES'

  recognition.onstart = () => {
    isListening.value = true
    transcript.value = ''
  }

  recognition.onresult = (event: any) => {
    let interimTranscript = ''
    let finalTranscript = ''

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcriptText = event.results[i][0].transcript
      if (event.results[i].isFinal) {
        finalTranscript += transcriptText
      } else {
        interimTranscript += transcriptText
      }
    }

    transcript.value = finalTranscript || interimTranscript

    if (finalTranscript) {
      processCommand(finalTranscript)
    }
  }

  recognition.onerror = (event: any) => {
    console.error('Speech recognition error:', event.error)
    isListening.value = false
  }

  recognition.onend = () => {
    isListening.value = false
  }
}

async function toggleListening() {
  if (recognition) {
    if (isListening.value) {
      recognition.stop()
    } else {
      recognition.start()
    }
    return
  }

  if (!recorderSupported) return

  if (recorder && recorder.state === 'recording') {
    recorder.stop()
    return
  }

  await startRecording()
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks = []
    recorder = new MediaRecorder(stream)
    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop())
      isListening.value = false
      const blob = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' })
      await processAudio(blob)
    }
    recorder.start()
    isListening.value = true
  } catch (error) {
    console.error('Microphone unavailable:', error)
    lastResult.value = 'Micrófono no disponible'
  }
}

/** Backend round-trip: audio → local STT → voice command → result. */
async function processAudio(blob: Blob) {
  isProcessing.value = true
  try {
    const form = new FormData()
    form.append('audio', blob, 'command.webm')
    form.append('language', 'es')

    const response = await fetch('/api/voice/commands/audio', { method: 'POST', body: form })
    const result = await response.json()

    if (!response.ok) {
      lastResult.value = result?.detail ?? `Error ${response.status}`
      return
    }

    transcript.value = result.transcript ?? ''
    lastCommand.value = result.command_type
    lastResult.value = result.message ?? ''
    speakFeedback(result.voice_feedback)
  } catch (error) {
    console.error('Error sending audio command:', error)
    lastResult.value = 'Error enviando audio'
  } finally {
    isProcessing.value = false
  }
}

async function processCommand(text: string) {
  isProcessing.value = true
  lastCommand.value = text

  try {
    const response = await fetch('/api/voice/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })

    const result = await response.json()
    lastResult.value = result?.message ?? ''
    speakFeedback(result?.voice_feedback)
  } catch (error) {
    console.error('Error processing voice command:', error)
    lastResult.value = 'Error procesando comando'
  } finally {
    isProcessing.value = false
  }
}

/** Speak the backend's voice feedback: local piper, browser speechSynthesis otherwise. */
function speakFeedback(feedback?: string) {
  if (!feedback || isMuted.value) return
  void voice.speak(feedback)
}

function toggleMute() {
  isMuted.value = !isMuted.value
  if (isMuted.value) voice.cancelSpeech()
}

const canListen = computed(() => recognition !== null || recorderSupported)
const statusText = computed(() => {
  if (isListening.value) return 'Escuchando...'
  if (isProcessing.value) return 'Procesando...'
  return 'Presiona para hablar'
})
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50">
    <div class="glass-panel rounded-2xl p-4 w-80 border border-border/40 bg-surface/30 backdrop-blur-xl">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <div :class="['w-2 h-2 rounded-full', isListening ? 'bg-success animate-pulse' : 'bg-muted-foreground']" />
          <span class="font-mono text-xs text-muted-foreground uppercase tracking-wider">
            Voice Control
          </span>
        </div>
        <button class="p-1.5 rounded-lg hover:bg-surface/40 transition-colors">
          <SettingsIcon class="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      <!-- Status -->
      <div class="mb-4">
        <p class="font-mono text-sm text-foreground mb-2">{{ statusText }}</p>
        <p v-if="transcript" class="font-mono text-xs text-muted-foreground truncate">
          "{{ transcript }}"
        </p>
        <p v-if="lastCommand" class="font-mono text-xs text-success mt-1">
          Comando: {{ lastCommand }}
        </p>
        <p v-if="lastResult" class="font-mono text-xs text-foreground mt-1">
          {{ lastResult }}
        </p>
      </div>

      <!-- Mic Button -->
      <div class="flex items-center justify-center gap-4">
        <button
          @click="toggleMute"
          class="p-2 rounded-lg hover:bg-surface/40 transition-colors"
          :disabled="!canListen"
        >
          <VolumeX v-if="isMuted" class="w-5 h-5 text-muted-foreground" />
          <Volume2 v-else class="w-5 h-5 text-muted-foreground" />
        </button>

        <button
          @click="toggleListening"
          :disabled="!canListen"
          :class="[
            'w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300',
            isListening
              ? 'bg-destructive/20 scale-110 shadow-lg shadow-destructive/20'
              : 'bg-primary/10 hover:bg-primary/20 hover:scale-105',
          ]"
        >
          <MicOff v-if="isListening" class="w-8 h-8 text-destructive" />
          <Mic v-else class="w-8 h-8 text-primary" />
        </button>

        <div class="w-12">
          <input
            v-model.number="volume"
            type="range"
            min="0"
            max="100"
            class="w-full accent-primary"
            :disabled="isMuted"
          />
        </div>
      </div>

      <!-- Processing Indicator -->
      <div v-if="isProcessing" class="mt-4 flex items-center gap-2">
        <div class="w-2 h-2 rounded-full bg-primary animate-bounce" />
        <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay: 0.1s" />
        <div class="w-2 h-2 rounded-full bg-primary animate-bounce" style="animation-delay: 0.2s" />
        <span class="font-mono text-xs text-muted-foreground">Procesando comando...</span>
      </div>

      <!-- Not Supported -->
      <div v-if="!canListen" class="mt-4 p-2 rounded-lg bg-destructive/10 border border-destructive/20">
        <p class="font-mono text-xs text-destructive text-center">
          Speech recognition not supported
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.glass-panel {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
</style>
