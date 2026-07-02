<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import type { ToolsSettings } from '@/stores/settings'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import Separator from '@/components/ui/Separator.vue'
import OnboardingWizard from '@/components/onboarding/OnboardingWizard.vue'
import {
  Settings, Palette, Bell, Shield, Cpu, Globe, Eye, Key, Save, CheckCircle2,
  AlertTriangle, Loader2, RefreshCw, ExternalLink, Plus, Trash2, Link, Unlink,
  User, Languages, Monitor, Wrench, Server, Lock, Download, Upload, RotateCcw,
  Play, Square, Sliders, Gauge, Box, Activity, Database, Wifi, HardDrive,
  ChevronRight, Zap, Sparkles, Bug, Crosshair, Scan, DollarSign,
} from '@lucide/vue'

const settings = useSettingsStore()

const toolsWithInfo = computed(() =>
  toolsList.map(t => ({ ...t, info: (settings.data.tools as Record<string, { installed: boolean; version: string }>)[t.id] || { installed: false, version: '' } }))
)

type ApiKeyEntry = { key: string; label: string; link?: string }
function hasLink(k: ApiKeyEntry): k is ApiKeyEntry & { link: string } {
  return 'link' in k && !!k.link
}
const activeTab = ref<'general' | 'ai' | 'tools' | 'apikeys' | 'mission' | 'system' | 'security' | 'appearance'>('general')
const saving = ref(false)
const saveSuccess = ref('')
const saveError = ref('')
const showOnboarding = ref(false)

