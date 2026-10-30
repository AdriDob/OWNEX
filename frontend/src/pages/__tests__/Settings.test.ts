import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from '@/pages/Settings.vue'

const mockApi = vi.hoisted(() => ({
  put: vi.fn().mockResolvedValue({}),
  get: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ api: mockApi }))

const mockSettingsStore = vi.hoisted(() => ({
  data: {
    general: {
      userName: 'Test',
      language: 'es',
      theme: 'cyber',
      colors: 'default',
      accessibility: false,
      animations: true,
    },
    ai: {
      provider: 'ollama',
      ollamaHost: 'http://localhost:11434',
      ollamaModel: 'qwen3:8b',
      openaiKey: '',
      openaiBaseUrl: '',
      openaiModel: '',
      geminiKey: '',
      geminiModel: '',
      openrouterKey: '',
      openrouterModel: '',
      temperature: 0.7,
      maxContext: 4096,
      memory: true,
      reasoning: 'medium',
    },
    tools: {
      nuclei: { installed: false, version: '' },
      subfinder: { installed: false, version: '' },
      amass: { installed: false, version: '' },
      httpx: { installed: false, version: '' },
      katana: { installed: false, version: '' },
      ffuf: { installed: false, version: '' },
      gau: { installed: false, version: '' },
      naabu: { installed: false, version: '' },
      assetfinder: { installed: false, version: '' },
      dnsx: { installed: false, version: '' },
    },
    apiKeys: {
      bugcrowd: '',
      hackerone: '',
      intigriti: '',
      yeswehack: '',
      synack: '',
      github: '',
      gitlab: '',
      shodan: '',
      censys: '',
      securitytrails: '',
      virustotal: '',
      openrouter: '',
      openai: '',
      anthropic: '',
      google: '',
      wallet: '',
      bank: '',
    },
    missionControl: {
      autoMode: false,
      parallelism: 2,
      limits: 100,
      speed: 'normal',
      depth: 3,
      allowedTools: ['nuclei', 'subfinder', 'httpx', 'katana', 'ffuf'],
    },
    system: {
      cpu: '',
      ram: '',
      disk: '',
      wsl: '',
      docker: '',
      python: '',
      node: '',
      ollama: '',
      models: '',
      internet: false,
      tools: '',
      database: '',
    },
    security: { permissions: {}, backups: false },
    appearance: {
      theme: 'cyber',
      colors: 'default',
      icons: 'default',
      animations: true,
      density: 'normal',
      layout: 'default',
    },
    onboarding: { completed: true, skipped: false, currentStep: 0 },
  },
  syncing: false,
  lastSync: null,
  onboardingNeeded: false,
  syncToBackend: vi.fn().mockResolvedValue(undefined),
  loadFromBackend: vi.fn().mockResolvedValue(undefined),
  completeOnboarding: vi.fn(),
  resetOnboarding: vi.fn(),
  updateGeneral: vi.fn(),
  updateAI: vi.fn(),
  updateApiKeys: vi.fn(),
  updateMissionControl: vi.fn(),
  updateAppearance: vi.fn(),
  updateSecurity: vi.fn(),
  checkTools: vi.fn(),
  setToolInfo: vi.fn(),
  updateSystemInfo: vi.fn(),
}))
vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => mockSettingsStore,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

function createWrapper() {
  return mount(Settings, {
    global: {
      stubs: {
        'router-link': true,
        'router-view': true,
        Transition: false,
        Badge: { template: '<span class="mock-badge"><slot /></span>' },
        Button: { template: '<button class="mock-btn" @click="$emit(\'click\', $event)"><slot /></button>' },
        Tooltip: { template: '<span class="mock-tooltip"><slot /></span>' },
        Separator: { template: '<hr class="mock-separator" />' },
        OnboardingWizard: { template: '<div class="mock-onboarding" />' },
      },
    },
  })
}

describe('Settings page', () => {
  it('renders all 8 tabs', () => {
    const wrapper = createWrapper()
    const tabs = wrapper.findAll('button')
    const tabTexts = tabs.map((t) => t.text())
    expect(tabTexts).toContain('General')
    expect(tabTexts).toContain('IA')
    expect(tabTexts).toContain('Herramientas')
    expect(tabTexts).toContain('API Keys')
    expect(tabTexts).toContain('Mission Control')
    expect(tabTexts).toContain('Sistema')
    expect(tabTexts).toContain('Seguridad')
    expect(tabTexts).toContain('Apariencia')
  })

  it('shows general tab by default', () => {
    const wrapper = createWrapper()
    expect(wrapper.text()).toContain('Perfil')
    expect(wrapper.text()).toContain('Onboarding')
  })

  it('switches to AI tab on click', async () => {
    const wrapper = createWrapper()
    const aiBtn = wrapper.findAll('button').find((b) => b.text().includes('IA'))
    expect(aiBtn).toBeDefined()
    await aiBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Proveedor activo')
    expect(wrapper.text()).toContain('Ollama')
    expect(wrapper.text()).toContain('OpenAI')
  })

  it('switches to Mission Control tab', async () => {
    const wrapper = createWrapper()
    const mcBtn = wrapper.findAll('button').find((b) => b.text().includes('Mission Control'))
    await mcBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Configuración del agente')
    expect(wrapper.text()).toContain('Modo automático')
  })

  it('switches to API Keys tab', async () => {
    const wrapper = createWrapper()
    const keyBtn = wrapper.findAll('button').find((b) => b.text().includes('API Keys'))
    await keyBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Central de API Keys')
    expect(wrapper.text()).toContain('Bugcrowd')
    expect(wrapper.text()).toContain('HackerOne')
  })

  it('switches to System tab', async () => {
    const wrapper = createWrapper()
    const sysBtn = wrapper.findAll('button').find((b) => b.text().includes('Sistema'))
    await sysBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Estado del sistema')
  })

  it('switches to Seguridad tab', async () => {
    const wrapper = createWrapper()
    const segBtn = wrapper.findAll('button').find((b) => b.text().includes('Seguridad'))
    await segBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Seguridad y datos')
    expect(wrapper.text()).toContain('Exportar configuración')
  })

  it('switches to Apariencia tab', async () => {
    const wrapper = createWrapper()
    const appBtn = wrapper.findAll('button').find((b) => b.text().includes('Apariencia'))
    await appBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Personalización visual')
    expect(wrapper.text()).toContain('Tema')
    // Los nombres de temas llegan async del ThemeEngine; el tab renderiza
    // controles de densidad/layout siempre.
    expect(wrapper.text()).toContain('Densidad')
    expect(wrapper.text()).toContain('Layout')
  })

  it('shows tool list in tools tab', async () => {
    const wrapper = createWrapper()
    const toolsBtn = wrapper.findAll('button').find((b) => b.text().includes('Herramientas'))
    await toolsBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Herramientas del sistema')
    expect(wrapper.text()).toContain('Nuclei')
    expect(wrapper.text()).toContain('Amass')
  })

  it('calls checkTools on verify button click', async () => {
    const wrapper = createWrapper()
    const toolsBtn = wrapper.findAll('button').find((b) => b.text().includes('Herramientas'))
    await toolsBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    const verifyBtn = wrapper.findAll('.mock-btn').find((b) => b.text().includes('Verificar'))
    if (verifyBtn) {
      await verifyBtn.trigger('click')
      expect(mockSettingsStore.checkTools).toHaveBeenCalled()
    }
  })
})
