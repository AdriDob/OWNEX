<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { evaluateGoal, getGoalEvaluatorStatus, type GoalEvalResult } from '@/services/controlPanel'

const result = ref<GoalEvalResult | null>(null)
const loading = ref(true)
const busy = ref(false)
const mode = ref<'monthly' | 'multiplier'>('monthly')
const amount = ref(10000)
const multiplier = ref(5)
const statusInfo = ref<{ success?: boolean; last_eval?: GoalEvalResult | null }>({})

const ev = computed(() => result.value?.evaluation)
const context = computed(() => result.value?.context)
const statusColor = computed(() => {
  const s = ev.value?.status
  if (s === 'on_track') return '#4ade80'
  if (s === 'possible') return '#fbbf24'
  if (s === 'ambitious') return '#fb923c'
  if (s === 'unrealistic') return '#e11d48'
  return '#6b7280'
})

async function load() {
  loading.value = true
  try {
    statusInfo.value = await getGoalEvaluatorStatus()
    if (statusInfo.value.last_eval) result.value = statusInfo.value.last_eval
  } finally {
    loading.value = false
  }
}

async function run() {
  busy.value = true
  try {
    const res = await evaluateGoal(mode.value, amount.value, multiplier.value)
    if (res.success || res.evaluation) {
      result.value = res
    }
  } catch {
    result.value = { success: false }
  } finally {
    busy.value = false
  }
}

function fmt(n: number | undefined) {
  return `$${Math.round(n ?? 0).toLocaleString()}`
}

onMounted(() => load())
</script>

