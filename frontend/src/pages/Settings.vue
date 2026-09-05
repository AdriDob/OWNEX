<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useI18n } from '@/composables/useI18n'
import type { ToolsSettings } from '@/stores/settings'
import { useThemeEngine } from '@/composables/useThemeEngine'
import { api } from '@/lib/api'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import Separator from '@/components/ui/Separator.vue'
import OnboardingWizard from '@/components/onboarding/OnboardingWizard.vue'
import { useAccessibilityStore } from '@/stores/accessibility'
import type { AccessibilityState } from '@/stores/accessibility'
import {
  Settings, Palette, Shield, Cpu, Globe, Eye, Key, Save, CheckCircle2,
  AlertTriangle, RefreshCw, ExternalLink, User, Wrench, Server, Lock, Download, Upload, RotateCcw,
  Activity, Database, Wifi, HardDrive, Monitor, Box,
  Sparkles, Bug, Crosshair, Scan, DollarSign, Plug,
} from '@lucide/vue'

const settings = useSettingsStore()
const a11y = useAccessibilityStore()
const { initialize: initThemeEngine, currentTheme, availableThemes, themeNames, setTheme } = useThemeEngine()
const { setLocale, currentLocale, supportedLocales } = useI18n()

const fontScaleOptions = [75, 85, 100, 115, 130, 150]

const toolsWithInfo = computed(() =>
  toolsList.map(t => ({ ...t, info: (settings.data.tools as Record<string, { installed: boolean; version: string }>)[t.id] || { installed: false, version: '' } }))
)

type ApiKeyEntry = { key: string; label: string; link?: string }
function hasLink(k: ApiKeyEntry): k is ApiKeyEntry & { link: string } {
  return 'link' in k && !!k.link
}
const activeTab = ref<'general' | 'ai' | 'tools' | 'apikeys' | 'integrations' | 'mission' | 'system' | 'security' | 'appearance' | 'accessibility'>('general')
const saving = ref(false)
const saveSuccess = ref('')
const saveError = ref('')
const showOnboarding = ref(false)
const toolsLoading = ref(false)
const themeLoading = ref(false)

const tabs = [
  { id: 'general' as const, label: 'General', icon: Settings },
  { id: 'ai' as const, label: 'IA', icon: Cpu },
  { id: 'tools' as const, label: 'Herramientas', icon: Wrench },
  { id: 'apikeys' as const, label: 'API Keys', icon: Key },
  { id: 'integrations' as const, label: 'Integraciones', icon: Plug },
  { id: 'mission' as const, label: 'Mission Control', icon: Crosshair },
  { id: 'system' as const, label: 'Sistema', icon: Server },
  { id: 'security' as const, label: 'Seguridad', icon: Shield },
  { id: 'appearance' as const, label: 'Apariencia', icon: Palette },
  { id: 'accessibility' as const, label: 'Accesibilidad', icon: Eye },
]

const toolsList = [
  { id: 'nuclei', name: 'Nuclei', desc: 'Template-based scanner' },
  { id: 'amass', name: 'Amass', desc: 'Subdomain enumeration' },
  { id: 'subfinder', name: 'Subfinder', desc: 'Passive subdomain discovery' },
  { id: 'httpx', name: 'Httpx', desc: 'HTTP probe & analysis' },
  { id: 'katana', name: 'Katana', desc: 'Crawler & spider' },
  { id: 'ffuf', name: 'Ffuf', desc: 'Fuzzing framework' },
  { id: 'gau', name: 'Gau', desc: 'URL gathering' },
  { id: 'naabu', name: 'Naabu', desc: 'Port scanner' },
  { id: 'assetfinder', name: 'Assetfinder', desc: 'Asset discovery' },
  { id: 'dnsx', name: 'Dnsx', desc: 'DNS resolver' },
]

const apiSections = [
  {
    label: 'Bug Bounty', icon: Bug, keys: [
      { key: 'bugcrowd', label: 'Bugcrowd', link: 'https://bugcrowd.com/user/edit' },
      { key: 'hackerone', label: 'HackerOne', link: 'https://hackerone.com/settings/api' },
      { key: 'intigriti', label: 'Intigriti', link: 'https://app.intigriti.com/profile' },
      { key: 'yeswehack', label: 'YesWeHack', link: 'https://yeswehack.com/profile' },
      { key: 'synack', label: 'Synack', link: 'https://synack.com/account' },
    ],
  },
  {
    label: 'OSINT', icon: Scan, keys: [
      { key: 'shodan', label: 'Shodan', link: 'https://account.shodan.io' },
      { key: 'censys', label: 'Censys', link: 'https://search.censys.io/account/api' },
      { key: 'securitytrails', label: 'SecurityTrails', link: 'https://securitytrails.com/app/account/credentials' },
      { key: 'virustotal', label: 'VirusTotal', link: 'https://virustotal.com/gui/my-apikey' },
    ],
  },
  {
    label: 'Código', icon: Globe, keys: [
      { key: 'github', label: 'GitHub', link: 'https://github.com/settings/tokens' },
      { key: 'gitlab', label: 'GitLab', link: 'https://gitlab.com/-/user_settings/personal_access_tokens' },
    ],
  },
  {
    label: 'IA', icon: Cpu, keys: [
      { key: 'openai', label: 'OpenAI', link: 'https://platform.openai.com/api-keys' },
      { key: 'anthropic', label: 'Anthropic', link: 'https://console.anthropic.com/' },
      { key: 'openrouter', label: 'OpenRouter', link: 'https://openrouter.ai/keys' },
      { key: 'google', label: 'Google (Gemini)', link: 'https://aistudio.google.com/apikey' },
    ],
  },
  {
    label: 'Financiero', icon: DollarSign, keys: [
      { key: 'wallet', label: 'Wallet cripto' },
      { key: 'bank', label: 'Banco (CBU/IBAN)' },
    ],
  },
]

