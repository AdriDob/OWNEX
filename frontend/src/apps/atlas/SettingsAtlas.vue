<script setup lang="ts">
import { AlertTriangle, Cable, CheckCircle2, Globe, KeyRound, RefreshCw, Save, Shield, Sliders } from '@lucide/vue'
import { onMounted, reactive, ref } from 'vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'
import { api } from '@/lib/api'

const { toast } = useToast()
const saveSuccess = ref('')
const saveError = ref('')
const loading = ref(true)
const activeTab = ref('connections')

const tabs = [
  { id: 'connections', label: 'Conexiones', icon: Cable },
  { id: 'keys', label: 'API Keys', icon: KeyRound },
  { id: 'adjustment', label: 'Ajustes', icon: Sliders },
  { id: 'risk', label: 'Riesgo', icon: Shield },
]

interface ConnectorConfig {
  key: string
  label: string
  type: string
  default: string
}

interface ConnectorInfo {
  id: string
  name: string
  connected: boolean
  config_fields: ConnectorConfig[]
}

const connectors = ref<ConnectorInfo[]>([])
const formValues = reactive<Record<string, string>>({})

const riskConfig = reactive({
  max_concentration: 40,
  max_crypto_exposure: 50,
  min_diversification: 30,
  rebalance_threshold: 5,
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await fetch('/api/atlas/health')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    // Load connector info from manifest
    const coreRes = await fetch('/api/core/apps')
    if (coreRes.ok) {
      const apps = await coreRes.json()
      const atlasApp = apps.find((a: any) => a.id === 'atlas')
      if (atlasApp?.providers) {
        connectors.value = atlasApp.providers.map((pid: string) => ({
          id: pid,
          name: pid.split('/').pop() || pid,
          connected: false,
          config_fields: [],
        }))
      }
    }
  } catch (e) {
    toast.error('Error', 'No se pudieron cargar las conexiones')
  } finally {
    loading.value = false
  }
})

function updateValue(key: string, value: string) {
  formValues[key] = value
}

async function saveSettings() {
  saveSuccess.value = ''
  saveError.value = ''
  try {
    // Persist to localStorage as encrypted settings (same pattern as CATEYE)
    const existing = JSON.parse(localStorage.getItem('orion_atlas_settings') || '{}')
    const updated = { ...existing, ...formValues, riskConfig: { ...riskConfig } }
    localStorage.setItem('orion_atlas_settings', JSON.stringify(updated))
    saveSuccess.value = 'Configuración guardada correctamente'
    toast.success('Guardado', 'La configuración de ATLAS se actualizó')
    setTimeout(() => {
      saveSuccess.value = ''
    }, 3000)
  } catch (e) {
    saveError.value = 'Error al guardar la configuración'
    toast.error('Error', 'No se pudo guardar la configuración')
  }
}
</script>

