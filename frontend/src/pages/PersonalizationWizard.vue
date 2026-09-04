<template>
  <div class="personalization-wizard">
    <!-- ═══ WIZARD HEADER ═══ -->
    <header class="wizard-header">
      <div class="logo-section">
        <div class="logo-mark">
          <div class="o-ring o-ring-outer" />
          <div class="o-ring o-ring-inner" />
          <div class="o-dot" />
          <div class="o-core" />
        </div>
        <div>
          <h1 class="wizard-title">OWNEX Alpha</h1>
          <p class="wizard-subtitle">Configura tu sistema según tus necesidades</p>
        </div>
      </div>
      <div class="progress-section">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progress}%` }" />
        </div>
        <span class="progress-text">Paso {{ currentStep }} de {{ totalSteps }}</span>
      </div>
    </header>

    <!-- ═══ WIZARD STEPS ═══ -->
    <div class="wizard-content">
      <!-- Step 1: Use Case -->
      <div v-if="currentStep === 1" class="wizard-step">
        <h2 class="step-title">¿Para qué quieres usar OWNEX Alpha?</h2>
        <p class="step-description">Selecciona el caso de uso que mejor describe tus necesidades</p>

        <div class="use-case-grid">
          <div
            v-for="useCase in useCases"
            :key="useCase.id"
            class="use-case-card"
            :class="{ 'selected': selectedUseCase === useCase.id }"
            @click="selectedUseCase = useCase.id"
          >
            <div class="use-case-icon">{{ useCase.icon }}</div>
            <div class="use-case-info">
              <h3 class="use-case-title">{{ useCase.title }}</h3>
              <p class="use-case-desc">{{ useCase.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: Modules -->
      <div v-if="currentStep === 2" class="wizard-step">
        <h2 class="step-title">Selecciona los módulos que quieres habilitar</h2>
        <p class="step-description">Deja vacío para usar los módulos recomendados</p>

        <div class="modules-grid">
          <div
            v-for="module in availableModules"
            :key="module.id"
            class="module-card"
            :class="{ 'selected': selectedModules.includes(module.id) }"
            @click="toggleModule(module.id)"
          >
            <div class="module-icon">{{ module.icon }}</div>
            <div class="module-info">
              <h3 class="module-title">{{ module.title }}</h3>
              <p class="module-desc">{{ module.description }}</p>
            </div>
            <div class="module-checkbox">
              <div v-if="selectedModules.includes(module.id)" class="checkbox-checked">
                <Check class="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>

        <button @click="useRecommendedModules" class="btn btn-secondary">
          <Sparkles class="w-4 h-4" /> Usar módulos recomendados
        </button>
      </div>

      <!-- Step 3: Expertise Level -->
      <div v-if="currentStep === 3" class="wizard-step">
        <h2 class="step-title">¿Cuál es tu nivel de experiencia?</h2>
        <p class="step-description">Esto ajustará el nivel de automatización y features disponibles</p>

        <div class="expertise-grid">
          <div
            v-for="level in expertiseLevels"
            :key="level.id"
            class="expertise-card"
            :class="{ 'selected': selectedExpertise === level.id }"
            @click="selectedExpertise = level.id"
          >
            <div class="expertise-icon">{{ level.icon }}</div>
            <div class="expertise-info">
              <h3 class="expertise-title">{{ level.title }}</h3>
              <p class="expertise-desc">{{ level.description }}</p>
              <div class="expertise-features">
                <span v-for="feature in level.features" :key="feature" class="feature-tag">
                  {{ feature }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: Platforms -->
      <div v-if="currentStep === 4" class="wizard-step">
        <h2 class="step-title">¿Cuáles son tus plataformas principales?</h2>
        <p class="step-description">Deja vacío para habilitar todas las plataformas</p>

        <div class="platforms-grid">
          <div
            v-for="platform in platforms"
            :key="platform.id"
            class="platform-card"
            :class="{ 'selected': selectedPlatforms.includes(platform.id) }"
            @click="togglePlatform(platform.id)"
          >
            <div class="platform-icon">{{ platform.icon }}</div>
            <div class="platform-info">
              <h3 class="platform-title">{{ platform.title }}</h3>
              <p class="platform-desc">{{ platform.description }}</p>
            </div>
            <div class="platform-checkbox">
              <div v-if="selectedPlatforms.includes(platform.id)" class="checkbox-checked">
                <Check class="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>

        <button @click="selectAllPlatforms" class="btn btn-secondary">
          <Globe class="w-4 h-4" /> Todas las plataformas
        </button>
      </div>

      <!-- Step 5: Custom Name -->
      <div v-if="currentStep === 5" class="wizard-step">
        <h2 class="step-title">Personaliza tu instalación</h2>
        <p class="step-description">Opcional: Define un nombre personalizado para tu aplicación</p>

        <div class="form-section">
          <div class="form-group">
            <label class="form-label">Nombre personalizado (opcional)</label>
            <input
              v-model="customName"
              type="text"
              class="form-input"
              placeholder="Ej: Mi Bug Bounty Hub"
              maxlength="50"
            />
            <p class="form-hint">Deja vacío para usar el nombre por defecto: OWNEX Alpha</p>
          </div>
        </div>
      </div>

      <!-- Step 6: Summary -->
      <div v-if="currentStep === 6" class="wizard-step">
        <h2 class="step-title">Resumen de configuración</h2>
        <p class="step-description">Revisa tu configuración antes de finalizar</p>

        <div class="summary-section">
          <div class="summary-card">
            <h3 class="summary-title">Caso de uso</h3>
            <p class="summary-value">{{ getUseCaseTitle(selectedUseCase) }}</p>
          </div>

          <div class="summary-card">
            <h3 class="summary-title">Módulos habilitados</h3>
            <div class="summary-tags">
              <span v-for="module in selectedModules" :key="module" class="summary-tag">
                {{ module }}
              </span>
            </div>
          </div>

          <div class="summary-card">
            <h3 class="summary-title">Nivel de experiencia</h3>
            <p class="summary-value">{{ getExpertiseTitle(selectedExpertise) }}</p>
            <p class="summary-detail">Automatización: {{ getAutomationLevel(selectedExpertise) }}</p>
          </div>

          <div class="summary-card">
            <h3 class="summary-title">Plataformas</h3>
            <div class="summary-tags">
              <span v-if="selectedPlatforms.length === 0" class="summary-tag">Todas</span>
              <span v-for="platform in selectedPlatforms" :key="platform" class="summary-tag">
                {{ platform }}
              </span>
            </div>
          </div>

          <div v-if="customName" class="summary-card">
            <h3 class="summary-title">Nombre personalizado</h3>
            <p class="summary-value">{{ customName }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ WIZARD FOOTER ═══ -->
    <footer class="wizard-footer">
      <button
        v-if="currentStep > 1"
        @click="previousStep"
        class="btn btn-secondary"
      >
        <ArrowLeft class="w-4 h-4" /> Anterior
      </button>

      <div class="footer-actions">
        <button
          v-if="currentStep < totalSteps"
          @click="nextStep"
          class="btn btn-primary"
          :disabled="!canProceed"
        >
          Siguiente <ArrowRight class="w-4 h-4" />
        </button>

        <button
          v-if="currentStep === totalSteps"
          @click="completeWizard"
          class="btn btn-success"
        >
          <Check class="w-4 h-4" /> Completar configuración
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, ArrowRight, Check, Globe, Sparkles } from '@lucide/vue'
import axios from 'axios'
import { computed, ref } from 'vue'

const currentStep = ref(1)
const totalSteps = 6

const selectedUseCase = ref('bug_bounty_researcher')
const selectedModules = ref<string[]>([])
const selectedExpertise = ref('intermediate')
const selectedPlatforms = ref<string[]>([])
const customName = ref('')

const useCases = [
  {
    id: 'bug_bounty_researcher',
    title: 'Bug Bounty Researcher',
    description: 'Investigación individual de vulnerabilidades',
    icon: '🔍',
  },
  {
    id: 'bug_bounty_company',
    title: 'Bug Bounty Company',
    description: 'Gestión empresarial de programas',
    icon: '🏢',
  },
  {
    id: 'cybersecurity_consultant',
    title: 'Cybersecurity Consultant',
    description: 'Consultoría y auditoría de seguridad',
    icon: '🛡️',
  },
  {
    id: 'penetration_tester',
    title: 'Penetration Tester',
    description: 'Testing de penetración profesional',
    icon: '💻',
  },
  { id: 'security_analyst', title: 'Security Analyst', description: 'Análisis de seguridad y amenazas', icon: '📊' },
  { id: 'developer', title: 'Developer', description: 'Desarrollo seguro de aplicaciones', icon: '⌨️' },
  { id: 'researcher', title: 'Researcher', description: 'Investigación en ciberseguridad', icon: '🔬' },
  { id: 'hobbyist', title: 'Hobbyist', description: 'Aprendizaje y práctica personal', icon: '🎮' },
  { id: 'other', title: 'Otro', description: 'Uso personalizado', icon: '⚙️' },
]

const availableModules = [
  { id: 'forge', title: 'Forge', description: 'Automatización de búsqueda de objetivos', icon: '🎯' },
  { id: 'pulse', title: 'Pulse', description: 'Monitoreo y análisis de targets', icon: '💓' },
  { id: 'vault', title: 'Vault', description: 'Gestión financiera y pagos', icon: '💰' },
  { id: 'atlas', title: 'Atlas', description: 'Colaboración y teamwork', icon: '🗺️' },
  { id: 'security', title: 'Security', description: 'Herramientas de seguridad', icon: '🔒' },
  { id: 'copilot', title: 'Copilot', description: 'Asistente IA integrado', icon: '🤖' },
  { id: 'analytics', title: 'Analytics', description: 'Análisis y métricas', icon: '📈' },
  { id: 'reports', title: 'Reports', description: 'Generación de reportes', icon: '📄' },
  { id: 'targets', title: 'Targets', description: 'Gestión de objetivos', icon: '🎯' },
  { id: 'integrations', title: 'Integrations', description: 'Integraciones externas', icon: '🔗' },
]

const expertiseLevels = [
  {
    id: 'beginner',
    title: 'Beginner',
    description: 'Principiante en bug bounty',
    icon: '🌱',
    features: ['Manual', 'Guided', 'Step-by-step'],
  },
  {
    id: 'intermediate',
    title: 'Intermediate',
    description: 'Experiencia moderada',
    icon: '🌿',
    features: ['Assisted', 'Templates', 'Semi-automated'],
  },
  {
    id: 'advanced',
    title: 'Advanced',
    description: 'Experiencia avanzada',
    icon: '🌳',
    features: ['Semi-automated', 'Custom workflows', 'Advanced analytics'],
  },
  {
    id: 'expert',
    title: 'Expert',
    description: 'Experto en el campo',
    icon: '🏔️',
    features: ['Fully automated', 'Custom everything', 'Enterprise features'],
  },
]

const platforms = [
  { id: 'hackerone', title: 'HackerOne', description: 'Plataforma más grande', icon: '🎯' },
  { id: 'bugcrowd', title: 'Bugcrowd', description: 'Programas diversos', icon: '🐛' },
  { id: 'intigriti', title: 'Intigriti', description: 'Plataforma europea', icon: '🇪🇺' },
  { id: 'yeswehack', title: 'YesWeHack', description: 'Plataforma francesa', icon: '🇫🇷' },
  { id: 'synack', title: 'Synack', description: 'Crowdsec elite', icon: '🛡️' },
]

const progress = computed(() => {
  return ((currentStep.value - 1) / (totalSteps - 1)) * 100
})

const canProceed = computed(() => {
  if (currentStep.value === 1) return selectedUseCase.value !== ''
  if (currentStep.value === 2) return true // Modules are optional
  if (currentStep.value === 3) return selectedExpertise.value !== ''
  if (currentStep.value === 4) return true // Platforms are optional
  if (currentStep.value === 5) return true // Custom name is optional
  if (currentStep.value === 6) return true
  return false
})

function nextStep() {
  if (currentStep.value < totalSteps) {
    currentStep.value++
  }
}

function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

function toggleModule(moduleId: string) {
  const index = selectedModules.value.indexOf(moduleId)
  if (index > -1) {
    selectedModules.value.splice(index, 1)
  } else {
    selectedModules.value.push(moduleId)
  }
}

function togglePlatform(platformId: string) {
  const index = selectedPlatforms.value.indexOf(platformId)
  if (index > -1) {
    selectedPlatforms.value.splice(index, 1)
  } else {
    selectedPlatforms.value.push(platformId)
  }
}

function useRecommendedModules() {
  const recommendedMap: Record<string, string[]> = {
    bug_bounty_researcher: ['forge', 'pulse', 'vault', 'security', 'copilot', 'analytics', 'reports', 'targets'],
    bug_bounty_company: [
      'forge',
      'pulse',
      'vault',
      'atlas',
      'security',
      'copilot',
      'analytics',
      'reports',
      'integrations',
    ],
    cybersecurity_consultant: [
      'forge',
      'pulse',
      'vault',
      'atlas',
      'security',
      'copilot',
      'analytics',
      'reports',
      'targets',
    ],
    penetration_tester: ['forge', 'pulse', 'vault', 'security', 'copilot', 'analytics', 'reports', 'targets'],
    security_analyst: ['forge', 'pulse', 'atlas', 'security', 'copilot', 'analytics', 'reports'],
    developer: ['forge', 'security', 'copilot', 'analytics', 'targets'],
    researcher: ['forge', 'pulse', 'atlas', 'copilot', 'analytics', 'reports'],
    hobbyist: ['forge', 'pulse', 'copilot', 'analytics'],
    other: ['forge', 'pulse', 'copilot', 'analytics'],
  }

  selectedModules.value = recommendedMap[selectedUseCase.value] || []
}

function selectAllPlatforms() {
  selectedPlatforms.value = platforms.map((p) => p.id)
}

function getUseCaseTitle(useCaseId: string) {
  const useCase = useCases.find((uc) => uc.id === useCaseId)
  return useCase?.title || useCaseId
}

function getExpertiseTitle(expertiseId: string) {
  const expertise = expertiseLevels.find((el) => el.id === expertiseId)
  return expertise?.title || expertiseId
}

function getAutomationLevel(expertiseId: string) {
  const levels: Record<string, string> = {
    beginner: 'Manual',
    intermediate: 'Asistido',
    advanced: 'Semi-automatizado',
    expert: 'Completamente automatizado',
  }
  return levels[expertiseId] || 'Asistido'
}

async function completeWizard() {
  try {
    const response = await axios.post('/api/setup/personalization', {
      use_case: selectedUseCase.value,
      modules: selectedModules.value,
      custom_name: customName.value,
      expertise_level: selectedExpertise.value,
      primary_platforms: selectedPlatforms.value.length > 0 ? selectedPlatforms.value : ['all'],
    })

    if (response.data.status === 'ok') {
      alert('¡Configuración completada con éxito!')
      // Redirect to dashboard or next step
      window.location.href = '/'
    } else {
      alert('Error: ' + response.data.message)
    }
  } catch (error) {
    console.error('Error completing wizard:', error)
    alert('Error al completar la configuración')
  }
}
</script>

<style scoped>
/* ═══ STEAM-STYLE WIZARD ═══ */
.personalization-wizard {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  min-height: 100vh;
  padding: 2rem;
  font-family: 'Inter', system-ui, sans-serif;
}

/* ═══ WIZARD HEADER ═══ */
.wizard-header {
  margin-bottom: 3rem;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 2rem;
  margin-bottom: 2rem;
}

.logo-mark {
  position: relative;
  width: 64px;
  height: 64px;
}

.o-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid;
}

.o-ring-outer {
  inset: 0;
  border-color: rgba(255, 255, 255, 0.3);
  animation: pulse-ring 3s ease-in-out infinite;
}

.o-ring-inner {
  inset: 12px;
  border-color: rgba(255, 255, 255, 0.5);
  animation: pulse-ring 3s ease-in-out infinite 1s;
}

.o-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #60A5FA;
  animation: pulse-dot 2s ease-in-out infinite;
}

.o-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: white;
}

@keyframes pulse-ring {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.05); }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 0.7; transform: translate(-50%, -50%) scale(1.2); }
}

.wizard-title {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  font-family: 'Inter', system-ui, sans-serif;
  letter-spacing: 0.05em;
}

.wizard-subtitle {
  color: #94A3B8;
  font-size: 1rem;
  margin-top: 0.5rem;
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #60A5FA, #34D399);
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.progress-text {
  color: #94A3B8;
  font-size: 0.875rem;
  font-weight: 600;
}

/* ═══ WIZARD CONTENT ═══ */
.wizard-content {
  max-width: 1200px;
  margin: 0 auto;
}

.wizard-step {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.5rem;
}

.step-description {
  color: #94A3B8;
  margin-bottom: 2rem;
}

/* ═══ USE CASE GRID ═══ */
.use-case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.use-case-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.use-case-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.use-case-card.selected {
  border-color: #60A5FA;
  background: rgba(255, 255, 255, 0.1);
}

.use-case-icon {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.use-case-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.use-case-desc {
  color: #94A3B8;
  font-size: 0.875rem;
}

/* ═══ MODULES GRID ═══ */
.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.module-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
  position: relative;
}

.module-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.module-card.selected {
  border-color: #60A5FA;
  background: rgba(255, 255, 255, 0.1);
}

.module-icon {
  font-size: 1.5rem;
  margin-bottom: 0.75rem;
}

.module-title {
  font-size: 1rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.module-desc {
  color: #94A3B8;
  font-size: 0.875rem;
}

.module-checkbox {
  position: absolute;
  top: 1rem;
  right: 1rem;
}

.checkbox-checked {
  color: #34D399;
}

/* ═══ EXPERTISE GRID ═══ */
.expertise-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.expertise-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.expertise-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.expertise-card.selected {
  border-color: #60A5FA;
  background: rgba(255, 255, 255, 0.1);
}

.expertise-icon {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.expertise-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.expertise-desc {
  color: #94A3B8;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.expertise-features {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.feature-tag {
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 9999px;
  font-size: 0.75rem;
  color: #60A5FA;
}

/* ═══ PLATFORMS GRID ═══ */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.platform-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
  position: relative;
}

.platform-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.platform-card.selected {
  border-color: #60A5FA;
  background: rgba(255, 255, 255, 0.1);
}

.platform-icon {
  font-size: 1.5rem;
  margin-bottom: 0.75rem;
}

.platform-title {
  font-size: 1rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.platform-desc {
  color: #94A3B8;
  font-size: 0.875rem;
}

.platform-checkbox {
  position: absolute;
  top: 1rem;
  right: 1rem;
}

/* ═══ FORM SECTION ═══ */
.form-section {
  max-width: 600px;
}

.form-group {
  margin-bottom: 2rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.375rem;
  color: white;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
}

.form-input:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.5);
}

.form-hint {
  color: #94A3B8;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

/* ═══ SUMMARY SECTION ═══ */
.summary-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.summary-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  backdrop-filter: blur(10px);
}

.summary-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
}

.summary-detail {
  color: #94A3B8;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.summary-tag {
  padding: 0.25rem 0.5rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 9999px;
  font-size: 0.75rem;
  color: #60A5FA;
}

/* ═══ WIZARD FOOTER ═══ */
.wizard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.footer-actions {
  display: flex;
  gap: 1rem;
}

.btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid;
  transition: all 0.2s;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.4);
  color: #60A5FA;
}

.btn-primary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.6);
}

.btn-secondary {
  background: rgba(100, 116, 139, 0.2);
  border-color: rgba(100, 116, 139, 0.4);
  color: #94A3B8;
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(100, 116, 139, 0.3);
  border-color: rgba(100, 116, 139, 0.6);
}

.btn-success {
  background: rgba(52, 211, 153, 0.2);
  border-color: rgba(52, 211, 153, 0.4);
  color: #34D399;
}

.btn-success:hover:not(:disabled) {
  background: rgba(52, 211, 153, 0.3);
  border-color: rgba(52, 211, 153, 0.6);
}
</style>