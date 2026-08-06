<template>
  <div class="mobile-companion-jarvis">
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

      <!-- Voice Assistant (grabar en OMEGA → respuesta con audio en ALPHA) -->
      <VoiceAssistantRecorder />

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
        <h2 class="section-title">MERLIN Chat</h2>
        <div class="merlin-mini-interface">
          <div class="merlin-avatar-mini">
            <div class="avatar-ring outer-ring"></div>
            <div class="avatar-ring middle-ring"></div>
            <div class="avatar-ring inner-ring"></div>
            <div class="avatar-core">🧙</div>
          </div>
          <div class="merlin-messages">
            <div class="merlin-message greeting">
              <div class="message-content">
                <p class="greeting">{{ merlinGreeting }}</p>
              </div>
            </div>
            <div
              v-for="(msg, i) in merlinMessages"
              :key="i"
              class="merlin-message"
              :class="msg.role"
            >
              <div class="message-content">
                <p>{{ msg.content }}</p>
              </div>
            </div>
            <div v-if="merlinLoading" class="merlin-message assistant">
              <div class="message-content">
                <p class="typing">...</p>
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

      <!-- Notifications -->
      <div class="notifications-section" v-if="notifications.length > 0">
        <h2 class="section-title">Notificaciones ({{ notifications.length }})</h2>
        <div class="notifications-list">
          <div
            v-for="notif in notifications"
            :key="notif.notification_id"
            class="notification-item"
            :class="{ unread: !notif.read, [notif.level]: true }"
            @click="markNotificationRead(notif.notification_id)"
          >
            <div class="notification-content">
              <span class="notification-title">{{ notif.title }}</span>
              <span class="notification-message">{{ notif.message }}</span>
            </div>
            <span class="notification-level">{{ notif.level }}</span>
          </div>
        </div>
      </div>

      <!-- Pending Approvals -->
      <div class="approvals-section" v-if="pendingApprovals.length > 0">
        <h2 class="section-title">Aprobaciones Pendientes ({{ pendingApprovals.length }})</h2>
        <div class="approvals-list">
          <div
            v-for="approval in pendingApprovals"
            :key="approval.request_id"
            class="approval-item"
          >
            <div class="approval-content">
              <span class="approval-title">{{ approval.title }}</span>
              <span class="approval-description">{{ approval.description }}</span>
            </div>
            <div class="approval-actions">
              <button class="btn-approve" @click="respondApproval(approval.request_id, true)">✓</button>
              <button class="btn-reject" @click="respondApproval(approval.request_id, false)">✗</button>
            </div>
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
import VoiceAssistantRecorder from '@/components/voice/VoiceAssistantRecorder.vue'
import {
  fetchWearOSStatus,
  fetchWearOSNotifications,
  fetchWearOSPendingApprovals,
  markWearOSNotificationRead,
  respondWearOSApproval,
  sendChatMessage,
  type WearOSStatus,
  type WearOSNotification,
  type WearOSApproval,
  type ChatMessage,
} from '@/services/ownexData'

const router = useRouter()

const companionConnected = ref(true)
const androidConnected = ref(true)
const watchConnected = ref(false)
const notificationsEnabled = ref(true)
const merlinInput = ref('')
const merlinMessages = ref<Array<{ role: string; content: string }>>([])
const merlinLoading = ref(false)

const wearStatus = ref<WearOSStatus | null>(null)
const notifications = ref<WearOSNotification[]>([])
const pendingApprovals = ref<WearOSApproval[]>([])
const loading = ref(false)

const status = computed(() => ({
  findings_total: wearStatus.value?.findings_total ?? 0,
  findings_confirmed: wearStatus.value?.findings_confirmed ?? 0,
  findings_pending: wearStatus.value?.pending_approvals ?? 0,
  targets_active: wearStatus.value?.targets_active ?? 0,
  scheduler_running: wearStatus.value?.scheduler_running ?? false,
  next_action: wearStatus.value?.active_workflows
    ? `${wearStatus.value.active_workflows} workflows activos`
    : 'Sin actividad',
}))