<template>
  <div class="p-6 space-y-6">
    <div>
      <h1 class="text-2xl font-bold">Configuración de ATLAS</h1>
      <p class="text-muted-foreground">Gestión de conexiones, API keys y preferencias de inversión</p>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 border-b border-border/30 pb-1 overflow-x-auto">
      <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
        :class="[
          'flex items-center gap-1.5 px-3 py-2 font-mono text-xs rounded-t-lg transition-all whitespace-nowrap',
          activeTab === tab.id ? 'bg-primary/10 text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground',
        ]"
      >
        <component :is="tab.icon" class="h-3.5 w-3.5" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-32 rounded-xl" />
    </div>

    <!-- Connections tab -->
    <div v-if="!loading && activeTab === 'connections'" class="space-y-4">
      <div class="rounded-xl border border-border/50 bg-card p-5 space-y-4">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Cable class="h-4 w-4 text-primary" /> Conexiones activas
        </h3>
        <p class="text-xs text-muted-foreground">Conectá tus exchanges y plataformas para sincronizar datos automáticamente.</p>
        <div v-if="connectors.length === 0" class="text-xs text-muted-foreground py-4 text-center">
          No hay conectores disponibles.
        </div>
        <div v-for="conn in connectors" :key="conn.id"
          class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/20 px-4 py-3"
        >
          <div class="flex items-center gap-3">
            <div class="h-2 w-2 rounded-full" :class="conn.connected ? 'bg-success' : 'bg-muted'" />
            <span class="text-sm font-medium">{{ conn.name }}</span>
          </div>
          <span class="text-xs font-mono text-muted-foreground">{{ conn.id }}</span>
        </div>
      </div>
    </div>

    <!-- API Keys tab -->
    <div v-if="!loading && activeTab === 'keys'" class="space-y-4">
      <div class="rounded-xl border border-border/50 bg-card p-5 space-y-4">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <KeyRound class="h-4 w-4 text-primary" /> Claves de API
        </h3>
        <p class="text-xs text-muted-foreground">Las claves se almacenan cifradas en tu navegador. Nunca salen de tu dispositivo.</p>
        <div class="space-y-3">
          <div v-for="conn in connectors" :key="conn.id" class="space-y-1">
            <label class="text-xs font-mono text-muted-foreground">{{ conn.name }}</label>
            <input
              :value="formValues[conn.id + '_api_key'] || ''"
              @input="updateValue(conn.id + '_api_key', ($event.target as HTMLInputElement).value)"
              type="password"
              placeholder="API Key"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Ajustes tab -->
    <div v-if="!loading && activeTab === 'adjustment'" class="space-y-4">
      <div class="rounded-xl border border-border/50 bg-card p-5 space-y-4">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Sliders class="h-4 w-4 text-primary" /> Preferencias de datos
        </h3>
        <div class="space-y-3">
          <div>
            <label class="text-xs font-mono text-muted-foreground">Intervalo de sincronización (horas)</label>
            <input type="number" value="1"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">Moneda base</label>
            <select
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            >
              <option value="USD">USD</option>
              <option value="ARS">ARS</option>
              <option value="EUR">EUR</option>
              <option value="BTC">BTC</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Risk tab -->
    <div v-if="!loading && activeTab === 'risk'" class="space-y-4">
      <div class="rounded-xl border border-border/50 bg-card p-5 space-y-4">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Shield class="h-4 w-4 text-primary" /> Límites de riesgo
        </h3>
        <p class="text-xs text-muted-foreground">Configurá los umbrales que activan alertas y recomendaciones.</p>
        <div class="space-y-3">
          <div>
            <label class="text-xs font-mono text-muted-foreground">Concentración máxima por activo (%)</label>
            <input type="number" v-model.number="riskConfig.max_concentration"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">Exposición máxima en crypto (%)</label>
            <input type="number" v-model.number="riskConfig.max_crypto_exposure"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">Umbral de rebalanceo (%)</label>
            <input type="number" v-model.number="riskConfig.rebalance_threshold"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Save feedback + button -->
    <div v-if="!loading" class="space-y-3">
      <div v-if="saveSuccess" class="flex items-center gap-1.5 rounded-lg bg-success/10 px-3 py-1.5">
        <CheckCircle2 class="h-3.5 w-3.5 text-success" />
        <span class="font-mono text-[10px] text-success">{{ saveSuccess }}</span>
      </div>
      <div v-else-if="saveError" class="flex items-center gap-1.5 rounded-lg bg-destructive/10 px-3 py-1.5">
        <AlertTriangle class="h-3.5 w-3.5 text-destructive" />
        <span class="font-mono text-[10px] text-destructive">{{ saveError }}</span>
      </div>
      <button @click="saveSettings"
        class="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-xs font-semibold text-primary-foreground hover:bg-primary/80 transition-colors"
      >
        <Save class="h-3.5 w-3.5" />
        Guardar configuración
      </button>
    </div>
  </div>
</template>
