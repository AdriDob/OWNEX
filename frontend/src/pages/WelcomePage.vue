<template>
  <div class="welcome-page">
    <!-- ═══ MODERN NAVBAR ═══ -->
    <ModernNavbar />

    <!-- ═══ HERO SECTION ═══ -->
    <section class="hero-section">
      <div class="hero-content">
        <div class="hero-mark">
          <div class="o-ring o-ring-outer" />
          <div class="o-ring o-ring-inner" />
          <div class="o-dot" />
          <div class="o-core" />
        </div>
        <div class="hero-text">
          <h1 class="hero-title">OWNEX Alpha</h1>
          <p class="hero-subtitle">Sistema de Inteligencia Autónoma para Bug Bounty</p>
          <div class="hero-features">
            <div class="feature-pill">
              <span class="feature-icon">🎯</span>
              <span class="feature-text">Target Discovery</span>
            </div>
            <div class="feature-pill">
              <span class="feature-icon">🔍</span>
              <span class="feature-text">Vulnerability Analysis</span>
            </div>
            <div class="feature-pill">
              <span class="feature-icon">📊</span>
              <span class="feature-text">Automated Reporting</span>
            </div>
            <div class="feature-pill">
              <span class="feature-icon">🧙</span>
              <span class="feature-text">MERLIN AI Assistant</span>
            </div>
          </div>
        </div>
      </div>
      <div class="hero-merlin">
        <div class="merlin-mini">
          <div class="merlin-avatar-mini">
            <div class="avatar-retro-border-mini"></div>
            <div class="avatar-icon-mini">🧙</div>
          </div>
          <div class="merlin-bubble">
            <p class="merlin-greeting">{{ merlinGreeting }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ QUICK ACTIONS ═══ -->
    <section class="quick-actions-section">
      <h2 class="section-title">Acciones Rápidas</h2>
      <div class="actions-grid">
        <div @click="navigateTo('/merlin')" class="action-card">
          <div class="action-icon-large">🧙</div>
          <h3 class="action-title">Hablar con MERLIN</h3>
          <p class="action-desc">Tu asistente de inteligencia autónoma</p>
          <div class="action-arrow">→</div>
        </div>
        <div @click="navigateTo('/targets/discovery')" class="action-card">
          <div class="action-icon-large">🎯</div>
          <h3 class="action-title">Discovery</h3>
          <p class="action-desc">Descubrir nuevos objetivos</p>
          <div class="action-arrow">→</div>
        </div>
        <div @click="navigateTo('/intelligence/findings')" class="action-card">
          <div class="action-icon-large">🔍</div>
          <h3 class="action-title">Hallazgos</h3>
          <p class="action-desc">Gestionar vulnerabilidades encontradas</p>
          <div class="action-arrow">→</div>
        </div>
        <div @click="navigateTo('/reports/queue')" class="action-card">
          <div class="action-icon-large">📊</div>
          <h3 class="action-title">Reportes</h3>
          <p class="action-desc">Cola de reportes priorizada</p>
          <div class="action-arrow">→</div>
        </div>
        <div @click="navigateTo('/capital')" class="action-card">
          <div class="action-icon-large">💰</div>
          <h3 class="action-title">Capital</h3>
          <p class="action-desc">Gestión financiera y pagos</p>
          <div class="action-arrow">→</div>
        </div>
        <div @click="navigateTo('/operations/version-backup')" class="action-card">
          <div class="action-icon-large">💾</div>
          <h3 class="action-title">Backup</h3>
          <p class="action-desc">Sistema de backup de versiones</p>
          <div class="action-arrow">→</div>
        </div>
      </div>
    </section>

    <!-- ═══ SYSTEM STATUS ═══ -->
    <section class="system-status-section">
      <h2 class="section-title">Estado del Sistema</h2>
      <div class="status-grid">
        <div class="status-card">
          <div class="status-header">
            <span class="status-icon">🟢</span>
            <span class="status-label">OWNEX Alpha</span>
          </div>
          <div class="status-value">Online</div>
          <div class="status-detail">Sistema operativo</div>
        </div>
        <div class="status-card">
          <div class="status-header">
            <span class="status-icon">🟢</span>
            <span class="status-label">MERLIN</span>
          </div>
          <div class="status-value">Ready</div>
          <div class="status-detail">Asistente activo</div>
        </div>
        <div class="status-card">
          <div class="status-header">
            <span class="status-icon" :class="systemStatus.scheduler.icon">{{ systemStatus.scheduler.icon }}</span>
            <span class="status-label">Scheduler</span>
          </div>
          <div class="status-value">{{ systemStatus.scheduler.status }}</div>
          <div class="status-detail">{{ systemStatus.scheduler.detail }}</div>
        </div>
        <div class="status-card">
          <div class="status-header">
            <span class="status-icon" :class="systemStatus.database.icon">{{ systemStatus.database.icon }}</span>
            <span class="status-label">Database</span>
          </div>
          <div class="status-value">{{ systemStatus.database.status }}</div>
          <div class="status-detail">{{ systemStatus.database.detail }}</div>
        </div>
      </div>
    </section>

    <!-- ═══ RECENT ACTIVITY ═══ -->
    <section class="recent-activity-section">
      <h2 class="section-title">Actividad Reciente</h2>
      <div class="activity-list">
        <div v-for="activity in recentActivities" :key="activity.id" class="activity-item">
          <div class="activity-icon">{{ activity.icon }}</div>
          <div class="activity-content">
            <div class="activity-title">{{ activity.title }}</div>
            <div class="activity-desc">{{ activity.description }}</div>
          </div>
          <div class="activity-time">{{ formatTime(activity.timestamp) }}</div>
        </div>
      </div>
    </section>

    <!-- ═══ QUICK STATS ═══ -->
    <section class="quick-stats-section">
      <h2 class="section-title">Estadísticas Rápidas</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">🎯</div>
          <div class="stat-value">{{ stats.targets }}</div>
          <div class="stat-label">Targets Activos</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🔍</div>
          <div class="stat-value">{{ stats.findings }}</div>
          <div class="stat-label">Hallazgos Totales</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-value">{{ stats.reports }}</div>
          <div class="stat-label">Reportes del Mes</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">💰</div>
          <div class="stat-value">${{ stats.revenue.toLocaleString() }}</div>
          <div class="stat-label">Ingresos del Mes</div>
        </div>
      </div>
    </section>

    <!-- ═══ CORE VISUALIZATION ═══ -->
    <section class="core-viz-section">
      <h2 class="section-title">OWNEX Core Intelligence</h2>
      <p class="section-subtitle">Módulos orbitando alrededor de la inteligencia central</p>
      <CoreVisualization class="core-viz-canvas" />
    </section>

    <!-- ═══ THEME SHOWCASE ═══ -->
    <section class="theme-showcase-section">
      <h2 class="section-title">Temas Visuales</h2>
      <p class="section-subtitle">Elige la identidad visual que mejor se adapte a tu flujo de trabajo</p>
      <div class="theme-cards">
        <div
          v-for="t in themeNames"
          :key="t.id"
          @click="setTheme(t.id)"
          class="theme-card"
          :class="{ active: currentTheme?.id === t.id }"
        >
          <div class="theme-preview" :style="getThemePreviewStyle(t.id)">
            <div class="theme-preview-core" :style="getThemeCoreStyle(t.id)" />
          </div>
          <div class="theme-info">
            <h3 class="theme-name">{{ t.name }}</h3>
            <p class="theme-desc">{{ t.description }}</p>
            <span v-if="currentTheme?.id === t.id" class="theme-active-badge">Activo</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ FOOTER ═══ -->
    <footer class="welcome-footer">
      <div class="footer-content">
        <p class="footer-text">OWNEX Alpha — Sistema de Inteligencia Autónoma para Bug Bounty</p>
        <p class="footer-sub">Versión 1.0.0 — © 2024</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeEngine } from '@/composables/useThemeEngine'
