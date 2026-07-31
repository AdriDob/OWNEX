<template>
  <div class="mobile-companion-jarvis">
    <!-- ═══ JARVIS HUD LAYER ═══ -->
    <div class="jarvis-hud">
      <div class="scan-lines"></div>
      <div class="grid-overlay"></div>
      <div class="particles-container">
        <div v-for="i in 20" :key="i" class="particle" :style="getParticleStyle(i)"></div>
      </div>
    </div>

    <!-- ═══ HEADER ═══ -->
    <header class="mobile-header">
      <div class="header-left">
        <div class="device-icon">📱</div>
        <div class="header-text">
          <h1 class="header-title">ORION COMPANION</h1>
          <p class="header-subtitle">Android & Wear OS Extension</p>
        </div>
      </div>
      <div class="header-right">
        <div class="status-indicator" :class="{ 'status-online': companionConnected }">
          <div class="status-dot"></div>
        </div>
      </div>
    </header>

    <!-- ═══ MAIN CONTENT ═══ -->
    <div class="main-content">
      <!-- Device Cards -->
      <div class="device-cards">
        <div class="device-card android-card">
          <div class="device-icon-large">📱</div>
          <h3 class="device-title">Android</h3>
          <p class="device-desc">Control remoto y notificaciones</p>
          <div class="device-status">
            <span class="status-label">Estado:</span>
            <span class="status-value" :class="androidStatusClass">{{ androidStatus }}</span>
          </div>
          <button @click="connectAndroid" class="device-btn">
            {{ androidConnected ? 'Conectado' : 'Conectar' }}
          </button>
        </div>

        <div class="device-card watch-card">
          <div class="device-icon-large">⌚</div>
          <h3 class="device-title">Wear OS</h3>
          <p class="device-desc">Alertas y aprobaciones rápidas</p>
          <div class="device-status">
            <span class="status-label">Estado:</span>
            <span class="status-value" :class="watchStatusClass">{{ watchStatus }}</span>
          </div>
          <button @click="connectWatch" class="device-btn">
            {{ watchConnected ? 'Conectado' : 'Conectar' }}
          </button>
        </div>
      </div>

      <!-- Features Grid -->
      <div class="features-section">
        <h2 class="section-title">Funcionalidades</h2>
        <div class="features-grid">
          <div class="feature-item">
            <div class="feature-icon">📊</div>
            <h3 class="feature-title">Dashboard Móvil</h3>
            <p class="feature-desc">Estado del sistema en tiempo real</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🧙</div>
            <h3 class="feature-title">MERLIN Chat</h3>
            <p class="feature-desc">Asistente en tu bolsillo</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔔</div>
            <h3 class="feature-title">Notificaciones</h3>
            <p class="feature-desc">Alertas de workflows y errores</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">✅</div>
            <h3 class="feature-title">Aprobaciones</h3>
            <p class="feature-desc">Aprobar acciones desde el reloj</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🎯</div>
            <h3 class="feature-title">Targets</h3>
            <p class="feature-desc">Ver objetivos activos</p>
          </div>
          <div class="feature-item">
            <div class="feature-icon">💰</div>
            <h3 class="feature-title">Capital</h3>
            <p class="feature-desc">Gestión financiera móvil</p>
          </div>
        </div>
      </div>

      <!-- MERLIN Mini -->
      <div class="merlin-mini-section">
        <h2 class="section-title">MERLIN Mini</h2>
        <div class="merlin-mini-interface">
          <div class="merlin-avatar-mini">
            <div class="avatar-ring outer-ring"></div>
            <div class="avatar-ring middle-ring"></div>
            <div class="avatar-ring inner-ring"></div>
            <div class="avatar-core">🧙</div>
          </div>
          <div class="merlin-messages">
            <div class="merlin-message">
              <div class="message-content">
                <p class="greeting">{{ merlinGreeting }}</p>
              </div>
            </div>
          </div>
          <div class="merlin-input">
            <input
              v-model="merlinInput"
              @keyup.enter="sendMerlinMessage"
              type="text"
              placeholder="Escribe a MERLIN..."
              class="merlin-textarea"
            />
            <button @click="sendMerlinMessage" class="merlin-send">📤</button>
          </div>
        </div>
      </div>

      <!-- Status Grid -->
      <div class="status-section">
        <h2 class="section-title">Estado del Sistema</h2>
        <div class="status-grid">
          <div class="status-item">
            <span class="status-label">Findings Totales</span>
            <span class="status-value">{{ status.findings_total }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Confirmados</span>
            <span class="status-value">{{ status.findings_confirmed }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Pendientes</span>
            <span class="status-value">{{ status.findings_pending }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Targets Activos</span>
            <span class="status-value">{{ status.targets_active }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">Scheduler</span>
            <span class="status-value" :class="status.scheduler_running ? 'status-ok' : 'status-warning'">
              {{ status.scheduler_running ? 'Activo' : 'Detenido' }}
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">Próxima Acción</span>
            <span class="status-value">{{ status.next_action || '—' }}</span>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions-section">
        <h2 class="section-title">Acciones Rápidas</h2>
        <div class="quick-actions-grid">
          <button @click="refreshStatus" class="quick-action-btn">
            <div class="action-icon">🔄</div>
            <span class="action-text">Actualizar Estado</span>
          </button>
          <button @click="navigateTo('/merlin')" class="quick-action-btn">
            <div class="action-icon">🧙</div>
            <span class="action-text">MERLIN Full</span>
          </button>
          <button @click="navigateTo('/dashboard')" class="quick-action-btn">
            <div class="action-icon">📊</div>
            <span class="action-text">Dashboard</span>
          </button>
          <button @click="toggleNotifications" class="quick-action-btn">
            <div class="action-icon">{{ notificationsEnabled ? '🔔' : '🔕' }}</div>
            <span class="action-text">{{ notificationsEnabled ? 'Notificaciones On' : 'Notificaciones Off' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ FOOTER ═══ -->
    <footer class="mobile-footer">
      <div class="footer-content">
        <p class="footer-text">ORION Companion — Extensión móvil para OWNEX OMEGA</p>
        <p class="footer-sub">Compatible con Android 10+ y Wear OS 3+</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const companionConnected = ref(true)
const androidConnected = ref(false)
const watchConnected = ref(false)
const notificationsEnabled = ref(true)
const merlinInput = ref('')

const status = ref({
  findings_total: 42,
  findings_confirmed: 23,
  findings_pending: 19,
  targets_active: 8,
  scheduler_running: true,
  next_action: 'Discovery scan in progress'
})

const androidStatus = computed(() => androidConnected.value ? 'Conectado' : 'Desconectado')
const androidStatusClass = computed(() => androidConnected.value ? 'status-ok' : 'status-warning')
const watchStatus = computed(() => watchConnected.value ? 'Conectado' : 'Desconectado')
const watchStatusClass = computed(() => watchConnected.value ? 'status-ok' : 'status-warning')

const merlinGreeting = ref('¡Hola! Soy MERLIN mini. ¿En qué puedo ayudarte desde tu móvil?')

function getParticleStyle(index: number) {
  const angle = (index / 20) * 360
  const distance = 50 + Math.random() * 100
  const x = Math.cos(angle * Math.PI / 180) * distance
  const y = Math.sin(angle * Math.PI / 180) * distance
  const size = 2 + Math.random() * 2
  const delay = Math.random() * 2

  return {
    left: `calc(50% + ${x}px)`,
    top: `calc(50% + ${y}px)`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
  }
}

function connectAndroid() {
  androidConnected.value = !androidConnected.value
}

function connectWatch() {
  watchConnected.value = !watchConnected.value
}

function refreshStatus() {
  // Simular refresh
  console.log('Refreshing status...')
}

function navigateTo(path: string) {
  router.push(path)
}

function toggleNotifications() {
  notificationsEnabled.value = !notificationsEnabled.value
}

function sendMerlinMessage() {
  if (!merlinInput.value.trim()) return

  // Send message to MERLIN
  console.log('Sending to MERLIN:', merlinInput.value)
  merlinInput.value = ''
}

onMounted(() => {
  // Initialize polling
  const interval = setInterval(() => {
    refreshStatus()
  }, 120000) // 2 minutes

  onUnmounted(() => {
    clearInterval(interval)
  })
})
</script>

<style scoped>
/* ═══ MOBILE COMPANION — JARVIS STYLE ═══ */
.mobile-companion-jarvis {
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

/* ═══ HEADER ═══ */
.mobile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: rgba(10, 14, 39, 0.8);
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
  backdrop-filter: blur(10px);
  z-index: 2;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.device-icon {
  font-size: 2rem;
}

.header-text {
  display: flex;
  flex-direction: column;
}

.header-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #00f0ff;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

.header-subtitle {
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.6);
}

.header-right {
  display: flex;
  align-items: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff6b35;
  animation: status-pulse 2s ease-in-out infinite;
}

.status-online .status-dot {
  background: #00ff88;
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ═══ MAIN CONTENT ═══ */
.main-content {
  position: relative;
  z-index: 2;
  padding: 1.5rem;
  flex: 1;
  overflow-y: auto;
}

.device-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.device-card {
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 1rem;
  padding: 1.5rem;
  text-align: center;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.device-card:hover {
  border-color: rgba(0, 240, 255, 0.5);
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 240, 255, 0.2);
}

.device-icon-large {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.device-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #00f0ff;
  margin-bottom: 0.5rem;
}

.device-desc {
  font-size: 0.875rem;
  color: rgba(0, 240, 255, 0.6);
  margin-bottom: 1rem;
}

.device-status {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.75rem;
}

.status-label {
  color: rgba(0, 240, 255, 0.6);
}

.status-value {
  font-weight: 700;
  color: #00f0ff;
}

.status-ok {
  color: #00ff88;
}

.status-warning {
  color: #ff6b35;
}

.device-btn {
  padding: 0.5rem 1.5rem;
  background: rgba(0, 240, 255, 0.2);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.5rem;
  color: #00f0ff;
  font-family: 'Rajdhani', 'Orbitron', monospace;
  font-size: 0.875rem;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all 0.2s;
}

.device-btn:hover {
  border-color: rgba(0, 240, 255, 0.5);
  background: rgba(0, 240, 255, 0.3);
  box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

/* ═══ FEATURES ═══ */
.features-section {
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #00f0ff;
  margin-bottom: 1rem;
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.feature-item {
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.5rem;
  padding: 1rem;
  text-align: center;
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}

.feature-item:hover {
  border-color: rgba(0, 240, 255, 0.5);
  transform: translateY(-2px);
}

.feature-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.feature-title {
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #00f0ff;
  margin-bottom: 0.25rem;
}

.feature-desc {
  font-size: 0.75rem;
  color: rgba(0, 240, 255, 0.6);
}

/* ═══ MERLIN MINI ═══ */
.merlin-mini-section {
  margin-bottom: 2rem;
}

.merlin-mini-interface {
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 1rem;
  padding: 1rem;
  backdrop-filter: blur(10px);
}

.merlin-avatar-mini {
  display: flex;
  justify-content: center;
  margin-bottom: 1rem;
}

.avatar-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(0, 240, 255, 0.3);
}

.outer-ring {
  width: 50px;
  height: 50px;
  animation: ring-rotate 30s linear infinite;
}

.middle-ring {
  width: 38px;
  height: 38px;
  animation: ring-rotate 20s linear infinite reverse;
}

.inner-ring {
  width: 26px;
  height: 26px;
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
  font-size: 1.25rem;
  z-index: 1;
}

.merlin-messages {
  margin-bottom: 1rem;
}

.merlin-message {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-left: 3px solid #00f0ff;
  border-radius: 0.25rem;
  padding: 0.75rem;
}

.message-content {
  font-size: 0.875rem;
  color: #00f0ff;
  line-height: 1.5;
}

.greeting {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.merlin-input {
  display: flex;
  gap: 0.5rem;
}

.merlin-textarea {
  flex: 1;
  padding: 0.5rem;
  background: rgba(10, 14, 39, 0.5);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.25rem;
  color: #00f0ff;
  font-family: 'Rajdhani', 'Orbitron', monospace;
  font-size: 0.875rem;
  outline: none;
}

.merlin-textarea::placeholder {
  color: rgba(0, 240, 255, 0.4);
}

.merlin-send {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(0, 240, 255, 0.3);
  background: rgba(0, 240, 255, 0.2);
  border-radius: 0.25rem;
  color: #00f0ff;
  cursor: pointer;
  transition: all 0.2s;
}

.merlin-send:hover {
  border-color: rgba(0, 240, 255, 0.5);
  background: rgba(0, 240, 255, 0.3);
}

/* ═══ STATUS ═══ */
.status-section {
  margin-bottom: 2rem;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
}

.status-item {
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 0.5rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  backdrop-filter: blur(10px);
}

.status-label {
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.6);
}

.status-value {
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #00f0ff;
}

/* ═══ QUICK ACTIONS ═══ */
.quick-actions-section {
  margin-bottom: 2rem;
}

.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
}

.quick-action-btn {
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0 240, 255, 0.3);
  border-radius: 0.5rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.quick-action-btn:hover {
  border-color: rgba(0, 240, 255, 0.5);
  transform: translateY(-2px);
}

.action-icon {
  font-size: 1.5rem;
}

.action-text {
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: #00f0ff;
}

/* ═══ FOOTER ═══ */
.mobile-footer {
  padding: 1.5rem;
  background: rgba(10, 14, 39, 0.8);
  border-top: 1px solid rgba(0, 240, 255, 0.3);
  backdrop-filter: blur(10px);
  z-index: 2;
}

.footer-content {
  text-align: center;
}

.footer-text {
  font-size: 0.875rem;
  color: rgba(0, 240, 255, 0.6);
  margin-bottom: 0.25rem;
}

.footer-sub {
  font-size: 0.75rem;
  color: rgba(0, 240, 255, 0.4);
}
</style>