<template>
  <section class="ge">
    <div class="ge-head">
      <h3 class="ge-title">GOAL EVALUATOR · DECILE TU META</h3>
    </div>

    <div class="ge-row">
      <button class="ge-mode" :class="{ active: mode === 'monthly' }" @click="mode = 'monthly'">Meta mensual</button>
      <button class="ge-mode" :class="{ active: mode === 'multiplier' }" @click="mode = 'multiplier'">xMultiplicador</button>
    </div>

    <div v-if="mode === 'monthly'" class="ge-field">
      <label>Quiero ganar este mes (USD)</label>
      <input v-model.number="amount" type="number" min="0" step="100" placeholder="ej. 100000" />
      <span class="ge-hint">Probarlo con 100000 te va a mostrar la verdad del tamaño.</span>
    </div>
    <div v-else class="ge-field">
      <label>Quiero multiplicar por</label>
      <input v-model.number="multiplier" type="number" min="1" step="1" placeholder="ej. 5" />
      <span class="ge-hint">Se usa tu último mes real registrado (si no hay datos, poné un monto).</span>
    </div>

    <button class="ge-btn" :disabled="busy" @click="run">EVALUAR CON DATOS REALES</button>

    <div v-if="loading" class="ge-muted">Cargando estado anterior...</div>

    <div v-if="ev" class="ge-verdict" :style="{ borderColor: statusColor + '66', background: statusColor + '14' }">
      <span class="ge-status" :style="{ color: statusColor }">{{ ev.status.toUpperCase() }}</span>
      <p class="ge-verdict-text">{{ ev.verdict }}</p>
    </div>

    <div v-if="context" class="ge-context">
      <div class="ge-cell"><span>Último mes real</span><b>{{ fmt(context.last_month) }}</b></div>
      <div class="ge-cell"><span>Promedio mensual</span><b>{{ fmt(context.avg_monthly) }}</b></div>
      <div class="ge-cell"><span>Proyección plan mes</span><b>{{ fmt(context.plan_monthly_projection) }}</b></div>
      <div class="ge-cell"><span>Pool capital</span><b>{{ fmt(context.pool_capital) }}</b></div>
    </div>

    <div v-if="ev" class="ge-num">
      <span>Proyección realista mes</span>
      <b>{{ fmt(ev.realistic_projection) }}</b>
      <span class="ge-multiple">×{{ ev.multiple_to_target }} para tu meta</span>
    </div>

    <div v-if="result?.breakdown?.length" class="ge-break">
      <div v-for="b in result.breakdown" :key="b.name" class="ge-b-item">
        <span class="ge-b-name">{{ b.name }}</span>
        <span class="ge-b-note">{{ b.note }}</span>
        <span class="ge-b-amt">{{ fmt(b.monthly_est) }}</span>
      </div>
    </div>

    <div v-if="result?.gaps?.length" class="ge-gaps">
      <p class="ge-gaps-title">PARA ACERCARTE</p>
      <div v-for="g in result.gaps" :key="g.label" class="ge-gap">
        <span class="ge-g-prio">{{ g.priority }}</span>
        <div class="ge-g-body">
          <span class="ge-g-label">{{ g.label }}</span>
          <span class="ge-g-why">{{ g.why }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ge { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.ge-head { display: flex; align-items: center; }
.ge-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.ge-row { display: flex; gap: 0.4rem; }
.ge-mode { border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); border-radius: 8px; padding: 0.35rem 0.7rem; font-size: 0.65rem; color: rgba(255,255,255,0.7); cursor: pointer; }
.ge-mode.active { border-color: rgba(96,165,250,0.5); background: rgba(96,165,250,0.12); color: #93c5fd; }
.ge-field { display: flex; flex-direction: column; gap: 0.3rem; }
.ge-field label { font-size: 0.65rem; color: rgba(255,255,255,0.6); }
.ge-field input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.5rem 0.65rem; color: rgba(255,255,255,0.95); font-size: 0.9rem; }
.ge-hint { font-size: 0.6rem; color: rgba(255,255,255,0.4); }
.ge-btn { border: 1px solid rgba(96,165,250,0.4); border-radius: 8px; background: rgba(96,165,250,0.1); color: #93c5fd; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; padding: 0.5rem 0.7rem; cursor: pointer; }
.ge-btn:disabled { opacity: 0.4; cursor: default; }
.ge-muted { font-size: 0.7rem; color: rgba(255,255,255,0.5); }
.ge-verdict { border: 1px solid; border-radius: 10px; padding: 0.6rem 0.7rem; display: flex; flex-direction: column; gap: 0.3rem; }
.ge-status { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em; }
.ge-verdict-text { margin: 0; font-size: 0.75rem; color: rgba(255,255,255,0.9); line-height: 1.5; }
.ge-context { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; }
.ge-cell { display: flex; flex-direction: column; gap: 0.1rem; padding: 0.45rem 0.55rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); }
.ge-cell span { font-size: 0.6rem; color: rgba(255,255,255,0.45); }
.ge-cell b { font-size: 0.8rem; color: rgba(255,255,255,0.9); }
.ge-num { display: flex; align-items: baseline; gap: 0.5rem; padding: 0.55rem 0.6rem; border: 1px solid rgba(96,165,250,0.2); border-radius: 8px; background: rgba(96,165,250,0.06); }
.ge-num span { font-size: 0.65rem; color: rgba(255,255,255,0.6); }
.ge-num b { font-size: 1rem; color: #93c5fd; }
.ge-multi { font-size: 0.6rem; color: rgba(255,255,255,0.5); }
.ge-break { display: flex; flex-direction: column; gap: 0.3rem; }
.ge-b-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.55rem; background: rgba(255,255,255,0.02); border-radius: 8px; }
.ge-b-name { font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.9); }
.ge-b-note { font-size: 0.6rem; color: rgba(255,255,255,0.45); flex: 1; }
.ge-b-amt { font-size: 0.7rem; font-weight: 700; color: #93c5fd; }
.ge-gaps-title { margin: 0; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); }
.ge-gap { display: flex; gap: 0.5rem; padding: 0.45rem 0.55rem; background: rgba(255,255,255,0.02); border-radius: 8px; }
.ge-g-prio { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); padding: 0.1rem 0.35rem; border-radius: 4px; height: fit-content; }
.ge-g-body { display: flex; flex-direction: column; gap: 0.1rem; }
.ge-g-label { font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.9); }
.ge-g-why { font-size: 0.62rem; color: rgba(255,255,255,0.5); }
</style>