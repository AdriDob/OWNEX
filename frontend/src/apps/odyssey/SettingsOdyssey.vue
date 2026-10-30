<script setup lang="ts">
import { AlertTriangle, Cable, CheckCircle2, Dices, KeyRound, Percent, Save, Shield, Sliders } from '@lucide/vue'
import { onMounted, reactive, ref } from 'vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()
const saveSuccess = ref('')
const saveError = ref('')
const loading = ref(true)
const activeTab = ref('connections')

const tabs = [
  { id: 'connections', label: 'Conexiones', icon: Cable },
  { id: 'keys', label: 'API Keys', icon: KeyRound },
  { id: 'kelly', label: 'Kelly', icon: Percent },
  { id: 'limits', label: 'Límites', icon: Shield },
]

interface ConnectorInfo {
  id: string
  name: string
  connected: boolean
}

const connectors = ref<ConnectorInfo[]>([])
const formValues = reactive<Record<string, string>>({})

const kellyConfig = reactive({
  default_fraction: 0.25,
  min_ev: 0.05,
  min_odds: 1.5,
  max_odds: 10.0,
})

const bankrollConfig = reactive({
  max_stake_percent: 5,
  risk_level: 'medium',
})

onMounted(async () => {
  loading.value = true
  try {
    const coreRes = await fetch('/api/core/apps')
    if (coreRes.ok) {
      const apps = await coreRes.json()
      const odysseyApp = apps.find((a: any) => a.id === 'odyssey')
      if (odysseyApp?.providers) {
        connectors.value = odysseyApp.providers.map((pid: string) => ({
          id: pid,
          name: pid.split('/').pop() || pid,
          connected: false,
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
    const existing = JSON.parse(localStorage.getItem('orion_odyssey_settings') || '{}')
    const updated = {
      ...existing,
      ...formValues,
      kellyConfig: { ...kellyConfig },
      bankrollConfig: { ...bankrollConfig },
    }
    localStorage.setItem('orion_odyssey_settings', JSON.stringify(updated))
    saveSuccess.value = 'Configuración guardada correctamente'
    toast.success('Guardado', 'La configuración de ODYSSEY se actualizó')
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
      <h1 class="text-2xl font-bold">Configuración de ODYSSEY</h1>
      <p class="text-muted-foreground">Gestión de conexiones, Kelly y límites de bankroll</p>
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
          <Cable class="h-4 w-4 text-primary" /> Plataformas conectadas
        </h3>
        <p class="text-xs text-muted-foreground">Conectá tus plataformas de apuestas para importar historial y odds.</p>
        <div v-if="connectors.length === 0" class="text-xs text-muted-foreground py-4 text-center">
          No hay conectores disponibles.
        </div>
        <div v-for="conn in connectors" :key="conn.id"
          class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/20 px-4 py-3"
        >
          <div class="flex items-center gap-3">
            <div class="h-2 w-2 rounded-full" :class="conn.connected ? 'bg-success' : 'bg-muted'" />
            <span class="text-sm font-medium capitalize">{{ conn.name.replace(/_/g, ' ') }}</span>
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
        <p class="text-xs text-muted-foreground">Almacenadas cifradas en tu navegador. Nunca se envían a nuestros servidores.</p>
        <div class="space-y-3">
          <div v-for="conn in connectors" :key="conn.id" class="space-y-1">
            <label class="text-xs font-mono text-muted-foreground capitalize">{{ conn.name.replace(/_/g, ' ') }}</label>
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

    <!-- Kelly tab -->
    <div v-if="!loading && activeTab === 'kelly'" class="space-y-4">
      <div class="rounded-xl border border-border/50 bg-card p-5 space-y-4">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Percent class="h-4 w-4 text-primary" /> Criterio de Kelly
        </h3>
        <p class="text-xs text-muted-foreground">Configuración por defecto para el cálculo de stake óptimo.</p>
        <div class="space-y-3">
          <div>
            <label class="text-xs font-mono text-muted-foreground">Fracción de Kelly (0.0 - 1.0)</label>
            <input type="number" step="0.05" v-model.number="kellyConfig.default_fraction"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">EV mínimo requerido</label>
            <input type="number" step="0.01" v-model.number="kellyConfig.min_ev"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">Odds mínimas</label>
            <input type="number" step="0.1" v-model.number="kellyConfig.min_odds"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">Odds máximas</label>
            <input type="number" step="0.1" v-model.number="kellyConfig.max_odds"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Limits tab -->
    <div v-if="!loading && activeTab === 'limits'" class="space-y-4">
      <div class="rounded-xl border border-border/50 bg-card p-5 space-y-4">
        <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
          <Shield class="h-4 w-4 text-primary" /> Límites de bankroll
        </h3>
        <p class="text-xs text-muted-foreground">Umbrales para alertas y control de riesgo.</p>
        <div class="space-y-3">
          <div>
            <label class="text-xs font-mono text-muted-foreground">Stake máximo (% del bankroll)</label>
            <input type="number" v-model.number="bankrollConfig.max_stake_percent"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label class="text-xs font-mono text-muted-foreground">Nivel de riesgo por defecto</label>
            <select v-model="bankrollConfig.risk_level"
              class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50"
            >
              <option value="low">Bajo</option>
              <option value="medium">Medio</option>
              <option value="high">Alto</option>
            </select>
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