import CoreVisualization from '@/components/CoreVisualization.vue'
import ModernNavbar from '@/components/layout/ModernNavbar.vue'

const router = useRouter()
const { themeNames, currentTheme, setTheme } = useThemeEngine()

const merlinGreeting = ref('¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma. ¿En qué puedo ayudarte hoy?')

const systemStatus = ref({
  scheduler: {
    icon: '🟢',
    status: 'Running',
    detail: '4 workflows activos'
  },
  database: {
    icon: '🟢',
    status: 'Connected',
    detail: 'SQLite local'
  }
})

const recentActivities = ref([
  {
    id: 1,
    icon: '🎯',
    title: 'Nuevo target descubierto',
    description: 'example.com agregado al sistema',
    timestamp: new Date(Date.now() - 3600000)
  },
  {
    id: 2,
    icon: '🔍',
    title: 'Vulnerabilidad encontrada',
    description: 'XSS en /search endpoint',
    timestamp: new Date(Date.now() - 7200000)
  },
  {
    id: 3,
    icon: '📊',
    title: 'Reporte generado',
    description: 'Reporte #1234 enviado a HackerOne',
    timestamp: new Date(Date.now() - 86400000)
  },
  {
    id: 4,
    icon: '💰',
    title: 'Pago recibido',
    description: '$500 por validación de reporte',
    timestamp: new Date(Date.now() - 172800000)
  }
])

