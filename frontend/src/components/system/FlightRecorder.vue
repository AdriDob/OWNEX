<script setup lang="ts">
/**
 * FlightRecorder — Log de actividad del sistema estilo "grabadora de vuelo".
 * Muestra eventos en tiempo real: qué hizo OWNEX, cuándo, y qué necesita.
 */

import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '@/lib/api'
import { useNotificationsStore } from '@/stores/notifications'

interface FlightEvent {
  id: string
  timestamp: string
  type: 'system' | 'work' | 'intel' | 'money' | 'error' | 'approval'
  source: string
  message: string
  details?: string
  actionRequired?: boolean
  actionLabel?: string
  actionRoute?: string
}

const notifications = useNotificationsStore()

const events = ref<FlightEvent[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const autoRefresh = ref(true)
let refreshInterval: ReturnType<typeof setInterval> | null = null
const maxEvents = 100

const typeIcons: Record<FlightEvent['type'], string> = {
  system: 'cpu',
  work: 'zap',
  intel: 'shield',
  money: 'dollar-sign',
  error: 'alert-triangle',
  approval: 'user-round',
}

const typeLabels: Record<FlightEvent['type'], string> = {
  system: 'SISTEMA',
  work: 'TRABAJO',
  intel: 'INTEL',
  money: 'DINERO',
  error: 'ERROR',
  approval: 'APROBACIÓN',
}

async function load(limit = 50) {
  loading.value = true
  error.value = null
  try {
    const res = await api.get<{ events: FlightEvent[] }>(`/activity?limit=${limit}`)
    events.value = res.events || []
  } catch (e: any) {
    error.value = e?.message || 'No se pudo cargar actividad'
    events.value = []
  } finally {
    loading.value = false
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'ahora'
  if (minutes < 60) return `hace ${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `hace ${hours}h`
  return `hace ${Math.floor(hours / 24)}d`
}

function handleAction(event: FlightEvent) {
  if (event.actionRoute) {
    window.location.href = event.actionRoute
  }
}

onMounted(() => {
  load()
  if (autoRefresh.value) {
    refreshInterval = setInterval(() => load(20), 15000)
  }
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="flex flex-col h-full bg-background rounded-xl border border-border/30 overflow-hidden">
    <!-- Header -->
    <header class="flex items-center justify-between px-4 py-3 border-b border-border/30 bg-surface/30 backdrop-blur-sm">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <svg class="h-5 w-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
            <line x1="12" y1="22.08" x2="12" y2="12" />
          </svg>
        </div>
        <div>
          <h3 class="font-mono text-xs uppercase tracking-wider text-foreground">FLIGHT RECORDER</h3>
          <p class="font-mono text-[9px] text-muted-foreground">Actividad del sistema en tiempo real</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button @click="autoRefresh = !autoRefresh" :class="autoRefresh ? 'text-primary' : 'text-muted-foreground'" class="p-1.5 hover:bg-muted/30 rounded" title="Auto-refresh">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6" />
            <path d="M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
        <button @click="load" :disabled="loading" class="p-1.5 hover:bg-muted/30 rounded" title="Actualizar ahora">
          <svg class="h-4 w-4" :class="loading ? 'animate-spin' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Events List -->
    <div class="flex-1 overflow-y-auto p-3 space-y-2" v-if="!loading || events.length">
      <template v-if="events.length === 0 && !loading">
        <div class="flex flex-col items-center justify-center h-full text-muted-foreground/50">
          <svg class="h-12 w-12 mb-3 opacity-30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <p class="text-sm">Sin actividad registrada</p>
          <p class="text-xs">OWNEX registra eventos aquí cuando trabaja</p>
        </div>
      </template>

      <template v-else>
        <div v-for="event in events" :key="event.id" class="group relative flex gap-3 px-2 py-2.5 hover:bg-muted/30 rounded-lg transition-colors">
          <!-- Timeline connector -->
          <div class="relative shrink-0 w-1.5">
            <div class="absolute left-0.5 top-0 bottom-0 w-0.5 bg-border/30" />
            <div class="relative w-1.5 h-1.5 rounded-full border-2 flex-shrink-0"
              :class="[
                event.type === 'error' ? 'bg-destructive border-destructive' :
                event.type === 'approval' ? 'bg-warning border-warning' :
                event.type === 'money' ? 'bg-success border-success' :
                event.type === 'work' ? 'bg-primary border-primary' :
                event.type === 'intel' ? 'bg-blue-500 border-blue-500' :
                'bg-muted border-border'
              ]"
            />
          </div>

          <!-- Event content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="badge badge-xs" :class="[
                event.type === 'error' ? 'badge-destructive' :
                event.type === 'approval' ? 'badge-warning' :
                event.type === 'money' ? 'badge-success' :
                event.type === 'work' ? 'badge-primary' :
                event.type === 'intel' ? 'badge-blue' : 'badge-muted'
              ]">{{ typeLabels[event.type] }}</span>
              <span class="font-mono text-[10px] text-muted-foreground">{{ event.source }}</span>
              <span class="font-mono text-[10px] text-muted-foreground/60 ml-auto">{{ formatRelative(event.timestamp) }}</span>
            </div>
            <p class="mt-1 text-sm text-foreground leading-relaxed">{{ event.message }}</p>
            <p v-if="event.details" class="mt-0.5 text-[11px] text-muted-foreground font-mono">{{ event.details }}</p>

            <!-- Action button -->
            <div v-if="event.actionRequired && event.actionLabel" class="mt-2">
              <button
                @click="handleAction(event)"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-sm font-mono hover:bg-primary/20 transition-colors"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
                {{ event.actionLabel }}
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- Loading indicator at bottom -->
      <div v-if="loading" class="flex justify-center py-4">
        <svg class="h-5 w-5 animate-spin text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error && !events.length" class="flex-1 flex items-center justify-center p-4 text-destructive">
      <svg class="h-6 w-6 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
      {{ error }}
    </div>
  </div>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.625rem;
  font-family: var(--font-mono);
  font-weight: 500;
}
.badge-primary { background: var(--color-primary); color: var(--color-primary-foreground); opacity: 0.15; }
.badge-success { background: var(--color-success); color: var(--color-success); opacity: 0.15; }
.badge-warning { background: var(--color-warning); color: var(--color-warning); opacity: 0.15; }
.badge-destructive { background: var(--color-destructive); color: var(--color-destructive); opacity: 0.15; }
.badge-blue { background: #3b82f6; color: #3b82f6; opacity: 0.15; }
.badge-muted { background: var(--color-muted); color: var(--color-muted-foreground); }
</style>