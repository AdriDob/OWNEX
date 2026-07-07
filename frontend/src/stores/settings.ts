import { defineStore } from 'pinia'
import { ref, watch, computed } from 'vue'
import { api } from '@/lib/api'

const STORAGE_KEY = 'cateye_settings'
const ENCRYPTION_KEY_STORAGE = 'cateye_crypto_key'

async function generateEncryptionKey(): Promise<CryptoKey> {
  return await crypto.subtle.generateKey(
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt', 'decrypt'],
  )
}

async function exportKey(key: CryptoKey): Promise<JsonWebKey> {
  return await crypto.subtle.exportKey('jwk', key)
}

async function importKey(jwk: JsonWebKey): Promise<CryptoKey> {
  return await crypto.subtle.importKey('jwk', jwk, { name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
}

async function getCryptoKey(): Promise<CryptoKey> {
  const stored = localStorage.getItem(ENCRYPTION_KEY_STORAGE)
  if (stored) {
    return await importKey(JSON.parse(stored))
  }
  const key = await generateEncryptionKey()
  const jwk = await exportKey(key)
  localStorage.setItem(ENCRYPTION_KEY_STORAGE, JSON.stringify(jwk))
  return key
}

async function encrypt(plaintext: string, key: CryptoKey): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const encoded = new TextEncoder().encode(plaintext)
  const encrypted = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded)
  const combined = new Uint8Array(iv.length + encrypted.byteLength)
  combined.set(iv)
  combined.set(new Uint8Array(encrypted), iv.length)
  const binary = String.fromCharCode(...combined)
  return btoa(binary)
}

async function decrypt(ciphertext: string, key: CryptoKey): Promise<string> {
  const binary = atob(ciphertext)
  const combined = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    combined[i] = binary.charCodeAt(i)
  }
  const iv = combined.slice(0, 12)
  const data = combined.slice(12)
  const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, data)
  return new TextDecoder().decode(decrypted)
}

export interface GeneralSettings {
  userName: string
  language: string
  theme: string
  colors: string
  accessibility: boolean
  animations: boolean
}

export interface AISettings {
  provider: 'ollama' | 'openai' | 'gemini' | 'openrouter'
  ollamaHost: string
  ollamaModel: string
  openaiKey: string
  openaiBaseUrl: string
  openaiModel: string
  geminiKey: string
  geminiModel: string
  openrouterKey: string
  openrouterModel: string
  temperature: number
  maxContext: number
  memory: boolean
  reasoning: string
}

export interface ToolInfo {
  installed: boolean
  version: string
}

export interface ToolsSettings {
  nuclei: ToolInfo
  amass: ToolInfo
  subfinder: ToolInfo
  httpx: ToolInfo
  katana: ToolInfo
  ffuf: ToolInfo
  gau: ToolInfo
  naabu: ToolInfo
  assetfinder: ToolInfo
  dnsx: ToolInfo
}

export interface ApiKeysSettings {
  bugcrowd: string
  hackerone: string
  intigriti: string
  yeswehack: string
  synack: string
  github: string
  gitlab: string
  shodan: string
  censys: string
  securitytrails: string
  virustotal: string
  openrouter: string
  openai: string
  anthropic: string
  google: string
  wallet: string
  bank: string
}

export interface MissionControlSettings {
  autoMode: boolean
  parallelism: number
  limits: number
  speed: 'slow' | 'normal' | 'fast' | 'aggressive'
  depth: number
  allowedTools: string[]
}

export interface SystemInfo {
  cpu: string
  ram: string
  disk: string
  wsl: string
  docker: string
  python: string
  node: string
  ollama: string
  models: string
  internet: boolean
  tools: string
  database: string
}

export interface SecuritySettings {
  permissions: Record<string, boolean>
  backups: boolean
}

export interface AppearanceSettings {
  theme: string
  colors: string
  icons: string
  animations: boolean
  density: 'compact' | 'normal' | 'comfortable'
  layout: 'default' | 'wide' | 'sidebar'
}

export interface OnboardingState {
  completed: boolean
  skipped: boolean
  currentStep: number
}

export interface SettingsState {
  general: GeneralSettings
  ai: AISettings
  tools: ToolsSettings
  apiKeys: ApiKeysSettings
  missionControl: MissionControlSettings
  system: SystemInfo
  security: SecuritySettings
  appearance: AppearanceSettings
  onboarding: OnboardingState
}

