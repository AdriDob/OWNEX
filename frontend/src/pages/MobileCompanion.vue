<template>
  <div class="mobile-companion-wrapper">
    <!-- Header -->
    <div class="mobile-header">
      <div class="header-content">
        <div class="logo">🤖 ORION</div>
        <div class="status-indicator" :class="systemStatus">
          <div class="status-dot"></div>
          <span>{{ statusText }}</span>
        </div>
      </div>
      <div class="header-actions">
        <button @click="refreshStatus" class="icon-btn" title="Refresh">
          <RefreshCw :class="{ spinning: refreshing }" />
        </button>
        <button @click="showSettings = true" class="icon-btn" title="Settings">
          ⚙️
        </button>
      </div>
    </div>

    <!-- Dashboard -->
    <div class="dashboard">
      <!-- System Health Card -->
      <div class="card health-card">
        <div class="card-header">
          <h3>📊 System Health</h3>
          <Badge :variant="healthVariant">{{ healthScore }}/100</Badge>
        </div>
        <div class="health-metrics">
          <div class="metric">
            <div class="metric-label">Backend</div>
            <div class="metric-value" :class="backendStatus">{{ backendStatusText }}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Scheduler</div>
            <div class="metric-value" :class="schedulerStatus">{{ schedulerStatusText }}</div>
          </div>
          <div class="metric">
            <div class="metric-label">EventBus</div>
            <div class="metric-value" :class="eventBusStatus">{{ eventBusStatusText }}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Database</div>
            <div class="metric-value" :class="databaseStatus">{{ databaseStatusText }}</div>
          </div>
        </div>
      </div>

      <!-- Workflows Card -->
      <div class="card workflows-card">
        <div class="card-header">
          <h3>🔄 Active Workflows</h3>
          <Badge>{{ activeWorkflows }}</Badge>
        </div>
        <div class="workflows-list">
          <div v-for="workflow in workflows" :key="workflow.id" class="workflow-item">
            <div class="workflow-info">
              <div class="workflow-name">{{ workflow.name }}</div>
              <div class="workflow-status" :class="workflow.status">{{ workflow.status }}</div>
            </div>
            <div class="workflow-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: workflow.progress + '%' }"></div>
              </div>
              <span class="progress-text">{{ workflow.progress }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Notifications Card -->
      <div class="card notifications-card">
        <div class="card-header">
          <h3>🔔 Notifications</h3>
          <Badge>{{ unreadNotifications }}</Badge>
        </div>
        <div class="notifications-list">
          <div v-for="notif in notifications" :key="notif.id" class="notification-item" :class="{ unread: !notif.read }">
            <div class="notification-icon">{{ notif.icon }}</div>
            <div class="notification-content">
              <div class="notification-title">{{ notif.title }}</div>
              <div class="notification-message">{{ notif.message }}</div>
              <div class="notification-time">{{ formatTime(notif.timestamp) }}</div>
            </div>
            <button @click="markAsRead(notif.id)" class="icon-btn-small">✓</button>
          </div>
        </div>
      </div>

      <!-- MERLIN Chat Card -->
      <div class="card merlin-card">
        <div class="card-header">
          <h3>🧙 MERLIN</h3>
          <Badge variant="outline">Online</Badge>
        </div>
        <div class="merlin-chat">
          <div class="chat-messages" ref="chatMessages">
            <div v-for="msg in merlinMessages" :key="msg.id" class="chat-message" :class="msg.role">
              <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🧙' }}</div>
              <div class="message-content">
                <div class="message-text">{{ msg.content }}</div>
                <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
              </div>
            </div>
          </div>
          <div class="chat-input">
            <input
              v-model="merlinInput"
              @keyup.enter="sendMerlinMessage"
              placeholder="Ask MERLIN anything..."
              class="message-input-field"
            />
            <button @click="sendMerlinMessage" class="send-btn">📤</button>
          </div>
        </div>
      </div>

      <!-- Approvals Card -->
      <div class="card approvals-card">
        <div class="card-header">
          <h3>✅ Pending Approvals</h3>
          <Badge variant="warning">{{ pendingApprovals }}</Badge>
        </div>
        <div class="approvals-list">
          <div v-for="approval in approvals" :key="approval.id" class="approval-item">
            <div class="approval-info">
              <div class="approval-title">{{ approval.title }}</div>
              <div class="approval-description">{{ approval.description }}</div>
              <div class="approval-risk" :class="approval.risk">{{ approval.risk }}</div>
            </div>
            <div class="approval-actions">
              <button @click="approveRequest(approval.id)" class="btn-approve">✓</button>
              <button @click="rejectRequest(approval.id)" class="btn-reject">✗</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Life Management Card -->
      <div class="card life-card">
        <div class="card-header">
          <h3>🧘 Life Management</h3>
          <Badge>{{ lifeScore }}/100</Badge>
        </div>
        <div class="life-summary">
          <div class="life-metric">
            <div class="life-icon">📋</div>
            <div class="life-data">
              <div class="life-label">Tasks</div>
              <div class="life-value">{{ lifeData.tasks_completed }}/{{ lifeData.tasks_total }}</div>
            </div>
          </div>
          <div class="life-metric">
            <div class="life-icon">🎯</div>
            <div class="life-data">
              <div class="life-label">Goals</div>
              <div class="life-value">{{ lifeData.goals_progress }}%</div>
            </div>
          </div>
          <div class="life-metric">
            <div class="life-icon">🔄</div>
            <div class="life-data">
              <div class="life-label">Habits</div>
              <div class="life-value">{{ lifeData.habits_completed }}/{{ lifeData.habits_total }}</div>
            </div>
          </div>
          <div class="life-metric">
            <div class="life-icon">😊</div>
            <div class="life-data">
              <div class="life-label">Mood</div>
              <div class="life-value">{{ lifeData.mood }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <div v-if="showSettings" class="modal-overlay" @click="showSettings = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>⚙️ Settings</h3>
          <button @click="showSettings = false" class="close-btn">✕</button>
        </div>
        <div class="settings-content">
          <div class="setting-item">
            <label>Push Notifications</label>
            <input type="checkbox" v-model="settings.pushEnabled" class="toggle" />
          </div>
          <div class="setting-item">
            <label>Polling Interval (min)</label>
            <input type="number" v-model="settings.pollingInterval" class="number-input" />
          </div>
          <div class="setting-item">
            <label>Critical-Only Mode</label>
            <input type="checkbox" v-model="settings.criticalOnly" class="toggle" />
          </div>
          <div class="setting-item">
            <label>Sound Alerts</label>
            <input type="checkbox" v-model="settings.soundAlerts" class="toggle" />
          </div>
          <div class="setting-item">
            <label>Vibration</label>
            <input type="checkbox" v-model="settings.vibration" class="toggle" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="saveSettings" class="btn-primary">Save</button>
        </div>
      </div>
    </div>

    <!-- Navigation Bar -->
    <div class="nav-bar">
      <button @click="activeTab = 'dashboard'" class="nav-item" :class="{ active: activeTab === 'dashboard' }">
        📊
      </button>
      <button @click="activeTab = 'merlin'" class="nav-item" :class="{ active: activeTab === 'merlin' }">
        🧙
      </button>
      <button @click="activeTab = 'notifications'" class="nav-item" :class="{ active: activeTab === 'notifications' }">
        🔔
      </button>
      <button @click="activeTab = 'approvals'" class="nav-item" :class="{ active: activeTab === 'approvals' }">
        ✅
      </button>
      <button @click="activeTab = 'life'" class="nav-item" :class="{ active: activeTab === 'life' }">
        🧘
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { RefreshCw } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'

// State
const activeTab = ref('dashboard')
const showSettings = ref(false)
const refreshing = ref(false)

// System Status
const systemStatus = ref('online')
const statusText = computed(() => {
  const status = systemStatus.value
  return status === 'online' ? 'Online' : status === 'offline' ? 'Offline' : 'Connecting'
})

// Health
const healthScore = ref(85)
const healthVariant = computed(() => {
  if (healthScore.value >= 80) return 'success'
  if (healthScore.value >= 50) return 'warning'
  return 'danger'
})

const backendStatus = ref('online')
const backendStatusText = computed(() => backendStatus.value === 'online' ? 'Online' : 'Offline')
const schedulerStatus = ref('running')
const schedulerStatusText = computed(() => schedulerStatus.value === 'running' ? 'Running' : 'Stopped')
const eventBusStatus = ref('active')
const eventBusStatusText = computed(() => eventBusStatus.value === 'active' ? 'Active' : 'Inactive')
const databaseStatus = ref('connected')
const databaseStatusText = computed(() => databaseStatus.value === 'connected' ? 'Connected' : 'Disconnected')

// Workflows
const activeWorkflows = ref(3)
const workflows = ref([
  { id: 1, name: 'Security Scan', status: 'running', progress: 65 },
  { id: 2, name: 'Code Review', status: 'pending', progress: 0 },
  { id: 3, name: 'Report Generation', status: 'completed', progress: 100 },
])

// Notifications
const unreadNotifications = ref(5)
const notifications = ref([
  { id: 1, icon: '🚨', title: 'Finding Detected', message: 'SQL injection in target', timestamp: Date.now() - 300000, read: false },
  { id: 2, icon: '✅', title: 'Report Accepted', message: 'HackerOne accepted report', timestamp: Date.now() - 600000, read: false },
  { id: 3, icon: '🔄', title: 'Workflow Started', message: 'Security scan initiated', timestamp: Date.now() - 900000, read: true },
  { id: 4, icon: '💰', title: 'Payout Received', message: '$500 received from Bugcrowd', timestamp: Date.now() - 1800000, read: true },
  { id: 5, icon: '🧙', title: 'MERLIN Insight', message: 'New opportunity detected', timestamp: Date.now() - 3600000, read: true },
])

// MERLIN
const merlinMessages = ref([
  { id: 1, role: 'assistant', content: 'Hello! I am MERLIN, your AI assistant. How can I help you today?', timestamp: Date.now() },
])
const merlinInput = ref('')
const chatMessages = ref<HTMLElement | null>(null)

// Approvals
const pendingApprovals = ref(2)
const approvals = ref([
  { id: 1, title: 'Submit Report', description: 'Submit SQL injection finding to HackerOne', risk: 'high' },
  { id: 2, title: 'Approve Payment', description: 'Approve $500 payout from Bugcrowd', risk: 'low' },
])

// Life Management
const lifeScore = ref(75)
const lifeData = ref({
  tasks_completed: 8,
  tasks_total: 12,
  goals_progress: 65,
  habits_completed: 4,
  habits_total: 6,
  mood: 'Positive',
})

// Settings
const settings = ref({
  pushEnabled: true,
  pollingInterval: 2,
  criticalOnly: false,
  soundAlerts: true,
  vibration: true,
})

// Methods
const refreshStatus = async () => {
  refreshing.value = true
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1000))
  refreshing.value = false
}

