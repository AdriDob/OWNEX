<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { fetchMoneyPlan, updateMoneyPlan, type MoneyPlanData } from '@/services/controlPanel'

const data = ref<MoneyPlanData | null>(null)
const loading = ref(true)
const saving = ref(false)
const hours = ref(5)

const plan = computed(() => data.value?.plan)
const proj = computed(() => data.value?.projection)
const est = computed(() => proj.value?.total_estimate ?? 0)
const target = computed(() => proj.value?.target_weekly ?? 1500)
const gap = computed(() => proj.value?.gap_to_target ?? 0)

async function load() {
  loading.value = true
  try {
    data.value = await fetchMoneyPlan()
    hours.value = data.value?.plan?.hours_per_day ?? 5
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    data.value = await updateMoneyPlan({ hours_per_day: hours.value })
    hours.value = data.value?.plan?.hours_per_day ?? hours.value
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="mo">
    <div class="mo-head">
      <h3 class="mo-title">PLAN DE PLATA</h3>
      <span v-if="proj" class="mo-target">meta ${{ (target * 2).toLocaleString('es-AR') }}/quincena</span>
    </div>

    <p v-if="loading" class="mo-muted">Calculando tu proyección...</p>
    <p v-else-if="!proj" class="mo-muted">Plan no disponible.</p>

    <template v-else>
      <!-- Horas / día -->
      <div class="mo-hours">
        <span class="mo-label">Horas por día</span>
        <div class="mo-hours-input">
          <input v-model.number="hours" type="number" min="1" max="16" class="mo-input" />
          <button class="mo-btn" :disabled="saving || hours === plan?.hours_per_day" @click="save">
            {{ saving ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>

      <!-- Proyección -->
      <div class="mo-grid">
        <div class="mo-card">
          <span class="mo-label">Pulse (tareas IA)</span>
          <span class="mo-value">${{ proj.pulse_income.toLocaleString('es-AR') }}</span>
          <span class="mo-sub">@ ${{ proj.pulse_rate }}/h selectivo</span>
        </div>
        <div class="mo-card">
          <span class="mo-label">Forge (bounts)</span>
          <span class="mo-value">${{ proj.forge_income.toLocaleString('es-AR') }}</span>
          <span class="mo-sub">grande pero lento</span>
        </div>
        <div class="mo-card">
          <span class="mo-label">Estimado total</span>
          <span class="mo-value hot">${{ est.toLocaleString('es-AR') }}</span>
          <span class="mo-sub">a {{ proj.weekly_hours }}h/sem</span>
        </div>
      </div>

      <!-- Carga real con asistente -->
      <div v-if="proj.assistant_enabled" class="mo-effort">
        <span class="mo-label">Con asistente: tu parte real</span>
        <span class="mo-effort-value">
          {{ proj.real_hours }}h/sem
          <span class="mo-effort-saved">(ahorrás {{ proj.saved_hours }}h)</span>
        </span>
      </div>

      <!-- Gap -->
      <div class="mo-gap" :class="{ positive: gap <= 0 }">
        <span class="mo-label">{{ gap <= 0 ? 'Meta alcanzada 🎯' : 'Para llegar a la meta' }}</span>
        <span class="mo-gap-value">
          {{ gap <= 0 ? '¡Vas bien!' : '$' + gap.toLocaleString('es-AR') + ' restantes/sem' }}
        </span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.mo {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.mo-head { display: flex; align-items: center; gap: 0.75rem; }
.mo-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.mo-target { margin-left: auto; font-size: 0.68rem; font-weight: 700; color: #4ade80; }
.mo-muted { font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); margin: 0; }
.mo-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255, 255, 255, 0.45); }
.mo-hours { display: flex; align-items: center; gap: 0.6rem; }
.mo-hours-input { display: flex; align-items: center; gap: 0.4rem; margin-left: auto; }
.mo-input {
  width: 60px; padding: 0.3rem 0.4rem; border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb; font-size: 0.85rem; text-align: center;
}
.mo-btn {
  border: 1px solid rgba(22, 163, 74, 0.4); border-radius: 8px;
  background: rgba(22, 163, 74, 0.12); color: #4ade80;
  font-size: 0.72rem; font-weight: 600; padding: 0.35rem 0.7rem; cursor: pointer;
}
.mo-btn:disabled { opacity: 0.4; cursor: default; }
.mo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.5rem; }
.mo-card {
  border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 10px;
  padding: 0.5rem 0.6rem; display: flex; flex-direction: column; gap: 0.15rem;
}
.mo-value { font-size: 1.1rem; font-weight: 700; color: #4ade80; }
.mo-value.hot { color: #fbbf24; }
.mo-sub { font-size: 0.6rem; color: rgba(255, 255, 255, 0.5); }
.mo-effort {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  border: 1px solid rgba(96, 165, 250, 0.3); border-radius: 8px;
  padding: 0.5rem 0.7rem; background: rgba(96, 165, 250, 0.06);
}
.mo-effort-value { font-size: 0.78rem; font-weight: 700; color: #93c5fd; }
.mo-effort-saved { font-size: 0.62rem; font-weight: 400; color: #4ade80; }
.mo-gap {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 8px;
  padding: 0.5rem 0.7rem; background: rgba(251, 191, 36, 0.06);
}
.mo-gap.positive { border-color: rgba(22, 163, 74, 0.3); background: rgba(22, 163, 74, 0.06); }
.mo-gap-value { font-size: 0.72rem; font-weight: 700; color: #fbbf24; }
.mo-gap.positive .mo-gap-value { color: #4ade80; }
</style>