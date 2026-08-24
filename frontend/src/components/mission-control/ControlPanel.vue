<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  getMegaFastStatus, activateMegaFast, deactivateMegaFast,
  getFirstTimeStatus, activateFirstTime, deactivateFirstTime,
  syncObsidian, runLifeCycle, runStartupChecks,
  getActionRequired, resolveActionRequired,
  runFullCycle, getAutoModules, type AutoModuleInfo,
  getVpnInfo, checkVpnOutlier, installWindscribe, connectWindscribeWindows, type VpnInfo, type WindscribeConnect,
  updateMoneyPlan,
  completeDailyTasksFromState,
  type MegaFastStatus, type FirstTimeStatus, type ActionRequiredItem,
} from '@/services/controlPanel'

const megaFast = ref<MegaFastStatus | null>(null)
const firstTime = ref<FirstTimeStatus | null>(null)
const actions = ref<ActionRequiredItem[]>([])
const startupChecks = ref<Array<{ title: string; status: string; detail?: string }>>([])
const modules = ref<Record<string, AutoModuleInfo>>({})
const vpn = ref<VpnInfo | null>(null)
const vpnSteps = ref<string[]>([])
const vpnAim = ref('')
const busy = ref('')
const loading = ref(true)
const lastRun = ref('')
const lastRunType = ref<'ok' | 'error'>('ok')

async function refreshAll() {
  loading.value = true
  const [mf, ft, acts, checks, modRes, vpnInfo] = await Promise.all([
    getMegaFastStatus(), getFirstTimeStatus(), getActionRequired(), runStartupChecks(), getAutoModules(), getVpnInfo(),
  ])
  megaFast.value = mf
  firstTime.value = ft
  actions.value = acts
  startupChecks.value = checks.checks || []
  modules.value = modRes.modules || {}
  vpn.value = vpnInfo
  loading.value = false
}

async function act(key: string, fn: () => Promise<unknown>) {
  if (busy.value) return
  busy.value = key
  try {
    await fn()
  } finally {
    busy.value = null
  }
  await refreshAll()
}

async function actAndNote(key: string, label: string, fn: () => Promise<unknown>) {
  if (busy.value) return
  busy.value = key
  try {
    await fn()
    lastRun.value = `${label} ejecutado correctamente`
    lastRunType.value = 'ok'
  } catch {
    lastRun.value = `${label} falló`
    lastRunType.value = 'error'
  } finally {
    busy.value = null
  }
  await refreshAll()
}

function moduleCount(): number {
  return Object.keys(modules.value).length
}

async function vpnConnect() {
  const res = await actResult('vpn', connectWindscribeWindows)
  if (res) {
    vpnSteps.value = res.next_steps || []
    vpnAim.value = res.aimed_country || res.country_code || ''
  }
}

async function guidedMax() {
  await actAndNote('gmf', 'Mega Fast', activateMegaFast)
  await actAndNote('gft', 'First-Time', activateFirstTime)
  await updateMoneyPlan({ guided_mode: true, guided_priority: 'max_success' })
  // Marca automáticamente las tareas del día ya resueltas por el sistema
  await completeDailyTasksFromState()
  lastRun.value = 'Modo Guiado Máximo Éxito activado: Mega Fast + First-Time + plan 5h/d'
  lastRunType.value = 'ok'
}

async function actResult<T>(key: string, fn: () => Promise<T>): Promise<T | null> {
  if (busy.value) return null
  busy.value = key
  try {
    return await fn()
  } catch {
    return null
  } finally {
    busy.value = null
  }
}

function checkColor(status: string) {
  return status === 'ok' || status === 'passed' || status === 'healthy'
    ? '#16a34a' : status === 'warning' || status === 'degraded'
      ? '#d97706' : '#00d5ff'
}

onMounted(refreshAll)
</script>