const stats = ref({
  targets: 42,
  findings: 156,
  reports: 23,
  revenue: 4500
})

function formatTime(date: Date) {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (hours < 1) return 'Hace menos de 1 hora'
  if (hours < 24) return `Hace ${hours} horas`
  if (days < 7) return `Hace ${days} días`
  return date.toLocaleDateString()
}

function navigateTo(path: string) {
  router.push(path)
}

onMounted(() => {
  // Rotate merlin greetings
  const greetings = [
    '¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma. ¿En qué puedo ayudarte hoy?',
    '¡Bienvenido de nuevo! MERLIN está listo para asistirte.',
    'MERLIN aquí. ¿En qué puedo ayudarte hoy?',
    '¡Saludos! MERLIN reportándose para el servicio.',
    '¡Hey! MERLIN online y listo para rockear.'
  ]

  setInterval(() => {
    merlinGreeting.value = greetings[Math.floor(Math.random() * greetings.length)]
  }, 10000)
})

function getThemePreviewStyle(themeId: string) {
  const theme = themeNames.value.find(t => t.id === themeId)
  if (!theme) return {}
  return {
    background: theme.id === 'tesla' ? '#000000' : '#05060A',
  }
}

function getThemeCoreStyle(themeId: string) {
  const theme = themeNames.value.find(t => t.id === themeId)
  if (!theme) return {}
  // We need to get the actual theme definition for colors
  return {
    background: theme.id === 'tesla' ? '#00d5ff' : '#00D5FF',
  }
}
</script>

<style scoped>
/* ═══ WELCOME PAGE — STEAM-LIKE DESIGN ═══ */
.welcome-page {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f3460 100%);
  min-height: 100vh;
  padding: 2rem;
  font-family: 'Inter', system-ui, sans-serif;
  color: #e8e8e8;
}

/* ═══ HERO SECTION ═══ */
.hero-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4rem;
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-content {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.hero-mark {
  position: relative;
  width: 120px;
  height: 120px;
}

.o-ring {
  position: absolute;
  border-radius: 50%;
  border: 3px solid;
}

.o-ring-outer {
  inset: 0;
  border-color: rgba(255, 255, 255, 0.3);
  animation: pulse-ring 3s ease-in-out infinite;
}

.o-ring-inner {
  inset: 24px;
  border-color: rgba(255, 255, 255, 0.5);
  animation: pulse-ring 3s ease-in-out infinite 1s;
}

.o-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #60A5FA;
  animation: pulse-dot 2s ease-in-out infinite;
}

.o-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
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

.hero-text {
  max-width: 600px;
}

.hero-title {
  font-size: 3rem;
  font-weight: 700;
  color: white;
  font-family: 'Inter', system-ui, sans-serif;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.hero-subtitle {
  font-size: 1.25rem;
  color: #94A3B8;
  margin-bottom: 1.5rem;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.feature-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 9999px;
  font-size: 0.875rem;
  color: #60A5FA;
  transition: all 0.2s;
}

.feature-pill:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 1rem;
}

.hero-merlin {
  position: relative;
}