const androidStatus = computed(() => androidConnected.value ? 'Conectado' : 'Desconectado')
const androidStatusClass = computed(() => androidConnected.value ? 'status-ok' : 'status-warning')
const watchStatus = computed(() => watchConnected.value ? 'Conectado' : 'Desconectado')
const watchStatusClass = computed(() => watchConnected.value ? 'status-ok' : 'status-warning')

const merlinGreeting = ref('¡Hola! Soy MERLIN mini. ¿En qué puedo ayudarte desde tu móvil?')

async function refreshStatus() {
  loading.value = true
  try {
    const [wearNotifs, wearApprovals] = await Promise.all([
      fetchWearOSNotifications({ unread_only: true, limit: 10 }),
      fetchWearOSPendingApprovals(),
    ])
    notifications.value = wearNotifs
    pendingApprovals.value = wearApprovals
  } catch {
    // API not available yet
  } finally {
    loading.value = false
  }
}

async function loadWearOSStatus() {
  try {
    wearStatus.value = await fetchWearOSStatus()
  } catch {
    // Fallback to defaults
    wearStatus.value = {
      system_online: true,
      scheduler_running: false,
      active_workflows: 0,
      pending_approvals: 0,
      findings_total: 0,
      findings_confirmed: 0,
      targets_active: 0,
      health_score: 100,
      last_updated: new Date().toISOString(),
    }
  }
}

async function markNotificationRead(id: string) {
  try {
    await markWearOSNotificationRead(id)
    notifications.value = notifications.value.map((n) =>
      n.notification_id === id ? { ...n, read: true } : n,
    )
  } catch {
    // ignore
  }
}

async function respondApproval(requestId: string, approved: boolean) {
  try {
    await respondWearOSApproval(requestId, approved)
    pendingApprovals.value = pendingApprovals.value.filter((a) => a.request_id !== requestId)
  } catch {
    // ignore
  }
}

function connectAndroid() {
  androidConnected.value = !androidConnected.value
}

function connectWatch() {
  watchConnected.value = !watchConnected.value
  if (watchConnected.value) {
    loadWearOSStatus()
  }
}

function navigateTo(path: string) {
  router.push(path)
}

function toggleNotifications() {
  notificationsEnabled.value = !notificationsEnabled.value
}

async function sendMerlinMessage() {
  const text = merlinInput.value.trim()
  if (!text) return

  merlinMessages.value.push({ role: 'user', content: text })
  merlinInput.value = ''
  merlinLoading.value = true

  try {
    const response = await sendChatMessage(text, merlinMessages.value.slice(0, -1))
    merlinMessages.value.push({
      role: 'assistant',
      content: response.response || response.error || 'Sin respuesta',
    })
  } catch {
    merlinMessages.value.push({
      role: 'assistant',
      content: 'Error de conexión. Verificá que el backend esté corriendo.',
    })
  } finally {
    merlinLoading.value = false
  }
}

onMounted(() => {
  loadWearOSStatus()
  refreshStatus()
  const interval = setInterval(() => {
    refreshStatus()
  }, 120000)

  onUnmounted(() => {
    clearInterval(interval)
  })
})
</script>