<template>
  <section class="cp">
    <div class="cp-head">
      <h3 class="cp-title">CONTROL PANEL</h3>
      <button class="cp-btn ghost" :disabled="loading" @click="refreshAll">Actualizar</button>
    </div>

    <p v-if="loading" class="cp-muted">Cargando sistema...</p>

    <template v-else>
      <!-- MODOS -->
      <div class="cp-row">
        <div class="cp-card cp-accent">
          <div class="cp-card-head">
            <span class="cp-label">MODO GUIADO · MÁX ÉXITO</span>
          </div>
          <p class="cp-sub">Activa Mega Fast + First-Time + plan 5h/d. OWNEX te lleva de la mano.</p>
          <button class="cp-btn primary" :disabled="!!busy" @click="guidedMax">Iniciar todo</button>
        </div>

        <div class="cp-card">
          <div class="cp-card-head">
            <span class="cp-label">MEGA FAST MODE</span>
            <span class="cp-badge" :style="{ color: megaFast?.active ? '#16a34a' : '#6b7280' }">
              {{ megaFast?.active ? 'ACTIVO' : 'INACTIVO' }}
            </span>
          </div>
          <p v-if="megaFast?.daily_plan?.length" class="cp-sub">
            Plan: {{ megaFast.daily_plan[0] }}
          </p>
          <div class="cp-actions">
            <button class="cp-btn on" @click="act('mega', activateMegaFast)">Activar</button>
            <button class="cp-btn off" @click="act('mega', deactivateMegaFast)">Desactivar</button>
          </div>
        </div>

        <div class="cp-card">
          <div class="cp-card-head">
            <span class="cp-label">FIRST-TIME MODE</span>
            <span class="cp-badge" :style="{ color: firstTime?.active ? '#16a34a' : '#6b7280' }">
              {{ firstTime?.active ? 'ACTIVO' : 'INACTIVO' }}
            </span>
          </div>
          <div class="cp-actions">
            <button class="cp-btn on" @click="act('ft', activateFirstTime)">Activar</button>
            <button class="cp-btn off" @click="act('ft', deactivateFirstTime)">Desactivar</button>
          </div>
        </div>

        <div class="cp-card">
          <div class="cp-card-head">
            <span class="cp-label">SINCRONIZAR OBSIDIAN</span>
          </div>
          <button class="cp-btn on" @click="actAndNote('obs', 'Obsidian', syncObsidian)">Sync memory</button>
          <button class="cp-btn on" @click="actAndNote('life', 'Life', runLifeCycle)">Ciclo vida</button>
          <button class="cp-btn on" @click="actAndNote('checks', 'Chequeos', runStartupChecks)">Chequeos</button>
        </div>
      </div>

      <!-- VPN: acceso a Outlier / DataAnnotation -->
      <div class="cp-card">
        <div class="cp-card-head">
          <span class="cp-label">VPN GRATIS · OUTLIER/DATAANNOTATION</span>
          <span
            class="cp-badge"
            :style="{ color: vpn?.status?.compatible ? '#16a34a' : '#00d5ff' }"
          >
            {{ vpn?.status?.compatible ? 'COMPATIBLE' : 'BLOQUEADO' }}
          </span>
        </div>
        <p v-if="vpn?.status" class="cp-sub">
          IP <span class="cp-ip">{{ vpn.status.public_ip || '—' }}</span>
          · {{ vpn.status.country_name }} ({{ vpn.status.country_code }}) · {{ vpn.status.isp }}
        </p>
        <p class="cp-sub">{{ vpn?.status?.reason || 'Detectando conexión...' }}</p>

        <!-- Qué VPNs te faltan instalar -->
        <div v-if="vpn?.vpns?.length" class="cp-vpns">
          <span class="cp-label">TUS VPNs GRATIS</span>
          <ul class="cp-mod-list">
            <li v-for="v in vpn.vpns" :key="v.key">
              <span class="cp-mod-dot" :class="v.installed ? 'ok' : 'off'" />
              <span class="cp-mod-name">{{ v.name }}</span>
              <span class="cp-mod-status" :style="{ color: v.installed ? '#16a34a' : '#94a3b8' }">
                {{ v.installed ? 'LISTA' : 'FALTA' }}
              </span>
            </li>
          </ul>
        </div>

        <!-- Plan de intercalado -->
        <ol v-if="vpn?.vpn_plan?.length" class="cp-steps cp-plan">
          <li v-for="(s, i) in vpn.vpn_plan" :key="i">{{ s }}</li>
        </ol>

        <p v-if="vpn?.is_wsl" class="cp-warn">
          Estás en WSL2: para Outlier en el navegador, activá Windscribe en el lado Windows.
        </p>
        <div class="cp-actions">
          <button class="cp-btn primary" :disabled="!!busy" @click="vpnConnect">Conectar VPN</button>
          <button class="cp-btn on" @click="act('vchk', checkVpnOutlier)">Chequear</button>
          <button class="cp-btn on" @click="actAndNote('vins', 'Windscribe', installWindscribe)">Instalar CLI</button>
        </div>
        <ol v-if="vpnSteps.length" class="cp-steps">
          <li v-for="(s, i) in vpnSteps" :key="i">{{ s }}</li>
        </ol>
      </div>

      <!-- FULL CYCLE + MODULOS AUTO -->
      <div class="cp-row">
        <div class="cp-card cp-accent">
          <div class="cp-card-head">
            <span class="cp-label">CICLO COMPLETO</span>
          </div>
          <p class="cp-sub">Ejecuta todo el pipeline autónomo: descubrir → validar → reportar → enviar.</p>
          <button class="cp-btn primary" :disabled="!!busy" @click="actAndNote('cycle', 'Ciclo completo', runFullCycle)">
            Ejecutar ahora
          </button>
        </div>
        <div class="cp-card">
          <div class="cp-card-head">
            <span class="cp-label">MODULOS AUTO</span>
            <span class="cp-badge">{{ moduleCount() }} activos</span>
          </div>
          <ul class="cp-mod-list">
            <li v-for="(m, key) in modules" :key="key">
              <span class="cp-mod-dot" :class="m.enabled ? 'ok' : 'off'" />
              <span class="cp-mod-name">{{ m.name }}</span>
              <span class="cp-mod-status">{{ m.enabled ? 'ON' : 'OFF' }}</span>
            </li>
          </ul>
        </div>
      </div>

      <p v-if="lastRun" class="cp-note" :class="lastRunType">{{ lastRun }}</p>

      <!-- STARTUP CHECKS -->
      <div v-if="startupChecks.length" class="cp-block">
        <span class="cp-label">STATE / CHECKLIST</span>
        <ul class="cp-list">
          <li v-for="c in startupChecks" :key="c.title">
            <span class="cp-dot" :style="{ background: checkColor(c.status) }" />
            <span class="cp-item-title">{{ c.title }}</span>
            <span class="cp-item-detail">{{ c.status }}</span>
          </li>
        </ul>
      </div>

      <!-- ACCIONES REQUERIDAS -->
      <div v-if="actions.length" class="cp-block">
        <span class="cp-label">TU ACCIÓN ES NECESARIA</span>
        <ul class="cp-list">
          <li v-for="a in actions" :key="a.action_id || a.id" class="cp-action">
            <div class="cp-action-info">
              <span class="cp-item-title">{{ a.title }}</span>
              <span class="cp-item-detail">{{ a.reason }}</span>
            </div>
            <button class="cp-btn on" @click="act('res' + a.action_id, () => resolveActionRequired(a.action_id))">
              Resolver
            </button>
          </li>
        </ul>
      </div>

      <p v-else class="cp-muted keep">No hay acciones pendientes que requieran tu atención.</p>
    </template>

    <p class="cp-note" :aria-busy="!!busy">{{ busy ? 'Procesando ' + busy + '...' : '' }}</p>  </section>