const integrationsData = ref<{ integrations: any[]; by_category: Record<string, any[]>; by_status: Record<string, number> } | null>(null)
const integrationsLoading = ref(false)
const integrationsError = ref('')
const testingIntegration = ref<string | null>(null)
const testResults = ref<Record<string, { status: string; error: string | null }>>({})

const categoryLabels: Record<string, string> = {
  platform: 'Bug Bounty',
  ai: 'Inteligencia Artificial',
  exchange: 'Exchanges',
  blockchain: 'Blockchain',
  financial: 'Finanzas',
  messaging: 'Mensajería',
  infrastructure: 'Infraestructura',
}
const categoryIcons: Record<string, any> = {
  platform: Bug,
  ai: Cpu,
  exchange: DollarSign,
  blockchain: Database,
  financial: DollarSign,
  messaging: Globe,
  infrastructure: Server,
}

const statusIcon = (s: string) => {
  if (s === 'connected') return '🟢'
  if (s === 'disconnected') return '🟡'
  if (s === 'error') return '🔴'
  return '⚪'
}
const statusLabel = (s: string) => {
  if (s === 'connected') return 'Conectado'
  if (s === 'disconnected') return 'Desconectado'
  if (s === 'error') return 'Error'
  return 'No verificado'
}

async function loadIntegrations() {
  integrationsLoading.value = true
  integrationsError.value = ''
  try {
    const { getIntegrations } = await import('@/lib/api')
    const data = await getIntegrations()
    const byCat: Record<string, any[]> = {}
    for (const int of data.integrations) {
      ;(byCat[int.category] ||= []).push(int)
    }
    // Sort categories by display order
    const order = ['ai', 'platform', 'messaging', 'exchange', 'blockchain', 'financial', 'infrastructure']
    const sorted: Record<string, any[]> = {}
    for (const cat of order) {
      if (byCat[cat]) sorted[cat] = byCat[cat]
    }
    for (const cat of Object.keys(byCat).sort()) {
      if (!sorted[cat]) sorted[cat] = byCat[cat]
    }
    integrationsData.value = { ...data, by_category: sorted }
  } catch (e: any) {
    integrationsError.value = e?.message || 'Error al cargar integraciones'
  } finally {
    integrationsLoading.value = false
  }
}

async function testIntegration(name: string) {
  testingIntegration.value = name
  testResults.value[name] = { status: 'testing', error: null }
  try {
    const { testIntegration: ti } = await import('@/lib/api')
    const r = await ti(name)
    testResults.value[name] = { status: r.status, error: r.error }
    // Refresh after brief delay
    setTimeout(loadIntegrations, 2000)
  } catch (e: any) {
    testResults.value[name] = { status: 'error', error: e?.message || 'Error de conexión' }
  } finally {
    testingIntegration.value = null
  }
}

const systemItems = [
  { id: 'cpu', label: 'CPU', icon: Cpu },
  { id: 'ram', label: 'RAM', icon: Monitor },
  { id: 'disk', label: 'Disco', icon: HardDrive },
  { id: 'wsl', label: 'WSL', icon: Box },
  { id: 'docker', label: 'Docker', icon: Box },
  { id: 'python', label: 'Python', icon: Cpu },
  { id: 'node', label: 'Node.js', icon: Globe },
  { id: 'ollama', label: 'Ollama', icon: Cpu },
  { id: 'internet', label: 'Internet', icon: Wifi },
  { id: 'database', label: 'Base de datos', icon: Database },
]

const appearanceDensities = ['compact', 'normal', 'comfortable'] as const
const appearanceLayouts = ['default', 'wide', 'sidebar'] as const

// ── AI provider catalog: real backend list (GET /api/settings/ai/providers),
//    static fallback mirrors cores.ai.provider.PROVIDER_CATALOG ids. ──
interface ProviderCatalogEntry {
  id: string
  label: string
  desc: string
  models?: string[]
  available?: boolean | null
  active?: boolean
}
const FALLBACK_PROVIDERS: ProviderCatalogEntry[] = [
  { id: 'ollama', label: 'Ollama (Local)', desc: 'Local (gratuito)' },
  { id: 'openai', label: 'OpenAI Compatible', desc: 'GPT-4o / compatible' },
  { id: 'gemini', label: 'Google Gemini', desc: 'AI Studio' },
  { id: 'openrouter', label: 'OpenRouter', desc: 'Multi-modelo premium' },
  { id: 'devin', label: 'Devin AI Agent', desc: 'Agente free' },
  { id: 'freebuff', label: 'Freebuff', desc: 'Agente free' },
  { id: 'local', label: 'Local Rule-Based', desc: 'Sin LLM (fallback)' },
]
const providerCatalog = ref<ProviderCatalogEntry[]>(FALLBACK_PROVIDERS)
const catalogLoaded = ref(false)

