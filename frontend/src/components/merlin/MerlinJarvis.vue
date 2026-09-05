<template>
  <div class="merlin-jarvis">
    <!-- ═══ JARVIS HEADER ═══ -->
    <header class="jarvis-header">
      <div class="header-left">
        <div class="merlin-core">
          <div class="core-ring outer-core">
            <div class="core-segment"></div>
            <div class="core-segment"></div>
            <div class="core-segment"></div>
          </div>
          <div class="core-ring middle-core">
            <div class="core-segment"></div>
            <div class="core-segment"></div>
            <div class="core-segment"></div>
          </div>
          <div class="core-ring inner-core">
            <div class="core-dot"></div>
            <div class="core-pulse"></div>
          </div>
        </div>
        <div class="merlin-info">
          <h1 class="merlin-title">MERLIN</h1>
          <p class="merlin-subtitle">AI ASSISTANT SYSTEM</p>
          <div class="merlin-status">
            <span class="status-indicator status-online"></span>
            <span class="status-text">SISTEMA EN LÍNEA</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="mode-toggle">
          <button
            @click="toggleMode"
            class="mode-btn"
            :class="{ 'mode-beginner': isBeginnerMode, 'mode-expert': !isBeginnerMode }"
          >
            <span class="mode-icon">{{ isBeginnerMode ? '🎓' : '🔬' }}</span>
            <span class="mode-text">{{ isBeginnerMode ? 'BEGINNER' : 'EXPERT' }}</span>
          </button>
        </div>
        <div class="header-metrics">
          <div class="metric">
            <span class="metric-label">CPU</span>
            <span class="metric-value">45%</span>
          </div>
          <div class="metric">
            <span class="metric-label">MEM</span>
            <span class="metric-value">62%</span>
          </div>
          <div class="metric">
            <span class="metric-label">NET</span>
            <span class="metric-value">78%</span>
          </div>
        </div>
      </div>
    </header>

    <!-- ═══ JARVIS CHAT AREA ═══ -->
    <div class="jarvis-chat-area">
      <div class="chat-scroll-area">
        <div class="messages-container">
          <!-- Welcome message -->
          <div class="message message-merlin">
            <div class="message-avatar">
              <div class="avatar-ring"></div>
              <div class="avatar-core">🧙</div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-author">MERLIN</span>
                <span class="message-time">{{ formatTime(new Date()) }}</span>
              </div>
              <div class="message-body">
                <p class="greeting">{{ greeting }}</p>
                <p class="description" v-if="systemHealth > 0">SISTEMA OPERATIVO — Salud: {{ systemHealth }}% · {{ activeTargets }} targets activos · {{ workBankReady }} listos para entregar</p>
                <p class="description" v-else>INICIALIZANDO INTERFAZ JARVIS...</p>
                <p class="description">READY TO ASSIST WITH:</p>
                <ul class="capabilities-list">
                  <li v-for="capability in capabilities" :key="capability">{{ capability }}</li>
                </ul>
                <p class="prompt" v-if="topOpportunity">💡 Top oportunidad: {{ topOpportunity.title }} ({{ topOpportunity.platform }}) — ${{ topOpportunity.reward }} · {{ topOpportunity.ev_per_hour.toFixed(0) }}/h</p>
                <p class="prompt" v-else>AWAITING INPUT...</p>
              </div>
            </div>
          </div>

          <!-- Chat messages -->
          <div
            v-for="message in messages"
            :key="message.id"
            class="message"
            :class="{
              'message-user': message.role === 'user',
              'message-merlin': message.role === 'merlin'
            }"
          >
            <div v-if="message.role === 'merlin'" class="message-avatar">
              <div class="avatar-ring"></div>
              <div class="avatar-core">🧙</div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-author">{{ message.role === 'user' ? 'USER' : 'MERLIN' }}</span>
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
              </div>
              <div class="message-body">
                <div v-if="message.role === 'merlin' && message.isTyping" class="typing-indicator">
                  <span class="typing-dot"></span>
                  <span class="typing-dot"></span>
                  <span class="typing-dot"></span>
                </div>
                <div v-else class="message-text">{{ message.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ JARVIS INPUT AREA ═══ -->
      <div class="jarvis-input-area">
        <div class="input-container">
          <div class="input-frame">
            <textarea
              v-model="userInput"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.shift.enter.exact="userInput += '\n'"
              placeholder="ENTER COMMAND OR QUERY..."
              class="jarvis-textarea"
              rows="1"
              ref="inputRef"
            ></textarea>
          </div>
          <button
            @click="sendMessage"
            :disabled="!userInput.trim() || isProcessing"
            class="jarvis-send-btn"
          >
            <div class="send-icon">►</div>
          </button>
        </div>
        <div class="input-hint">
          <span class="hint-text">ENTER TO SEND • SHIFT+ENTER FOR NEW LINE</span>
        </div>
      </div>
    </div>

    <!-- ═══ JARVIS SIDEBAR ═══ -->
    <aside class="jarvis-sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <div class="sidebar-header">
        <button @click="toggleSidebar" class="sidebar-toggle">
          <div class="toggle-icon">{{ sidebarCollapsed ? '►' : '◄' }}</div>
        </button>
        <h3 class="sidebar-title" v-if="!sidebarCollapsed">DATA LOGS</h3>
      </div>

      <div class="sidebar-content">
        <div class="sidebar-section">
          <h4 class="section-title" v-if="!sidebarCollapsed">RECENT</h4>
          <div class="logs-list">
            <div
              v-for="log in recentLogs"
              :key="log.id"
              class="log-item"
              @click="loadLog(log)"
            >
              <div class="log-icon">📄</div>
              <div class="log-info" v-if="!sidebarCollapsed">
                <span class="log-title">{{ log.title }}</span>
                <span class="log-time">{{ log.time }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="sidebar-section">
          <h4 class="section-title" v-if="!sidebarCollapsed">MEMORY</h4>
          <div class="memory-list">
            <div
              v-for="memory in recentMemories"
              :key="memory.id"
              class="memory-item"
              @click="loadMemory(memory)"
            >
              <div class="memory-icon">💾</div>
              <div class="memory-info" v-if="!sidebarCollapsed">
                <span class="memory-title">{{ memory.title }}</span>
                <span class="memory-type">{{ memory.type }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="sidebar-section">
          <h4 class="section-title" v-if="!sidebarCollapsed">VOZ</h4>
          <VoiceAssistantRecorder v-if="!sidebarCollapsed" />
        </div>

        <div class="sidebar-section">
          <h4 class="section-title" v-if="!sidebarCollapsed">COMMANDS</h4>
          <div class="quick-commands">
            <button @click="executeCommand('analyze')" class="quick-command-btn">
              <span class="command-icon">🎯</span>
              <span class="command-text" v-if="!sidebarCollapsed">ANALYZE</span>
            </button>
            <button @click="executeCommand('report')" class="quick-command-btn">
              <span class="command-icon">📊</span>
              <span class="command-text" v-if="!sidebarCollapsed">REPORT</span>
            </button>
            <button @click="executeCommand('optimize')" class="quick-command-btn">
              <span class="command-icon">⚡</span>
              <span class="command-text" v-if="!sidebarCollapsed">OPTIMIZE</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, nextTick, onMounted, ref } from 'vue'
import VoiceAssistantRecorder from '@/components/voice/VoiceAssistantRecorder.vue'
import { fetchGoodMorning, fetchDirectWorkWorkBank, fetchOwnexDashboard, fetchDirectWorkDailyBrief } from '@/services/ownexData'

const isOnline = ref(true)
const isProcessing = ref(false)
const userInput = ref('')
const sidebarCollapsed = ref(false)
const isBeginnerMode = ref(true)

const greeting = ref('INICIALIZANDO INTERFAZ JARVIS... SISTEMA LISTO. ESPERANDO ENTRADA.')
const capabilities = ref([
  'TARGET ANALYSIS',
  'VULNERABILITY DETECTION',
  'REPORT GENERATION',
  'WORKFLOW OPTIMIZATION',
  'DATA ANALYSIS',
  'STRATEGIC PLANNING',
])

const messages = ref([
  {
    id: 1,
    role: 'merlin',
    content: greeting.value,
    timestamp: new Date(),
    isTyping: false,
  },
])

// Real system state
const systemHealth = ref(0)
const systemStatus = ref('unknown')
const activeTargets = ref(0)
const totalFindings = ref(0)
const monthlyReports = ref(0)
const monthlyRevenue = ref(0)
const workBankReady = ref(0)
const workBankNeedsAccess = ref(0)
const topOpportunity = ref<{ title: string; platform: string; reward: number; ev_per_hour: number } | null>(null)
const availableHoursToday = ref(0)

const recentLogs = ref([
  { id: 1, title: 'TARGET_ANALYSIS_001', time: '12:45:32' },
  { id: 2, title: 'VULN_DETECTION_XSS', time: '12:44:15' },
  { id: 3, title: 'REPORT_GENERATION', time: '12:42:00' },
])

const recentMemories = ref([
  { id: 1, title: 'XSS_PATTERN_001', type: 'PATTERN' },
  { id: 2, title: 'WORKFLOW_REPORTING', type: 'WORKFLOW' },
  { id: 3, title: 'STRATEGY_TARGETS', type: 'STRATEGY' },
])

const chatScrollArea = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function sendMessage() {
  if (!userInput.value.trim() || isProcessing.value) return

  const userMessage = userInput.value.trim()
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: userMessage,
    timestamp: new Date(),
    isTyping: false,
  })

  userInput.value = ''
  isProcessing.value = true

  const typingId = Date.now()
  messages.value.push({
    id: typingId,
    role: 'merlin',
    content: '',
    timestamp: new Date(),
    isTyping: true,
  })

  await nextTick()
  scrollToBottom()

  try {
    const response = await axios.post('/api/merlin/chat', {
      message: userMessage,
      context: {
        detail_level: isBeginnerMode.value ? 'beginner' : 'expert',
        response_tone: isBeginnerMode.value ? 'simple' : 'technical',
        enable_analytics: true,
        enable_learning: true,
      },
    })

    messages.value = messages.value.filter((m) => m.id !== typingId)

    messages.value.push({
      id: Date.now(),
      role: 'merlin',
      content: response.data.response,
      timestamp: new Date(),
      isTyping: false,
    })
  } catch (error) {
    console.error('Error sending message:', error)
    messages.value = messages.value.filter((m) => m.id !== typingId)
    messages.value.push({
      id: Date.now(),
      role: 'merlin',
      content: 'ERROR: COMMAND FAILED. RETRY.',
      timestamp: new Date(),
      isTyping: false,
    })
  } finally {
    isProcessing.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (chatScrollArea.value) {
    chatScrollArea.value.scrollTop = chatScrollArea.value.scrollHeight
  }
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleMode() {
  isBeginnerMode.value = !isBeginnerMode.value
  const mode = isBeginnerMode.value ? 'beginner' : 'expert'
  messages.value.push({
    id: Date.now(),
    role: 'merlin',
    content: isBeginnerMode.value
      ? 'BEGINNER MODE ACTIVATED. I will explain everything simply, like I would to a 10-year-old.'
      : 'EXPERT MODE ACTIVATED. I will provide detailed technical information and implementation details.',
    timestamp: new Date(),
    isTyping: false,
  })
}

function loadLog(log: any) {
  userInput.value = `LOAD LOG: ${log.title}`
  sendMessage()
}

function loadMemory(memory: any) {
  userInput.value = `RETRIEVE MEMORY: ${memory.title}`
  sendMessage()
}

function executeCommand(command: string) {
  const commands = {
    analyze: 'ANALYZE TARGET: PRIMARY',
    report: 'GENERATE REPORT: LATEST FINDING',
    optimize: 'OPTIMIZE WORKFLOW: CURRENT',
  }
  userInput.value = commands[command]
  sendMessage()
}

async function loadSystemState() {
  try {
    const [dashboard, workbank, brief, goodmorning] = await Promise.allSettled([
      fetchOwnexDashboard(),
      fetchDirectWorkWorkBank(),
      fetchDirectWorkDailyBrief(),
      fetchGoodMorning(),
    ])

    if (dashboard.status === 'fulfilled') {
      systemHealth.value = dashboard.value?.systemHealth ?? 0
      systemStatus.value = dashboard.value?.systemStatus ?? 'unknown'
    }

    if (workbank.status === 'fulfilled') {
      workBankReady.value = workbank.value?.ready_to_deliver ?? 0
      workBankNeedsAccess.value = workbank.value?.needs_access ?? 0

      // Get top opportunity from weekly_best
      const weeklyBest = workbank.value?.weekly_best?.[0]
      if (weeklyBest) {
        topOpportunity.value = {
          title: weeklyBest.title,
          platform: weeklyBest.platform,
          reward: weeklyBest.reward,
          ev_per_hour: weeklyBest.barrier_score ? weeklyBest.reward / weeklyBest.barrier_score : 0,
        }
      }
    }

    if (brief.status === 'fulfilled') {
      const top = brief.value?.top_opportunity
      if (top?.opportunity) {
        topOpportunity.value = {
          title: top.opportunity.title,
          platform: top.opportunity.platform,
          reward: top.expected_value,
          ev_per_hour: top.ev_per_human_hour_usd ?? 0,
        }
      }
    }

    if (goodmorning.status === 'fulfilled') {
      availableHoursToday.value = goodmorning.value?.personal?.pending_tasks ?? 0
    }
  } catch (e) {
    console.warn('Failed to load system state for MERLIN:', e)
  }
}

onMounted(async () => {
  if (inputRef.value) {
    inputRef.value.focus()
  }
  await loadSystemState()
  // Refresh system state every 60 seconds
  setInterval(loadSystemState, 60000)
})
</script>

<style scoped>
/* ═══ OWNEX — PREMIUM MINIMAL THEME (Tesla-grade) ═══ */
.merlin-jarvis {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--ownex-bg-base);
  color: var(--ownex-bg-surface);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  position: relative;
  overflow: hidden;
}

/* ── Header ── */
.jarvis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: var(--ownex-bg-base);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.merlin-core {
  position: relative;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.core-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.outer-core { width: 42px; height: 42px; }
.middle-core { width: 32px; height: 32px; border-color: rgba(0, 213, 255, 0.25); }
.inner-core { width: 24px; height: 24px; border-color: rgba(0, 227, 154, 0.35); }
.core-segment { display: none; }
.core-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ownex-green);
}
.core-pulse {
  position: absolute;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid rgba(0, 227, 154, 0.3);
  animation: pulse-soft 2.4s ease-out infinite;
}
@keyframes pulse-soft {
  0% { transform: scale(0.6); opacity: 0.8; }
  100% { transform: scale(1.4); opacity: 0; }
}
.merlin-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.merlin-title {
  margin: 0;
  font-family: 'Space Grotesk', 'Inter', sans-serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--ownex-bg-surface);
}
.merlin-subtitle {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ownex-text-secondary);
}
.merlin-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}
.status-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ownex-text-muted);
}
.status-indicator.status-online { background: var(--ownex-green); }
.status-text {
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--ownex-text-secondary);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 18px;
}
.mode-toggle {
  display: flex;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
}
.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: none;
  background: transparent;
  color: var(--ownex-text-secondary);
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  cursor: pointer;
}
.mode-btn.mode-beginner { background: rgba(0, 227, 154, 0.08); color: var(--ownex-green); }
.mode-btn.mode-expert { background: rgba(0, 213, 255, 0.08); color: var(--ownex-accent); }
.header-metrics {
  display: flex;
  gap: 16px;
}
.metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.metric-label {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--ownex-text-muted);
}
.metric-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--ownex-text-secondary);
}

