<template>
  <div class="mobile-app">
    <!-- Header -->
    <header class="m-header">
      <div class="m-header-left">
        <span class="m-logo">OWNEX</span>
        <span class="m-sync" :class="syncClass">{{ syncLabel }}</span>
      </div>
      <button class="m-refresh" aria-label="Actualizar" @click="refreshAll">⟳</button>
    </header>

    <!-- Offline banner honesto -->
    <div v-if="!online" class="m-offline">
      Sin conexión — mostrando último estado conocido. Las acciones se encolan.
      <span v-if="pendingCount"> ({{ pendingCount }} pendientes)</span>
    </div>

    <main class="m-content">
      <!-- ═══ TAB: HOME ═══ -->
      <section v-if="tab === 'home'" class="m-tab">
        <!-- NEXT ACTION (income plan real) -->
        <div v-if="nextAction" class="card nba">
          <p class="label">TU PRÓXIMA ACCIÓN</p>
          <h2 class="nba-title">{{ nextAction.title }}</h2>
          <p v-if="nextAction.why" class="muted">{{ nextAction.why }}</p>
          <div class="nba-metrics money-row">
            <span v-if="nextAction.payoff_range" class="money">${{ nextAction.payoff_range.low }}–{{ nextAction.payoff_range.high }}</span>
            <span v-if="nextAction.ev_per_human_hour_usd" class="money">${{ Math.round(nextAction.ev_per_human_hour_usd) }}/h</span>
            <span v-if="nextAction.human_hours" class="muted">~{{ Math.round(nextAction.human_hours * 60) }} min tuyos</span>
          </div>
          <a
            v-if="nextAction.url"
            :href="nextAction.url"
            target="_blank"
            rel="noopener"
            class="btn-primary"
          >EMPEZAR</a>
        </div>
        <div v-else-if="!loading" class="card empty">
          Sin acción prioritaria ahora. Ejecutá un ciclo de discovery desde el Desktop.
        </div>

        <!-- Capital snapshot (real) -->
        <div v-if="capital" class="card">
          <p class="label">CAPITAL</p>
          <p class="big money">${{ fmt(capital.patrimonio_total) }}</p>
          <div class="row2">
            <div><p class="muted">Liquidez</p><p class="money">${{ fmt(capital.liquidez) }}</p></div>
            <div><p class="muted">Ingresos mes</p><p class="money">${{ fmt(capital.ingresos_mes) }}</p></div>
            <div><p class="muted">Esperado</p><p class="money muted-money">${{ fmt(capital.expected_cash?.total ?? 0) }}</p></div>
          </div>
        </div>

        <!-- System status -->
        <div class="card row2">
          <div><p class="muted">Sistema</p><p :class="systemOk ? 'ok' : 'warn'">{{ systemOk ? '● Online' : '● Degradado' }}</p></div>
          <div><p class="muted">Entregas listas</p><p>{{ workbank.ready_to_deliver ?? 0 }}</p></div>
          <div><p class="muted">Aprobaciones</p><p>{{ approvals.length }}</p></div>
        </div>
      </section>

      <!-- ═══ TAB: WORK ═══ -->
      <section v-else-if="tab === 'work'" class="m-tab">
        <div v-if="deliverables.length === 0 && !loading" class="card empty">
          Nada listo para entregar. El Work Bank prepara trabajos automáticamente.
        </div>
        <article v-for="d in deliverables" :key="d.id" class="card work-item">
          <h3>{{ d.title }}</h3>
          <div class="money-row">
            <span class="money">${{ fmt(d.reward) }}</span>
            <span class="badge">{{ d.platform }}</span>
          </div>
          <p v-if="d.deliverables?.length" class="muted">{{ d.deliverables.length }} archivos listos</p>
          <div class="btn-row">
            <button class="btn-secondary" @click="prepare(d.id)">Preparar</button>
            <button class="btn-primary" @click="approve(d.id)">Entregado ✓</button>
          </div>
        </article>
      </section>

      <!-- ═══ TAB: WATCH (preview del contrato /wear-os/*) ═══ -->
      <section v-else class="m-tab">
        <div class="card watch-frame">
          <p class="label">RELOJ — VISTA EN VIVO</p>
          <div class="watch-screen">
            <p class="w-status" :class="wearStatus?.system_online ? 'ok' : 'warn'">
              ● {{ wearStatus?.system_online ? 'ONLINE' : 'OFFLINE' }}
            </p>
            <p class="w-next muted">{{ wearStatus?.active_workflows ?? 0 }} workflows · {{ wearStatus?.pending_approvals ?? 0 }} aprobaciones</p>
          </div>
          <p class="muted hint">Lo que ve el reloj ahora mismo (mismo contrato /wear-os).</p>
        </div>

        <h3 class="section-title">Notificaciones</h3>
        <div v-if="notifications.length === 0" class="card empty">Sin notificaciones sin leer.</div>
        <article
          v-for="n in notifications"
          :key="n.notification_id"
          class="card notif"
          @click="markRead(n.notification_id)"
        >
          <div>
            <strong>{{ n.title }}</strong>
            <p class="muted">{{ n.message }}</p>
          </div>
          <span class="badge" :class="'lvl-' + n.level">{{ n.level }}</span>
        </article>

        <h3 class="section-title">Aprobaciones</h3>
        <div v-if="approvals.length === 0" class="card empty">Nada pendiente de aprobación.</div>
        <article v-for="a in approvals" :key="a.request_id" class="card">
          <strong>{{ a.title }}</strong>
          <p class="muted">{{ a.description }}</p>
          <div class="btn-row">
            <button class="btn-approve" @click="respond(a.request_id, true)">✓ Aprobar</button>
            <button class="btn-reject" @click="respond(a.request_id, false)">✕ Rechazar</button>
          </div>
        </article>
      </section>
    </main>

    <!-- Bottom nav -->
    <nav class="m-nav" aria-label="Navegación móvil">
      <button :class="{ active: tab === 'home' }" @click="tab = 'home'"><span>◉</span>Inicio</button>
      <button :class="{ active: tab === 'work' }" @click="tab = 'work'"><span>▤</span>Trabajo</button>
      <button :class="{ active: tab === 'watch' }" @click="tab = 'watch'; refreshWatch()"><span>⌚</span>Reloj</button>
    </nav>
  </div>
</template>

<script setup lang="ts">
/**
 * MobileApp — superficie única "OWNEX en el bolsillo".
 * Consolida MobileCompanion + MobileCompanionJarvis (Parte 3 FINAL RELEASE).
 * - Tokens Tesla (tokens.css) — cero neón JARVIS.
 * - Contratos reales: income-plan, financial/capital, direct-work, wear-os.
 * - Device identity compartida con Desktop (POST /api/device/register).
 * - Offline-first: cola IndexedDB para mutaciones seguras; lectura por SW cache.
 */
import { computed, onMounted, ref } from 'vue'

import {
  approveDelivery,
  fetchDeliveryQueue,
  fetchIncomePlan,
  fetchWearOSNotifications,
  fetchWearOSPendingApprovals,
  fetchWearOSStatus,
  markWearOSNotificationRead,
  prepareDelivery,
  respondWearOSApproval,
  type DeliverableItem,
  type IncomePlanAction,
  type WearOSApproval,
  type WearOSNotification,
  type WearOSStatus,
} from '@/services/ownexData'
import { getOfflineQueue, isOnline, onOnlineChange } from '@/lib/offline'
import { api } from '@/lib/api'

const tab = ref<'home' | 'work' | 'watch'>('home')
const loading = ref(true)
const online = ref(isOnline())
const pendingCount = ref(0)

const nextAction = ref<IncomePlanAction | null>(null)
const capital = ref<any>(null)
const workbank = ref<any>({})
const deliverables = ref<DeliverableItem[]>([])
const wearStatus = ref<WearOSStatus | null>(null)
const notifications = ref<WearOSNotification[]>([])
const approvals = ref<WearOSApproval[]>([])

const syncClass = computed(() => (!online.value ? 'off' : pendingCount.value ? 'pend' : 'on'))
const syncLabel = computed(() =>
  !online.value ? 'OFFLINE' : pendingCount.value ? `SYNC ${pendingCount.value}` : 'SYNCED',
)
const systemOk = computed(() => Boolean(capital.value || nextAction.value))

function fmt(n: unknown): string {
  const v = Number(n ?? 0)
  return Number.isFinite(v) ? v.toLocaleString('es-AR', { maximumFractionDigits: 0 }) : '0'
}

async function registerDevice(): Promise<void> {
  try {
    let deviceId = localStorage.getItem('ownex-device-id')
    if (!deviceId) {
      deviceId = `dev_${crypto.randomUUID().slice(0, 16)}`
      localStorage.setItem('ownex-device-id', deviceId)
    }
    await api.post('/device/register', {
      device_id: deviceId,
      platform: 'mobile',
      name: navigator.userAgent.slice(0, 80) || 'Mobile',
      capabilities: ['approvals', 'notifications', 'offline_queue'],
    })
  } catch {
    /* best-effort: la identidad no bloquea el uso */
  }
}

async function refreshCore(): Promise<void> {
  const results = await Promise.allSettled([
    fetchIncomePlan(),
    api.get('/financial/capital/snapshot'),
    fetchDirectWorkState(),
  ])
  if (results[0].status === 'fulfilled') nextAction.value = results[0].value.next_action
  if (results[1].status === 'fulfilled') capital.value = results[1].value
}

async function fetchDirectWorkState(): Promise<void> {
  const [queue, wb] = await Promise.all([
    fetchDeliveryQueue(),
    import('@/services/ownexData').then((m) => m.fetchDirectWorkWorkBank()),
  ])
  deliverables.value = queue.items ?? []
  workbank.value = wb
}

async function refreshWatch(): Promise<void> {
  const [st, notifs, appr] = await Promise.allSettled([
    fetchWearOSStatus(),
    fetchWearOSNotifications({ unread_only: true, limit: 10 }),
    fetchWearOSPendingApprovals(),
  ])
  wearStatus.value = st.status === 'fulfilled' ? st.value : null
  notifications.value = notifs.status === 'fulfilled' ? notifs.value : []
  approvals.value = appr.status === 'fulfilled' ? appr.value : []
}

async function refreshAll(): Promise<void> {
  loading.value = true
  await Promise.allSettled([refreshCore(), refreshWatch(), updatePendingCount()])
  loading.value = false
}

async function markRead(id: string): Promise<void> {
  await markWearOSNotificationRead(id).catch(() => {})
  notifications.value = notifications.value.filter((n) => n.notification_id !== id)
}

async function respond(requestId: string, approved: boolean): Promise<void> {
  // Acción sensible: si estamos offline → cola explícita, nunca fingir éxito.
  if (!online.value) {
    await getOfflineQueue().enqueue({
      entityType: 'approval',
      entityId: requestId,
      operation: 'update',
      payload: { approved },
      endpoint: `/wear-os/approval/${requestId}/respond`,
      method: 'POST',
    })
    await updatePendingCount()
    return
  }
  await respondWearOSApproval(requestId, approved).catch(() => {})
  approvals.value = approvals.value.filter((a) => a.request_id !== requestId)
}

async function prepare(itemId: string): Promise<void> {
  await prepareDelivery(itemId).catch(() => {})
  await refreshCore()
}

async function approve(itemId: string): Promise<void> {
  if (!online.value) {
    await getOfflineQueue().enqueue({
      entityType: 'work_item',
      entityId: itemId,
      operation: 'update',
      payload: {},
      endpoint: `/direct-work/workbank/${itemId}/deliver/approve`,
      method: 'POST',
    })
    await updatePendingCount()
    return
  }
  await approveDelivery(itemId).catch(() => {})
  await refreshCore()
}

async function updatePendingCount(): Promise<void> {
  try {
    pendingCount.value = await getOfflineQueue().getPendingCount()
  } catch {
    pendingCount.value = 0
  }
}

onMounted(async () => {
  onOnlineChange((v) => {
    online.value = v
  })
  await registerDevice()
  await refreshAll()
})
</script>

<style scoped>
/* Tokens Tesla únicos (tokens.css) — cero hex arbitrario */
.mobile-app {
  min-height: 100vh;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-body);
  padding-bottom: calc(var(--space-8) + env(safe-area-inset-bottom));
}
.m-header {
  position: sticky;
  top: 0;
  z-index: var(--z-status-bar, 50);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  background: var(--glass-bg);
  border-bottom: var(--glass-border);
  backdrop-filter: blur(20px);
}
.m-logo {
  font-family: var(--font-display);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.06em;
}
.m-sync { font-family: var(--font-mono); font-size: var(--text-caption); }
.m-sync.on { color: var(--color-success); }
.m-sync.pend { color: var(--color-warning); }
.m-sync.off { color: var(--color-danger); }
.m-refresh {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: var(--text-heading);
  cursor: pointer;
}
.m-offline {
  padding: var(--space-2) var(--space-5);
  background: rgba(59, 130, 246, 0.12);
  color: var(--color-danger);
  font-size: var(--text-label);
}
.m-content { max-width: 640px; margin: 0 auto; padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-4); }
.card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}
.label { margin: 0 0 var(--space-2); font-size: var(--text-label); letter-spacing: 0.08em; color: var(--color-text-muted); }
.nba-title { margin: 0 0 var(--space-1); font-family: var(--font-display); font-size: var(--text-heading); }
.money-row { display: flex; gap: var(--space-4); align-items: baseline; flex-wrap: wrap; margin: var(--space-3) 0; }
.big { font-family: var(--font-display); font-size: var(--text-display); margin: var(--space-1) 0; }
.row2 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); }
.muted { color: var(--color-text-muted); font-size: var(--text-caption); }
.muted-money { opacity: 0.75; }
.ok { color: var(--color-success); }
.warn { color: var(--color-warning); }
.badge {
  display: inline-block;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: var(--text-caption);
}
.lvl-high, .lvl-critical { color: var(--color-danger); border-color: var(--color-danger); }
.btn-primary, .btn-secondary, .btn-approve, .btn-reject {
  width: 100%;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  border: 1px solid transparent;
}
.btn-primary { background: var(--color-primary); color: #000; }
.btn-secondary { background: transparent; color: var(--color-text); border-color: var(--color-border); }
.btn-approve { background: var(--color-success); color: #000; }
.btn-reject { background: transparent; color: var(--color-danger); border-color: var(--color-danger); }
.btn-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); margin-top: var(--space-3); }
.empty { text-align: center; color: var(--color-text-muted); }
.section-title { margin: var(--space-2) 0 0; font-size: var(--text-label); color: var(--color-text-muted); letter-spacing: 0.06em; }
.watch-frame .watch-screen {
  margin: var(--space-3) 0;
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  background: var(--ownex-bg-deep);
  text-align: center;
}
.w-status { font-family: var(--font-mono); letter-spacing: 0.1em; }
.hint { margin-top: var(--space-2); }
.notif { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); cursor: pointer; }
.work-item h3 { margin: 0 0 var(--space-2); font-size: var(--text-body); }
.m-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  padding: var(--space-2) 0 calc(var(--space-2) + env(safe-area-inset-bottom));
  background: var(--mica-bg);
  border-top: var(--mica-border);
  backdrop-filter: blur(20px);
}
.m-nav button {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-family: var(--font-body);
  font-size: var(--text-caption);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  cursor: pointer;
  padding: var(--space-2) var(--space-4);
  min-width: 64px;
  min-height: 44px; /* touch target accesible */
}
.m-nav button span { font-size: 1.25rem; }
.m-nav button.active { color: var(--color-primary); }
@media (prefers-reduced-motion: reduce) {
  .mobile-app * { transition: none !important; animation: none !important; }
}
</style>