<style scoped>
/* ═══ OWNEX — PREMIUM MINIMAL MOBILE THEME ═══ */
.mobile-companion-jarvis {
  min-height: 100vh;
  background: #05060a;
  color: #f5f5f4;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* ── Header ── */
.mobile-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(5, 6, 10, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}
.header-left { display: flex; align-items: center; gap: 12px; }
.device-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.header-text { display: flex; flex-direction: column; gap: 1px; }
.header-title {
  margin: 0;
  font-family: 'Space Grotesk', 'Inter', sans-serif;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.header-subtitle { margin: 0; font-size: 11px; color: #8b8d98; }
.header-right { display: flex; align-items: center; }
.status-indicator {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}
.status-indicator.status-online { border-color: rgba(0, 227, 154, 0.4); }
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #5e6272;
}
.status-online .status-dot { background: #00e39a; }

/* ── Layout ── */
.main-content {
  max-width: 720px;
  margin: 0 auto;
  padding: 20px 20px 40px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ── Device cards ── */
.device-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}
.device-card {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.device-icon-large { font-size: 26px; }
.device-title { margin: 0; font-size: 15px; font-weight: 600; }
.device-desc { margin: 0; font-size: 12px; color: #8b8d98; }
.device-status { display: flex; gap: 6px; align-items: center; }
.status-label { font-size: 11px; color: #5e6272; }
.status-value { font-size: 12px; font-weight: 600; }
.status-value.status-ok { color: #00e39a; }
.status-value.status-warning { color: #ff7a1a; }
.device-btn {
  margin-top: 6px;
  padding: 10px 14px;
  border: 1px solid rgba(0, 213, 255, 0.35);
  border-radius: 9px;
  background: rgba(0, 213, 255, 0.06);
  color: #00d5ff;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.12s ease;
}
.device-btn:hover { background: rgba(0, 213, 255, 0.14); }

/* ── Sections ── */
.section-title {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.feature-item {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 14px;
}
.feature-icon { font-size: 20px; }
.feature-title { margin: 8px 0 2px; font-size: 13px; font-weight: 600; }
.feature-desc { margin: 0; font-size: 11px; color: #8b8d98; line-height: 1.4; }

/* ── MERLIN mini ── */
.merlin-mini-interface {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.merlin-avatar-mini {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.avatar-ring {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(0, 227, 154, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-ring.middle-ring { width: 28px; height: 28px; border-color: rgba(0, 213, 255, 0.3); }
.avatar-ring.inner-ring { width: 22px; height: 22px; border-color: rgba(255, 255, 255, 0.2); }
.avatar-core { font-size: 16px; }
.merlin-messages { display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto; }
.merlin-message { display: flex; }
.merlin-message.user { justify-content: flex-end; }
.merlin-message.assistant { justify-content: flex-start; }
.merlin-message.greeting { justify-content: flex-start; }
.message-content {
  max-width: 85%;
  background: #13161d;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 8px 12px;
}
.merlin-message.user .message-content {
  background: #1a2332;
  border-color: rgba(0, 213, 255, 0.2);
}
.typing {
  animation: blink 1s infinite;
  color: #888;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.greeting { margin: 0; font-size: 13px; line-height: 1.5; color: #d9dbdf; }
.merlin-input { display: flex; gap: 8px; }
.merlin-textarea {
  flex: 1;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9px;
  color: #f5f5f4;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  padding: 10px 12px;
  outline: none;
}
.merlin-textarea::placeholder { color: #5e6272; }
.merlin-textarea:focus { border-color: rgba(0, 213, 255, 0.4); }
.merlin-send {
  width: 42px;
  border: none;
  border-radius: 9px;
  background: #00d5ff;
  font-size: 15px;
  cursor: pointer;
}

/* ── Status grid ── */
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.status-item {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.status-item .status-label { color: #5e6272; }
.status-item .status-value { font-size: 15px; }

/* ── Quick actions ── */
.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.quick-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px;
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  color: #d9dbdf;
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.12s ease;
}
.quick-action-btn:hover { border-color: rgba(0, 213, 255, 0.4); }
.action-icon { font-size: 18px; }
.action-text { text-align: center; }

/* ── Footer ── */
.mobile-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 20px;
  text-align: center;
}
.footer-text { margin: 0; font-size: 12px; color: #a6a9b1; }
.footer-sub { margin: 4px 0 0; font-size: 11px; color: #5e6272; }
</style>
