<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { Activity, Bug, Dices, TrendingUp } from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

interface Widget {
  id: string
  label: string
  value: string | number
  icon: string
  color?: string
}

const { toast } = useToast()
const widgets = ref<Widget[]>([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/core/status')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    const w: Widget[] = []
    if (data.apps) {
      for (const [_appId, app] of Object.entries(data.apps) as [string, any][]) {
        w.push({
          id: `${_appId}-status`,
          label: app.name || _appId,
          value: 'En línea',
          icon: app.icon || 'AppWindow',
          color: 'text-primary',
        })
      }
    }
    w.push({ id: 'databases', label: 'Bases de datos', value: Object.keys(data.databases || {}).length, icon: 'Database', color: 'text-accent' })
    widgets.value = w.length > 0 ? w : []
  } catch (e) {
    error.value = 'No se pudo conectar con el servidor'
    toast.error('Error de conexión', 'Verificá que el backend esté corriendo')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="p-6 space-y-6">
    <div>
      <h1 class="text-2xl font-bold">ORION Platform</h1>
      <p class="text-muted-foreground">Sistema de inteligencia operativa privada</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-lg" />
    </div>

    <!-- Widgets grid -->
    <div v-if="!loading && !error && widgets.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div
        v-for="w in widgets" :key="w.id"
        class="border border-border/50 rounded-lg p-4 bg-card hover:bg-accent/5 transition-colors"
      >
        <div class="text-sm text-muted-foreground">{{ w.label }}</div>
        <div class="text-2xl font-bold mt-1" :class="w.color || 'text-foreground'">{{ w.value }}</div>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="border border-destructive/30 rounded-lg p-6 text-center bg-card">
      <p class="text-sm text-destructive font-semibold">{{ error }}</p>
      <button @click="onMounted" class="mt-3 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/80 transition-colors">
        Reintentar
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState
      v-if="!loading && !error && widgets.length === 0"
      title="Sin datos del sistema"
      description="No se recibieron métricas del backend. Verificá que los servicios estén activos."
    />

    <!-- App shortcuts -->
    <div>
      <h2 class="text-lg font-semibold mb-3">Aplicaciones</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <router-link to="/cateye/"
          class="border border-border/50 rounded-lg p-4 bg-card hover:border-primary/50 transition-colors group">
          <div class="text-2xl mb-2">🐛</div>
          <div class="font-semibold group-hover:text-primary transition-colors">CATEYE</div>
          <div class="text-sm text-muted-foreground">Bug Bounty Intelligence</div>
        </router-link>
        <router-link to="/atlas/"
          class="border border-border/50 rounded-lg p-4 bg-card hover:border-primary/50 transition-colors group">
          <div class="text-2xl mb-2">📈</div>
          <div class="font-semibold group-hover:text-primary transition-colors">ATLAS</div>
          <div class="text-sm text-muted-foreground">Gestión de inversiones</div>
        </router-link>
        <router-link to="/odyssey/"
          class="border border-border/50 rounded-lg p-4 bg-card hover:border-primary/50 transition-colors group">
          <div class="text-2xl mb-2">🎲</div>
          <div class="font-semibold group-hover:text-primary transition-colors">ODYSSEY</div>
          <div class="text-sm text-muted-foreground">Analítica de apuestas</div>
        </router-link>
      </div>
    </div>
  </div>
</template>
