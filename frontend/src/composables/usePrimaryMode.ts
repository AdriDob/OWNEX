import { computed, onMounted, onUnmounted, ref } from 'vue'

export type PrimaryMode = 'lite' | 'full' | 'capital'

export interface ModeConfig {
  name: string
  description: string
  icon: string
  color: string
  features: string[]
  visibleSections: string[]
}

export const MODE_CONFIGS: Record<PrimaryMode, ModeConfig> = {
  lite: {
    name: 'LITE',
    description: 'Earn More — Minimalista, next best action, maximizar EV/hora',
    icon: '⚡',
    color: '#10b981',
    features: [
      'Next Best Action destacado',
      'Oportunidades rankeadas por EV',
      'Dashboard simplificado',
      'Foco en ingresos rápidos',
    ],
    visibleSections: [
      'income-home',
      'targets-prioritization',
      'reports-queue',
      'copilot-assistant',
      'operations-settings',
    ],
  },
  full: {
    name: 'FULL',
    description: 'Operate Everything — Completo, toda la complejidad visible',
    icon: '🚀',
    color: '#3b82f6',
    features: [
      'Todas las secciones visibles',
      'Pipelines y automatización',
      'Analytics avanzados',
      'Control total del sistema',
    ],
    visibleSections: [
      'income-home',
      'intelligence',
      'targets',
      'reports',
      'capital',
      'security',
      'operations',
      'integrations',
      'copilot',
    ],
  },
  capital: {
    name: 'CAPITAL',
    description: 'Keep & Compound — Patrimonio, asignación, proyección $1M',
    icon: '💰',
    color: '#f59e0b',
    features: [
      'Patrimonial Ladder',
      'Asignación de capital',
      'Proyecciones a largo plazo',
      'Tracking de inversiones',
    ],
    visibleSections: [
      'income-home',
      'capital',
      'targets-prioritization',
      'reports-queue',
      'copilot-assistant',
      'operations-settings',
    ],
  },
}

const currentMode = ref<PrimaryMode>('lite')
const loading = ref(false)
const initialized = ref(false)

export function usePrimaryMode() {
  async function fetchMode() {
    try {
      const res = await fetch('/api/settings/runtime/mode/primary')
      const data = await res.json()
      if (data.mode && data.mode in MODE_CONFIGS) {
        currentMode.value = data.mode as PrimaryMode
      }
    } catch (e) {
      console.error('Failed to fetch mode:', e)
    } finally {
      initialized.value = true
    }
  }

  async function setMode(mode: PrimaryMode) {
    if (mode === currentMode.value || loading.value) return false

    loading.value = true
    try {
      const res = await fetch('/api/settings/runtime/mode/primary', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      })
      const data = await res.json()
      if (data.status === 'ok' || data.status === 'success') {
        currentMode.value = mode
        // Persist to localStorage for instant UI updates
        localStorage.setItem('ownex:primary-mode', mode)
        // Emit event for other components
        window.dispatchEvent(
          new CustomEvent('ownex:mode-change', { detail: { mode } })
        )
        return true
      }
      return false
    } catch (e) {
      console.error('Failed to set mode:', e)
      return false
    } finally {
      loading.value = false
    }
  }

  function isSectionVisible(section: string): boolean {
    const config = MODE_CONFIGS[currentMode.value]
    if (!config) return true
    // FULL mode shows everything
    if (currentMode.value === 'full') return true
    return config.visibleSections.some(
      (s) => section === s || section.startsWith(s)
    )
  }

  const modeConfig = computed(() => MODE_CONFIGS[currentMode.value])

  const isLite = computed(() => currentMode.value === 'lite')
  const isFull = computed(() => currentMode.value === 'full')
  const isCapital = computed(() => currentMode.value === 'capital')

  // Listen for mode changes from other components
  function handleModeChange(e: Event) {
    const detail = (e as CustomEvent).detail
    if (detail?.mode && detail.mode in MODE_CONFIGS) {
      currentMode.value = detail.mode as PrimaryMode
    }
  }

  onMounted(() => {
    // Try localStorage first for instant UI
    const stored = localStorage.getItem('ownex:primary-mode')
    if (stored && stored in MODE_CONFIGS) {
      currentMode.value = stored as PrimaryMode
    }
    // Then fetch from API
    fetchMode()
    window.addEventListener('ownex:mode-change', handleModeChange)
  })

  onUnmounted(() => {
    window.removeEventListener('ownex:mode-change', handleModeChange)
  })

  return {
    currentMode,
    loading,
    initialized,
    modeConfig,
    isLite,
    isFull,
    isCapital,
    setMode,
    fetchMode,
    isSectionVisible,
    modes: MODE_CONFIGS,
  }
}
