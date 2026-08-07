<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getDailyTasks, completeDailyTasksFromState, getVpnInfo, getActionRequired,
  activateMegaFast, activateFirstTime, updateMoneyPlan,
  type DailyTasksResult, type VpnInfo, type ActionRequiredItem,
} from '@/services/controlPanel'

const tasksResult = ref<DailyTasksResult>({})
const vpnInfo = ref<VpnInfo>({})
const actions = ref<ActionRequiredItem[]>([])
const loading = ref(true)
const busy = ref('')
const note = ref('')

onMounted(async () => {
  loading.value = true
  try {
    const [t, v, a] = await Promise.all([getDailyTasks(), getVpnInfo(), getActionRequired()])
    tasksResult.value = t
    vpnInfo.value = v
    actions.value = a
  } finally {
    loading.value = false
  }
})

const steps = computed(() => {
  const t = tasksResult.value
  const vpn = vpnInfo.value
  const acts = actions.value
  const dayTasks: Array<{ id: string; label: string; done: boolean }> = (t.tasks ?? []).map(task => {
    let label = task.title
    if (task.id === 'github_profile') label = 'Vincular perfil de GitHub'
    else if (task.id === 'portfolio_repo') label = 'Crear repo portfolio'
    else if (task.id === 'gh_token') label = 'Configurar GITHUB_TOKEN'
    else if (task.id === 'money_plan') label = 'Definir plan de plata objetivo'
    else if (task.id === 'platform_select') label = 'Elegir plataformas de inicio'
    else if (task.id === 'dev_bounty') label = 'Activar Dev Bounty Autopilot'
    return { id: task.id, label, done: task.status === 'done' }
  })

  return [
    {
      key: 'github',
      label: 'Vincular perfil de GitHub',
      done: t.github_linked === true,
      sub: 'OWNEX auto-push de bounties validados.',
    },
    {
      key: 'repo',
      label: 'Crear repo portfolio',
      done: !!t.portfolio_ready,
      sub: 'usuario/repo público y pinneado.',
    },
    {
      key: 'token',
      label: 'GITHUB_TOKEN (scope repo)',
      done: !!t.token_ready,
      sub: 'Almacenado en vault/.env con Vault Lock.',
    },
    {
      key: 'vpn',
      label: 'VPN gratis (Outlier/DataAnnotation)',
      done: vpn?.status?.compatible === true,
      sub: vpn?.status?.reason || 'Detectando conexión...',
    },
    {
      key: 'money',
      label: 'Definir plan de plata objetivo',
      done: !!t.money_plan_set,
      sub: 'Objetivo: $500-1K/semana guiado max éxito.',
    },
    {
      key: 'bounty',
      label: 'Activar Dev Bounty Autopilot',
      done: !!t.dev_bounty_active,
      sub: 'OWNEY propone + tú validas (nunca auto-submit).',
    },
    ...dayTasks.map(dt => ({
      key: `t_${dt.id}`,
      label: dt.label,
      done: dt.done,
      sub: 'Tarea guiada del día 1',
    })),
  ]
})

const progress = computed(() => {
  const s = steps.value
  const done = s.filter(x => x.done).length
  return Math.round((done / Math.max(s.length, 1)) * 100)
})

