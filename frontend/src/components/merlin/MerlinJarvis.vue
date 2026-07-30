<template>
  <div class="merlin-jarvis">
    <!-- ═══ JARVIS HUD LAYER ═══ -->
    <div class="jarvis-hud">
      <div class="scan-lines"></div>
      <div class="grid-overlay"></div>
      <div class="particles-container">
        <div v-for="i in 30" :key="i" class="particle" :style="getParticleStyle(i)"></div>
      </div>
    </div>

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
            <span class="status-text">SYSTEM ONLINE</span>
          </div>
        </div>
      </div>
      <div class="header-right">
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
                <p class="description">INITIALIZING JARVIS INTERFACE...</p>
                <p class="description">READY TO ASSIST WITH:</p>
                <ul class="capabilities-list">
                  <li v-for="capability in capabilities" :key="capability">{{ capability }}</li>
                </ul>
                <p class="prompt">AWAITING INPUT...</p>
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
                <div v-if="message.role === 'merlin'" class="typing-indicator" v-if="message.isTyping">
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
import { ref, computed, onMounted, nextTick } from 'vue'
import axios from 'axios'

const isOnline = ref(true)
const isProcessing = ref(false)
const userInput = ref('')
const sidebarCollapsed = ref(false)

const greeting = ref('INITIALIZING JARVIS INTERFACE... SYSTEM READY. AWAITING INPUT.')
const capabilities = ref([
  'TARGET ANALYSIS',
  'VULNERABILITY DETECTION',
  'REPORT GENERATION',
  'WORKFLOW OPTIMIZATION',
  'DATA ANALYSIS',
  'STRATEGIC PLANNING'
])

const messages = ref([
  {
    id: 1,
    role: 'merlin',
    content: greeting.value,
    timestamp: new Date(),
    isTyping: false
  }
])

const recentLogs = ref([
  { id: 1, title: 'TARGET_ANALYSIS_001', time: '12:45:32' },
  { id: 2, title: 'VULN_DETECTION_XSS', time: '12:44:15' },
  { id: 3, title: 'REPORT_GENERATION', time: '12:42:00' }
])

const recentMemories = ref([
  { id: 1, title: 'XSS_PATTERN_001', type: 'PATTERN' },
  { id: 2, title: 'WORKFLOW_REPORTING', type: 'WORKFLOW' },
  { id: 3, title: 'STRATEGY_TARGETS', type: 'STRATEGY' }
])

const chatScrollArea = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
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
    animationDelay: `${delay}s`
  }
}

async function sendMessage() {
  if (!userInput.value.trim() || isProcessing.value) return

  const userMessage = userInput.value.trim()
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: userMessage,
    timestamp: new Date(),
    isTyping: false
  })

  userInput.value = ''
  isProcessing.value = true

  const typingId = Date.now()
  messages.value.push({
    id: typingId,
    role: 'merlin',
    content: '',
    timestamp: new Date(),
    isTyping: true
  })

  await nextTick()
  scrollToBottom()

  try {
    const response = await axios.post('/api/merlin/chat', {
      message: userMessage,
      context: {
        detail_level: 'normal',
        response_tone: 'professional',
        enable_analytics: true,
        enable_learning: true
      }
    })

    messages.value = messages.value.filter(m => m.id !== typingId)

    messages.value.push({
      id: Date.now(),
      role: 'merlin',
      content: response.data.response,
      timestamp: new Date(),
      isTyping: false
    })

  } catch (error) {
    console.error('Error sending message:', error)
    messages.value = messages.value.filter(m => m.id !== typingId)
    messages.value.push({
      id: Date.now(),
      role: 'merlin',
      content: 'ERROR: COMMAND FAILED. RETRY.',
      timestamp: new Date(),
      isTyping: false
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
    optimize: 'OPTIMIZE WORKFLOW: CURRENT'
  }
  userInput.value = commands[command]
  sendMessage()
}

onMounted(() => {
  if (inputRef.value) {
    inputRef.value.focus()
  }
})
</script>

<style scoped>
/* ═══ JARVIS — HIGH-TECH HUD DESIGN ═══ */
.merlin-jarvis {
  display: flex;
  flex-direction: column;
  height: 100vh;
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

/* ═══ JARVIS HEADER ═══ */
.jarvis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: rgba(10, 14, 39, 0.8);
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
  backdrop-filter: blur(10px);
  z-index: 2;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.merlin-core {
  position: relative;
  width: 60px;
  height: 60px;
}

.core-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(0, 240, 255, 0.3);
}

.outer-core {
  width: 60px;
  height: 60px;
  animation: ring-rotate 30s linear infinite;
}

.middle-core {
  width: 45px;
  height: 45px;
  animation: ring-rotate 20s linear infinite reverse;
}

.inner-core {
  width: 30px;
  height: 30px;
  animation: ring-rotate 15s linear infinite;
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.core-segment {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: rgba(0, 240, 255, 0.6);
  border-right-color: rgba(0, 240, 255, 0.6);
  animation: segment-pulse 2s ease-in-out infinite;
}

.core-ring .core-segment:nth-child(2) {
  transform: rotate(120deg);
  animation-delay: 0.5s;
}

.core-ring .core-segment:nth-child(3) {
  transform: rotate(240deg);
  animation-delay: 1s;
}

@keyframes segment-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.core-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background: #00f0ff;
  border-radius: 50%;
  box-shadow: 0 0 15px #00f0ff, 0 0 30px rgba(0, 240, 255, 0.5);
  animation: core-pulse 2s ease-in-out infinite;
}

@keyframes core-pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    box-shadow: 0 0 15px #00f0ff, 0 0 30px rgba(0, 240, 255, 0.5);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.2);
    box-shadow: 0 0 25px #00f0ff, 0 0 50px rgba(0, 240, 255, 0.7);
  }
}

