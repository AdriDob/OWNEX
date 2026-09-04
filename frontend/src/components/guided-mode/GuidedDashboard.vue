<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useFirstDayGuide } from '@/composables/useFirstDayGuide'
import { useGuidedMode } from '@/composables/useGuidedMode'
import { fetchDirectWorkDailyBrief, fetchDirectWorkWorkBank, runDirectWorkCycle } from '@/services/ownexData'
import type { DailyBrief, GuidedMode } from '@/types/guided'
import FirstDayGuide from './FirstDayGuide.vue'
import IncomeGuidanceAssistant from './IncomeGuidanceAssistant.vue'
import ModeSelector from './ModeSelector.vue'
import UniversalExplanationLayer from './UniversalExplanationLayer.vue'

const { currentMode, initMode, setMode } = useGuidedMode()
const { fetchFirstDayGuide, fetchFirstDayProgress, completeFirstDayStep } = useFirstDayGuide()

const dailyBrief = ref<DailyBrief | null>(null)
const workBank = ref<any>(null)
const firstDayGuide = ref<any>(null)
const firstDayProgress = ref({ completed_steps: [], total_steps: 5, pct: 0 })
const loading = ref(false)
const error = ref('')

const topOpportunity = computed(() => dailyBrief.value?.top_opportunity || null)

const incomeGuidance = computed(() => {
  if (!topOpportunity.value) return null
  const opp = topOpportunity.value.opportunity
  return {
    title: opp.title,
    summary: `Oportunidad ${opp.category} en ${opp.platform} con recompensa de $${opp.payment}`,
    difficulty:
      (opp.estimated_time_hours || 0) <= 4
        ? 'beginner'
        : (opp.estimated_time_hours || 0) <= 8
          ? 'intermediate'
          : 'advanced',
    required: {
      programming: opp.technology_tags && opp.technology_tags.length > 0,
      portfolio: opp.portfolio_required,
      interview: opp.interview_required,
    },
    own_prep_pct: Math.min(90, 50 + (opp.zero_barrier_score?.total || 0) * 0.4),
    user_action: `Revisa la oportunidad, prepara la entrega y envía. OWNEX prepara el ${Math.min(90, 50 + (opp.zero_barrier_score?.total || 0) * 0.4)}% del trabajo.`,
    explanation: {
      what: `Se detectó una oportunidad de ${opp.category} en ${opp.platform} con recompensa de $${opp.payment}.`,
      why: `Tiene score de barrera ${opp.zero_barrier_score?.total || 0}/100 y probabilidad de aceptación del ${Math.round((opp.acceptance_probability || 0) * 100)}%.`,
      how: 'OWNEX descubrió, filtró y preparó la oportunidad. Tú solo revisas y entregas.',
      result: 'Entrega lista para enviar en la plataforma correspondiente.',
      nextStep: 'Revisa los detalles, prepara tu entrega y confirma cuando esté listo.',
    },
    confidence: {
      level:
        (opp.zero_barrier_score?.total || 0) >= 70
          ? 'high'
          : (opp.zero_barrier_score?.total || 0) >= 40
            ? 'medium'
            : 'low',
      detail: `Score de barrera: ${opp.zero_barrier_score?.total || 0}/100. Probabilidad: ${Math.round((opp.acceptance_probability || 0) * 100)}%.`,
    },
  }
})

const showFirstDay = computed(
  () => firstDayGuide.value && firstDayGuide.value.steps && firstDayGuide.value.steps.length > 0,
)

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [brief, bank, guide, progress] = await Promise.allSettled([
      fetchDirectWorkDailyBrief(),
      fetchDirectWorkWorkBank(),
      fetchFirstDayGuide(),
      fetchFirstDayProgress(),
    ])

    if (brief.status === 'fulfilled') dailyBrief.value = brief.value
    if (bank.status === 'fulfilled') workBank.value = bank.value
    if (guide.status === 'fulfilled') firstDayGuide.value = guide.value?.guide || null
    if (progress.status === 'fulfilled') firstDayProgress.value = progress.value

    if (brief.status === 'rejected' && bank.status === 'rejected') {
      error.value = 'No se pudo cargar el dashboard guiado'
    }
  } catch (e) {
    error.value = 'Error cargando datos'
  } finally {
    loading.value = false
  }
}

async function handleFirstDayStepComplete(step: number) {
  try {
    await completeFirstDayStep(step)
    const progress = await fetchFirstDayProgress()
    firstDayProgress.value = progress
  } catch (e) {
    console.error('Error completando paso:', e)
  }
}

async function handleRunCycle() {
  loading.value = true
  try {
    await runDirectWorkCycle(10)
    await loadAll()
  } catch (e) {
    error.value = 'Error ejecutando ciclo'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  initMode()
  loadAll()
})

watch(currentMode, (mode) => {
  localStorage.setItem('ownex:guidedMode', mode)
})
</script>

