import { computed, onMounted, type Ref, ref, watch } from 'vue'

export interface ThemePalette {
  'bg-deep': string
  'bg-base': string
  'bg-surface': string
  'bg-glass': string
  'bg-glass-border': string
  primary: string
  'primary-foreground': string
  accent: string
  'accent-foreground': string
  gold: string
  green: string
  red: string
  yellow: string
  'text-primary': string
  'text-secondary': string
  'text-muted': string
  'text-disabled': string
  border: string
  'border-light': string
  'surface-hover': string
}

export interface ThemePlatforms {
  hackerone: string
  bugcrowd: string
  intigriti: string
  synack: string
  yeswehack: string
}

export interface ThemeCycles {
  security: string
  forge: string
  pulse: string
  vault: string
  atlas: string
  odyssey: string
}

export interface ThemeMotion {
  style: 'stiff' | 'gravitational' | 'organic' | 'clinical' | 'fluid' | 'refined'
  duration: { fast: number; normal: number; slow: number }
  spring: { damping: number; stiffness: number; mass: number }
}

export interface ThemeAudio {
  profile: 'minimal' | 'spatial' | 'ambient' | 'synaptic' | 'precise' | 'crystalline' | 'silent'
  volume: number
  enabled: string[]
}

export interface ThemeVisualization {
  coreColor: string
  coreGlow: string
  orbitColor: string
  particleColor: string
  trailLength: number
  gravityCenter?: boolean
  pulseSync?: boolean
  gridOverlay?: boolean
  refraction?: boolean
  minimal?: boolean
}

export interface ThemeDefinition {
  id: string
  name: string
  description: string
  isDefault?: boolean
  palette: ThemePalette
  platforms: ThemePlatforms
  cycles: ThemeCycles
  motion: ThemeMotion
  audio: ThemeAudio
  visualization: ThemeVisualization
}

const THEME_STORAGE_KEY = 'ownex_theme'

let themesCache: Map<string, ThemeDefinition> | null = null

async function loadThemeDefinitions(): Promise<Map<string, ThemeDefinition>> {
  if (themesCache) return themesCache

  const themeIds = ['tesla', 'event-horizon', 'neural-flow', 'precision-lab', 'quantum-glass', 'executive-intelligence']

  const map = new Map<string, ThemeDefinition>()

  for (const id of themeIds) {
    try {
      const response = await fetch(`/assets/branding/themes/${id}.json`)
      const contentType = response.headers.get('content-type') ?? ''
      if (response.ok && contentType.includes('application/json')) {
        const theme = await response.json()
        map.set(id, theme)
      } else {
        console.warn(`[ThemeEngine] Theme ${id} not found (${response.status}, ${contentType})`)
      }
    } catch (e) {
      console.warn(`[ThemeEngine] Failed to load theme: ${id}`, e)
    }
  }

  themesCache = map
  return map
}

function applyThemeToDOM(theme: ThemeDefinition) {
  if (typeof document === 'undefined') return

  const root = document.documentElement

  Object.entries(theme.palette).forEach(([key, value]) => {
    root.style.setProperty(`--ownex-${key}`, value)
  })

  Object.entries(theme.platforms).forEach(([key, value]) => {
    root.style.setProperty(`--ownex-${key}`, value)
  })

  Object.entries(theme.cycles).forEach(([key, value]) => {
    root.style.setProperty(`--ownex-cycle-${key}`, value)
  })

  root.style.setProperty('--ownex-core-color', theme.visualization.coreColor)
  root.style.setProperty('--ownex-core-glow', theme.visualization.coreGlow)
  root.style.setProperty('--ownex-orbit-color', theme.visualization.orbitColor)
  root.style.setProperty('--ownex-particle-color', theme.visualization.particleColor)
  root.style.setProperty('--ownex-trail-length', theme.visualization.trailLength.toString())

  root.setAttribute('data-theme', theme.id)
  root.setAttribute('data-motion-style', theme.motion.style)
  root.setAttribute('data-audio-profile', theme.audio.profile)

  if (theme.visualization.gravityCenter) root.setAttribute('data-gravity-center', 'true')
  if (theme.visualization.pulseSync) root.setAttribute('data-pulse-sync', 'true')
  if (theme.visualization.gridOverlay) root.setAttribute('data-grid-overlay', 'true')
  if (theme.visualization.refraction) root.setAttribute('data-refraction', 'true')
  if (theme.visualization.minimal) root.setAttribute('data-minimal', 'true')
}

