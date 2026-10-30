<template>
  <div class="content-factory-dashboard">
    <div class="dashboard-header">
      <div class="header-content">
        <div class="header-left">
          <h1>Content Factory</h1>
          <p class="subtitle">Generación automatizada de videos para YouTube Shorts</p>
        </div>
        <div class="header-actions">
          <Button variant="secondary" @click="loadAll">
            <Icon name="refresh-cw" />
            Actualizar
          </Button>
          <Button variant="primary" @click="handleSeedTopics">
            <Icon name="seedling" />
            Sembrar Topics
          </Button>
          <Button variant="primary" @click="handleGenerateRandom">
            <Icon name="zap" />
            Generar Ahora
          </Button>
        </div>
      </div>

      <div class="kpi-bar">
        <KpiCard
          v-for="stat in kpiStats"
          :key="stat.key"
          :label="stat.label"
          :value="stat.value"
          :icon="stat.icon"
          :trend="stat.trend"
        />
      </div>
    </div>

    <Tabs v-model="activeTab" class="dashboard-tabs">
      <TabPanel name="overview">
        <OverviewView :stats="overviewStats" :recentJobs="recentJobs" :loading="loading" />
      </TabPanel>

      <TabPanel name="topics">
        <TopicsView
          :topics="topics"
          :loading="loadingTopics"
          @refresh="loadTopics"
          @generate="handleGenerateFromTopic"
        />
      </TabPanel>

      <TabPanel name="queue">
        <QueueView
          :jobs="jobs"
          :loading="loadingJobs"
          @retry="handleRetry"
          @view="viewJobDetails"
        />
      </TabPanel>

      <TabPanel name="analytics">
        <AnalyticsView :analytics="analytics" :loading="loadingAnalytics" />
      </TabPanel>

      <TabPanel name="settings">
        <SettingsView
          :config="channelConfig"
          @save="saveConfig"
          @test="testConnection"
        />
      </TabPanel>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  fetchContentFactoryDashboard,
  fetchContentFactoryTopics,
  fetchContentFactoryJobs,
  fetchContentFactoryAnalytics,
  generateVideo,
  runQualityGate,
  retryJob as apiRetryJob,
  seedTopics,
  fetchChannelConfig,
  updateChannelConfig,
  testYouTubeConnection,
} from '@/services/ownexData'
import type {
  ContentFactoryDashboard,
  ContentFactoryTopic,
  ContentFactoryJob,
  ContentFactoryAnalytics,
  ChannelConfig,
} from '@/services/ownexData'
import {
  Tabs,
  TabPanel,
  Button,
  Icon,
  KpiCard,
  Tabs,
} from '@/components/ui'
import OverviewView from './ContentFactoryOverview.vue'
import TopicsView from './ContentFactoryTopics.vue'
import QueueView from './ContentFactoryQueue.vue'
import AnalyticsView from './ContentFactoryAnalytics.vue'
import SettingsView from './ContentFactorySettings.vue'

const loading = ref(true)
const loadingJobs = ref(false)
const loadingTopics = ref(false)
const loadingAnalytics = ref(false)
const error = ref('')
const activeTab = ref('overview')
const channelId = ref(1) // Default channel

const dashboard = ref<ContentFactoryDashboard | null>(null)
const topics = ref<any[]>([])
const jobs = ref<any[]>([])
const recentJobs = ref<any[]>([])
const analytics = ref<any | null>(null)
const channelConfig = ref<any | null>(null)
const error = ref('')

