<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getCapitalBar, setCapitalRatio, recordCapitalIncome,
  type CapitalBarStatus,
} from '@/services/controlPanel'

const status = ref<CapitalBarStatus>({})
const loading = ref(true)
const busy = ref(false)
const note = ref('')
const form = ref({ amount: 0, source: '', note: '' })
const showForm = ref(false)

const pool = computed(() => status.value.pool ?? 0)
const thresholds = computed(() => status.value.thresholds ?? [])
const ratio = computed(() => Math.round((status.value.feed_ratio ?? 0.8) * 100))

async function load() {
  loading.value = true
  try {
    status.value = await getCapitalBar()
  } finally {
    loading.value = false
  }
}

async function setRatio() {
  await setCapitalRatio((status.value.feed_ratio ?? 0.8) * 100)
}

async function submitIncome() {
  busy.value = true
  note.value = ''
  try {
    const res = await recordCapitalIncome(form.value.amount, form.value.source, form.value.note)
    if (res.success) {
      note.value = `Ingreso registrado — pool actual: $${res.pool?.toLocaleString()}`
      form.value.amount = 0
      form.value.source = ''
      form.value.note = ''
      showForm.value = false
      await load()
    } else {
      note.value = 'No se pudo registrar.'
    }
  } catch {
    note.value = 'Error al registrar.'
  } finally {
    busy.value = false
  }
}

function fmt(n: number) {
  return `$${Math.round(n).toLocaleString()}`
}

onMounted(() => load())
</script>

<template>
  <section class="cb">
    <div class="cb-head">
      <h3 class="cb-title">CAPITAL BAR · HACIA LOS 100K</h3>
      <span class="cb-badge">{{ fmt(pool) }}</span>
    </div>

    <p v-if="loading" class="cb-muted">Calculando capital...</p>

    <template v-else>
      <p class="cb-msg">{{ status.message }}</p>

      <div class="cb-passive">
        <span class="cb-p-label">Pasivo mensual al nivel actual:</span>
        <span class="cb-p-value">{{ fmt(status.monthly_passive ?? 0) }}</span>
      </div>

      <div class="cb-ratio">
        <label>Feed ratio ({{ ratio }}% de cada ingreso al pool)</label>
        <input type="range" min="0" max="100" step="5" :value="ratio" @change="setRatio" @input="(e: any) => (status.feed_ratio = Number(e.target.value) / 100)" />
      </div>

      <div class="cb-thresholds">
        <div v-for="t in thresholds" :key="t.key" class="cb-th" :class="{ reached: t.reached }">
          <div class="cb-t-head">
            <span class="cb-t-name">{{ t.name }}</span>
            <span class="cb-t-amt">{{ fmt(t.amount) }}</span>
          </div>
          <div class="cb-t-bar"><div class="cb-t-fill" :style="{ width: t.pct + '%' }"></div></div>
          <div class="cb-t-foot">
            <span v-if="t.reached" class="cb-t-status">✓ Alcanzado</span>
            <span v-else class="cb-t-gap">Faltan {{ fmt(t.gap) }}</span>
            <span class="cb-t-mode">{{ t.mode }}</span>
          </div>
        </div>
      </div>

      <button class="cb-btn" @click="showForm = !showForm">
        {{ showForm ? 'Cerrar' : '+ Registrar ingreso' }}
      </button>

      <form v-if="showForm" class="cb-form" @submit.prevent="submitIncome">
        <input v-model.number="form.amount" type="number" min="0" step="1" placeholder="Monto recibido (USD)" required />
        <input v-model="form.source" placeholder="Fuente (ej: bounty, pulse)" />
        <input v-model="form.note" placeholder="Nota" />
        <button class="cb-btn" :disabled="busy">Guardar</button>
      </form>

      <p v-if="note" class="cb-note">{{ note }}</p>
    </template>
  </section>
</template>

<style scoped>
.cb { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.cb-head { display: flex; align-items: center; gap: 0.7rem; }
.cb-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.cb-badge { margin-left: auto; font-size: 0.65rem; font-weight: 700; color: #fbbf24; background: rgba(251,191,36,0.12); border: 1px solid rgba(251,191,36,0.3); border-radius: 6px; padding: 0.2rem 0.5rem; }
.cb-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.cb-msg { font-size: 0.72rem; color: rgba(255,255,255,0.8); margin: 0; line-height: 1.5; }
.cb-passive { display: flex; justify-content: space-between; align-items: center; font-size: 0.7rem; padding: 0.5rem 0.6rem; background: rgba(251,191,36,0.06); border: 1px solid rgba(251,191,36,0.2); border-radius: 8px; }
.cb-p-label { color: rgba(255,255,255,0.7); }
.cb-p-value { font-weight: 700; color: #fbbf24; }
.cb-ratio { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.62rem; color: rgba(255,255,255,0.6); }
.cb-ratio input { accent-color: #fbbf24; }
.cb-thresholds { display: flex; flex-direction: column; gap: 0.5rem; }
.cb-th { padding: 0.55rem 0.6rem; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; background: rgba(255,255,255,0.02); display: flex; flex-direction: column; gap: 0.35rem; }
.cb-th.reached { border-color: rgba(74,222,128,0.3); background: rgba(74,222,128,0.04); }
.cb-t-head { display: flex; justify-content: space-between; font-size: 0.7rem; }
.cb-t-name { font-weight: 600; color: rgba(255,255,255,0.9); }
.cb-t-amt { color: rgba(255,255,255,0.5); }
.cb-t-bar { height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.cb-t-fill { height: 100%; background: linear-gradient(90deg, #f59e0b, #fbbf24); border-radius: 3px; transition: width 0.3s; }
.cb-t-foot { display: flex; justify-content: space-between; align-items: center; font-size: 0.6rem; }
.cb-t-gap { color: rgba(255,255,255,0.5); }
.cb-t-status { color: #4ade80; font-weight: 700; }
.cb-t-mode { color: rgba(255,255,255,0.4); }
.cb-btn { align-self: flex-start; border: 1px solid rgba(251,191,36,0.4); border-radius: 8px; background: rgba(251,191,36,0.1); color: #fbbf24; font-size: 0.68rem; font-weight: 600; padding: 0.35rem 0.7rem; cursor: pointer; }
.cb-btn:disabled { opacity: 0.4; cursor: default; }
.cb-form { display: flex; flex-direction: column; gap: 0.4rem; }
.cb-form input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.45rem 0.6rem; color: rgba(255,255,255,0.9); font-size: 0.7rem; }
.cb-note { font-size: 0.68rem; color: #fbbf24; margin: 0; }
</style>