const formatTime = (timestamp: number) => {
  const diff = Date.now() - timestamp
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

const markAsRead = (id: number) => {
  const notif = notifications.value.find(n => n.id === id)
  if (notif) {
    notif.read = true
    unreadNotifications.value--
  }
}

const sendMerlinMessage = async () => {
  if (!merlinInput.value.trim()) return

  const userMessage = {
    id: Date.now(),
    role: 'user',
    content: merlinInput.value,
    timestamp: Date.now(),
  }

  merlinMessages.value.push(userMessage)
  merlinInput.value = ''

  // Scroll to bottom
  await nextTick()
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }

  // Simulate MERLIN response
  setTimeout(() => {
    const assistantMessage = {
      id: Date.now(),
      role: 'assistant',
      content: 'I understand your request. Let me analyze the situation and provide you with the best course of action.',
      timestamp: Date.now(),
    }
    merlinMessages.value.push(assistantMessage)

    nextTick(() => {
      if (chatMessages.value) {
        chatMessages.value.scrollTop = chatMessages.value.scrollHeight
      }
    })
  }, 1000)
}

const approveRequest = (id: number) => {
  approvals.value = approvals.value.filter(a => a.id !== id)
  pendingApprovals.value--
}

const rejectRequest = (id: number) => {
  approvals.value = approvals.value.filter(a => a.id !== id)
  pendingApprovals.value--
}