function defaultSettings(): SettingsState {
  return {
    general: {
      userName: 'Operador',
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
      openaiBaseUrl: 'https://api.openai.com/v1',
      openaiModel: 'gpt-4o-mini',
      geminiKey: '',
      geminiModel: 'gemini-2.0-flash',
      openrouterKey: '',
      openrouterModel: 'anthropic/claude-3-haiku',
      temperature: 0.7,
      maxContext: 4096,
      memory: true,
      reasoning: 'medium',
    },
    tools: {
      nuclei: { installed: false, version: '' },
      amass: { installed: false, version: '' },
      subfinder: { installed: false, version: '' },
      httpx: { installed: false, version: '' },
      katana: { installed: false, version: '' },
      ffuf: { installed: false, version: '' },
      gau: { installed: false, version: '' },
      naabu: { installed: false, version: '' },
      assetfinder: { installed: false, version: '' },
      dnsx: { installed: false, version: '' },
    },
    apiKeys: {
      bugcrowd: '', hackerone: '', intigriti: '', yeswehack: '', synack: '',
      github: '', gitlab: '', shodan: '', censys: '', securitytrails: '',
      virustotal: '', openrouter: '', openai: '', anthropic: '', google: '',
      wallet: '', bank: '',
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
      cpu: '', ram: '', disk: '', wsl: '', docker: '', python: '', node: '',
      ollama: '', models: '', internet: false, tools: '', database: '',
    },
    security: {
      permissions: {},
      backups: false,
    },
    appearance: {
      theme: 'cyber',
      colors: 'default',
      icons: 'default',
      animations: true,
      density: 'normal',
      layout: 'default',
    },
    onboarding: {
      completed: false,
      skipped: false,
      currentStep: 0,
    },
  }
}

const SENSITIVE_KEYS = new Set(['wallet', 'bank', 'openai', 'openrouter', 'anthropic', 'google', 'bugcrowd', 'hackerone', 'intigriti', 'yeswehack', 'synack', 'github', 'gitlab', 'shodan', 'censys', 'securitytrails', 'virustotal'])
const SENSITIVE_STORAGE_KEY = 'cateye_sensitive'

async function loadFromStorage(): Promise<SettingsState> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const sensitiveRaw = sessionStorage.getItem(SENSITIVE_STORAGE_KEY)
    const saved = raw ? JSON.parse(raw) : {}
    if (sensitiveRaw) {
      try {
        const key = await getCryptoKey()
        const decrypted = await decrypt(sensitiveRaw, key)
        const sensitive = JSON.parse(decrypted)
        if (sensitive.apiKeys) {
          saved.apiKeys = { ...saved.apiKeys, ...sensitive.apiKeys }
        }
      } catch {
        sessionStorage.removeItem(SENSITIVE_STORAGE_KEY)
      }
    }
    return { ...defaultSettings(), ...saved }
  } catch { /* ignore */ }
  return defaultSettings()
}

async function saveToStorage(state: SettingsState) {
  try {
    const sensitive: Record<string, any> = {}
    const safe: Record<string, any> = {}
    for (const [key, value] of Object.entries(state)) {
      if (key === 'apiKeys') {
        const safeKeys: Record<string, string> = {}
        const secretKeys: Record<string, string> = {}
        for (const [k, v] of Object.entries(value as Record<string, string>)) {
          if (SENSITIVE_KEYS.has(k)) {
            secretKeys[k] = v
          } else {
            safeKeys[k] = v
          }
        }
        safe.apiKeys = safeKeys
        sensitive.apiKeys = secretKeys
      } else {
        safe[key] = value
      }
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(safe))
    if (Object.keys(sensitive.apiKeys || {}).length > 0) {
      const key = await getCryptoKey()
      const ciphertext = await encrypt(JSON.stringify(sensitive), key)
      sessionStorage.setItem(SENSITIVE_STORAGE_KEY, ciphertext)
    } else {
      sessionStorage.removeItem(SENSITIVE_STORAGE_KEY)
    }
  } catch { /* ignore */ }
}