/* ── Chat area ── */
.jarvis-chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chat-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 22px;
}
.messages-container {
  max-width: 780px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.message {
  display: flex;
  gap: 12px;
}
.message-user { flex-direction: row-reverse; }
.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
.avatar-ring { display: none; }
.message-content { flex: 1; min-width: 0; }
.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
}
.message-author {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ownex-text-secondary);
}
.message-user .message-author { color: var(--ownex-accent); }
.message-time { font-size: 11px; color: var(--ownex-text-muted); }
.message-body {
  font-size: 14px;
  line-height: 1.55;
  color: var(--ownex-text-secondary);
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 12px 15px;
}
.message-user .message-body {
  background: rgba(0, 213, 255, 0.05);
  border-color: rgba(0, 213, 255, 0.15);
}
.greeting { margin: 0 0 6px; font-weight: 500; color: var(--ownex-bg-surface); }
.description { margin: 2px 0; font-size: 13px; color: var(--ownex-text-secondary); }
.capabilities-list {
  margin: 8px 0;
  padding-left: 18px;
  color: var(--ownex-text-secondary);
}
.capabilities-list li { margin: 2px 0; }
.prompt {
  margin: 10px 0 0;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ownex-green);
}
.message-text { white-space: pre-wrap; word-break: break-word; }
.typing-indicator { display: flex; gap: 4px; padding: 4px 0; }
.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ownex-text-secondary);
  animation: typing-bounce 1.2s ease-in-out infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.15s; }