const saveSettings = () => {
  showSettings.value = false
  // Save to localStorage or API
  localStorage.setItem('mobileSettings', JSON.stringify(settings.value))
}

// Lifecycle
onMounted(() => {
  // Load settings
  const savedSettings = localStorage.getItem('mobileSettings')
  if (savedSettings) {
    settings.value = JSON.parse(savedSettings)
  }

  // Start polling
  refreshStatus()
  setInterval(refreshStatus, settings.value.pollingInterval * 60000)
})

onUnmounted(() => {
  // Cleanup
})
</script>

<style scoped>
.mobile-companion-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 100%);
  color: #fff;
  font-family: 'Inter', sans-serif;
  padding-bottom: 80px;
}

.mobile-header {
  background: rgba(0, 240, 255, 0.1);
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
  padding: 15px 20px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: #00f0ff;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.status-indicator.online .status-dot {
  background: #00ff88;
}

.status-indicator.offline .status-dot {
  background: #ff6b35;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00ff88;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-actions {
  display: flex;
  gap: 10px;
}

.icon-btn {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #00f0ff;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.icon-btn:hover {
  background: rgba(0, 240, 255, 0.2);
}

.icon-btn.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.dashboard {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(10px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h3 {
  margin: 0;
  color: #00f0ff;
  font-size: 1.1rem;
}

.health-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.metric {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
}

.metric-label {
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 5px;
}

.metric-value {
  color: #fff;
  font-weight: bold;
  font-size: 1rem;
}

.metric-value.online,
.metric-value.running,
.metric-value.active,
.metric-value.connected {
  color: #00ff88;
}

.metric-value.offline,
.metric-value.stopped,
.metric-value.inactive,
.metric-value.disconnected {
  color: #ff6b35;
}

.workflows-list,
.notifications-list,
.approvals-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.workflow-item,
.notification-item,
.approval-item {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
}

.workflow-info,
.notification-content,
.approval-info {
  flex: 1;
}

.workflow-name,
.notification-title,
.approval-title {
  color: #fff;
  font-weight: 600;
  margin-bottom: 5px;
}

.workflow-status {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.workflow-status.running {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.workflow-status.pending {
  background: rgba(255, 170, 0, 0.2);
  color: #ffaa00;
}

.workflow-status.completed {
  background: rgba(0, 240, 255, 0.2);
  color: #00f0ff;
}

.workflow-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.progress-bar {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  height: 6px;
  overflow: hidden;
}

.progress-fill {
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.progress-text {
  color: #00f0ff;
  font-size: 0.85rem;
  font-weight: bold;
}

.notification-item.unread {
  border-color: #00f0ff;
  background: rgba(0, 240, 255, 0.1);
}

.notification-icon {
  font-size: 1.5rem;
  margin-right: 12px;
}

.notification-message {
  color: #ccc;
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.notification-time {
  color: #666;
  font-size: 0.8rem;
}

.icon-btn-small {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: #00ff88;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.merlin-chat {
  display: flex;
  flex-direction: column;
  height: 300px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.chat-message {
  display: flex;
  gap: 10px;
  max-width: 80%;
}

.chat-message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 1.5rem;
}

.message-content {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 12px;
  padding: 10px 15px;
}

.chat-message.user .message-content {
  background: rgba(0, 255, 136, 0.1);
  border-color: rgba(0, 255, 136, 0.2);
}

.message-text {
  color: #fff;
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.message-time {
  color: #666;
  font-size: 0.75rem;
}

.chat-input {
  display: flex;
  gap: 10px;
}

.message-input-field {
  flex: 1;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  padding: 10px 15px;
  font-family: 'Inter', sans-serif;
}

.send-btn {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 10px 15px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
}

.approval-description {
  color: #ccc;
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.approval-risk {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.approval-risk.high {
  background: rgba(255, 107, 53, 0.2);
  color: #ff6b35;
}

.approval-risk.low {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.approval-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.btn-approve {
  background: #00ff88;
  color: #000;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}

.btn-reject {
  background: #ff6b35;
  color: #fff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}

.life-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.life-metric {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.life-icon {
  font-size: 1.5rem;
}

.life-data {
  flex: 1;
}

.life-label {
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 3px;
}

.life-value {
  color: #fff;
  font-weight: bold;
  font-size: 1rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid #00f0ff;
  border-radius: 16px;
  padding: 30px;
  max-width: 400px;
  width: 90%;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
  color: #00f0ff;
}

.close-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-item label {
  color: #fff;
  font-size: 0.95rem;
}

.toggle,
.number-input {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  padding: 8px 12px;
}

.number-input {
  width: 80px;
}

.modal-footer {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
}

.nav-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.9);
  border-top: 1px solid rgba(0, 240, 255, 0.3);
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
  backdrop-filter: blur(10px);
}

.nav-item {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.2);
  color: #00f0ff;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.5rem;
  transition: all 0.3s ease;
}

.nav-item.active {
  background: #00f0ff;
  color: #000;
  transform: scale(1.1);
}
</style>