async function startAll() {
  if (busy.value) return
  busy.value = 'start'
  note.value = ''
  try {
    await activateMegaFast()
    await activateFirstTime()
    await updateMoneyPlan({ guided_mode: true, guided_priority: 'max_success' })
    await completeDailyTasksFromState()
    await getDailyTasks(true)
    await getVpnInfo()
    await getActionRequired()
    note.value = 'Modo Guiado Máximo Éxito activado: Mega Fast + First-Time + plan 5h/d.'
  } catch {
    note.value = 'Algún paso falló. Revisa las alertas.'
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <section class="wg">
    <div class="wg-head">
      <div class="wg-greeting">
        <span class="wg-wave">👋</span>
        <span class="wg-name">{{ vpnInfo.status?.isp ? `Operador ${vpnInfo.status.isp}` : 'Buenas, Operador' }}</span>
      </div>
      <span class="wg-day">Día 1 · Bienvenido a OWNEX</span>
    </div>

    <p v-if="loading" class="wg-muted">Preparando tu primer día...</p>

    <template v-else>
      <p class="wg-msg">Te guío paso a paso. OWNEX activa todo, vos validás cada hito.</p>

      <div class="wg-progress">
        <div class="wg-bar"><div class="wg-fill" :style="{ width: `${progress}%` }"></div></div>
        <span class="wg-pct">{{ progress }}% · {{ steps.filter(s => s.done).length }}/{{ steps.length }} listos</span>
      </div>

      <div class="wg-steps">
        <div
          v-for="(s, i) in steps"
          :key="s.key"
          class="wg-step"
          :class="{ done: s.done }"
        >
          <div class="wg-step-head">
            <span class="wg-step-num">{{ i + 1 }}</span>
            <span class="wg-step-icon" :style="{ color: s.done ? '#16a34a' : '#4ade80' }">
              {{ s.done ? '✓' : '○' }}
            </span>
            <span class="wg-step-label">{{ s.label }}</span>
          </div>
          <p class="wg-step-sub">{{ s.sub }}</p>
        </div>
      </div>

      <div class="wg-actions">
        <button class="wg-btn primary" :disabled="!!busy" @click="startAll">
          {{ busy ? 'Activando...' : '¡Manos a la obra!' }}
        </button>
      </div>

      <p v-if="note" class="wg-note">{{ note }}</p>

      <div v-if="actions.length" class="wg-alert">
        <span class="wg-alert-icon">⚠️</span>
        <span class="wg-alert-text">{{ actions[0].title }}: {{ actions[0].reason }}</span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.wg {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(96,165,250,0.04) 0%, rgba(22,132,54,0.03) 100%);
  padding: 1.1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.wg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.wg-greeting {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}
.wg-wave {
  font-size: 1.1rem;
}
.wg-name {
  font-weight: 700;
  font-size: 0.8rem;
  color: rgba(255,255,255,0.9);
}
.wg-day {
  font-size: 0.62rem;
  font-weight: 700;
  color: #93c5fd;
  background: rgba(96,165,250,0.12);
  border: 1px solid rgba(96,165,250,0.3);
  border-radius: 6px;
  padding: 0.18rem 0.5rem;
}
.wg-muted {
  font-size: 0.72rem;
  color: rgba(255,255,255,0.5);
  margin: 0;
}
.wg-msg {
  font-size: 0.72rem;
  color: rgba(255,255,255,0.8);
  margin: 0;
  line-height: 1.5;
}
.wg-progress {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.25rem;
}
.wg-bar {
  flex: 1;
  height: 8px;
  background: rgba(255,255,255,0.08);
  border-radius: 4px;
  overflow: hidden;
}
.wg-fill {
  height: 100%;
  background: linear-gradient(90deg, #16a34a, #4ade80);
  border-radius: 4px;
  transition: width 0.35s ease;
}
.wg-pct {
  font-size: 0.62rem;
  color: rgba(255,255,255,0.6);
  white-space: nowrap;
}
.wg-steps {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.1rem;
}
.wg-step {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.06);
  border-left: 3px solid rgba(96,165,250,0.35);
  border-radius: 11px;
  padding: 0.6rem 0.75rem;
  transition: all 0.2s;
}
.wg-step.done {
  border-left-color: #16a34a;
  opacity: 0.7;
}
.wg-step.done .wg-step-label {
  text-decoration: line-through;
}
.wg-step-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.wg-step-num {
  font-size: 0.6rem;
  font-weight: 700;
  color: #93c5fd;
  background: rgba(96,165,250,0.12);
  border-radius: 50%;
  width: 19px;
  height: 19px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.wg-step-icon {
  font-size: 0.85rem;
  flex-shrink: 0;
}
.wg-step-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
  flex: 1;
}
.wg-step-sub {
  font-size: 0.6rem;
  color: rgba(255,255,255,0.42);
  margin: 0.2rem 0 0 0;
  line-height: 1.4;
}
.wg-actions {
  margin-top: 0.15rem;
}
.wg-btn {
  border: none;
  border-radius: 11px;
  padding: 0.55rem 1.1rem;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s;
}
.wg-btn.primary {
  background: linear-gradient(135deg, #16a34a, #15803d);
  color: #fff;
  box-shadow: 0 0 0 0 rgba(22,132,54,0.45);
}
.wg-btn.primary:hover:not(:disabled) {
  box-shadow: 0 0 12px 5px rgba(22,132,54,0.55);
  transform: translateY(-1px);
}
.wg-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}
.wg-note {
  font-size: 0.66rem;
  color: #93c5fd;
  margin: 0;
}
.wg-alert {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  background: rgba(234,179,8,0.09);
  border: 1px solid rgba(234,179,8,0.35);
  border-radius: 10px;
  padding: 0.5rem 0.7rem;
  margin-top: 0.2rem;
}
.wg-alert-icon {
  font-size: 0.9rem;
}
.wg-alert-text {
  font-size: 0.65rem;
  color: rgba(255,255,255,0.85);
  line-height: 1.45;
}
</style>