export const useSettingsStore = defineStore('settings', () => {
  const data = ref<SettingsState>(defaultSettings())
  const syncing = ref(false)
  const lastSync = ref<string | null>(null)
  const ready = ref(false)

  const onboardingNeeded = computed(() => !data.value.onboarding.completed && !data.value.onboarding.skipped)

  loadFromStorage().then((s) => {
    data.value = s
    ready.value = true
    saveToStorage(s)
  })

  async function persist() {
    await saveToStorage(data.value)
  }

  async function syncToBackend() {
    syncing.value = true
    try {
      const payload: Record<string, any> = {}
      payload['general'] = data.value.general
      payload['ai'] = data.value.ai
      payload['apiKeys'] = data.value.apiKeys
      payload['missionControl'] = data.value.missionControl
      payload['appearance'] = data.value.appearance
      payload['security'] = data.value.security
      payload['onboarding'] = data.value.onboarding
      await api.put('/settings/all', { settings: payload })
      lastSync.value = new Date().toISOString()
    } catch { /* backend may not be available */ }
    finally { syncing.value = false }
  }

  async function loadFromBackend() {
    try {
      const res = await api.get<{ settings: Record<string, any> }>('/settings/all')
      if (res?.settings) {
        if (res.settings.general) Object.assign(data.value.general, res.settings.general)
        if (res.settings.ai) Object.assign(data.value.ai, res.settings.ai)
        if (res.settings.apiKeys) Object.assign(data.value.apiKeys, res.settings.apiKeys)
        if (res.settings.missionControl) Object.assign(data.value.missionControl, res.settings.missionControl)
        if (res.settings.appearance) Object.assign(data.value.appearance, res.settings.appearance)
        if (res.settings.security) Object.assign(data.value.security, res.settings.security)
        if (res.settings.onboarding) Object.assign(data.value.onboarding, res.settings.onboarding)
        persist()
      }
    } catch { /* backend may not be available */ }
  }

  function completeOnboarding(skip = false) {
    data.value.onboarding.completed = !skip
    data.value.onboarding.skipped = skip
    data.value.onboarding.currentStep = 0
    persist()
    syncToBackend()
  }

  function resetOnboarding() {
    data.value.onboarding.completed = false
    data.value.onboarding.skipped = false
    data.value.onboarding.currentStep = 0
    persist()
  }

  function updateGeneral(patch: Partial<GeneralSettings>) {
    Object.assign(data.value.general, patch)
    persist()
  }

  function updateAI(patch: Partial<AISettings>) {
    Object.assign(data.value.ai, patch)
    persist()
  }

  function updateApiKeys(patch: Partial<ApiKeysSettings>) {
    Object.assign(data.value.apiKeys, patch)
    persist()
    syncToBackend()
  }

  function updateMissionControl(patch: Partial<MissionControlSettings>) {
    Object.assign(data.value.missionControl, patch)
    persist()
  }

  function updateAppearance(patch: Partial<AppearanceSettings>) {
    Object.assign(data.value.appearance, patch)
    persist()
  }

  function updateSecurity(patch: Partial<SecuritySettings>) {
    Object.assign(data.value.security, patch)
    persist()
  }

  async function checkTools() {
    try {
      const res = await api.get<{ tools: Record<string, { installed: boolean; version: string }> }>('/system/tools')
      if (res?.tools) {
        for (const [key, info] of Object.entries(res.tools)) {
          if (key in data.value.tools) {
            (data.value.tools as any)[key] = info
          }
        }
        persist()
      }
    } catch { /* backend endpoint may not exist */ }
  }

  function setToolInfo(key: keyof ToolsSettings, info: Partial<ToolInfo>) {
    Object.assign(data.value.tools[key], info)
    persist()
  }

  async function updateSystemInfo() {
    try {
      const health = await api.get<Record<string, any>>('/system/health')
      if (health) {
        data.value.system = { ...data.value.system, ...health }
      }
    } catch { /* ignore */ }
    persist()
  }

  return {
    data, syncing, lastSync, ready, onboardingNeeded,
    syncToBackend, loadFromBackend,
    completeOnboarding, resetOnboarding,
    updateGeneral, updateAI, updateApiKeys, updateMissionControl,
    updateAppearance, updateSecurity,
    checkTools, setToolInfo, updateSystemInfo,
  }
})
