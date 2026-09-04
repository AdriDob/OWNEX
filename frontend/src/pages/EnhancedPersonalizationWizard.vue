<template>
  <div class="enhanced-wizard">
    <!-- ═══ WIZARD CONTAINER ═══ -->
    <div class="wizard-container">
      <!-- Progress Bar -->
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>

      <!-- Step Indicator -->
      <div class="step-indicator">
        <div
          v-for="(step, index) in steps"
          :key="step.step_id"
          class="step-dot"
          :class="{
            'step-active': currentStepIndex === index,
            'step-completed': currentStepIndex > index,
          }"
        >
          <div class="step-number">{{ index + 1 }}</div>
        </div>
      </div>

      <!-- Current Step -->
      <div class="step-content">
        <div class="step-merlin">
          <div class="merlin-avatar">
            <div class="avatar-ring outer-ring"></div>
            <div class="avatar-ring middle-ring"></div>
            <div class="avatar-ring inner-ring"></div>
            <div class="avatar-core">🧙</div>
          </div>
          <div class="merlin-message">
            <p class="greeting">{{ getMerlinGreeting() }}</p>
            <p class="description">{{ currentStep.description }}</p>
          </div>
        </div>

        <h1 class="step-title">{{ currentStep.title }}</h1>

        <!-- Questions -->
        <div class="questions-container">
          <div
            v-for="question in currentStep.questions"
            :key="question.id"
            class="question-item"
          >
            <label class="question-label">{{ question.question }}</label>

            <!-- Text Input -->
            <input
              v-if="question.type === 'text'"
              v-model="answers[question.id]"
              :placeholder="question.placeholder"
              class="jarvis-input"
              :required="question.required"
            />

            <!-- Number Input -->
            <input
              v-if="question.type === 'number'"
              v-model.number="answers[question.id]"
              type="number"
              :placeholder="question.placeholder"
              class="jarvis-input"
              :required="question.required"
            />

            <!-- Time Input -->
            <input
              v-if="question.type === 'time'"
              v-model="answers[question.id]"
              type="time"
              class="jarvis-input"
              :required="question.required"
            />

            <!-- Select -->
            <select
              v-if="question.type === 'select'"
              v-model="answers[question.id]"
              class="jarvis-select"
              :required="question.required"
            >
              <option
                v-for="option in question.options"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>

            <!-- Boolean -->
            <div v-if="question.type === 'boolean'" class="boolean-toggle">
              <button
                @click="answers[question.id] = true"
                class="toggle-btn"
                :class="{ active: answers[question.id] === true }"
              >
                Sí
              </button>
              <button
                @click="answers[question.id] = false"
                class="toggle-btn"
                :class="{ active: answers[question.id] === false }"
              >
                No
              </button>
            </div>
          </div>
        </div>

        <!-- Navigation -->
        <div class="wizard-navigation">
          <button
            v-if="currentStepIndex > 0"
            @click="previousStep"
            class="nav-btn btn-secondary"
          >
            ← Anterior
          </button>
          <button
            @click="nextStep"
            class="nav-btn btn-primary"
            :disabled="!isStepValid"
          >
            {{ isLastStep ? 'Comenzar' : 'Siguiente →' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { WizardQuestion, WizardStep } from '@/types'

const router = useRouter()

const steps = ref<WizardStep[]>([])
const currentStepIndex = ref(0)
const answers = ref<Record<string, unknown>>({})
const userProfile = ref<unknown>(null)

const currentStep = computed(() => steps.value[currentStepIndex.value])
const progress = computed(() => ((currentStepIndex.value + 1) / steps.value.length) * 100)
const isLastStep = computed(() => currentStepIndex.value === steps.value.length - 1)

const isStepValid = computed(() => {
  if (!currentStep.value) return false
  return currentStep.value.questions.every((q: WizardQuestion) => {
    if (q.required && !answers.value[q.id]) return false
    return true
  })
})

async function loadWizardSteps() {
  try {
    const response = await axios.get('/api/setup/enhanced-personalization/steps')
    steps.value = response.data.steps
  } catch (error) {
    console.error('Error loading wizard steps:', error)
  }
}

function getMerlinGreeting() {
  const name = answers.value.name || answers.value.preferred_name || 'amigo'
  const stepIndex = currentStepIndex.value

  const greetings = [
    `¡Hola ${name}! Soy MERLIN, tu asistente de inteligencia autónoma del 2030. Vamos a personalizar tu experiencia.`,
    `Perfecto, ${name}. Ahora entiendo mejor tu nivel. Adaptaré mi guía a tu experiencia.`,
    `Entendido, ${name}. Ajustaré mi nivel de guía para que te sientas cómodo.`,
    `Excelente, ${name}. Esos objetivos son muy claros. Te ayudaré a alcanzarlos.`,
    `Perfecto, ${name}. Integraré Obsidian para que todo esté organizado.`,
    `Genial, ${name}. Configuraré tu sistema de productividad automáticamente.`,
    `¡Increíble, ${name}! Con comandos de voz serás aún más productivo.`,
    `¡Confirmado, ${name}! Estoy listo para empezar. ¡Vamos a ganar dinero juntos!`,
  ]

  return greetings[stepIndex] || greetings[0]
}

async function nextStep() {
  if (!isStepValid.value) return

  const stepId = currentStep.value.step_id

  try {
    await axios.post('/api/setup/enhanced-personalization/step', {
      step_id: stepId,
      answers: answers.value,
    })
  } catch (error) {
    console.error('Error processing step:', error)
  }

  if (isLastStep.value) {
    await completeWizard()
  } else {
    currentStepIndex.value++
  }
}

function previousStep() {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
  }
}

async function completeWizard() {
  try {
    await axios.post('/api/setup/enhanced-personalization/complete')
    router.push('/dashboard')
  } catch (error) {
    console.error('Error completing wizard:', error)
  }
}

onMounted(() => {
  loadWizardSteps()
})
</script>

<style scoped>
/* ═══ OWNEX — PREMIUM MINIMAL SETUP WIZARD THEME ═══ */
.enhanced-wizard {
  min-height: 100vh;
  background: var(--ownex-bg-base);
  color: var(--ownex-bg-surface);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.wizard-container {
  width: 100%;
  max-width: 620px;
  background: #0c0e13;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 18px;
  padding: 28px;
}

/* ── Progress ── */
.progress-bar {
  height: 4px;
  border-radius: 999px;
  background: var(--ownex-bg-elevated);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--ownex-accent), var(--ownex-accent));
  border-radius: 999px;
  transition: width 0.3s ease;
}