const kpiStats = computed(() => {
  if (!dashboard.value) return []
  return [
    {
      key: 'generated',
      label: 'Generados Hoy',
      value: dashboard.value?.today?.generated || 0,
      icon: 'cpu',
      trend: 'up',
    },
    {
      key: 'published',
      label: 'Publicados Hoy',
      value: dashboard.value?.today?.published || 0,
      icon: 'upload',
      trend: 'up',
    },
    {
      key: 'views',
      label: 'Vistas (7d)',
      value: formatNumber(dashboard.value?.week?.views || 0),
      icon: 'eye',
      trend: 'up',
    },
    {
      key: 'revenue',
      label: 'Ingresos Est. (7d)',
      value: '$' + (dashboard.value?.week?.estimated_revenue_usd || 0).toFixed(2),
      icon: 'dollar-sign',
      trend: 'up',
    },
  ]
}

const loading = computed(() => loadingJobs.value || loadingTopics.value)

async function loadAll() {
  error.value = ''
  try {
    const [dash, top, jbs, anl, cfg] = await Promise.allSettled([
      fetchContentFactoryDashboard(1),
      fetchContentFactoryTopics(1),
      fetchContentFactoryJobs(1),
      fetchContentFactoryAnalytics(1, 30),
      fetchChannelConfig(1),
    ])

    if (dash.status === 'fulfilled') dashboard.value = dash.value
    if (top.status === 'fulfilled') topics.value = top.value
    if (jbs.status === 'fulfilled') {
      jobs.value = jbs.value
      recentJobs.value = jbs.value.slice(0, 10)
    }
    if (anl.status === 'fulfilled') analytics.value = anl.value
    if (cfg.status === 'fulfilled') channelConfig.value = cfg.value

    const errors = [dash, top, jbs, anl, cfg].filter(r => r.status === 'rejected')
    if (errors.length > 0) {
      error.value = errors.map(e => e.reason?.message).join(', ')
    }
  } catch (e: any) {
    error.value = e.message || 'Error cargando dashboard'
  } finally {
    loading.value = false
  }
}

async function loadTopics() {
  loadingTopics.value = true
  try {
    topics.value = await fetchContentFactoryTopics(1)
  } catch (e: any) {
    console.error('Error loading topics:', e)
  } finally {
    loadingTopics.value = false
  }
}

async function loadJobs() {
  loadingJobs.value = true
  try {
    jobs.value = await fetchContentFactoryJobs(1)
  } catch (e: any) {
    console.error('Error loading jobs:', e)
  } finally {
    loadingJobs.value = false
  }
}

async function loadAnalytics() {
  loadingAnalytics.value = true
  try {
    analytics.value = await fetchContentFactoryAnalytics(1, 30)
  } catch (e: any) {
    console.error('Error loading analytics:', e)
  } finally {
    loadingAnalytics.value = false
  }
}

async function handleGenerateRandom() {
  try {
    const result = await generateVideo(1, {})
    await loadJobs()
  } catch (e: any) {
    console.error('Error generating:', e)
  }
}

async function handleGenerateFromTopic(topicId: number) {
  try {
    const result = await generateVideo(1, { topic_id: topicId })
    await loadJobs()
  } catch (e: any) {
    console.error('Error generating from topic:', e)
  }
}

async function handleRetry(jobId: number) {
  try {
    await retryJob(1, jobId)
    await loadJobs()
  } catch (e: any) {
    console.error('Error retrying:', e)
  }
}

async function handleSeedTopics() {
  try {
    await seedTopics(1)
    await loadTopics()
  } catch (e: any) {
    console.error('Error seeding topics:', e)
  }
}

async function saveConfig(config: Partial<ChannelConfig>) {
  try {
    await updateChannelConfig(1, config)
    await fetchChannelConfig(1).then(c => channelConfig.value = c)
  } catch (e: any) {
    console.error('Error saving config:', e)
  }
}

async function testConnection() {
  try {
    const result = await testYouTubeConnection(1)
    alert(result.success ? 'Conexión exitosa' : 'Error: ' + result.error)
  } catch (e: any) {
    alert('Error: ' + e.message)
  }
}

async function viewJobDetails(job: any) {
  // Navigate to job detail or show modal
  console.log('View job:', job)
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

onMounted(() => {
  loadAll()
  // Auto-refresh every 30 seconds
  setInterval(() => {
    if (!loading.value && !document.hidden) {
      loadJobs()
    }
  }, 30000)
})

// Refresh when tab becomes visible
watch(() => document.hidden, (hidden) => {
  if (!hidden && !loading.value) {
    loadJobs()
  }
})
</script>

<style scoped>
.content-factory-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: calc(100vh - 120px);
  padding: 24px;
  background: var(--bg-primary);
}

.dashboard-header {
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.kpi-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.dashboard-tabs {
  height: calc(100% - 200px);
  min-height: 500px;
}

.dashboard-tabs :deep(.tabs-content) {
  height: calc(100% - 48px);
}

@media (max-width: 1024px) {
  .content-factory-dashboard {
    padding: 16px;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
    justify-content: stretch;
  }

  .header-actions > * {
    flex: 1;
  }
}
</style>