.core-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  animation: core-expand 2s ease-in-out infinite;
}

@keyframes core-expand {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.5;
  }
  50% {
    transform: translate(-50%, -50%) scale(2);
    opacity: 0;
  }
}

.merlin-info {
  display: flex;
  flex-direction: column;
}

.merlin-title {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: #00f0ff;
  text-shadow: 0 0 10px #00f0ff;
  margin-bottom: 0.25rem;
}

.merlin-subtitle {
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  color: rgba(0, 240, 255, 0.6);
  margin-bottom: 0.5rem;
}

.merlin-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: status-pulse 2s ease-in-out infinite;
}

.status-online {
  background: #00ff88;
  box-shadow: 0 0 10px #00ff88;
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.6);
}

.header-right {
  display: flex;
  gap: 1rem;
}

.header-metrics {
  display: flex;
  gap: 1rem;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.metric-label {
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.5);
}

.metric-value {
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #00f0ff;
}

/* ═══ JARVIS CHAT AREA ═══ */
.jarvis-chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2;
}

.chat-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  background: rgba(10, 14, 39, 0.3);
}

.chat-scroll-area::-webkit-scrollbar {
  width: 6px;
}

.chat-scroll-area::-webkit-scrollbar-track {
  background: rgba(0, 240, 255, 0.1);
}

.chat-scroll-area::-webkit-scrollbar-thumb {
  background: rgba(0, 240, 255, 0.3);
  border-radius: 3px;
}

.chat-scroll-area::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 240, 255, 0.5);
}

.messages-container {
  max-width: 900px;
  margin: 0 auto;
}

.message {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  animation: message-slide 0.3s ease;
}

@keyframes message-slide {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.message-user {
  flex-direction: row-reverse;
}

.message-merlin .message-content {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-left: 3px solid #00f0ff;
}

.message-user .message-content {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-right: 3px solid #00ff88;
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  position: relative;
}

.avatar-ring {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 50%;
  animation: ring-rotate 10s linear infinite;
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

.message-content {
  flex: 1;
  padding: 1rem 1.5rem;
  border-radius: 0.25rem;
  backdrop-filter: blur(10px);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(0, 240, 255, 0.2);
}

.message-author {
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #00f0ff;
}

.message-time {
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.5);
}

.message-body {
  line-height: 1.6;
}

.greeting {
  font-size: 1rem;
  font-weight: 600;
  color: #00f0ff;
  margin-bottom: 0.5rem;
  letter-spacing: 0.1em;
}

.description {
  color: rgba(0, 240, 255, 0.7);
  margin-bottom: 0.5rem;
  letter-spacing: 0.05em;
}

.capabilities-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.capabilities-list li {
  padding: 0.25rem 0;
  color: rgba(0, 240, 255, 0.7);
  position: relative;
  padding-left: 1.5rem;
  letter-spacing: 0.05em;
}

.capabilities-list li::before {
  content: "▸";
  position: absolute;
  left: 0;
  color: #00f0ff;
}

.prompt {
  color: #00f0ff;
  font-weight: 600;
  margin-top: 1rem;
  letter-spacing: 0.1em;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem 0;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: #00f0ff;
  border-radius: 50%;
  animation: typing-bounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-6px);
  }
}