async function loadProviderCatalog(): Promise<void> {
  try {
    const res = await api.get<{ providers: Array<{
      id: string; label: string; models?: string[]; available?: boolean | null; active?: boolean
    }> }>('/settings/ai/providers')
    if (Array.isArray(res.providers) && res.providers.length > 0) {
      providerCatalog.value = res.providers.map((p) => ({
        id: p.id,
        label: p.label,
        desc: `${(p.models ?? []).slice(0, 2).join(' · ') || 'sin modelos'}${(p.models?.length ?? 0) > 2 ? ' …' : ''}`,
        models: p.models,
        available: p.available,
        active: p.active,
      }))
      catalogLoaded.value = true
    }
  } catch {
    // backend unreachable → keep fallback catalog (UI stays usable offline)
  }
}

async function saveAI() {
  saving.value = true
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await settings.syncToBackend()
    // Aplicar el provider AL VIVO: PUT /settings/ai/config reconstruye el
    // registry de cores.ai.provider (persistir JSON solo no basta).
    const ai = settings.data.ai
    await api.put('/settings/ai/config', {
      provider_type: ai.provider,
      host:
        ai.provider === 'ollama' ? ai.ollamaHost
        : ai.provider === 'devin' ? ai.devinPath
        : ai.provider === 'freebuff' ? ai.freebuffConfigPath
        : '',
      model:
        ai.provider === 'ollama' ? ai.ollamaModel
        : ai.provider === 'openai' ? ai.openaiModel
        : ai.provider === 'gemini' ? ai.geminiModel
        : ai.provider === 'openrouter' ? ai.openrouterModel
        : ai.provider === 'devin' ? ai.devinModel
        : '',
      api_key:
        ai.provider === 'openai' ? ai.openaiKey
        : ai.provider === 'gemini' ? ai.geminiKey
        : ai.provider === 'openrouter' ? ai.openrouterKey
        : '',
      api_base: ai.provider === 'openai' ? ai.openaiBaseUrl : '',
    })
    saveSuccess.value = 'Configuración de IA guardada'
    setTimeout(() => saveSuccess.value = '', 3000)
  } catch (e: any) {
    saveError.value = e?.message || 'Error al guardar'
  } finally {
    saving.value = false
  }
}

async function saveApiKeys() {
  saving.value = true
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await settings.syncToBackend()
    saveSuccess.value = 'API Keys guardadas'
    setTimeout(() => saveSuccess.value = '', 3000)
  } catch (e: any) {
    saveError.value = e?.message || 'Error al guardar'
  } finally {
    saving.value = false
  }
}

