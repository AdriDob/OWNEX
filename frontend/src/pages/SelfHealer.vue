<template>
  <div class="self-healer-page animate-in">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">Self-Healer</h1>
        <p class="page-subtitle">Autonomía de reparación: detecta, diagnostica, parchea, despliega y aprende</p>
      </div>
      <div class="header-actions">
        <StatusBadge :status="status.scheduler_running ? 'running' : 'stopped'" :label="status.scheduler_running ? 'Activo' : 'Detenido'" />
        <button @click="toggleScheduler" class="btn-primary" :class="{ 'btn-warning': status.scheduler_running }">
          {{ status.scheduler_running ? 'Detener' : 'Iniciar' }} Scheduler
        </button>
        <button @click="triggerScan" class="btn-secondary" :disabled="scanning">
          <span v-if="scanning" class="spinner"></span>
          Escanear Ahora
        </button>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <StatCard title="Problemas Detectados" :value="stats.problems_found" icon="⚠️" color="warning" />
      <StatCard title="Diagnosticados" :value="stats.problems_diagnosed" icon="🔍" color="info" />
      <StatCard title="Fixes Exitosos" :value="stats.fixes_succeeded" icon="✅" color="success" />
      <StatCard title="Fixes Fallidos" :value="stats.fixes_failed" icon="❌" color="danger" />
      <StatCard title="Tasa Éxito" :value="stats.fixes_attempted ? Math.round((stats.fixes_succeeded / stats.fixes_attempted) * 100) + '%' : '—'" icon="📊" color="primary" />
      <StatCard title="Último Ciclo" :value="formatRelativeTime(stats.cycle_end)" icon="🕐" color="muted" />
    </div>

    <!-- Tabs -->
    <div class="tabs-container">
      <div class="tabs-header">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
        >
          {{ tab.label }}
          <span v-if="tab.count !== undefined" class="tab-count">{{ tab.count }}</span>
        </button>
      </div>

      <!-- Problems Tab -->
      <div v-if="activeTab === 'problems'" class="tab-content">
        <ProblemsList
          :problems="problems"
          @view-diagnosis="viewDiagnosis"
          @approve-fix="approveFix"
        />
      </div>

      <!-- Diagnoses Tab -->
      <div v-if="activeTab === 'diagnoses'" class="tab-content">
        <DiagnosesList :diagnoses="diagnoses" />
      </div>

      <!-- Fix Plans Tab -->
      <div v-if="activeTab === 'plans'" class="tab-content">
        <FixPlansList
          :plans="fixPlans"
          @approve="approveFix"
          @reject="rejectFix"
        />
      </div>

      <!-- Patches Tab -->
      <div v-if="activeTab === 'patches'" class="tab-content">
        <PatchesList :patches="patches" />
      </div>

      <!-- Deployments Tab -->
      <div v-if="activeTab === 'deployments'" class="tab-content">
        <DeploymentsList
          :deployments="deployments"
          @rollback="rollbackDeployment"
        />
      </div>

      <!-- Learning Tab -->
      <div v-if="activeTab === 'learning'" class="tab-content">
        <LearningPanel
          :stats="learningStats"
          :successful-patterns="successfulPatterns"
          :failed-patterns="failedPatterns"
        />
      </div>

      <!-- Settings Tab -->
      <div v-if="activeTab === 'settings'" class="tab-content">
        <SettingsPanel
          :config="config"
          @update="updateConfig"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

// Components
import StatCard from '@/components/ui/StatCard.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ProblemsList from '@/components/self-healer/ProblemsList.vue'
import DiagnosesList from '@/components/self-healer/DiagnosesList.vue'
import FixPlansList from '@/components/self-healer/FixPlansList.vue'
import PatchesList from '@/components/self-healer/PatchesList.vue'
import DeploymentsList from '@/components/self-healer/DeploymentsList.vue'
import LearningPanel from '@/components/self-healer/LearningPanel.vue'
import SettingsPanel from '@/components/self-healer/SettingsPanel.vue'

const router = useRouter()

// State
const activeTab = ref('problems')
const scanning = ref(false)
const status = ref<any>({})
const config = ref<any>({})
const stats = ref({
  problems_found: 0,
  problems_diagnosed: 0,
  fixes_attempted: 0,
  fixes_succeeded: 0,
  fixes_failed: 0,
  cycle_end: null,
})
const problems = ref<any[]>([])
const diagnoses = ref<any[]>([])
const fixPlans = ref<any[]>([])
const patches = ref<any[]>([])
const deployments = ref<any[]>([])
const learningStats = ref<any>({})
const successfulPatterns = ref<any[]>([])
const failedPatterns = ref<any[]>([])

const tabs = [
  { id: 'problems', label: 'Problemas', count: 0 },
  { id: 'diagnoses', label: 'Diagnósticos', count: 0 },
  { id: 'plans', label: 'Planes de Fix', count: 0 },
  { id: 'patches', label: 'Parches', count: 0 },
  { id: 'deployments', label: 'Despliegues', count: 0 },
  { id: 'learning', label: 'Aprendizaje', count: 0 },
  { id: 'settings', label: 'Configuración', count: 0 },
]