.message-text {
  color: #00f0ff;
  white-space: pre-wrap;
  letter-spacing: 0.05em;
}

/* ═══ JARVIS INPUT AREA ═══ */
.jarvis-input-area {
  padding: 1.5rem 2rem;
  background: rgba(10, 14, 39, 0.8);
  border-top: 1px solid rgba(0, 240, 255, 0.3);
  backdrop-filter: blur(10px);
  z-index: 2;
}

.input-container {
  display: flex;
  gap: 0.75rem;
  max-width: 900px;
  margin: 0 auto;
}

.input-frame {
  flex: 1;
  border: 1px solid rgba(0, 240, 255, 0.3);
  background: rgba(10, 14, 39, 0.5);
  transition: all 0.2s;
}

.input-frame:focus-within {
  border-color: rgba(0, 240, 255, 0.6);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
}

.jarvis-textarea {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  border: none;
  color: #00f0ff;
  font-family: 'Rajdhani', 'Orbitron', monospace;
  font-size: 0.875rem;
  letter-spacing: 0.05em;
  resize: none;
  outline: none;
}

.jarvis-textarea::placeholder {
  color: rgba(0, 240, 255, 0.4);
}

.jarvis-send-btn {
  width: 50px;
  height: 50px;
  border: 1px solid rgba(0, 240, 255, 0.3);
  background: rgba(0, 240, 255, 0.1);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.jarvis-send-btn:hover:not(:disabled) {
  border-color: rgba(0, 240, 255, 0.6);
  background: rgba(0, 240, 255, 0.2);
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.3);
}

.jarvis-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-icon {
  font-size: 1.25rem;
  color: #00f0ff;
}

.input-hint {
  text-align: center;
  margin-top: 0.5rem;
}

.hint-text {
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  color: rgba(0, 240, 255, 0.4);
}

/* ═══ JARVIS SIDEBAR ═══ */
.jarvis-sidebar {
  width: 250px;
  background: rgba(10, 14, 39, 0.8);
  border-left: 1px solid rgba(0, 240, 255, 0.3);
  padding: 1rem;
  overflow-y: auto;
  transition: width 0.3s ease;
  backdrop-filter: blur(10px);
  z-index: 2;
}

.sidebar-collapsed {
  width: 60px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
}

.sidebar-toggle {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(0, 240, 255, 0.3);
  background: rgba(0, 240, 255, 0.1);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-toggle:hover {
  border-color: rgba(0, 240, 255, 0.6);
  background: rgba(0, 240, 255, 0.2);
}

.toggle-icon {
  font-size: 1rem;
  color: #00f0ff;
}

.sidebar-title {
  font-size: 0.875rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #00f0ff;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-section {
  animation: section-fade 0.3s ease;
}

@keyframes section-fade {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: rgba(0, 240, 255, 0.6);
  margin-bottom: 1rem;
}

.logs-list,
.memory-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.log-item,
.memory-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid rgba(0, 240, 255, 0.2);
  background: rgba(0, 240, 255, 0.05);
  cursor: pointer;
  transition: all 0.2s;
}

.log-item:hover,
.memory-item:hover {
  border-color: rgba(0, 240, 255, 0.4);
  background: rgba(0, 240, 255, 0.1);
  transform: translateX(4px);
}

.log-icon,
.memory-icon {
  font-size: 1rem;
}

.log-info,
.memory-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.log-title,
.memory-title {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #00f0ff;
}

.log-time,
.memory-type {
  font-size: 0.625rem;
  letter-spacing: 0.05em;
  color: rgba(0, 240, 255, 0.5);
}

.quick-commands {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quick-command-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid rgba(0, 240, 255, 0.2);
  background: rgba(0, 240, 255, 0.05);
  cursor: pointer;
  transition: all 0.2s;
}

.quick-command-btn:hover {
  border-color: rgba(0, 240, 255, 0.4);
  background: rgba(0, 240, 255, 0.1);
  transform: translateX(4px);
}

.command-icon {
  font-size: 1rem;
}

.command-text {
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  color: #00f0ff;
}
</style>