<template>
  <div class="guided-dashboard">
    <ModeSelector />

    <div v-if="error" class="guided-dashboard__error">
      {{ error }}
      <button @click="loadAll" class="guided-dashboard__retry-btn">Reintentar</button>
    </div>

    <div v-else-if="loading" class="guided-dashboard__loading">
      <div class="guided-dashboard__spinner"></div>
      <p>Cargando tu panel guiado...</p>
    </div>

    <div v-else class="guided-dashboard__content">
      <!-- Mode selector at top -->
      <div class="guided-dashboard__mode-section">
        <ModeSelector />
      </div>

      <!-- First Day Guide (prominent for beginners) -->
      <div v-if="showFirstDay" class="guided-dashboard__section">
        <FirstDayGuide
          :guide="firstDayGuide"
          :progress="firstDayProgress"
          @step-complete="handleFirstDayStepComplete"
        />
      </div>

      <!-- Income Guidance Assistant - the core daily action -->
      <div class="guided-dashboard__section">
        <IncomeGuidanceAssistant
          :opportunity="incomeGuidance"
          @run-cycle="handleRunCycle"
        />
      </div>

      <!-- Quick Actions Row -->
      <div class="guided-dashboard__quick-actions">
        <button
          class="guided-dashboard__quick-btn"
          @click="handleRunCycle"
          :disabled="loading"
        >
          <span>🔄</span> Correr Ciclo Diario
        </button>
        <button
          class="guided-dashboard__quick-btn guided-dashboard__quick-btn--secondary"
          @click="loadAll"
        >
          <span>🔍</span> Actualizar Oportunidades
        </button>
        <button
          class="guided-dashboard__quick-btn guided-dashboard__quick-btn--secondary"
        >
          <span>💼</span> Ver Work Bank
        </button>
      </div>

      <!-- Work Bank Summary -->
      <div class="guided-dashboard__section" v-if="workBank">
        <h4 class="guided-dashboard__section-title">Work Bank</h4>
        <div class="guided-dashboard__bank-summary">
          <div class="guided-dashboard__bank-item">
            <span class="guided-dashboard__bank-label">Listos para entregar</span>
            <span class="guided-dashboard__bank-value">{{ workBank.ready_to_deliver || 0 }}</span>
          </div>
          <div class="guided-dashboard__bank-item">
            <span class="guided-dashboard__bank-label">Necesitan acceso</span>
            <span class="guided-dashboard__bank-value">{{ workBank.needs_access || 0 }}</span>
          </div>
          <div class="guided-dashboard__bank-item">
            <span class="guided-dashboard__bank-label">Total en banco</span>
            <span class="guided-dashboard__bank-value">{{ workBank.total_in_bank || 0 }}</span>
          </div>
          <div class="guided-dashboard__bank-item">
            <span class="guided-dashboard__bank-label">Meta diaria</span>
            <span class="guided-dashboard__bank-value">{{ workBank.targets?.daily?.achieved || 0 }} / {{ workBank.targets?.daily?.target || 10 }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.guided-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.guided-dashboard__error {
  background: rgba(148, 163, 184, 0.15);
  border: 1px solid rgba(148, 163, 184, 0.3);
  color: var(--ownex-text-secondary);
  padding: 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.guided-dashboard__retry-btn {
  background: linear-gradient(135deg, var(--ownex-accent), var(--ownex-accent));
  border: none;
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.guided-dashboard__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--ownex-text-secondary);
}

.guided-dashboard__spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(59, 130, 246, 0.3);
  border-top-color: var(--ownex-danger);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.guided-dashboard__content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.guided-dashboard__section {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
}

.guided-dashboard__mode-section {
  /* ModeSelector already has its own styling */
}

.guided-dashboard__section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--ownex-text-primary);
  margin: 0 0 16px;
}

.guided-dashboard__quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.guided-dashboard__quick-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--ownex-danger), var(--ownex-accent));
  border: none;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  padding: 12px 20px;
  border-radius: 9999px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.guided-dashboard__quick-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px color-mix(in srgb, var(--ownex-danger) 40%, transparent);
}

.guided-dashboard__quick-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.guided-dashboard__quick-btn--secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.guided-dashboard__quick-btn--secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 20px rgba(255, 255, 255, 0.1);
}

.guided-dashboard__bank-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.guided-dashboard__bank-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}

.guided-dashboard__bank-label {
  font-size: 0.75rem;
  color: var(--ownex-text-secondary);
  display: block;
  margin-bottom: 4px;
}

.guided-dashboard__bank-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--ownex-text-primary);
}

@media (max-width: 768px) {
  .guided-dashboard__bank-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .guided-dashboard__bank-summary {
    grid-template-columns: 1fr;
  }
  .guided-dashboard__quick-actions {
    flex-direction: column;
  }
  .guided-dashboard__quick-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>