/* ── Step indicator ── */
.step-indicator {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin: 20px 0;
}
.step-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ownex-text-muted);
  transition: border-color 0.15s ease;
}
.step-dot.step-active {
  border-color: rgba(0, 213, 255, 0.6);
  color: var(--ownex-accent);
}
.step-dot.step-completed {
  border-color: rgba(0, 227, 154, 0.4);
  color: var(--ownex-green);
}
.step-number { font-size: 13px; font-weight: 600; }

/* ── Step content ── */
.step-merlin {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.merlin-avatar { display: flex; align-items: center; }
.avatar-ring {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(0, 227, 154, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-ring.middle-ring { width: 28px; height: 28px; border-color: rgba(0, 213, 255, 0.25); }
.avatar-ring.inner-ring { width: 22px; height: 22px; border-color: rgba(255, 255, 255, 0.2); }
.avatar-core { font-size: 16px; }
.merlin-message { display: flex; flex-direction: column; gap: 2px; }
.greeting { margin: 0; font-size: 13px; font-weight: 500; color: var(--ownex-text-secondary); }
.description { margin: 0; font-size: 12px; color: var(--ownex-text-secondary); }

.step-title {
  margin: 0 0 18px;
  font-family: 'Space Grotesk', 'Inter', sans-serif;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* ── Questions ── */
.questions-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.question-item { display: flex; flex-direction: column; gap: 6px; }
.question-label { font-size: 13px; color: var(--ownex-text-secondary); }
.jarvis-input {
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9px;
  padding: 11px 13px;
  color: var(--ownex-bg-surface);
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s ease;
}
.jarvis-input::placeholder { color: var(--ownex-text-muted); }
.jarvis-input:focus { border-color: rgba(0, 213, 255, 0.4); }
.jarvis-select {
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9px;
  padding: 11px 13px;
  color: var(--ownex-bg-surface);
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  outline: none;
}
.boolean-toggle { display: flex; gap: 8px; }
.toggle-btn {
  flex: 1;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9px;
  background: transparent;
  color: var(--ownex-text-secondary);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.toggle-btn.active {
  border-color: rgba(0, 213, 255, 0.4);
  background: rgba(0, 213, 255, 0.08);
  color: var(--ownex-accent);
}

/* ── Navigation ── */
.wizard-navigation {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 24px;
}
.nav-btn {
  padding: 11px 18px;
  border-radius: 9px;
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-secondary {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: transparent;
  color: var(--ownex-text-secondary);
}
.btn-secondary:hover { border-color: rgba(255, 255, 255, 0.25); }
.btn-primary {
  border: none;
  background: var(--ownex-accent);
  color: var(--ownex-bg-base);
}
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-primary:disabled { background: var(--ownex-bg-elevated); color: var(--ownex-text-muted); cursor: not-allowed; }
</style>