function applyMotionConfig(motion: ThemeMotion) {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  root.style.setProperty('--transition-fast', `${motion.duration.fast}ms`)
  root.style.setProperty('--transition-base', `${motion.duration.normal}ms`)
  root.style.setProperty('--transition-slow', `${motion.duration.slow}ms`)
  root.style.setProperty('--spring-damping', motion.spring.damping.toString())
  root.style.setProperty('--spring-stiffness', motion.spring.stiffness.toString())
  root.style.setProperty('--spring-mass', motion.spring.mass.toString())
}

function applyAudioConfig(audio: ThemeAudio) {
  if (typeof window === 'undefined') return

  const event = new CustomEvent('ownex:theme-audio-change', {
    detail: { profile: audio.profile, volume: audio.volume, enabled: audio.enabled },
  })
  window.dispatchEvent(event)
}

// ── Theme mode (light / dark / auto) ──

export type ThemeMode = 'auto' | 'light' | 'dark'

const THEME_MODE_STORAGE_KEY = 'ownex_theme_mode'

export const LIGHT_MODE_VARS: Record<string, string> = {
  '--ownex-bg': 'var(--ownex-bg-surface)',
  '--ownex-bg-elevated': 'var(--ownex-text-primary)',
  '--ownex-bg-card': 'var(--ownex-text-primary)',
  '--ownex-bg-surface': 'var(--ownex-text-primary)',
  '--ownex-bg-base': 'var(--ownex-bg-surface)',
  '--ownex-bg-deep': 'var(--ownex-text-secondary)',
  '--ownex-bg-glass': 'rgba(255,255,255,0.8)',
  '--ownex-bg-glass-border': 'rgba(20,22,28,0.1)',
  '--ownex-border': 'var(--ownex-text-secondary)',
  '--ownex-border-light': 'var(--ownex-text-secondary)',
  '--ownex-text': 'var(--ownex-bg-base)',
  '--ownex-text-dim': 'var(--ownex-text-muted)',
  '--ownex-text-muted': 'var(--ownex-text-secondary)',
  '--ownex-text-primary': 'var(--ownex-bg-base)',
  '--ownex-text-secondary': 'var(--ownex-border)',
  '--ownex-text-disabled': 'var(--ownex-text-secondary)',
  '--ownex-surface': 'var(--ownex-text-primary)',
  '--ownex-surface-hover': 'var(--ownex-text-primary)',
  '--ownex-stroke': 'var(--ownex-text-secondary)',
  '--ownex-blue': 'var(--ownex-bg-base)',
  '--ownex-white': 'var(--ownex-bg-elevated)',
  '--ownex-gold': 'var(--ownex-gold)',
  '--ownex-accent': 'var(--ownex-bg-base)',
  '--ownex-accent-glow': 'rgba(20,22,28,0.25)',
  '--ownex-accent-dim': 'rgba(20,22,28,0.08)',
  '--ownex-info': 'var(--ownex-accent)',
  '--ownex-info-glow': 'rgba(9,105,218,0.25)',
  '--ownex-info-dim': 'rgba(9,105,218,0.1)',
  '--ownex-success': 'var(--ownex-green)',
  '--ownex-success-glow': 'rgba(26,127,55,0.25)',
  '--ownex-success-dim': 'rgba(26,127,55,0.1)',
  '--ownex-warning': 'var(--ownex-gold)',
  '--ownex-warning-glow': 'rgba(154,103,0,0.25)',
}

