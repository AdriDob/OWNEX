<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCompanion } from '@/composables/useCompanion'
import { useToast } from '@/composables/useToast'
import { Activity, Bell, BellOff, CheckCircle2, Clock, RefreshCw, Smartphone } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const { toast } = useToast()
const companion = useCompanion()
const pushSupported = ref(false)
const pushEnabled = ref(false)
const swRegistration = ref<ServiceWorkerRegistration | null>(null)

const statusEntries = computed(() => {
  const s = companion.status.value
  if (!s || !Object.keys(s).length) return []
  return [
    { label: 'Findings totales', value: s.findings_total ?? '—' },
    { label: 'Confirmados', value: s.findings_confirmed ?? '—' },
    { label: 'Pendientes', value: s.findings_pending ?? '—' },
    { label: 'Targets activos', value: s.targets_active ?? '—' },
    { label: 'Scheduler', value: s.scheduler_running ? 'Activo' : 'Detenido', ok: s.scheduler_running },
    { label: 'Próxima acción', value: s.next_action || '—' },
  ]
})

onMounted(async () => {
  companion.startPolling(120_000)

  if ('serviceWorker' in navigator && 'PushManager' in window) {
    pushSupported.value = true
    try {
      swRegistration.value = await navigator.serviceWorker.ready
      const sub = await swRegistration.value.pushManager.getSubscription()
      pushEnabled.value = !!sub
    } catch { /* push not available */ }
  }
})

onUnmounted(() => {
  companion.stopPolling()
})

async function togglePush() {
  if (!swRegistration.value) return
  try {
    if (pushEnabled.value) {
      const sub = await swRegistration.value.pushManager.getSubscription()
      if (sub) await sub.unsubscribe()
      pushEnabled.value = false
      toast.success('Notificaciones', 'Push desactivado')
    } else {
      const sub = await swRegistration.value.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: null, // TODO: configure VAPID key for production push
      })
      const body = JSON.parse(JSON.stringify(sub))
      await fetch('/api/mobile/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      pushEnabled.value = true
      toast.success('Notificaciones', 'Push activado')
    }
  } catch (e: any) {
    toast.error('Error', e?.message || 'No se pudo configurar push')
  }
}
</script>

<template>
  <div class="p-6 space-y-6 animate-in">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
          <Smartphone class="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight text-foreground">Companion</h1>
          <p class="text-xs text-muted-foreground">Estado del Companion móvil y polling</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button size="sm" variant="outline" @click="companion.pollStatus()">
          <RefreshCw class="h-3.5 w-3.5" /> Poll ahora
        </Button>
        <Button v-if="pushSupported" size="sm" :variant="pushEnabled ? 'default' : 'outline'" @click="togglePush">
          <Bell v-if="pushEnabled" class="h-3.5 w-3.5 mr-1" />
          <BellOff v-else class="h-3.5 w-3.5 mr-1" />
          {{ pushEnabled ? 'Push activo' : 'Activar push' }}
        </Button>
      </div>
    </div>

    <div v-if="companion.lastPoll.value" class="text-xs text-muted-foreground font-mono">
      Último poll: {{ new Date(companion.lastPoll.value).toLocaleTimeString() }}
    </div>

    <div v-if="!Object.keys(companion.status.value).length" class="space-y-3">
      <Skeleton v-for="i in 4" :key="i" class="h-14 rounded-xl" />
    </div>
    <div v-else>
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="e in statusEntries" :key="e.label"
          class="flex items-center justify-between rounded-xl border border-border/30 bg-surface/30 px-4 py-3"
        >
          <span class="font-mono text-xs text-muted-foreground">{{ e.label }}</span>
          <div class="flex items-center gap-2">
            <span class="font-mono text-sm font-medium text-foreground">{{ e.value }}</span>
            <CheckCircle2 v-if="e.ok" class="h-3.5 w-3.5 text-success" />
            <Clock v-else-if="e.ok === false" class="h-3.5 w-3.5 text-warning" />
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-border/30 bg-surface/30 p-4 space-y-2">
        <h3 class="font-mono text-xs font-semibold text-foreground uppercase tracking-wider">Polling info</h3>
        <p class="text-xs text-muted-foreground">
          El Companion pollea <code class="text-primary">/api/mobile/status</code> cada 2 minutos.
          Las notificaciones push requieren HTTPS o localhost.
        </p>
      </div>
    </div>
  </div>
</template>
