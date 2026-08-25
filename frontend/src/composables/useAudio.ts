import { ref, computed } from 'vue'

// Audio configuration
export const AUDIO_CONFIG = {
  volume: {
    silent: 0,
    minimal: 0.3,
    normal: 0.7,
    immersive: 1.0,
  },
  categories: {
    startup: { volume: 0.8, enabled: true },
    shutdown: { volume: 0.8, enabled: true },
    success: { volume: 0.6, enabled: true },
    error: { volume: 0.7, enabled: true },
    warning: { volume: 0.5, enabled: true },
    hover: { volume: 0.2, enabled: true },
    click: { volume: 0.4, enabled: true },
    toggle: { volume: 0.3, enabled: true },
    agent_thinking: { volume: 0.3, enabled: true },
    mission_completed: { volume: 0.8, enabled: true },
    new_opportunity: { volume: 0.7, enabled: true },
    background_ambience: { volume: 0.1, enabled: false },
  },
}

// Audio context singleton
let audioContext: AudioContext | null = null

/** Web Audio no disponible (jsdom, browsers viejos, autoplay policies) → noop. */
function isAudioSupported(): boolean {
  return typeof window !== 'undefined' && !!(window.AudioContext || (window as any).webkitAudioContext)
}

function getAudioContext(): AudioContext {
  if (!audioContext) {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext
    if (!Ctx) throw new Error('Web Audio API not supported')
    audioContext = new Ctx()
  }
  return audioContext
}

// Sound effects synthesis (Web Audio API)
function generateTone(frequency: number, duration: number, type: OscillatorType = 'sine', volume: number = 0.5): AudioBuffer {
  const ctx = getAudioContext()
  const sampleRate = ctx.sampleRate
  const frameCount = sampleRate * duration

  const buffer = ctx.createBuffer(1, frameCount, sampleRate)
  const data = buffer.getChannelData(0)

  for (let i = 0; i < frameCount; i++) {
    const t = i / sampleRate
    // Apply envelope
    const attack = 0.01
    const decay = 0.1
    const sustain = 0.7
    const release = 0.1

    let envelope = 0
    if (t < attack) {
      envelope = t / attack
    } else if (t < attack + decay) {
      envelope = 1 - ((t - attack) / decay) * (1 - sustain)
    } else if (t < duration - release) {
      envelope = sustain
    } else {
      envelope = sustain * ((duration - t) / release)
    }

    // Generate tone
    data[i] = Math.sin(2 * Math.PI * frequency * t) * envelope * volume
  }

  return buffer
}

function playBuffer(buffer: AudioBuffer, volume: number = 1.0) {
  const ctx = getAudioContext()
  const source = ctx.createBufferSource()
  source.buffer = buffer

  const gainNode = ctx.createGain()
  gainNode.gain.value = volume

  source.connect(gainNode)
  gainNode.connect(ctx.destination)

  source.start()
}