function exportConfig() {
  const blob = new Blob([JSON.stringify(settings.data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
    a.download = `ownex-config-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function importConfig() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const imported = JSON.parse(text)
      if (!imported || typeof imported !== 'object') throw new Error('Invalid config')
      const allowedKeys = ['general', 'ai', 'apiKeys', 'missionControl', 'appearance', 'security', 'tools', 'system']
      for (const key of Object.keys(imported)) {
        if (!allowedKeys.includes(key)) throw new Error(`Unknown key: ${key}`)
      }
      Object.assign(settings.data, imported)
      settings.syncToBackend()
      saveSuccess.value = 'Configuración importada'
      setTimeout(() => saveSuccess.value = '', 3000)
    } catch {
      saveError.value = 'Error al importar configuración'
    }
  }
  input.click()
}

async function resetConfig() {
  if (!confirm('¿Resetear toda la configuración?')) return
  if (!confirm('¿Estás seguro? Esta acción elimina TODA la configuración. No se puede deshacer.')) return
  localStorage.removeItem('ownex_settings')
  window.location.reload()
}

async function runToolCheck() {
  toolsLoading.value = true
  saveSuccess.value = ''
  saveError.value = ''
  try {
    await settings.checkTools()
    saveSuccess.value = 'Verificación de herramientas completada'
    setTimeout(() => saveSuccess.value = '', 3000)
  } catch {
    saveError.value = 'Error al verificar herramientas'
  } finally {
    toolsLoading.value = false
  }
}

async function runToolTest(toolId: string) {
  saveSuccess.value = ''
  saveError.value = ''
  try {
    await settings.checkTools()
    saveSuccess.value = `Test de ${toolId} completado`
    setTimeout(() => saveSuccess.value = '', 3000)
  } catch {
    saveError.value = `Error al probar ${toolId}`
  }
}

let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
watch(() => settings.data, () => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    saveSuccess.value = 'Configuración guardada'
    setTimeout(() => { if (saveSuccess.value === 'Configuración guardada') saveSuccess.value = '' }, 2000)
  }, 300)
}, { deep: true })

onMounted(async () => {
  settings.loadFromBackend()
  loadIntegrations()
  void loadProviderCatalog()
  await initThemeEngine()
})
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6 animate-in">
    <!-- Header -->
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <Cog class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">OWNEX CONFIG</span>
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Configuración</h1>
        <p class="text-xs text-muted-foreground">Centro de control del sistema</p>
      </div>
      <div v-if="saveSuccess" class="flex items-center gap-1.5 rounded-lg bg-success/10 px-3 py-1.5">
        <CheckCircle2 class="h-3.5 w-3.5 text-success" />
        <span class="font-mono text-[10px] text-success">{{ saveSuccess }}</span>
      </div>
      <div v-else-if="saveError" class="flex items-center gap-1.5 rounded-lg bg-destructive/10 px-3 py-1.5">
        <AlertTriangle class="h-3.5 w-3.5 text-destructive" />
        <span class="font-mono text-[10px] text-destructive">{{ saveError }}</span>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 border-b border-border/30 pb-1 overflow-x-auto">
      <button
        v-for="tab in tabs" :key="tab.id"
        @click="activeTab = tab.id as typeof activeTab"
        :class="[
          'flex items-center gap-1.5 px-3 py-2 font-mono text-xs rounded-t-lg transition-all whitespace-nowrap shrink-0',
          activeTab === tab.id
            ? 'bg-primary/10 text-primary border-b-2 border-primary'
            : 'text-muted-foreground hover:text-foreground',
        ]"
      >
        <component :is="tab.icon" class="h-3.5 w-3.5" />
        {{ tab.label }}
      </button>
    </div>

    <!-- ═══════ GENERAL ═══════ -->
    <div v-if="activeTab === 'general'" class="space-y-4">
      <div class="card-base rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <User class="h-4 w-4 text-primary" /> Perfil
        </h3>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Nombre
              <Tooltip text="Nombre visible en el sistema. Se usa en saludos y reportes." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.general.userName"
              @input="settings.updateGeneral({ userName: ($event.target as HTMLInputElement).value })"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Idioma
              <Tooltip text="Idioma de la interfaz de usuario." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <select
              :value="currentLocale"
              @change="setLocale(($event.target as HTMLSelectElement).value as any)"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            >
              <option v-for="locale in supportedLocales" :key="locale" :value="locale">
                {{ locale === 'en' ? 'English' : locale === 'es' ? 'Español' : locale === 'fr' ? 'Français' : locale === 'de' ? 'Deutsch' : locale === 'ja' ? '日本語' : locale === 'zh' ? '中文' : locale }}
              </option>
            </select>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              :checked="settings.data.general.animations"
              @change="settings.updateGeneral({ animations: ($event.target as HTMLInputElement).checked })"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
            <span class="font-mono text-xs text-muted-foreground">Animaciones</span>
            <Tooltip text="Activar animaciones de UI y transiciones entre vistas." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              :checked="settings.data.general.accessibility"
              @change="settings.updateGeneral({ accessibility: ($event.target as HTMLInputElement).checked })"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
            <span class="font-mono text-xs text-muted-foreground">Accesibilidad</span>
            <Tooltip text="Modo de alto contraste y soporte para lectores de pantalla." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </label>
        </div>
      </div>

      <div class="card-base rounded-xl p-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2 mb-3">
          <Sparkles class="h-4 w-4 text-primary" /> Onboarding
        </h3>
        <p class="font-mono text-[10px] text-muted-foreground mb-3">Reabrí el asistente de configuración inicial para ajustar tu perfil, IA, API keys y más.</p>
        <Button variant="outline" size="sm" @click="showOnboarding = true">
          <Sparkles class="mr-1 h-3.5 w-3.5" /> Reabrir onboarding
        </Button>
      </div>
    </div>

    <!-- ═══════ IA ═══════ -->
    <div v-if="activeTab === 'ai'" class="space-y-4">
      <div class="card-base rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Cpu class="h-4 w-4 text-primary" /> Proveedor activo
          <Tooltip text="Seleccioná el motor de IA que OWNEX usará para análisis, generación de hipótesis y redacción de reportes." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
        </h3>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <button
            v-for="p in providerCatalog" :key="p.id"
            @click="settings.updateAI({ provider: p.id as never })"
            class="rounded-xl border p-4 text-left transition-all"
            :class="settings.data.ai.provider === p.id ? 'border-primary/40 bg-primary/5' : 'border-border/20 bg-surface/20 hover:bg-surface/30'"
          >
            <div class="flex items-center justify-between mb-2">
              <Cpu class="h-5 w-5" :class="settings.data.ai.provider === p.id ? 'text-primary' : 'text-muted-foreground'" />
              <div class="flex items-center gap-1.5">
                <span
                  v-if="p.available === true || p.available === null"
                  class="h-1.5 w-1.5 rounded-full bg-success"
                  :title="p.available === true ? 'Disponible' : ''"
                />
                <span
                  v-else
                  class="h-1.5 w-1.5 rounded-full bg-muted-foreground/40"
                  title="No configurado (falta API key / host)"
                />
                <div v-if="settings.data.ai.provider === p.id" class="h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_rgba(255,255,255,0.5)]" />
              </div>
            </div>
            <p class="font-mono text-sm font-semibold text-foreground">{{ p.label }}</p>
            <p class="font-mono text-[9px] text-muted-foreground mt-0.5">{{ p.desc }}</p>
          </button>
        </div>
        <p v-if="!catalogLoaded" class="font-mono text-[9px] text-muted-foreground">
          Catálogo local (sin conexión al backend). Al conectar, OWNEX muestra los providers reales con su disponibilidad.
        </p>

        <Separator />

        <!-- Ollama config -->
        <div v-if="settings.data.ai.provider === 'ollama'" class="space-y-4">
          <h4 class="font-mono text-[11px] font-semibold text-foreground">Configuración Ollama</h4>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                Host
                <Tooltip text="Dirección del servidor Ollama. Por defecto http://localhost:11434" position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
              </label>
              <input
                :value="settings.data.ai.ollamaHost"
                @input="settings.updateAI({ ollamaHost: ($event.target as HTMLInputElement).value })"
                class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
              />
            </div>
            <div>
              <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                Modelo
                <Tooltip text="Nombre del modelo en Ollama. Ej: qwen3:8b, llama3:8b, phi3:mini" position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
              </label>
              <input
                :value="settings.data.ai.ollamaModel"
                @input="settings.updateAI({ ollamaModel: ($event.target as HTMLInputElement).value })"
                class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
              />
            </div>
          </div>
        </div>

        <!-- OpenAI config -->
        <div v-if="settings.data.ai.provider === 'openai'" class="space-y-4">
          <h4 class="font-mono text-[11px] font-semibold text-foreground">Configuración OpenAI</h4>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              API Key
              <Tooltip text="Clave de API de OpenAI. Se almacena cifrada en el servidor." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.ai.openaiKey"
              @input="settings.updateAI({ openaiKey: ($event.target as HTMLInputElement).value })"
              type="password" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>

        <!-- Gemini config -->
        <div v-if="settings.data.ai.provider === 'gemini'" class="space-y-4">
          <h4 class="font-mono text-[11px] font-semibold text-foreground">Configuración Gemini</h4>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              API Key
              <Tooltip text="Clave de API de Google Gemini. Disponible en aistudio.google.com." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.ai.geminiKey"
              @input="settings.updateAI({ geminiKey: ($event.target as HTMLInputElement).value })"
              type="password" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>

        <!-- Devin config (agent CLI free) -->
        <div v-if="settings.data.ai.provider === 'devin'" class="space-y-4">
          <h4 class="font-mono text-[11px] font-semibold text-foreground">Configuración Devin</h4>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                Ruta del binario
                <Tooltip text="Comando o ruta del CLI de Devin (default: devin)." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
              </label>
              <input
                :value="settings.data.ai.devinPath"
                @input="settings.updateAI({ devinPath: ($event.target as HTMLInputElement).value })"
                class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
              />
            </div>
            <div>
              <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Modelo</label>
              <input
                :value="settings.data.ai.devinModel"
                @input="settings.updateAI({ devinModel: ($event.target as HTMLInputElement).value })"
                class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
              />
            </div>
          </div>
        </div>

        <!-- Freebuff config -->
        <div v-if="settings.data.ai.provider === 'freebuff'" class="space-y-4">
          <h4 class="font-mono text-[11px] font-semibold text-foreground">Configuración Freebuff</h4>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Ruta del config
              <Tooltip text="Path al yaml de configuración de Freebuff." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.ai.freebuffConfigPath"
              @input="settings.updateAI({ freebuffConfigPath: ($event.target as HTMLInputElement).value })"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>

        <!-- Temperature -->
        <div>
          <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
            Temperatura
            <Tooltip text="Controla la creatividad de las respuestas. 0 = preciso/determinístico, 2 = máximo creativo." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </label>
          <div class="flex items-center gap-3">
            <input
              :value="settings.data.ai.temperature"
              @input="settings.updateAI({ temperature: parseFloat(($event.target as HTMLInputElement).value) })"
              type="range" min="0" max="2" step="0.1" class="flex-1 accent-primary"
            />
            <span class="font-mono text-sm text-foreground w-8 text-right">{{ settings.data.ai.temperature.toFixed(1) }}</span>
          </div>
        </div>

        <!-- Memory -->
        <div class="flex items-center gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              :checked="settings.data.ai.memory"
              @change="settings.updateAI({ memory: ($event.target as HTMLInputElement).checked })"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
            <span class="font-mono text-xs text-muted-foreground">Memoria persistente</span>
            <Tooltip text="Recordar contexto entre sesiones de análisis del mismo target." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </label>
        </div>

        <div class="flex justify-end pt-2">
          <Button @click="saveAI" :loading="saving"><Save class="mr-1 h-4 w-4" /> Guardar</Button>
        </div>
      </div>
    </div>

    <!-- ═══════ HERRAMIENTAS ═══════ -->
    <div v-if="activeTab === 'tools'" class="space-y-4">
      <div class="card-base rounded-xl p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
            <Wrench class="h-4 w-4 text-primary" /> Herramientas del sistema
            <Tooltip text="Herramientas de reconocimiento instaladas en el sistema. OWNEX las usa para escaneo automatizado." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </h3>
          <Button size="sm" variant="outline" @click="runToolCheck()" :loading="toolsLoading">
            <RefreshCw class="h-3.5 w-3.5" /> Verificar
          </Button>
        </div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div v-for="tool in toolsWithInfo" :key="tool.id"
            class="flex items-center justify-between rounded-lg border border-border/20 px-4 py-2.5"
          >
            <div class="flex items-center gap-3">
              <div
                :class="['h-2 w-2 rounded-full', tool.info.installed ? 'bg-success shadow-[0_0_6px_rgba(22,163,74,0.4)]' : 'bg-muted-foreground/30']"
              />
              <div>
                <p class="font-mono text-xs font-semibold text-foreground">{{ tool.name }}</p>
                <p class="font-mono text-[9px] text-muted-foreground">{{ tool.desc }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="tool.info.version" class="font-mono text-[9px] text-muted-foreground">v{{ tool.info.version }}</span>
              <Badge
                :variant="tool.info.installed ? 'success' : 'default'"
                class="font-mono text-[8px] px-1.5 py-0"
              >{{ tool.info.installed ? 'OK' : '—' }}</Badge>
              <button
                v-if="tool.info.installed"
                @click="runToolTest(tool.id)"
                class="font-mono text-[9px] text-muted-foreground hover:text-foreground transition-colors"
              >Test</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════ API KEYS ═══════ -->
    <div v-if="activeTab === 'apikeys'" class="space-y-4">
      <div class="card-base rounded-xl p-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2 mb-4">
          <Key class="h-4 w-4 text-primary" /> Central de API Keys
          <Tooltip text="Todas las claves de API en un solo lugar. Se almacenan cifradas en el servidor." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
        </h3>
        <div v-for="section in apiSections" :key="section.label" class="mb-5 last:mb-0">
          <div class="flex items-center gap-2 mb-2">
            <component :is="section.icon" class="h-3.5 w-3.5 text-muted-foreground" />
            <span class="font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{{ section.label }}</span>
          </div>
          <div class="space-y-2">
            <div v-for="k in section.keys" :key="k.key" class="flex items-center gap-2">
              <span class="w-28 text-right font-mono text-[10px] text-muted-foreground">{{ k.label }}</span>
              <input
                :value="(settings.data.apiKeys as any)[k.key] || ''"
                @input="settings.updateApiKeys({ [k.key]: ($event.target as HTMLInputElement).value } as any)"
                type="password"
                placeholder="••••••••"
                class="flex-1 rounded-lg border border-border/30 bg-surface/20 px-3 py-1.5 font-mono text-[11px] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
              />
              <a v-if="(k as any).link" :href="(k as any).link" target="_blank" rel="noopener" class="text-muted-foreground hover:text-primary transition-colors">
                <ExternalLink class="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>
        <div class="flex justify-end pt-2">
          <Button @click="saveApiKeys" :loading="saving"><Save class="mr-1 h-4 w-4" /> Guardar todo</Button>
        </div>
      </div>
    </div>

    <!-- ═══════ INTEGRACIONES ═══════ -->
    <div v-if="activeTab === 'integrations'" class="space-y-4">
      <div class="card-base rounded-xl p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
            <Plug class="h-4 w-4 text-primary" /> Centro de Integraciones
          </h3>
          <Button size="sm" variant="outline" @click="loadIntegrations()" :loading="integrationsLoading">
            <RefreshCw class="h-3.5 w-3.5" /> Actualizar
          </Button>
        </div>

        <div v-if="integrationsLoading && !integrationsData" class="py-8 text-center font-mono text-xs text-muted-foreground">
          Cargando integraciones...
        </div>
        <div v-else-if="integrationsError" class="py-8 text-center font-mono text-xs text-destructive">
          {{ integrationsError }}
        </div>
        <div v-else-if="integrationsData" class="space-y-6">
          <!-- Summary bar -->
          <div class="flex flex-wrap gap-3 text-[10px] font-mono">
            <span class="text-muted-foreground">{{ integrationsData.integrations.length }} integraciones</span>
            <span v-if="integrationsData.by_status.connected" class="text-success">{{ integrationsData.by_status.connected }} conectadas</span>
            <span v-if="integrationsData.by_status.disconnected" class="text-warning">{{ integrationsData.by_status.disconnected }} desconectadas</span>
            <span v-if="integrationsData.by_status.error" class="text-destructive">{{ integrationsData.by_status.error }} con error</span>
            <span v-if="integrationsData.by_status.unknown" class="text-muted-foreground">{{ integrationsData.by_status.unknown }} sin verificar</span>
          </div>

          <!-- Category groups -->
          <div v-for="(ints, cat) in integrationsData.by_category" :key="cat" class="space-y-2">
            <div class="flex items-center gap-2 mb-1">
              <component :is="categoryIcons[cat] || Plug" class="h-3.5 w-3.5 text-muted-foreground" />
              <span class="font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                {{ categoryLabels[cat] || cat }}
              </span>
            </div>
            <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div v-for="int in ints" :key="int.name"
                class="flex items-center justify-between rounded-lg border border-border/20 px-4 py-3"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <span class="text-sm" :title="statusLabel(int.status)">{{ statusIcon(int.status) }}</span>
                  <div class="min-w-0">
                    <p class="font-mono text-xs font-semibold text-foreground truncate">{{ int.name }}</p>
                    <p class="font-mono text-[9px] text-muted-foreground truncate">{{ int.description || statusLabel(int.status) }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                  <span v-if="testResults[int.name] && testResults[int.name].status !== 'testing'"
                    class="font-mono text-[8px] px-1 py-0.5 rounded"
                    :class="testResults[int.name].status === 'connected' ? 'text-success bg-success/10' : 'text-destructive bg-destructive/10'"
                  >{{ testResults[int.name].status === 'connected' ? 'OK' : 'FAIL' }}</span>
                  <Button
                    size="sm" variant="ghost"
                    class="text-[10px] h-6 px-2"
                    :loading="testingIntegration === int.name"
                    @click="testIntegration(int.name)"
                  >Test</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════ MISSION CONTROL ═══════ -->
    <div v-if="activeTab === 'mission'" class="space-y-4">
      <div class="card-base rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Crosshair class="h-4 w-4 text-primary" /> Configuración del agente
          <Tooltip text="Controlá cómo OWNEX ejecuta las cazas autónomas: velocidad, profundidad, paralelismo." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
        </h3>

        <label class="flex items-center justify-between cursor-pointer">
          <div class="flex items-center gap-3">
            <Zap class="h-4 w-4 text-accent" />
            <div>
              <p class="font-mono text-xs text-foreground">Modo automático</p>
              <p class="font-mono text-[9px] text-muted-foreground">Caza autónoma sin intervención manual</p>
            </div>
          </div>
          <input
            :checked="settings.data.missionControl.autoMode"
            @change="settings.updateMissionControl({ autoMode: ($event.target as HTMLInputElement).checked })"
            type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
          />
        </label>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Paralelismo
              <Tooltip text="Cantidad de herramientas ejecutadas en paralelo durante el escaneo." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.missionControl.parallelism"
              @input="settings.updateMissionControl({ parallelism: parseInt(($event.target as HTMLInputElement).value) || 2 })"
              type="number" min="1" max="20"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Límite / target
              <Tooltip text="Cantidad máxima de endpoints a escanear por target." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.missionControl.limits"
              @input="settings.updateMissionControl({ limits: parseInt(($event.target as HTMLInputElement).value) || 100 })"
              type="number" min="10" max="10000"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Velocidad
              <Tooltip text="Velocidad de ejecución del pipeline. 'Aggressive' usa más recursos pero escanea más rápido." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <select
              :value="settings.data.missionControl.speed"
              @change="settings.updateMissionControl({ speed: ($event.target as HTMLSelectElement).value as any })"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            >
              <option value="slow">Lenta</option>
              <option value="normal">Normal</option>
              <option value="fast">Rápida</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              Profundidad
              <Tooltip text="Niveles de profundidad en el crawling. Mayor profundidad = más URLs, más tiempo." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
            </label>
            <input
              :value="settings.data.missionControl.depth"
              @input="settings.updateMissionControl({ depth: parseInt(($event.target as HTMLInputElement).value) || 3 })"
              type="number" min="1" max="10"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
              IA utilizada
            </label>
            <div class="rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground capitalize">
              {{ settings.data.ai.provider }}
            </div>
          </div>
        </div>

        <div>
          <label class="mb-1.5 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
            Herramientas permitidas
            <Tooltip text="Seleccioná qué herramientas se usan durante la caza autónoma." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </label>
          <div class="flex flex-wrap gap-2">
            <label v-for="tool in toolsList" :key="tool.id"
              class="flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 cursor-pointer transition-all text-[10px] font-mono"
              :class="settings.data.missionControl.allowedTools.includes(tool.id)
                ? 'border-primary/40 bg-primary/10 text-primary'
                : 'border-border/20 text-muted-foreground hover:text-foreground'"
            >
              <input
                :checked="settings.data.missionControl.allowedTools.includes(tool.id)"
                @change="settings.updateMissionControl({
                  allowedTools: settings.data.missionControl.allowedTools.includes(tool.id)
                    ? settings.data.missionControl.allowedTools.filter(t => t !== tool.id)
                    : [...settings.data.missionControl.allowedTools, tool.id]
                })"
                type="checkbox" class="hidden"
              />
              {{ tool.name }}
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════ SISTEMA ═══════ -->
    <div v-if="activeTab === 'system'" class="space-y-4">
      <div class="card-base rounded-xl p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
            <Activity class="h-4 w-4 text-primary" /> Estado del sistema
          </h3>
          <Button size="sm" variant="outline" @click="settings.updateSystemInfo()">
            <RefreshCw class="h-3.5 w-3.5" /> Actualizar
          </Button>
        </div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div v-for="item in systemItems" :key="item.id"
            class="flex items-center justify-between rounded-lg border border-border/20 px-4 py-2.5"
          >
            <div class="flex items-center gap-3">
              <component :is="item.icon" class="h-4 w-4 text-muted-foreground" />
              <span class="font-mono text-xs text-foreground">{{ item.label }}</span>
            </div>
            <span class="font-mono text-[10px] text-muted-foreground">
              {{ (settings.data.system as any)[item.id] || '—' }}
            </span>
          </div>
        </div>
      </div>
      <div class="card-base rounded-xl p-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2 mb-3">
          <Database class="h-4 w-4 text-accent" /> Health Check
        </h3>
        <p class="font-mono text-[10px] text-muted-foreground">Ejecutá un health check completo desde el panel de sistema. <Button size="sm" variant="ghost" class="text-[10px]" @click="$router.push('/operations')">Ir a Operations</Button></p>
      </div>
    </div>

    <!-- ═══════ SEGURIDAD ═══════ -->
    <div v-if="activeTab === 'security'" class="space-y-4">
      <div class="card-base rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Shield class="h-4 w-4 text-primary" /> Seguridad y datos
        </h3>

        <div class="flex items-center justify-between">
          <div>
            <p class="font-mono text-xs text-foreground">Backups automáticos</p>
            <p class="font-mono text-[9px] text-muted-foreground">Respaldo periódico de configuración y datos</p>
          </div>
          <input
            :checked="settings.data.security.backups"
            @change="settings.updateSecurity({ backups: ($event.target as HTMLInputElement).checked })"
            type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
          />
        </div>

        <div class="flex flex-wrap gap-3 pt-2">
          <Button variant="outline" size="sm" @click="exportConfig">
            <Download class="mr-1 h-3.5 w-3.5" /> Exportar configuración
          </Button>
          <Button variant="outline" size="sm" @click="importConfig">
            <Upload class="mr-1 h-3.5 w-3.5" /> Importar configuración
          </Button>
          <Button variant="destructive" size="sm" @click="resetConfig">
            <RotateCcw class="mr-1 h-3.5 w-3.5" /> Reset
          </Button>
        </div>
      </div>
    </div>

    <!-- ═══════ APARIENCIA ═══════ -->
    <div v-if="activeTab === 'appearance'" class="space-y-4">
      <div class="card-base rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Palette class="h-4 w-4 text-primary" /> Personalización visual
        </h3>

        <div v-if="themeLoading" class="text-center py-8 text-muted-foreground font-mono text-xs">
          Cargando temas...
        </div>
        <template v-else>
          <div>
            <label class="mb-2 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Tema</label>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="t in themeNames" :key="t.id"
                @click="setTheme(t.id)"
                class="rounded-lg border px-4 py-2 font-mono text-xs capitalize transition-all"
                :class="currentTheme?.id === t.id ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border/20 text-muted-foreground hover:text-foreground'"
              >{{ t.name }}</button>
            </div>
            <p v-if="currentTheme" class="mt-2 font-mono text-[10px] text-muted-foreground">{{ currentTheme.description }}</p>
          </div>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label class="mb-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Densidad</label>
              <select
                :value="settings.data.appearance.density"
                @change="settings.updateAppearance({ density: ($event.target as HTMLSelectElement).value as any })"
                class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
              >
                <option v-for="d in appearanceDensities" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Layout</label>
              <select
                :value="settings.data.appearance.layout"
                @change="settings.updateAppearance({ layout: ($event.target as HTMLSelectElement).value as any })"
                class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
              >
                <option v-for="l in appearanceLayouts" :key="l" :value="l">{{ l }}</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Animaciones</label>
              <label class="flex items-center gap-2 cursor-pointer pt-2">
                <input
                  :checked="settings.data.appearance.animations"
                  @change="settings.updateAppearance({ animations: ($event.target as HTMLInputElement).checked })"
                  type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
                />
                <span class="font-mono text-xs text-muted-foreground">Activadas</span>
              </label>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- ═══════ ACCESIBILIDAD ═══════ -->
    <div v-if="activeTab === 'accessibility'" class="space-y-4">
      <div class="card-base rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Eye class="h-4 w-4 text-primary" /> Preferencias de accesibilidad
        </h3>

        <div class="space-y-3">
          <label class="flex items-center justify-between cursor-pointer">
            <div>
              <p class="font-mono text-xs text-foreground">Navegación por teclado</p>
              <p class="font-mono text-[9px] text-muted-foreground">Atajos de teclado globales activos</p>
            </div>
            <input
              :checked="a11y.state.keyboardNavigation"
              @change="a11y.toggle('keyboardNavigation')"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
          </label>

          <Separator />

          <label class="flex items-center justify-between cursor-pointer">
            <div>
              <p class="font-mono text-xs text-foreground">Alto contraste</p>
              <p class="font-mono text-[9px] text-muted-foreground">Máximo contraste visual para legibilidad</p>
            </div>
            <input
              :checked="a11y.state.highContrast"
              @change="a11y.toggle('highContrast')"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
          </label>

          <Separator />

          <label class="flex items-center justify-between cursor-pointer">
            <div>
              <p class="font-mono text-xs text-foreground">Movimiento reducido</p>
              <p class="font-mono text-[9px] text-muted-foreground">Desactiva animaciones y transiciones</p>
            </div>
            <input
              :checked="a11y.state.reducedMotion"
              @change="a11y.toggle('reducedMotion')"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
          </label>

          <Separator />

          <label class="flex items-center justify-between cursor-pointer">
            <div>
              <p class="font-mono text-xs text-foreground">Modo lector de pantalla</p>
              <p class="font-mono text-[9px] text-muted-foreground">Atributos ARIA mejorados y semántica</p>
            </div>
            <input
              :checked="a11y.state.screenReaderMode"
              @change="a11y.toggle('screenReaderMode')"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
          </label>

          <Separator />

          <label class="flex items-center justify-between cursor-pointer">
            <div>
              <p class="font-mono text-xs text-foreground">Indicador de foco</p>
              <p class="font-mono text-[9px] text-muted-foreground">Anillo visible al navegar con teclado</p>
            </div>
            <input
              :checked="a11y.state.focusIndicator"
              @change="a11y.toggle('focusIndicator')"
              type="checkbox" class="h-4 w-4 rounded border-border/60 accent-primary"
            />
          </label>
        </div>

        <Separator />

        <div>
          <label class="mb-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
            Escala de fuente ({{ a11y.state.fontScale }}%)
          </label>
          <div class="flex gap-2">
            <button
              v-for="s in fontScaleOptions" :key="s"
              @click="a11y.patch({ fontScale: s })"
              class="rounded-lg border px-3 py-1.5 font-mono text-xs transition-all"
              :class="a11y.state.fontScale === s ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border/20 text-muted-foreground hover:text-foreground'"
            >{{ s }}%</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <OnboardingWizard :open="showOnboarding" @close="showOnboarding = false" />
</template>
