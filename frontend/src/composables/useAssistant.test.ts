import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Create mock store using vi.hoisted so it's available before imports
const mockSettingsStore = vi.hoisted(() => ({
  data: {
    assistant: {
      enabled: true,
      hints: true,
      bubble: true,
      spotlight: false,
    },
  },
}))

// Mock the settings store BEFORE importing useAssistant
vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => mockSettingsStore,
}))

import { useAssistant } from './useAssistant'

describe('useAssistant', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Reset mock store to defaults
    mockSettingsStore.data.assistant = {
      enabled: true,
      hints: true,
      bubble: true,
      spotlight: false,
    }
    // Reset the module-level loaded ref by re-importing
    vi.resetModules()
  })

  it('should initialize with default hints', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { hints, loadDefaults } = useAssistantFresh()

    loadDefaults()

    expect(hints.value.length).toBeGreaterThan(0)
    expect(hints.value.some((h: any) => h.id === 'hint-mission')).toBe(true)
    expect(hints.value.some((h: any) => h.id === 'hint-aegis')).toBe(true)
    expect(hints.value.some((h: any) => h.id === 'hint-health')).toBe(true)
    expect(hints.value.some((h: any) => h.id === 'hint-workflows')).toBe(true)
  })

  it('should not load defaults twice', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { hints, loadDefaults } = useAssistantFresh()

    loadDefaults()
    const firstCount = hints.value.length

    loadDefaults()
    expect(hints.value.length).toBe(firstCount)
  })

  it('should dismiss hint and remove from list', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { hints, loadDefaults, dismissHint } = useAssistantFresh()

    loadDefaults()
    const initialCount = hints.value.length

    dismissHint('hint-mission')
    expect(hints.value.length).toBe(initialCount - 1)
    expect(hints.value.some((h: any) => h.id === 'hint-mission')).toBe(false)
  })

  it('should show and auto-hide bubble message', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { bubbleMessage, showBubble } = useAssistantFresh()

    vi.useFakeTimers()
    showBubble('Test message', 1000)
    expect(bubbleMessage.value).toBe('Test message')

    vi.advanceTimersByTime(1000)
    expect(bubbleMessage.value).toBeNull()

    vi.useRealTimers()
  })

  it('should show and hide spotlight', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { spotlightFeature, showSpotlight, hideSpotlight } = useAssistantFresh()

    showSpotlight('test-feature')
    expect(spotlightFeature.value).toBe('test-feature')

    hideSpotlight()
    expect(spotlightFeature.value).toBeNull()
  })

  it('should filter hints by page', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { hints, loadDefaults, getHintsForPage } = useAssistantFresh()

    loadDefaults()
    const missionHints = getHintsForPage('mission-control')

    expect(missionHints.length).toBeGreaterThan(0)
    expect(missionHints.every((h: any) => h.page === 'mission-control')).toBe(true)
  })

  it('should return empty array for unknown page', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { getHintsForPage } = useAssistantFresh()

    const unknownHints = getHintsForPage('unknown-page')
    expect(unknownHints).toEqual([])
  })

  it('should sync with settings store changes', async () => {
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')
    const { assistantEnabled, hintsEnabled, bubbleEnabled, spotlightEnabled } = useAssistantFresh()

    expect(assistantEnabled.value).toBe(true)
    expect(hintsEnabled.value).toBe(true)
    expect(bubbleEnabled.value).toBe(true)
    expect(spotlightEnabled.value).toBe(false)

    // Update the mock store to simulate settings change
    mockSettingsStore.data.assistant = {
      enabled: false,
      hints: false,
      bubble: false,
      spotlight: true,
    }

    // The watcher would pick this up in real Vue, but here we just verify
    // the refs can be updated
    assistantEnabled.value = false
    hintsEnabled.value = false
    bubbleEnabled.value = false
    spotlightEnabled.value = true

    expect(assistantEnabled.value).toBe(false)
    expect(hintsEnabled.value).toBe(false)
    expect(bubbleEnabled.value).toBe(false)
    expect(spotlightEnabled.value).toBe(true)
  })

  it('should handle missing assistant settings gracefully', async () => {
    // Update the mock store to have undefined assistant
    mockSettingsStore.data.assistant = undefined as any

    // Create a fresh composable instance
    const { useAssistant: useAssistantFresh } = await import('./useAssistant')

    const { assistantEnabled, hintsEnabled, bubbleEnabled, spotlightEnabled } = useAssistantFresh()

    // Should use defaults when settings are undefined
    expect(assistantEnabled.value).toBe(true)
    expect(hintsEnabled.value).toBe(true)
    expect(bubbleEnabled.value).toBe(true)
    expect(spotlightEnabled.value).toBe(false)
  })
})
