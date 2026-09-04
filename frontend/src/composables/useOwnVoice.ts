import { readonly, ref } from 'vue'
import { api } from '@/lib/api'

/**
 * OWNEX Voice abstraction.
 *
 * STT chain:  Capacitor native (Android APK) → browser Web Speech → null
 * TTS chain:  backend piper (OWNEX voice) → browser speechSynthesis → silent
 *
 * Config lives server-side (data/voice_profile.json, see
 * cores/voice/voice_engine.py). This layer only follows it.
 */

interface VoiceProfile {
  enabled: boolean
  provider: string
  language: string
  locale: string
  speed: number
  pitch: number
  volume: number
  personality: string
  fallback: string
}

interface RecognitionEventLike {
  results: Array<Array<{ transcript: string }>> & { length: number }
}
interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((e: RecognitionEventLike) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
  start: () => void
  stop: () => void
}

interface CapacitorSpeechRecognition {
  available: () => Promise<{ available: boolean }>
  requestPermissions: () => Promise<{ permissionStatus: unknown }>
  start: (options: {
    language?: string
    partialResults?: boolean
    maxResults?: number
  }) => Promise<{ matches: string[] | undefined; partialResults?: Array<{ matches: string[] }> }>
  stop: () => Promise<void>
}

type CapacitorPluginLike = {
  SpeechRecognition?: CapacitorSpeechRecognition
  [key: string]: unknown
}

const listening = ref(false)
const micSupported = ref(false)
const provider = ref<'capacitor' | 'browser' | 'none'>('none')
const profile = ref<VoiceProfile | null>(null)

let browserRec: SpeechRecognitionLike | null = null
let capacitorRec: CapacitorSpeechRecognition | null = null
let liveCallback: ((text: string, isFinal: boolean) => void) | null = null
let finalText = ''

function getBrowserRecognition(): SpeechRecognitionLike | null {
  const w = window as unknown as Record<string, unknown>
  const Ctor = (w.SpeechRecognition || w.webkitSpeechRecognition) as (new () => SpeechRecognitionLike) | undefined
  if (!Ctor) return null
  const rec = new Ctor()
  rec.lang = 'es-ES'
  rec.interimResults = true
  rec.continuous = false
  return rec
}

async function detectProvider(): Promise<void> {
  try {
    const cap = (window as unknown as { Capacitor?: CapacitorPluginLike }).Capacitor
    const plugin = cap?.SpeechRecognition
    if (plugin) {
      const res = await plugin.available()
      if (res.available) {
        capacitorRec = plugin
        provider.value = 'capacitor'
        micSupported.value = true
        return
      }
    }
  } catch {
    // fall through to browser detection
  }
  if (getBrowserRecognition()) {
    provider.value = 'browser'
    micSupported.value = true
    return
  }
  provider.value = 'none'
  micSupported.value = false
}

async function loadProfile(): Promise<VoiceProfile | null> {
  try {
    const data = await api.get<VoiceProfile>('/voice/config')
    profile.value = data
    return data
  } catch {
    return null
  }
}

async function ensureMicPermission(): Promise<boolean> {
  if (provider.value !== 'capacitor' || !capacitorRec) return true
  try {
    await capacitorRec.requestPermissions()
    return true
  } catch {
    return false
  }
}

async function start(cb: (text: string, isFinal: boolean) => void): Promise<void> {
  if (listening.value) return
  liveCallback = cb
  listening.value = true

  if (provider.value === 'capacitor' && capacitorRec) {
    const ok = await ensureMicPermission()
    if (!ok) {
      listening.value = false
      return
    }
    try {
      const res = await capacitorRec.start({
        language: profile.value?.locale === 'es-419' ? 'es-MX' : 'es-ES',
        partialResults: true,
        maxResults: 1,
      })
      const match = res.matches?.[0]?.trim()
      if (match) liveCallback?.(match, true)
    } catch {
      // user cancelled or unsupported language — no text produced
    } finally {
      listening.value = false
    }
    return
  }

  browserRec = getBrowserRecognition()
  if (!browserRec) {
    listening.value = false
    return
  }
  finalText = ''
  browserRec.onresult = (e) => {
    let text = ''
    for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
    finalText = text.trim()
    if (finalText) liveCallback?.(finalText, false)
  }
  browserRec.onend = () => {
    listening.value = false
    if (finalText) liveCallback?.(finalText, true)
  }
  browserRec.onerror = () => {
    listening.value = false
  }
  browserRec.start()
}

async function stop(): Promise<void> {
  if (provider.value === 'capacitor' && capacitorRec) {
    try {
      await capacitorRec.stop()
    } catch {
      // ignore
    }
  } else {
    browserRec?.stop()
  }
  listening.value = false
}

/**
 * Speak with the OWNEX voice: try backend piper → browser speechSynthesis.
 */
let audioEl: HTMLAudioElement | null = null
let speakingNow = false

async function speak(text: string): Promise<boolean> {
  try {
    const base = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
    const token = localStorage.getItem('token')
    const res = await fetch(`${base}/api/voice/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text }),
    })
    if (res.status === 200) {
      const blob = await res.blob()
      if (blob.type === 'audio/wav') {
        const url = URL.createObjectURL(blob)
        if (audioEl) audioEl.pause()
        audioEl = new Audio(url)
        speakingNow = true
        await audioEl.play()
        audioEl.onended = () => {
          speakingNow = false
        }
        return true
      }
    }
  } catch {
    // piper unavailable → fall through to system TTS
  }
  return speakSystem(text)
}

function speakSystem(text: string): boolean {
  try {
    const synth = window.speechSynthesis
    if (!synth) return false
    const p = profile.value
    synth.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'es-ES'
    const voice = synth.getVoices().find((v) => v.lang.startsWith('es'))
    if (voice) utterance.voice = voice
    utterance.rate = p?.speed ?? 1.05
    utterance.pitch = (p?.pitch ?? 0) / 2 + 1
    utterance.volume = p?.volume ?? 0.85
    synth.speak(utterance)
    return true
  } catch {
    return false
  }
}

function cancelSpeech(): void {
  try {
    window.speechSynthesis?.cancel()
  } catch {
    // ignore
  }
  if (audioEl) {
    audioEl.pause()
    audioEl = null
  }
}

async function init(): Promise<void> {
  await Promise.all([detectProvider(), loadProfile()])
}

export function useOwnVoice() {
  return {
    listening: readonly(listening),
    micSupported: readonly(micSupported),
    provider: readonly(provider),
    profile: readonly(profile),
    start,
    stop,
    speak,
    speakSystem,
    cancelSpeech,
    init,
  }
}
