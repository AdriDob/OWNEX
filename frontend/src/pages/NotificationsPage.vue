<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'
import type { Notification } from '@/stores/notifications'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart } from '@/components/charts'
import {
  AlertCircle, AlertTriangle, BarChart3, Bell, BellOff, CheckCheck,
  CheckCircle2, Filter, Info, Trash2, X,
} from '@lucide/vue'

const store = useNotificationsStore()
const filterType = ref<string | null>(null)

onMounted(() => {
  store.connectWs()
})

const typeIcon = computed(() => ({
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: AlertCircle,
}))

const typeVariant = computed(() => ({
  info: 'info' as const,
  success: 'success' as const,
  warning: 'warning' as const,
  error: 'destructive' as const,
}))

const typeCounts = computed(() => {
  const counts: Record<string, number> = { info: 0, success: 0, warning: 0, error: 0 }
  for (const n of store.notifications) {
    counts[n.type] = (counts[n.type] || 0) + 1
  }
  return counts
})

const chartData = computed(() => ({
  labels: ['Info', 'Success', 'Warning', 'Error'],
  datasets: [{
    label: 'Notificaciones',
    data: [typeCounts.value.info, typeCounts.value.success, typeCounts.value.warning, typeCounts.value.error],
    backgroundColor: ['rgba(59,130,246,0.7)', 'rgba(34,197,94,0.7)', 'rgba(234,179,8,0.7)', 'rgba(239,68,68,0.7)'],
  }],
}))

const filteredNotifications = computed(() => {
  if (!filterType.value) return store.notifications
  return store.notifications.filter(n => n.type === filterType.value)
})

const filteredGrouped = computed(() => {
  if (!filterType.value) return store.groupedByDate
  const groups: { label: string; items: Notification[] }[] = []
  for (const group of store.groupedByDate) {
    const items = group.items.filter(n => n.type === filterType.value)
    if (items.length > 0) {
      groups.push({ label: group.label, items })
    }
  }
  return groups
})

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between animate-in">
      <div class="min-w-0">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Notifications</p>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Centro de Notificaciones</h1>
        <p class="text-sm text-muted-foreground">
          {{ store.unreadCount > 0 ? `${store.unreadCount} sin leer` : 'Todas leídas' }}
          · {{ store.notifications.length }} total
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <Button v-if="store.unreadCount > 0" variant="ghost" size="sm" @click="store.markAllRead()">
          <CheckCheck class="h-3.5 w-3.5" /> Marcar todas leídas
        </Button>
        <Button v-if="store.notifications.length > 0" variant="ghost" size="sm" @click="store.clearAll()">
          <Trash2 class="h-3.5 w-3.5" /> Limpiar todo
        </Button>
      </div>
    </div>

    <Card class="p-4 animate-in">
      <div class="flex items-center gap-2 mb-3">
        <BarChart3 class="h-4 w-4 text-primary" />
        <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Volumen por Tipo</span>
      </div>
      <BarChart
        :labels="chartData.labels"
        :datasets="chartData.datasets"
        :height="180"
        yLabel="Cantidad"
        :show-legend="false"
      />
    </Card>

    <div class="flex items-center gap-2 animate-in">
      <Filter class="h-4 w-4 text-muted-foreground" />
      <span class="text-xs text-muted-foreground font-semibold">Filtrar:</span>
      <button
        v-for="t in ['info', 'success', 'warning', 'error']" :key="t"
        @click="filterType = filterType === t ? null : t"
        :class="[
          'rounded-lg px-3 py-1.5 text-xs font-semibold transition-all',
          filterType === t
            ? 'bg-primary/20 text-primary ring-1 ring-primary/30'
            : 'bg-surface/50 text-muted-foreground hover:text-foreground hover:bg-surface',
        ]"
      >
        {{ t.charAt(0).toUpperCase() + t.slice(1) }}
      </button>
      <button v-if="filterType" @click="filterType = null" class="text-xs text-muted-foreground hover:text-foreground ml-1">
        <X class="h-3.5 w-3.5 inline" /> Limpiar
      </button>
    </div>

    <template v-if="store.notifications.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <BellOff class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Sin notificaciones</p>
        <p class="mt-1 text-xs text-muted-foreground">No hay notificaciones para mostrar</p>
      </div>
    </template>

    <template v-else>
      <div v-for="group in filteredGrouped" :key="group.label" class="animate-in">
        <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-1">{{ group.label }}</p>
        <div class="space-y-1">
          <div
            v-for="n in group.items" :key="n.id"
            class="group flex items-start gap-3 rounded-xl p-3 transition-colors cursor-pointer"
            :class="n.read ? 'bg-transparent hover:bg-surface/30' : 'bg-surface/40 hover:bg-surface/60'"
            @click="store.markRead(n.id)"
          >
            <div class="mt-0.5 shrink-0">
              <component
                :is="typeIcon[n.type]"
                :class="[
                  'h-4 w-4',
                  n.type === 'error' ? 'text-destructive' : n.type === 'warning' ? 'text-warning' : n.type === 'success' ? 'text-success' : 'text-accent',
                ]"
              />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold" :class="n.read ? 'text-muted-foreground' : 'text-foreground'">{{ n.title }}</span>
                <Badge :variant="typeVariant[n.type]" class="text-[9px] px-1.5 py-0">{{ n.type }}</Badge>
              </div>
              <p class="text-xs text-muted-foreground/70 mt-0.5">{{ n.message }}</p>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-[10px] text-muted-foreground/50">{{ formatTime(n.timestamp) }}</span>
                <span v-if="n.source" class="text-[10px] text-muted-foreground/50">· {{ n.source }}</span>
              </div>
              <div v-if="n.action" class="mt-1">
                <Button variant="link" size="sm" class="h-auto p-0 text-xs text-accent" @click.stop>
                  {{ n.action.label }}
                </Button>
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                v-if="!n.read"
                @click.stop="store.markRead(n.id)"
                class="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-surface"
                title="Marcar leída"
              >
                <CheckCheck class="h-3.5 w-3.5" />
              </button>
              <button
                @click.stop="store.remove(n.id)"
                class="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                title="Eliminar"
              >
                <X class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