async function loadStatus() {
  try {
    const [statusRes, configRes, statsRes] = await Promise.all([
      axios.get('/api/self-healer/status'),
      axios.get('/api/self-healer/config'),
      axios.get('/api/self-healer/scan', { params: { force: false } }).catch(() => ({ data: {} })),
    ])
    status.value = statusRes.data
    config.value = configRes.data
    stats.value = statsRes.data || {}
    updateTabCounts()
  } catch (e) {
    console.error('Failed to load status:', e)
  }
}

async function loadAllData() {
  try {
    const [problemsRes, diagnosesRes, plansRes, patchesRes, deploymentsRes, learningRes, patternsRes, failedRes] = await Promise.all([
      axios.get('/api/self-healer/problems'),
      axios.get('/api/self-healer/diagnoses'),
      axios.get('/api/self-healer/fix-plans'),
      axios.get('/api/self-healer/patches'),
      axios.get('/api/self-healer/deployments'),
      axios.get('/api/self-healer/learning/stats'),
      axios.get('/api/self-healer/learning/patterns/successful'),
      axios.get('/api/self-healer/learning/patterns/failed'),
    ])
    problems.value = problemsRes.data
    diagnoses.value = diagnosesRes.data
    fixPlans.value = plansRes.data
    patches.value = patchesRes.data
    deployments.value = deploymentsRes.data
    learningStats.value = learningRes.data
    successfulPatterns.value = patternsRes.data
    failedPatterns.value = failedRes.data
    updateTabCounts()
  } catch (e) {
    console.error('Failed to load data:', e)
  }
}

function updateTabCounts() {
  tabs[0].count = problems.value.length
  tabs[1].count = diagnoses.value.length
  tabs[2].count = fixPlans.value.length
  tabs[3].count = patches.value.length
  tabs[4].count = deployments.value.length
}

async function toggleScheduler() {
  try {
    if (status.value.scheduler_running) {
      await axios.post('/api/self-healer/scheduler/stop')
    } else {
      await axios.post('/api/self-healer/scheduler/start')
    }
    await loadStatus()
  } catch (e) {
    console.error('Failed to toggle scheduler:', e)
  }
}

async function triggerScan() {
  scanning.value = true
  try {
    const res = await axios.post('/api/self-healer/scan', { force: true })
    stats.value = res.data
    await loadAllData()
  } catch (e) {
    console.error('Scan failed:', e)
  } finally {
    scanning.value = false
  }
}

async function updateConfig(newConfig: any) {
  try {
    await axios.put('/api/self-healer/config', newConfig)
    await loadStatus()
  } catch (e) {
    console.error('Config update failed:', e)
  }
}

async function approveFix(planId: string) {
  try {
    await axios.post(`/api/self-healer/fix-plans/${planId}/approve`, { approved: true })
    await loadAllData()
  } catch (e) {
    console.error('Approve failed:', e)
  }
}

async function rejectFix(planId: string) {
  try {
    await axios.post(`/api/self-healer/fix-plans/${planId}/approve`, { approved: false })
    await loadAllData()
  } catch (e) {
    console.error('Reject failed:', e)
  }
}

async function rollbackDeployment(deploymentId: string) {
  try {
    await axios.post(`/api/self-healer/deployments/${deploymentId}/rollback`)
    await loadAllData()
  } catch (e) {
    console.error('Rollback failed:', e)
  }
}

function formatRelativeTime(isoString: string | null) {
  if (!isoString) return '—'
  const diff = Date.now() - new Date(isoString).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  if (days > 0) return `hace ${days}d`
  if (hours > 0) return `hace ${hours}h`
  if (minutes > 0) return `hace ${minutes}m`
  return 'justo ahora'
}

onMounted(() => {
  loadStatus()
  loadAllData()
  // Poll status every 30 seconds
  const interval = setInterval(loadStatus, 30000)
  onUnmounted(() => clearInterval(interval))
})

// Watch for status changes
watch(status, (newStatus) => {
  if (newStatus.scheduler_running !== undefined) {
    // Status updated
  }
}, { deep: true })
</script>

<style scoped>
.self-healer-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px.
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--ownex-bg-surface);
  font-family: 'Space Grotesk', 'Inter', sans-serif;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--ownex-text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap.
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px.
}

.tabs-container {
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden.
}

.tabs-header {
  display: flex;
  gap: 4px;
  padding: 8px;
  background: var(--ownex-bg-base);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  overflow-x: auto.
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--ownex-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease.
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--ownex-text-secondary).
}

.tab-btn.active {
  background: rgba(0, 213, 255, 0.1);
  color: var(--ownex-accent).
}

.tab-count {
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600.
}

.tab-btn.active .tab-count {
  background: rgba(0, 213, 255, 0.3);
  color: var(--ownex-accent).
}

.tab-content {
  padding: 24px;
  min-height: 400px.
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start.
  }
  .header-actions {
    width: 100%;
    justify-content: space-between.
  }
}
</style>