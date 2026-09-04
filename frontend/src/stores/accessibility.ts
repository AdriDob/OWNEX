import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'ownex_accessibility'

export interface AccessibilityState {
  keyboardNavigation: boolean
  highContrast: boolean
  reducedMotion: boolean
  fontScale: number
  screenReaderMode: boolean
  focusIndicator: boolean
}

export const DEFAULT_ACCESSIBILITY: AccessibilityState = {
  keyboardNavigation: true,
  highContrast: false,
  reducedMotion: false,
  fontScale: 100,
  screenReaderMode: false,
  focusIndicator: true,
}

function load(): AccessibilityState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT_ACCESSIBILITY, ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_ACCESSIBILITY }
}

function save(state: AccessibilityState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    /* ignore */
  }
}

export const useAccessibilityStore = defineStore('accessibility', () => {
  const state = ref<AccessibilityState>(load())

  function patch(p: Partial<AccessibilityState>) {
    Object.assign(state.value, p)
    save(state.value)
    apply()
  }

  function toggle(key: keyof AccessibilityState) {
    if (typeof state.value[key] === 'boolean') {
      patch({ [key]: !state.value[key] })
    }
  }

  function apply() {
    const root = document.documentElement
    root.setAttribute('data-font-scale', String(state.value.fontScale))
    root.toggleAttribute('data-high-contrast', state.value.highContrast)
    root.toggleAttribute('data-reduced-motion', state.value.reducedMotion)
    root.toggleAttribute('data-keyboard-nav', state.value.keyboardNavigation)
    root.toggleAttribute('data-screen-reader', state.value.screenReaderMode)
    root.toggleAttribute('data-focus-indicator', state.value.focusIndicator)
    if (state.value.reducedMotion) {
      root.style.setProperty('--duration-fast', '0s')
      root.style.setProperty('--duration-normal', '0s')
    } else {
      root.style.setProperty('--duration-fast', '150ms')
      root.style.setProperty('--duration-normal', '300ms')
    }
    if (state.value.highContrast) {
      root.style.setProperty('--color-border', 'var(--ownex-text-primary)')
      root.style.setProperty('--color-border-light', 'var(--ownex-text-secondary)')
    } else {
      root.style.removeProperty('--color-border')
      root.style.removeProperty('--color-border-light')
    }
    root.style.fontSize = `${state.value.fontScale}%`
  }

  apply()

  const shortcutsVisible = ref(false)

  function toggleShortcuts() {
    shortcutsVisible.value = !shortcutsVisible.value
  }

  return { state, patch, toggle, apply, shortcutsVisible, toggleShortcuts }
})