.merlin-mini {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.merlin-avatar-mini {
  position: relative;
  width: 60px;
  height: 60px;
}

.avatar-retro-border-mini {
  position: absolute;
  inset: 0;
  border: 2px solid #4a5568;
  border-radius: 50%;
  animation: retro-border 3s linear infinite;
}

@keyframes retro-border {
  0% { border-color: #4a5568; }
  25% { border-color: #00d5ff; }
  50% { border-color: #4a5568; }
  75% { border-color: #00d5ff; }
  100% { border-color: #4a5568; }
}

.avatar-icon-mini {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #9CA3AF 0%, #00d5ff 100%);
  border-radius: 50%;
  font-size: 1.5rem;
  z-index: 1;
}

.merlin-bubble {
  max-width: 300px;
  padding: 1rem;
  background: rgba(30, 41, 59, 0.8);
  border: 2px solid #4a5568;
  border-radius: 1rem;
  backdrop-filter: blur(10px);
  animation: bubble-pulse 2s ease-in-out infinite;
}

@keyframes bubble-pulse {
  0%, 100% { box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); }
  50% { box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4); }
}

.merlin-greeting {
  font-size: 0.875rem;
  color: #e8e8e8;
  line-height: 1.5;
}

/* ═══ SECTIONS ═══ */
.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin-bottom: 1.5rem;
  letter-spacing: 0.05em;
}

/* ═══ QUICK ACTIONS ═══ */
.quick-actions-section {
  margin-bottom: 3rem;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.action-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.action-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.action-icon-large {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.action-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.action-desc {
  font-size: 0.875rem;
  color: #94A3B8;
}

.action-arrow {
  position: absolute;
  top: 1rem;
  right: 1rem;
  font-size: 1.5rem;
  color: #60A5FA;
  opacity: 0;
  transition: opacity 0.2s;
}

.action-card:hover .action-arrow {
  opacity: 1;
}

/* ═══ SYSTEM STATUS ═══ */
.system-status-section {
  margin-bottom: 3rem;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.status-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1rem;
  backdrop-filter: blur(10px);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.status-icon {
  font-size: 1rem;
}

.status-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #94A3B8;
}

.status-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.25rem;
}

.status-detail {
  font-size: 0.75rem;
  color: #6b7280;
}

/* ═══ RECENT ACTIVITY ═══ */
.recent-activity-section {
  margin-bottom: 3rem;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}

.activity-item:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateX(4px);
}

.activity-icon {
  font-size: 1.5rem;
}

.activity-content {
  flex: 1;
}

.activity-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.25rem;
}

.activity-desc {
  font-size: 0.75rem;
  color: #94A3B8;
}

.activity-time {
  font-size: 0.75rem;
  color: #6b7280;
}

/* ═══ QUICK STATS ═══ */
.quick-stats-section {
  margin-bottom: 3rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  text-align: center;
  backdrop-filter: blur(10px);
}

.stat-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #94A3B8;
}

/* ═══ CORE VISUALIZATION ═══ */
.core-viz-section {
  margin-bottom: 4rem;
}

.core-viz-canvas {
  max-width: 600px;
  margin: 0 auto;
}

/* ═══ THEME SHOWCASE ═══ */
.theme-showcase-section {
  margin-bottom: 4rem;
}

.theme-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.theme-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1rem;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.theme-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

.theme-card.active {
  border-color: rgba(96, 165, 250, 0.5);
  box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.3), 0 12px 32px rgba(0, 0, 0, 0.3);
}

.theme-preview {
  width: 100%;
  height: 120px;
  border-radius: 0.75rem;
  position: relative;
  overflow: hidden;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.theme-preview-core {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  box-shadow: 0 0 30px currentColor;
  animation: pulse-ring 2s ease-in-out infinite;
}

.theme-info {
  text-align: center;
}

.theme-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: white;
  margin-bottom: 0.5rem;
}

.theme-desc {
  font-size: 0.875rem;
  color: #94A3B8;
  margin-bottom: 1rem;
  line-height: 1.5;
}

.theme-active-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: rgba(96, 165, 250, 0.2);
  color: #60A5FA;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ═══ FOOTER ═══ */
.welcome-footer {
  margin-top: 4rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.footer-content {
  text-align: center;
}

.footer-text {
  font-size: 0.875rem;
  color: #94A3B8;
  margin-bottom: 0.25rem;
}

.footer-sub {
  font-size: 0.75rem;
  color: #6b7280;
}
</style>