function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function useThemeEngine() {
  const currentTheme = ref<ThemeDefinition | null>(null)
  const availableThemes = ref<ThemeDefinition[]>([])
  const themeNames = computed(() => availableThemes.value)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const themeMode = ref<ThemeMode>('dark')
  const systemDark = ref(true)
  let mediaQuery: MediaQueryList | null = null

  function applyThemeMode() {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    const effective = themeMode.value === 'auto' ? (systemDark.value ? 'dark' : 'light') : themeMode.value

    root.setAttribute('data-theme-mode', effective)
    root.classList.toggle('dark', effective === 'dark')
    root.classList.toggle('light', effective === 'light')

    if (effective === 'light') {
      Object.entries(LIGHT_MODE_VARS).forEach(([key, value]) => {
        root.style.setProperty(key, value)
      })
    } else {
      // Restaurar valores del tema (re-aplicar theme limpia overrides)
      if (currentTheme.value) {
        applyThemeToDOM(currentTheme.value)
      } else {
        Object.keys(LIGHT_MODE_VARS).forEach((key) => root.style.removeProperty(key))
      }
    }

    // Meta theme-color para móvil
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) {
      meta.setAttribute('content', effective === 'dark' ? 'var(--ownex-bg-deep)' : 'var(--ownex-bg-surface)')
    }
  }

  function onSystemChange(e: MediaQueryListEvent) {
    systemDark.value = e.matches
    if (themeMode.value === 'auto') applyThemeMode()
  }

  async function setThemeMode(mode: ThemeMode) {
    themeMode.value = mode
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(THEME_MODE_STORAGE_KEY, mode)
    }
    if (mode === 'auto' && typeof window !== 'undefined' && window.matchMedia) {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      systemDark.value = mediaQuery.matches
      mediaQuery.addEventListener('change', onSystemChange)
    } else if (mediaQuery) {
      mediaQuery.removeEventListener('change', onSystemChange)
      mediaQuery = null
    }
    applyThemeMode()
    window.dispatchEvent(new CustomEvent('ownex:theme-mode-change', { detail: { mode, systemDark: systemDark.value } }))
  }

  function initThemeMode() {
    let saved: ThemeMode = 'dark'
    if (typeof localStorage !== 'undefined') {
      saved = (localStorage.getItem(THEME_MODE_STORAGE_KEY) as ThemeMode) || 'dark'
    }
    setThemeMode(saved)
  }

  async function initialize() {
    isLoading.value = true
    error.value = null
    try {
      const themesMap = await loadThemeDefinitions()
      availableThemes.value = Array.from(themesMap.values())

      let savedThemeId = 'tesla'
      if (typeof localStorage !== 'undefined') {
        savedThemeId = localStorage.getItem(THEME_STORAGE_KEY) || 'tesla'
      }

      const theme = themesMap.get(savedThemeId) || themesMap.get('tesla') || availableThemes.value[0]
      if (theme) {
        await setTheme(theme.id)
      } else {
        initThemeMode()
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to initialize themes'
      console.error('[ThemeEngine] Initialization error:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function setTheme(themeId: string) {
    const themesMap = await loadThemeDefinitions()
    const theme = themesMap.get(themeId)
    if (!theme) {
      throw new Error(`Theme not found: ${themeId}`)
    }

    currentTheme.value = theme
    applyThemeToDOM(theme)
    applyMotionConfig(theme.motion)
    applyAudioConfig(theme.audio)

    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(THEME_STORAGE_KEY, themeId)
    }
    applyThemeMode()
    window.dispatchEvent(new CustomEvent('ownex:theme-change', { detail: { theme } }))
  }

  const effectiveMode = computed(() => {
    if (themeMode.value === 'auto') return systemDark.value ? 'dark' : 'light'
    return themeMode.value
  })

  return {
    currentTheme,
    availableThemes,
    isLoading,
    error,
    themeNames,
    themeMode,
    effectiveMode,
    systemDark,
    initialize,
    setTheme,
    getTheme: (id: string) => themesCache?.get(id) ?? null,
    getCurrentThemeId: () => currentTheme.value?.id ?? null,
    setThemeMode,
    initThemeMode,
  }
}

export const themeEngine = useThemeEngine()

export function useTheme() {
  return themeEngine
}
