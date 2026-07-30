<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Mic, MicOff, Volume2, VolumeX, Settings as SettingsIcon } from '@lucide/vue'

const isListening = ref(false)
const isProcessing = ref(false)
const volume = ref(80)
const isMuted = ref(false)
const lastCommand = ref('')
const transcript = ref('')

let recognition: SpeechRecognition | null = null

onMounted(() => {
  initSpeechRecognition()
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

function toggleListening() {
  if (!recognition) {
    alert('Speech recognition not supported in this browser')
    return
  }

  if (isListening.value) {
    recognition.stop()
  } else {
    recognition.start()
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
    console.log('Voice command result:', result)
  } catch (error) {
    console.error('Error processing voice command:', error)
  } finally {
    isProcessing.value = false
  }
}

function toggleMute() {
  isMuted.value = !isMuted.value
}

const canListen = computed(() => recognition !== null)
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