.typing-dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* ── Input area ── */
.jarvis-input-area {
  padding: 12px 22px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: var(--ownex-bg-base);
}
.input-container {
  max-width: 780px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: stretch;
}
.input-frame {
  flex: 1;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  transition: border-color 0.15s ease;
}
.input-frame:focus-within { border-color: rgba(0, 213, 255, 0.4); }
.jarvis-textarea {
  width: 100%;
  box-sizing: border-box;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  color: var(--ownex-bg-surface);
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  line-height: 1.4;
  padding: 12px 14px;
}
.jarvis-textarea::placeholder { color: var(--ownex-text-muted); }
.jarvis-send-btn {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border: none;
  border-radius: 10px;
  background: var(--ownex-accent);
  color: var(--ownex-bg-base);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.jarvis-send-btn:hover:not(:disabled) { opacity: 0.85; }
.jarvis-send-btn:disabled { background: var(--ownex-bg-elevated); color: var(--ownex-text-muted); cursor: not-allowed; }
.send-icon { font-size: 13px; }
.input-hint {
  max-width: 780px;
  margin: 8px auto 0;
  text-align: center;
}
.hint-text { font-size: 11px; letter-spacing: 0.1em; color: var(--ownex-text-muted); }

/* ── Sidebar ── */
.jarvis-sidebar {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 264px;
  background: var(--ownex-bg-base);
  border-left: 1px solid rgba(255, 255, 255, 0.06);
  overflow-y: auto;
  transition: width 0.2s ease;
  z-index: 5;
}
.jarvis-sidebar.sidebar-collapsed { width: 56px; }
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.sidebar-toggle {
  border: none;
  background: transparent;
  color: var(--ownex-text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 6px;
}
.sidebar-title {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--ownex-text-secondary);
}
.sidebar-content { padding: 12px 16px 24px; }
.sidebar-section { margin-bottom: 22px; }
.section-title {
  margin: 0 0 10px;
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--ownex-text-muted);
}
.logs-list, .memory-list { display: flex; flex-direction: column; gap: 4px; }
.log-item, .memory-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s ease;
}
.log-item:hover, .memory-item:hover { background: rgba(255, 255, 255, 0.04); }
.log-icon, .memory-icon { font-size: 14px; }
.log-info, .memory-info { display: flex; flex-direction: column; min-width: 0; }
.log-title, .memory-title {
  font-size: 12px;
  color: var(--ownex-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.log-time, .memory-type { font-size: 10px; color: var(--ownex-text-muted); }
.quick-commands { display: flex; flex-direction: column; gap: 6px; }
.quick-command-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  background: transparent;
  color: var(--ownex-text-secondary);
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.12s ease;
}
.quick-command-btn:hover { border-color: rgba(0, 213, 255, 0.4); }
.command-icon { font-size: 13px; }
.command-text { letter-spacing: 0.06em; }
</style>