const tabs = [
  { id: 'general' as const, label: 'General', icon: Settings },
  { id: 'ai' as const, label: 'IA', icon: Cpu },
  { id: 'tools' as const, label: 'Herramientas', icon: Wrench },
  { id: 'apikeys' as const, label: 'API Keys', icon: Key },
  { id: 'mission' as const, label: 'Mission Control', icon: Crosshair },
  { id: 'system' as const, label: 'Sistema', icon: Server },
  { id: 'security' as const, label: 'Seguridad', icon: Shield },
  { id: 'appearance' as const, label: 'Apariencia', icon: Palette },
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

const appearanceThemes = ['cyber', 'dark', 'light', 'ocean', 'sunset']
const appearanceColors = ['default', 'green', 'blue', 'purple', 'orange']
const appearanceDensities = ['compact', 'normal', 'comfortable'] as const
const appearanceLayouts = ['default', 'wide', 'sidebar'] as const

async function saveAI() {
  saving.value = true
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await settings.syncToBackend()
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
  a.download = `cateye-config-${new Date().toISOString().slice(0, 10)}.json`
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
  if (!confirm('¿Resetear toda la configuración? Esta acción no se puede deshacer.')) return
  localStorage.removeItem('cateye_settings')
  window.location.reload()
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

onMounted(() => {
  settings.loadFromBackend()
})
</script>

<template>
  <div class="space-y-6 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <Cog class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">CATEYE CONFIG</span>
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
      <div class="cyber-card rounded-xl p-5 space-y-5">
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
              :value="settings.data.general.language"
              @change="settings.updateGeneral({ language: ($event.target as HTMLSelectElement).value })"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            >
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="pt">Português</option>
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

      <div class="cyber-card rounded-xl p-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2 mb-3">
          <Bell class="h-4 w-4 text-accent" /> Notificaciones
        </h3>
        <p class="font-mono text-[10px] text-muted-foreground">Configuración de notificaciones disponible próximamente.</p>
      </div>

      <div class="cyber-card rounded-xl p-5">
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
      <div class="cyber-card rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Cpu class="h-4 w-4 text-primary" /> Proveedor activo
          <Tooltip text="Seleccioná el motor de IA que CATEYE usará para análisis, generación de hipótesis y redacción de reportes." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
        </h3>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <button
            v-for="p in [
              { id: 'ollama', label: 'Ollama', desc: 'Local (gratuito)' },
              { id: 'openai', label: 'OpenAI', desc: 'GPT-4o / GPT-4o-mini' },
              { id: 'gemini', label: 'Gemini', desc: 'Google Gemini' },
              { id: 'openrouter', label: 'OpenRouter', desc: 'Multi-modelo' },
            ]" :key="p.id"
            @click="settings.updateAI({ provider: p.id as any })"
            class="rounded-xl border p-4 text-left transition-all"
            :class="settings.data.ai.provider === p.id ? 'border-primary/40 bg-primary/5' : 'border-border/20 bg-surface/20 hover:bg-surface/30'"
          >
            <div class="flex items-center justify-between mb-2">
              <Cpu class="h-5 w-5" :class="settings.data.ai.provider === p.id ? 'text-primary' : 'text-muted-foreground'" />
              <div v-if="settings.data.ai.provider === p.id" class="h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_rgba(0,255,65,0.5)]" />
            </div>
            <p class="font-mono text-sm font-semibold text-foreground">{{ p.label }}</p>
            <p class="font-mono text-[9px] text-muted-foreground mt-0.5">{{ p.desc }}</p>
          </button>
        </div>

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
      <div class="cyber-card rounded-xl p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
            <Wrench class="h-4 w-4 text-primary" /> Herramientas del sistema
            <Tooltip text="Herramientas de reconocimiento instaladas en el sistema. CATEYE las usa para escaneo automatizado." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
          </h3>
          <Button size="sm" variant="outline" @click="settings.checkTools()">
            <RefreshCw class="h-3.5 w-3.5" /> Verificar
          </Button>
        </div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div v-for="tool in toolsWithInfo" :key="tool.id"
            class="flex items-center justify-between rounded-lg border border-border/20 px-4 py-2.5"
          >
            <div class="flex items-center gap-3">
              <div
                :class="['h-2 w-2 rounded-full', tool.info.installed ? 'bg-success shadow-[0_0_6px_rgba(0,230,118,0.5)]' : 'bg-muted-foreground/30']"
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
      <div class="cyber-card rounded-xl p-5">
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

    <!-- ═══════ MISSION CONTROL ═══════ -->
    <div v-if="activeTab === 'mission'" class="space-y-4">
      <div class="cyber-card rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Crosshair class="h-4 w-4 text-primary" /> Configuración del agente
          <Tooltip text="Controlá cómo CATEYE ejecuta las cazas autónomas: velocidad, profundidad, paralelismo." position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
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
      <div class="cyber-card rounded-xl p-5">
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
      <div class="cyber-card rounded-xl p-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2 mb-3">
          <Database class="h-4 w-4 text-accent" /> Health Check
        </h3>
        <p class="font-mono text-[10px] text-muted-foreground">Ejecutá un health check completo desde el panel de sistema. <Button size="sm" variant="ghost" class="text-[10px]" @click="$router.push('/operations')">Ir a Operations</Button></p>
      </div>
    </div>

    <!-- ═══════ SEGURIDAD ═══════ -->
    <div v-if="activeTab === 'security'" class="space-y-4">
      <div class="cyber-card rounded-xl p-5 space-y-5">
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
      <div class="cyber-card rounded-xl p-5 space-y-5">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Palette class="h-4 w-4 text-primary" /> Personalización visual
        </h3>

        <div>
          <label class="mb-2 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Tema</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="t in appearanceThemes" :key="t"
              @click="settings.updateAppearance({ theme: t })"
              class="rounded-lg border px-4 py-2 font-mono text-xs capitalize transition-all"
              :class="settings.data.appearance.theme === t ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border/20 text-muted-foreground hover:text-foreground'"
            >{{ t }}</button>
          </div>
        </div>

        <div>
          <label class="mb-2 flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Colores</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="c in appearanceColors" :key="c"
              @click="settings.updateAppearance({ colors: c })"
              class="rounded-lg border px-4 py-2 font-mono text-xs capitalize transition-all"
              :class="settings.data.appearance.colors === c ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border/20 text-muted-foreground hover:text-foreground'"
            >{{ c }}</button>
          </div>
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
      </div>
    </div>
  </div>
  <OnboardingWizard :open="showOnboarding" @close="showOnboarding = false" />
</template>
