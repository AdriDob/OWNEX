import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSettingsStore } from '@/stores/settings'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  put: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ api: mockApi }))

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('settings store', () => {
  it('initializes with defaults', () => {
    const store = useSettingsStore()
    expect(store.data.general.userName).toBe('Operador')
    expect(store.data.general.language).toBe('es')
    expect(store.data.ai.provider).toBe('ollama')
    expect(store.data.ai.ollamaHost).toBe('http://localhost:11434')
    expect(store.data.missionControl.autoMode).toBe(false)
    expect(store.data.missionControl.parallelism).toBe(2)
    expect(store.data.appearance.theme).toBe('cyber')
    expect(store.data.onboarding.completed).toBe(false)
    expect(store.syncing).toBe(false)
    expect(store.lastSync).toBeNull()
  })

  it('onboardingNeeded is true when not completed and not skipped', () => {
    const store = useSettingsStore()
    expect(store.onboardingNeeded).toBe(true)
    store.data.onboarding.completed = true
    expect(store.onboardingNeeded).toBe(false)
  })

  it('persists to localStorage on update', () => {
    const store = useSettingsStore()
    store.updateGeneral({ userName: 'TestUser' })
    const saved = JSON.parse(localStorage.getItem('ownex_settings')!)
    expect(saved.general.userName).toBe('TestUser')
  })

  it('loads from localStorage on init', async () => {
    localStorage.setItem('ownex_settings', JSON.stringify({
      general: { userName: 'Custom', language: 'en', theme: 'dark', colors: 'blue', accessibility: true, animations: false },
    }))
    const store = useSettingsStore()
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(store.data.general.userName).toBe('Custom')
    expect(store.data.general.language).toBe('en')
  })

  it('updateGeneral merges and persists', () => {
    const store = useSettingsStore()
    store.updateGeneral({ userName: 'NewName', language: 'en' })
    expect(store.data.general.userName).toBe('NewName')
    expect(store.data.general.language).toBe('en')
    expect(store.data.general.theme).toBe('cyber')
  })

  it('updateAI merges and persists', () => {
    const store = useSettingsStore()
    store.updateAI({ provider: 'openai', openaiKey: 'sk-123' })
    expect(store.data.ai.provider).toBe('openai')
    expect(store.data.ai.openaiKey).toBe('sk-123')
    expect(store.data.ai.ollamaHost).toBe('http://localhost:11434')
  })

  it('updateApiKeys merges and syncs to backend', async () => {
    mockApi.put.mockResolvedValue({})
    const store = useSettingsStore()
    await vi.waitFor(() => expect(store.ready).toBe(true))
    store.updateApiKeys({ hackerone: 'h1-token', bugcrowd: 'bc-token' })
    await vi.waitFor(() => expect(mockApi.put).toHaveBeenCalled())
    expect(store.data.apiKeys.hackerone).toBe('h1-token')
    expect(store.data.apiKeys.bugcrowd).toBe('bc-token')
    expect(mockApi.put).toHaveBeenCalledWith('/settings/all', expect.any(Object))
  })

  it('updateMissionControl merges and persists', () => {
    const store = useSettingsStore()
    store.updateMissionControl({ autoMode: true, parallelism: 5, speed: 'fast' })
    expect(store.data.missionControl.autoMode).toBe(true)
    expect(store.data.missionControl.parallelism).toBe(5)
    expect(store.data.missionControl.speed).toBe('fast')
    expect(store.data.missionControl.depth).toBe(3)
  })

  it('updateAppearance merges and persists', () => {
    const store = useSettingsStore()
    store.updateAppearance({ theme: 'dark', density: 'compact' })
    expect(store.data.appearance.theme).toBe('dark')
    expect(store.data.appearance.density).toBe('compact')
    expect(store.data.appearance.layout).toBe('default')
  })

  it('updateSecurity merges and persists', () => {
    const store = useSettingsStore()
    store.updateSecurity({ backups: true })
    expect(store.data.security.backups).toBe(true)
  })

  it('completeOnboarding sets completed true', () => {
    const store = useSettingsStore()
    store.completeOnboarding()
    expect(store.data.onboarding.completed).toBe(true)
    expect(store.data.onboarding.skipped).toBe(false)
    expect(store.data.onboarding.currentStep).toBe(0)
  })

  it('completeOnboarding with skip sets skipped true', () => {
    const store = useSettingsStore()
    store.completeOnboarding(true)
    expect(store.data.onboarding.completed).toBe(false)
    expect(store.data.onboarding.skipped).toBe(true)
  })

  it('resetOnboarding resets onboarding state', () => {
    const store = useSettingsStore()
    store.completeOnboarding()
    store.resetOnboarding()
    expect(store.data.onboarding.completed).toBe(false)
    expect(store.data.onboarding.skipped).toBe(false)
  })

  it('syncToBackend calls put and sets lastSync', async () => {
    mockApi.put.mockResolvedValue({})
    const store = useSettingsStore()
    await store.syncToBackend()
    expect(mockApi.put).toHaveBeenCalledWith('/settings/all', expect.any(Object))
    expect(store.lastSync).toBeDefined()
    expect(store.syncing).toBe(false)
  })

  it('syncToBackend handles API errors silently', async () => {
    mockApi.put.mockRejectedValue(new Error('fail'))
    const store = useSettingsStore()
    await store.syncToBackend()
    expect(store.syncing).toBe(false)
    expect(store.lastSync).toBeNull()
  })

  it('loadFromBackend merges settings from API', async () => {
    mockApi.get.mockResolvedValue({
      settings: {
        general: { userName: 'FromAPI' },
        ai: { provider: 'openai' },
      },
    })
    const store = useSettingsStore()
    await store.loadFromBackend()
    expect(store.data.general.userName).toBe('FromAPI')
    expect(store.data.ai.provider).toBe('openai')
  })

  it('loadFromBackend handles API errors silently', async () => {
    mockApi.get.mockRejectedValue(new Error('fail'))
    const store = useSettingsStore()
    await store.loadFromBackend()
    expect(store.data.general.userName).toBe('Operador')
  })

  it('checkTools updates tool info', async () => {
    mockApi.get.mockResolvedValue({
      tools: {
        nuclei: { installed: true, version: '3.0.0' },
        subfinder: { installed: true, version: '2.5.0' },
      },
    })
    const store = useSettingsStore()
    await store.checkTools()
    expect(store.data.tools.nuclei.installed).toBe(true)
    expect(store.data.tools.nuclei.version).toBe('3.0.0')
    expect(store.data.tools.subfinder.installed).toBe(true)
    expect(store.data.tools.subfinder.version).toBe('2.5.0')
  })

  it('checkTools handles errors silently', async () => {
    mockApi.get.mockRejectedValue(new Error('fail'))
    const store = useSettingsStore()
    await store.checkTools()
    expect(store.data.tools.nuclei.installed).toBe(false)
  })

  it('setToolInfo updates single tool info', () => {
    const store = useSettingsStore()
    store.setToolInfo('nuclei', { installed: true, version: '3.0' })
    expect(store.data.tools.nuclei.installed).toBe(true)
    expect(store.data.tools.nuclei.version).toBe('3.0')
  })

  it('updateSystemInfo fetches and merges health data', async () => {
    mockApi.get.mockResolvedValue({ cpu: 'Intel', ram: '16GB', python: '3.10' })
    const store = useSettingsStore()
    await store.updateSystemInfo()
    expect(store.data.system.cpu).toBe('Intel')
    expect(store.data.system.ram).toBe('16GB')
  })

  it('updateSystemInfo handles errors silently', async () => {
    mockApi.get.mockRejectedValue(new Error('fail'))
    const store = useSettingsStore()
    await store.updateSystemInfo()
    expect(store.data.system.cpu).toBe('')
  })
})
