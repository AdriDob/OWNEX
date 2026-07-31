<template>
  <div class="enhanced-wizard">
    <!-- ═══ JARVIS HUD LAYER ═══ -->
    <div class="jarvis-hud">
      <div class="scan-lines"></div>
      <div class="grid-overlay"></div>
      <div class="particles-container">
        <div v-for="i in 30" :key="i" class="particle" :style="getParticleStyle(i)"></div>
      </div>
    </div>

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

    <!-- ═══ LIGHT EFFECTS ═══ -->
    <div class="light-effects">
      <div class="light-orb orb-1"></div>
      <div class="light-orb orb-2"></div>
      <div class="light-orb orb-3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import type { WizardStep, WizardQuestion } from '@/types'

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

function getParticleStyle(index: number) {
  const angle = (index / 30) * 360
  const distance = 100 + Math.random() * 200
  const x = Math.cos(angle * Math.PI / 180) * distance
  const y = Math.sin(angle * Math.PI / 180) * distance
  const size = 2 + Math.random() * 3
  const delay = Math.random() * 3

  return {
    left: `calc(50% + ${x}px)`,
    top: `calc(50% + ${y}px)`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
  }
}

onMounted(() => {
  loadWizardSteps()
})
</script>

<style scoped>
/* ═══ ENHANCED WIZARD — JARVIS STYLE ═══ */
.enhanced-wizard {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1b2a 100%);
  font-family: 'Rajdhani', 'Orbitron', 'Segoe UI', sans-serif;
  color: #00f0ff;
  position: relative;
  overflow: hidden;
}

/* ═══ JARVIS HUD LAYER ═══ */
.jarvis-hud {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}

.scan-lines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 240, 255, 0.03) 2px,
    rgba(0, 240, 255, 0.03) 4px
  );
  animation: scan-move 8s linear infinite;
}

@keyframes scan-move {
  0% { transform: translateY(0); }
  100% { transform: translateY(100vh); }
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: grid-pulse 4s ease-in-out infinite;
}

@keyframes grid-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

.particles-container {
  position: absolute;
  inset: 0;
}

.particle {
  position: absolute;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: particle-float infinite ease-in-out;
}

@keyframes particle-float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(var(--tx, 0), var(--ty, 0)) scale(1.5);
    opacity: 0.8;
  }
}

/* ═══ WIZARD CONTAINER ═══ */
.wizard-container {
  position: relative;
  z-index: 2;
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

/* ═══ PROGRESS BAR ═══ */
.progress-bar {
  height: 4px;
  background: rgba(0, 240, 255, 0.2);
  border-radius: 2px;
  margin-bottom: 2rem;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  border-radius: 2px;
  transition: width 0.5s ease;
  box-shadow: 0 0 10px #00f0ff;
}

/* ═══ STEP INDICATOR ═══ */
.step-indicator {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 3rem;
}

.step-dot {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(0, 240, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.step-active {
  border-color: #00f0ff;
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.5);
}

.step-completed {
  border-color: #00ff88;
  background: rgba(0, 255, 136, 0.1);
}

.step-number {
  font-size: 0.875rem;
  font-weight: 700;
  color: rgba(0, 240, 255, 0.6);
}

.step-active .step-number {
  color: #00f0ff;
}

.step-completed .step-number {
  color: #00ff88;
}

/* ═══ STEP CONTENT ═══ */
.step-content {
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 1rem;
  padding: 2rem;
  backdrop-filter: blur(10px);
  animation: step-fade 0.5s ease;
}

@keyframes step-fade {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ═══ MERLIN AVATAR ═══ */
.step-merlin {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid rgba(0, 240, 255, 0.2);
}

.merlin-avatar {
  position: relative;
  width: 80px;
  height: 80px;
}

.avatar-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(0, 240, 255, 0.3);
}

.outer-ring {
  inset: 0;
  animation: ring-rotate 30s linear infinite;
}

.middle-ring {
  inset: 12px;
  animation: ring-rotate 20s linear infinite reverse;
}

.inner-ring {
  inset: 24px;
  animation: ring-rotate 15s linear infinite;
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.avatar-core {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  font-size: 2rem;
  z-index: 1;
}

.merlin-message {
  flex: 1;
}

.greeting {
  font-size: 1.25rem;
  font-weight: 700;
  color: #00f0ff;
  margin-bottom: 0.5rem;
  letter-spacing: 0.1em;
}

.description {
  font-size: 0.875rem;
  color: rgba(0, 240, 255, 0.7);
  line-height: 1.6;
}

/* ═══ STEP TITLE ═══ */
.step-title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: #00f0ff;
  margin-bottom: 2rem;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

/* ═══ QUESTIONS ═══ */
.questions-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.question-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.question-label {
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.8);
}

.jarvis-input,
.jarvis-select {
  padding: 0.75rem 1rem;
  background: rgba(10, 14, 39, 0.5);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.5rem;
  color: #00f0ff;
  font-family: 'Rajdhani', 'Orbitron', monospace;
  font-size: 0.875rem;
  letter-spacing: 0.05em;
  outline: none;
  transition: all 0.2s;
}

.jarvis-input:focus,
.jarvis-select:focus {
  border-color: rgba(0, 240, 255, 0.6);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}

.jarvis-input::placeholder {
  color: rgba(0, 240, 255, 0.4);
}

.jarvis-select {
  cursor: pointer;
}

.jarvis-select option {
  background: #0a0e27;
  color: #00f0ff;
}

/* ═══ BOOLEAN TOGGLE ═══ */
.boolean-toggle {
  display: flex;
  gap: 0.5rem;
}

.toggle-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  background: rgba(10, 14, 39, 0.5);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.5rem;
  color: rgba(0, 240, 255, 0.6);
  font-family: 'Rajdhani', 'Orbitron', monospace;
  font-size: 0.875rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn:hover {
  border-color: rgba(0, 240, 255, 0.5);
  background: rgba(0, 240, 255, 0.1);
}

.toggle-btn.active {
  border-color: #00f0ff;
  background: rgba(0, 240, 255, 0.2);
  color: #00f0ff;
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

/* ═══ NAVIGATION ═══ */
.wizard-navigation {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.nav-btn {
  flex: 1;
  padding: 1rem 2rem;
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.5rem;
  font-family: 'Rajdhani', 'Orbitron', monospace;
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: rgba(10, 14, 39, 0.5);
  color: rgba(0, 240, 255, 0.6);
}

.btn-secondary:hover {
  border-color: rgba(0, 240, 255, 0.5);
  background: rgba(0, 240, 255, 0.1);
}

.btn-primary {
  background: rgba(0, 240, 255, 0.2);
  color: #00f0ff;
  border-color: rgba(0, 240, 255, 0.5);
}

.btn-primary:hover:not(:disabled) {
  border-color: #00f0ff;
  background: rgba(0, 240, 255, 0.3);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ═══ LIGHT EFFECTS ═══ */
.light-effects {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.light-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  animation: orb-float 10s ease-in-out infinite;
}

.orb-1 {
  width: 300px;
  height: 300px;
  background: rgba(0, 240, 255, 0.1);
  top: 10%;
  left: 10%;
  animation-delay: 0s;
}

.orb-2 {
  width: 250px;
  height: 250px;
  background: rgba(0, 255, 136, 0.1);
  bottom: 20%;
  right: 15%;
  animation-delay: 3s;
}

.orb-3 {
  width: 200px;
  height: 200px;
  background: rgba(255, 107, 53, 0.05);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: 6s;
}

@keyframes orb-float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(30px, -30px) scale(1.2);
  }
}
</style>