// Sound effects
const soundEffects = {
  startup: () => {
    // Ascending sweep: 200Hz → 800Hz over 1s
    const ctx = getAudioContext()
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(200, ctx.currentTime)
    oscillator.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 1)

    gainNode.gain.setValueAtTime(0, ctx.currentTime)
    gainNode.gain.linearRampToValueAtTime(0.8, ctx.currentTime + 0.1)
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 1)

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    oscillator.start()
    oscillator.stop(ctx.currentTime + 1)
  },

  shutdown: () => {
    // Descending sweep: 800Hz → 200Hz over 1s
    const ctx = getAudioContext()
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(800, ctx.currentTime)
    oscillator.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 1)

    gainNode.gain.setValueAtTime(0.8, ctx.currentTime)
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 1)

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    oscillator.start()
    oscillator.stop(ctx.currentTime + 1)
  },

  success: () => {
    // Major chord arpeggio: C4 → E4 → G4 → C5
    const frequencies = [261.63, 329.63, 392.00, 523.25]
    const ctx = getAudioContext()

    frequencies.forEach((freq, i) => {
      const oscillator = ctx.createOscillator()
      const gainNode = ctx.createGain()

      oscillator.type = 'sine'
      oscillator.frequency.value = freq

      gainNode.gain.setValueAtTime(0, ctx.currentTime + i * 0.1)
      gainNode.gain.linearRampToValueAtTime(0.4, ctx.currentTime + i * 0.1 + 0.05)
      gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + i * 0.1 + 0.3)

      oscillator.connect(gainNode)
      gainNode.connect(ctx.destination)

      oscillator.start(ctx.currentTime + i * 0.1)
      oscillator.stop(ctx.currentTime + i * 0.1 + 0.3)
    })
  },

  error: () => {
    // Dissonant cluster
    const ctx = getAudioContext()
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.type = 'sawtooth'
    oscillator.frequency.setValueAtTime(150, ctx.currentTime)
    oscillator.frequency.linearRampToValueAtTime(100, ctx.currentTime + 0.3)

    gainNode.gain.setValueAtTime(0.5, ctx.currentTime)
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.3)

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    oscillator.start()
    oscillator.stop(ctx.currentTime + 0.3)
  },

  warning: () => {
    // Two-tone alert: 440Hz → 880Hz
    const ctx = getAudioContext()
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.type = 'square'
    oscillator.frequency.setValueAtTime(440, ctx.currentTime)
    oscillator.frequency.setValueAtTime(880, ctx.currentTime + 0.15)

    gainNode.gain.setValueAtTime(0.3, ctx.currentTime)
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.3)

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    oscillator.start()
    oscillator.stop(ctx.currentTime + 0.3)
  },

  hover: () => {
    // Subtle high-pitch ping: 1200Hz
    const buffer = generateTone(1200, 0.05, 'sine', 0.1)
    playBuffer(buffer, AUDIO_CONFIG.categories.hover.volume)
  },

  click: () => {
    // Short click: 800Hz
    const buffer = generateTone(800, 0.05, 'sine', 0.3)
    playBuffer(buffer, AUDIO_CONFIG.categories.click.volume)
  },

  toggle: () => {
    // Toggle sound: 600Hz → 900Hz
    const ctx = getAudioContext()
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(600, ctx.currentTime)
    oscillator.frequency.linearRampToValueAtTime(900, ctx.currentTime + 0.1)

    gainNode.gain.setValueAtTime(0.3, ctx.currentTime)
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.1)

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    oscillator.start()
    oscillator.stop(ctx.currentTime + 0.1)
  },

  agent_thinking: () => {
    // Ambient low-frequency pulse: 80Hz
    const buffer = generateTone(80, 0.5, 'sine', 0.15)
    playBuffer(buffer, AUDIO_CONFIG.categories.agent_thinking.volume)
  },

  mission_completed: () => {
    // Triumphant chord: C4 → E4 → G4 → C5 with longer duration
    const frequencies = [261.63, 329.63, 392.00, 523.25]
    const ctx = getAudioContext()

    frequencies.forEach((freq, i) => {
      const oscillator = ctx.createOscillator()
      const gainNode = ctx.createGain()

      oscillator.type = 'sine'
      oscillator.frequency.value = freq

      gainNode.gain.setValueAtTime(0, ctx.currentTime + i * 0.15)
      gainNode.gain.linearRampToValueAtTime(0.5, ctx.currentTime + i * 0.15 + 0.1)
      gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + i * 0.15 + 0.5)

      oscillator.connect(gainNode)
      gainNode.connect(ctx.destination)

      oscillator.start(ctx.currentTime + i * 0.15)
      oscillator.stop(ctx.currentTime + i * 0.15 + 0.5)
    })
  },

  new_opportunity: () => {
    // Bright arpeggio: C5 → E5 → G5 → B5
    const frequencies = [523.25, 659.25, 783.99, 987.77]
    const ctx = getAudioContext()

    frequencies.forEach((freq, i) => {
      const oscillator = ctx.createOscillator()
      const gainNode = ctx.createGain()

      oscillator.type = 'sine'
      oscillator.frequency.value = freq

      gainNode.gain.setValueAtTime(0, ctx.currentTime + i * 0.08)
      gainNode.gain.linearRampToValueAtTime(0.4, ctx.currentTime + i * 0.08 + 0.05)
      gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + i * 0.08 + 0.3)

      oscillator.connect(gainNode)
      gainNode.connect(ctx.destination)

      oscillator.start(ctx.currentTime + i * 0.08)
      oscillator.stop(ctx.currentTime + i * 0.08 + 0.3)
    })
  },
}

// Audio hook
export function useAudio() {
  const masterVolume = ref(AUDIO_CONFIG.volume.normal)
  const enabled = ref(true)

  const setVolume = (volume: keyof typeof AUDIO_CONFIG.volume) => {
    masterVolume.value = AUDIO_CONFIG.volume[volume]
  }

  const setEnabled = (value: boolean) => {
    enabled.value = value
  }

  const play = (category: keyof typeof soundEffects) => {
    if (!enabled.value) return
    if (!isAudioSupported()) return

    const categoryConfig = AUDIO_CONFIG.categories[category]
    if (!categoryConfig.enabled) return

    try {
      soundEffects[category]()
    } catch (error) {
      console.error(`[AUDIO] Error playing ${category}:`, error)
    }
  }

  const isSupported = computed(() => {
    return typeof window !== 'undefined' &&
      (window.AudioContext || (window as any).webkitAudioContext)
  })

  return {
    masterVolume,
    enabled,
    setVolume,
    setEnabled,
    play,
    isSupported,
    categories: AUDIO_CONFIG.categories,
  }
}