</template>

<style scoped>
.cp {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.cp-head { display: flex; align-items: center; gap: 0.75rem; }
.cp-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.cp-head .cp-btn { margin-left: auto; }
.cp-muted { font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); margin: 0; }
.cp-muted.keep { font-size: 0.7rem; }
.cp-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.6rem;
}
.cp-card {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 0.6rem 0.7rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.cp-card-head { display: flex; align-items: center; justify-content: space-between; gap: 0.4rem; }
.cp-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255, 255, 255, 0.45); }
.cp-badge { font-size: 0.6rem; font-weight: 700; }
.cp-actions, .cp-card .cp-actions { display: flex; gap: 0.4rem; }
.cp-btn {
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.35rem 0.6rem;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.cp-btn:hover { opacity: 0.85; }
.cp-btn.on { border-color: rgba(22, 163, 74, 0.4); color: #4ade80; }
.cp-btn.off { border-color: rgba(0, 213, 255, 0.4); color: #94a3b8; }
.cp-btn.primary { border-color: rgba(0, 213, 255, 0.5); color: #fecaca; background: rgba(0, 213, 255, 0.12); width: 100%; }
.cp-accent { border-color: rgba(0, 213, 255, 0.25); }
.cp-sub { font-size: 0.68rem; color: rgba(255, 255, 255, 0.55); margin: 0; line-height: 1.4; }
.cp-mod-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.3rem; }
.cp-mod-list li { display: flex; align-items: center; gap: 0.45rem; font-size: 0.72rem; }
.cp-mod-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.cp-mod-dot.ok { background: #16a34a; }
.cp-mod-dot.off { background: #6b7280; }
.cp-mod-name { font-weight: 600; color: rgba(255, 255, 255, 0.85); }
.cp-mod-status { margin-left: auto; font-size: 0.6rem; font-weight: 700; color: #16a34a; }
.cp-ip { font-family: var(--font-mono, monospace); color: #93c5fd; }
.cp-warn { font-size: 0.66rem; color: #fbbf24; margin: 0; line-height: 1.4; }
.cp-steps { margin: 0.3rem 0 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: 0.25rem; }
.cp-steps li { font-size: 0.68rem; color: rgba(255, 255, 255, 0.7); line-height: 1.4; }
.cp-vpns { display: flex; flex-direction: column; gap: 0.3rem; }
.cp-plan { border: 1px solid rgba(251, 191, 36, 0.25); border-radius: 8px; padding: 0.5rem 0.8rem 0.5rem 1.4rem; background: rgba(251, 191, 36, 0.05); }
.cp-plan li { color: rgba(255, 255, 255, 0.8); }
.cp-note.ok { color: #4ade80; }
.cp-note.error { color: #94a3b8; }
.cp-btn:disabled { opacity: 0.4; cursor: default; }
.cp-block { display: flex; flex-direction: column; gap: 0.4rem; }
.cp-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 0.35rem;
}
.cp-list li {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 0.75rem; padding: 0.3rem 0.4rem;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}
.cp-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.cp-item-title { font-weight: 600; color: rgba(255, 255, 255, 0.9); }
.cp-item-detail { margin-left: auto; font-size: 0.65rem; color: rgba(255, 255, 255, 0.45); }
.cp-action { justify-content: space-between; }
.cp-action-info { display: flex; flex-direction: column; gap: 0.1rem; }
.cp-action-info .cp-item-detail { margin-left: 0; }
.cp-banner { min-height: 1.1rem; font-size: 0.7rem; color: #4ade80; margin: 0; }
.keep { margin-top: 0.1rem; }
</style>