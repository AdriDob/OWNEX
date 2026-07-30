<template>
  <div class="merlin-interface">
    <!-- ═══ OFFICE RETRO HEADER ═══ -->
    <header class="merlin-header">
      <div class="header-left">
        <div class="merlin-avatar">
          <div class="avatar-retro-border"></div>
          <div class="avatar-content">
            <div class="avatar-icon">🧙</div>
            <div class="avatar-glow"></div>
          </div>
        </div>
        <div class="merlin-info">
          <h1 class="merlin-title">MERLIN</h1>
          <p class="merlin-subtitle">Asistente de Inteligencia Autónoma</p>
          <div class="merlin-status">
            <span class="status-dot" :class="{ 'status-online': isOnline, 'status-offline': !isOnline }"></span>
            <span class="status-text">{{ isOnline ? 'En línea' : 'Desconectado' }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="retro-controls">
          <button @click="toggleTheme" class="retro-btn retro-theme" title="Cambiar tema">
            <div class="btn-icon">🎨</div>
          </button>
          <button @click="clearChat" class="retro-btn retro-clear" title="Limpiar chat">
            <div class="btn-icon">🗑️</div>
          </button>
          <button @click="toggleSettings" class="retro-btn retro-settings" title="Configuración">
            <div class="btn-icon">⚙️</div>
          </button>
        </div>
      </div>
    </header>

    <!-- ═══ OFFICE RETRO CHAT AREA ═══ -->
    <div class="merlin-chat-area">
      <div class="chat-scroll-area" ref="chatScrollArea">
        <div class="messages-container">
          <!-- Welcome message -->
          <div class="message message-welcome">
            <div class="message-avatar">
              <div class="avatar-retro-border-small"></div>
              <div class="avatar-icon-small">🧙</div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-author">MERLIN</span>
                <span class="message-time">{{ formatTime(new Date()) }}</span>
              </div>
              <div class="message-body">
                <p class="greeting">{{ greeting }}</p>
                <p class="description">Soy MERLIN, tu asistente de inteligencia autónoma. Estoy aquí para ayudarte con:</p>
                <ul class="capabilities-list">
                  <li v-for="capability in capabilities" :key="capability">{{ capability }}</li>
                </ul>
                <p class="prompt">¿En qué puedo ayudarte hoy?</p>
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
              <div class="avatar-retro-border-small"></div>
              <div class="avatar-icon-small">🧙</div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-author">{{ message.role === 'user' ? 'Tú' : 'MERLIN' }}</span>
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

      <!-- ═══ OFFICE RETRO INPUT AREA ═══ -->
      <div class="merlin-input-area">
        <div class="input-container">
          <div class="input-retro-border">
            <textarea
              v-model="userInput"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.shift.enter.exact="userInput += '\n'"
              placeholder="Escribe tu mensaje a MERLIN..."
              class="retro-textarea"
              rows="1"
              ref="inputRef"
            ></textarea>
          </div>
          <button
            @click="sendMessage"
            :disabled="!userInput.trim() || isProcessing"
            class="retro-send-btn"
            title="Enviar mensaje"
          >
            <div class="send-icon">📤</div>
          </button>
        </div>
        <div class="input-hint">
          <span class="hint-text">Enter para enviar • Shift+Enter para nueva línea</span>
        </div>
      </div>
    </div>

    <!-- ═══ OFFICE RETRO SIDEBAR ═══ -->
    <aside class="merlin-sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <div class="sidebar-header">
        <button @click="toggleSidebar" class="sidebar-toggle">
          <div class="toggle-icon">{{ sidebarCollapsed ? '➡️' : '⬅️' }}</div>
        </button>
        <h3 class="sidebar-title" v-if="!sidebarCollapsed">Herramientas</h3>
      </div>

      <div class="sidebar-content">
        <div class="sidebar-section">
          <h4 class="section-title" v-if="!sidebarCollapsed">📝 Apuntes</h4>
          <div class="notes-list">
            <div
              v-for="note in notes"
              :key="note.id"
              class="note-item"
              @click="loadNote(note)"
            >
              <div class="note-icon">📄</div>
              <div class="note-info" v-if="!sidebarCollapsed">
                <span class="note-title">{{ note.title }}</span>
                <span class="note-date">{{ formatDate(note.date) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="sidebar-section">
          <h4 class="section-title" v-if="!sidebarCollapsed">🧠 Memoria</h4>
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
          <h4 class="section-title" v-if="!sidebarCollapsed">⚡ Acciones rápidas</h4>
          <div class="quick-actions">
            <button @click="generateReport" class="quick-action-btn">
              <span class="action-icon">📊</span>
              <span class="action-text" v-if="!sidebarCollapsed">Generar reporte</span>
            </button>
            <button @click="analyzeTarget" class="quick-action-btn">
              <span class="action-icon">🎯</span>
              <span class="action-text" v-if="!sidebarCollapsed">Analizar target</span>
            </button>
            <button @click="optimizeWorkflow" class="quick-action-btn">
              <span class="action-icon">⚡</span>
              <span class="action-text" v-if="!sidebarCollapsed">Optimizar workflow</span>
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- ═══ OFFICE RETRO SETTINGS MODAL ═══ -->
    <div v-if="showSettings" class="modal-overlay" @click.self="showSettings = false">
      <div class="modal retro-modal">
        <div class="modal-header retro-modal-header">
          <h2 class="modal-title">Configuración de MERLIN</h2>
          <button @click="showSettings = false" class="modal-close retro-close">
            <div class="close-icon">✕</div>
          </button>
        </div>
        <div class="modal-body retro-modal-body">
          <div class="settings-section">
            <h3 class="settings-section-title">🎨 Personalización</h3>
            <div class="setting-item">
              <label class="setting-label">Nombre personalizado</label>
              <input v-model="customName" type="text" class="retro-input" placeholder="MERLIN" />
            </div>
            <div class="setting-item">
              <label class="setting-label">Saludo personalizado</label>
              <textarea v-model="customGreeting" class="retro-textarea" rows="2" placeholder="Hola, soy MERLIN..."></textarea>
            </div>
          </div>

          <div class="settings-section">
            <h3 class="settings-section-title">🧙 Comportamiento</h3>
            <div class="setting-item">
              <label class="setting-label">Nivel de detalle</label>
              <select v-model="detailLevel" class="retro-select">
                <option value="concise">Conciso</option>
                <option value="normal">Normal</option>
                <option value="detailed">Detallado</option>
              </select>
            </div>
            <div class="setting-item">
              <label class="setting-label">Tono de respuesta</label>
              <select v-model="responseTone" class="retro-select">
                <option value="professional">Profesional</option>
                <option value="friendly">Amigable</option>
                <option value="casual">Casual</option>
                <option value="formal">Formal</option>
              </select>
            </div>
          </div>

          <div class="settings-section">
            <h3 class="settings-section-title">📊 Analytics</h3>
            <div class="setting-item">
              <label class="setting-checkbox">
                <input type="checkbox" v-model="enableAnalytics" />
                <span>Habilitar analytics de conversación</span>
              </label>
            </div>
            <div class="setting-item">
              <label class="setting-checkbox">
                <input type="checkbox" v-model="enableLearning" />
                <span>Habilitar aprendizaje continuo</span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer retro-modal-footer">
          <button @click="saveSettings" class="retro-btn retro-primary">
            <div class="btn-icon">💾</div>
            Guardar configuración
          </button>
          <button @click="showSettings = false" class="retro-btn retro-secondary">
            <div class="btn-icon">✕</div>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import axios from 'axios'

const isOnline = ref(true)
const isProcessing = ref(false)
const userInput = ref('')
const showSettings = ref(false)
const sidebarCollapsed = ref(false)
const customName = ref('MERLIN')
const customGreeting = ref('¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma.')
const detailLevel = ref('normal')
const responseTone = ref('professional')
const enableAnalytics = ref(true)
const enableLearning = ref(true)

const greeting = computed(() => customGreeting.value)
const capabilities = ref([
  'Análisis de targets y vulnerabilidades',
  'Generación de reportes automatizados',
  'Optimización de workflows',
  'Investigación y análisis de datos',
  'Planificación estratégica',
  'Asistencia en decisiones técnicas'
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

const notes = ref([
  { id: 1, title: 'Análisis de target principal', date: new Date(Date.now() - 86400000) },
  { id: 2, title: 'Reporte de vulnerabilidad SQLi', date: new Date(Date.now() - 172800000) },
  { id: 3, title: 'Configuración de automatización', date: new Date(Date.now() - 259200000) }
])

const recentMemories = ref([
  { id: 1, title: 'Patrón de análisis XSS', type: 'Pattern' },
  { id: 2, title: 'Workflow de reporting', type: 'Workflow' },
  { id: 3, title: 'Estrategia de recon', type: 'Strategy' }
])

const chatScrollArea = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDate(date: Date) {
  return date.toLocaleDateString()
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

  // Add typing indicator
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
        detail_level: detailLevel.value,
        response_tone: responseTone.value,
        enable_analytics: enableAnalytics.value,
        enable_learning: enableLearning.value
      }
    })

    // Remove typing indicator
    messages.value = messages.value.filter(m => m.id !== typingId)

    // Add actual response
    messages.value.push({
      id: Date.now(),
      role: 'merlin',
      content: response.data.response,
      timestamp: new Date(),
      isTyping: false
    })

    if (enableLearning.value) {
      await saveToMemory(userMessage, response.data.response)
    }

  } catch (error) {
    console.error('Error sending message:', error)
    messages.value = messages.value.filter(m => m.id !== typingId)
    messages.value.push({
      id: Date.now(),
      role: 'merlin',
      content: 'Lo siento, tuve un error al procesar tu mensaje. Por favor, intenta de nuevo.',
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

function toggleTheme() {
  // Toggle between retro themes
  document.body.classList.toggle('merlin-theme-clasic')
  document.body.classList.toggle('merlin-theme-modern')
}

function clearChat() {
  if (confirm('¿Estás seguro de que quieres limpiar el chat?')) {
    messages.value = [
      {
        id: Date.now(),
        role: 'merlin',
        content: greeting.value,
        timestamp: new Date(),
        isTyping: false
      }
    ]
  }
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleSettings() {
  showSettings.value = !showSettings.value
}

function loadNote(note: any) {
  userInput.value = `¿Puedes mostrarme los detalles de ${note.title}?`
  sendMessage()
}

function loadMemory(memory: any) {
  userInput.value = `¿Puedes recordarme sobre ${memory.title}?`
  sendMessage()
}

async function generateReport() {
  userInput.value = 'Genera un reporte del análisis más reciente'
  sendMessage()
}

async function analyzeTarget() {
  userInput.value = 'Analiza el target principal del dashboard'
  sendMessage()
}

async function optimizeWorkflow() {
  userInput.value = 'Optimiza el workflow actual de operaciones'
  sendMessage()
}

async function saveSettings() {
  try {
    await axios.post('/api/merlin/settings', {
      custom_name: customName.value,
      custom_greeting: customGreeting.value,
      detail_level: detailLevel.value,
      response_tone: responseTone.value,
      enable_analytics: enableAnalytics.value,
      enable_learning: enableLearning.value
    })

    showSettings.value = false
    alert('Configuración guardada exitosamente')
  } catch (error) {
    console.error('Error saving settings:', error)
    alert('Error al guardar configuración')
  }
}

async function saveToMemory(question: string, response: string) {
  try {
    await axios.post('/api/merlin/memory', {
      question,
      response,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error saving to memory:', error)
  }
}

onMounted(() => {
  // Focus input on mount
  if (inputRef.value) {
    inputRef.value.focus()
  }
})
</script>

<style scoped>
/* ═══ OFFICE RETRO MODERNIZED THEME ═══ */
.merlin-interface {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  font-family: 'Courier New', 'Consolas', monospace;
  color: #e8e8e8;
}

/* ═══ HEADER ═══ */
.merlin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid #4a5568;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  animation: slideDown 0.5s ease;
}

@keyframes slideDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.merlin-avatar {
  position: relative;
  width: 60px;
  height: 60px;
  animation: pulseGlow 2s ease-in-out infinite;
}

@keyframes pulseGlow {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.6);
  }
}

.avatar-retro-border {
  position: absolute;
  inset: 0;
  border: 3px solid #4a5568;
  border-radius: 50%;
  animation: retroBorder 3s linear infinite;
}

@keyframes retroBorder {
  0% {
    border-color: #4a5568;
  }
  25% {
    border-color: #99199a;
  }
  50% {
    border-color: #4a5568;
  }
  75% {
    border-color: #99199a;
  }
  100% {
    border-color: #4a5568;
  }
}

.avatar-content {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #9500ff 100%);
  border-radius: 50%;
}

.avatar-icon {
  font-size: 1.5rem;
  z-index: 1;
}

.avatar-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  animation: glowPulse 3s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}

.merlin-info {
  display: flex;
  flex-direction: column;
}

.merlin-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #e8e8e8;
  letter-spacing: 0.1em;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  animation: titleGlow 2s ease-in-out infinite;
}

@keyframes titleGlow {
  0%, 100% {
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
  }
  50% {
    text-shadow: 2px 2px 8px rgba(99, 102, 241, 0.8);
  }
}

.merlin-subtitle {
  font-size: 0.875rem;
  color: #a0a0a0;
  margin-top: 0.25rem;
}

.merlin-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: statusPulse 2s ease-in-out infinite;
}

.status-online {
  background: #4ade80;
  box-shadow: 0 0 8px #4ade80;
}

.status-offline {
  background: #f87171;
  box-shadow: 0 0 8px #f87171;
}

@keyframes statusPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-text {
  font-size: 0.75rem;
  color: #a0a0a0;
}

.header-right {
  display: flex;
  gap: 0.5rem;
}

.retro-controls {
  display: flex;
  gap: 0.5rem;
}

.retro-btn {
  width: 40px;
  height: 40px;
  border: 2px solid #4a5568;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.retro-btn:hover {
  border-color: #99199a;
  background: rgba(153, 153, 154, 0.1);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.btn-icon {
  font-size: 1.25rem;
}

/* ═══ CHAT AREA ═══ */
.merlin-chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.1);
  scroll-behavior: smooth;
}

.chat-scroll-area::-webkit-scrollbar {
  width: 8px;
}

.chat-scroll-area::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}

.chat-scroll-area::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 4px;
}

.chat-scroll-area::-webkit-scrollbar-thumb:hover {
  background: #99199a;
}

.messages-container {
  max-width: 900px;
  margin: 0 auto;
}

.message {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  animation: messageSlide 0.3s ease;
}

@keyframes messageSlide {
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
  background: rgba(99, 102, 241, 0.2);
  border: 2px solid #6366f1;
  border-left: 4px solid #6366f1;
}

.message-user .message-content {
  background: rgba(21, 128, 61, 0.2);
  border: 2px solid #1b5e20;
  border-right: 4px solid #1b5e20;
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  position: relative;
}

.avatar-retro-border-small {
  position: absolute;
  inset: 0;
  border: 2px solid #4a5568;
  border-radius: 50%;
  animation: retroBorder 3s linear infinite;
}

.avatar-icon-small {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #9500ff 100%);
  border-radius: 50%;
  font-size: 1rem;
  z-index: 1;
}

.message-content {
  flex: 1;
  padding: 1rem 1.5rem;
  border-radius: 0.5rem;
  backdrop-filter: blur(10px);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.message-author {
  font-weight: 700;
  color: #e8e8e8;
  letter-spacing: 0.05em;
}

.message-time {
  font-size: 0.75rem;
  color: #a0a0a0;
}

.message-body {
  line-height: 1.6;
}

.greeting {
  font-size: 1.125rem;
  font-weight: 600;
  color: #e8e8e8;
  margin-bottom: 0.5rem;
}

.description {
  color: #a0a0a0;
  margin-bottom: 0.5rem;
}

.capabilities-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.capabilities-list li {
  padding: 0.25rem 0;
  color: #a0a0a0;
  position: relative;
  padding-left: 1.5rem;
}

.capabilities-list li::before {
  content: "▸";
  position: absolute;
  left: 0;
  color: #6366f1;
}

.prompt {
  color: #e8e8e8;
  font-weight: 600;
  margin-top: 1rem;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem 0;
}

.typing-dot {
  width: 8px;
  height: 8px;
  background: #6366f1;
  border-radius: 50%;
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
}

.message-text {
  color: #e8e8e8;
  white-space: pre-wrap;
}

/* ═══ INPUT AREA ═══ */
.merlin-input-area {
  padding: 1rem 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-top: 2px solid #4a5568;
}

.input-container {
  display: flex;
  gap: 0.5rem;
  max-width: 900px;
  margin: 0 auto;
}

.input-retro-border {
  flex: 1;
  border: 2px solid #4a5568;
  background: rgba(0, 0, 0, 0.2);
  transition: all 0.2s;
}

.input-retro-border:focus-within {
  border-color: #6366f1;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
}

.retro-textarea {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  border: none;
  color: #e8e8e8;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 0.875rem;
  resize: none;
  outline: none;
}

.retro-textarea::placeholder {
  color: #6b7280;
}

.retro-send-btn {
  width: 50px;
  height: 50px;
  border: 2px solid #4a5568;
  background: rgba(99, 102, 241, 0.2);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.retro-send-btn:hover:not(:disabled) {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(99, 102, 241, 0.3);
}

.retro-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-icon {
  font-size: 1.25rem;
}

.input-hint {
  text-align: center;
  margin-top: 0.5rem;
}

.hint-text {
  font-size: 0.75rem;
  color: #6b7280;
}

/* ═══ SIDEBAR ═══ */
.merlin-sidebar {
  width: 250px;
  background: rgba(0, 0, 0, 0.3);
  border-left: 2px solid #4a5568;
  padding: 1rem;
  overflow-y: auto;
  transition: width 0.3s ease;
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
  border-bottom: 1px solid #4a5568;
}

.sidebar-toggle {
  width: 40px;
  height: 40px;
  border: 2px solid #4a5568;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-toggle:hover {
  border-color: #99199a;
  background: rgba(153, 153, 154, 0.1);
}

.toggle-icon {
  font-size: 1.25rem;
}

.sidebar-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: #e8e8e8;
  letter-spacing: 0.05em;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-section {
  animation: sectionFade 0.3s ease;
}

@keyframes sectionFade {
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
  font-size: 0.875rem;
  font-weight: 700;
  color: #e8e8e8;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.notes-list,
.memory-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.note-item,
.memory-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid #4a5568;
  background: rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s;
}

.note-item:hover,
.memory-item:hover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
  transform: translateX(4px);
}

.note-icon,
.memory-icon {
  font-size: 1.25rem;
}

.note-info,
.memory-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.note-title,
.memory-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #e8e8e8;
}

.note-date,
.memory-type {
  font-size: 0.75rem;
  color: #a0a0a0;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quick-action-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid #4a5568;
  background: rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s;
}

.quick-action-btn:hover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.1);
  transform: translateX(4px);
}

.action-icon {
  font-size: 1rem;
}

.action-text {
  font-size: 0.875rem;
  color: #e8e8e8;
}

/* ═══ MODAL ═══ */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: modalFadeIn 0.3s ease;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.retro-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 2px solid #4a5568;
  border-radius: 0.5rem;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  animation: modalSlide 0.3s ease;
}

@keyframes modalSlide {
  from {
    transform: translateY(-50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.retro-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 2px solid #4a5568;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #e8e8e8;
  letter-spacing: 0.05em;
}

.retro-close {
  width: 40px;
  height: 40px;
  border: 2px solid #4a5568;
  background: rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.retro-close:hover {
  border-color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.close-icon {
  font-size: 1.25rem;
}

.retro-modal-body {
  padding: 1.5rem;
  max-height: 60vh;
  overflow-y: auto;
}

.settings-section {
  margin-bottom: 2rem;
}

.settings-section-title {
  font-size: 1rem;
  font-weight: 700;
  color: #e8e8e8;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setting-item {
  margin-bottom: 1rem;
}

.setting-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #e8e8e8;
  letter-spacing: 0.05em;
}

.retro-input,
.retro-select,
.retro-textarea {
  width: 100%;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  border: 2px solid #4a5568;
  color: #e8e8e8;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 0.875rem;
  outline: none;
  transition: all 0.2s;
}

.retro-input:focus,
.retro-select:focus,
.retro-textarea:focus {
  border-color: #6366f1;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
}

.setting-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.setting-checkbox input {
  accent-color: #6366f1;
}

.setting-checkbox span {
  color: #e8e8e8;
  font-size: 0.875rem;
}

.retro-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-top: 2px solid #4a5568;
}

.retro-primary {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.2);
}

.retro-primary:hover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.4);
}

.retro-secondary {
  border-color: #4a5568;
  background: rgba(0, 0, 0, 0.2);
}

.retro-secondary:hover {
  border-color: #99199a;
  background: rgba(153, 153, 154, 0.1);
}

/* ═══ THEME VARIATIONS ═══ */
.merlin-theme-classic {
  background: linear-gradient(135deg, #2d3436 0%, #1e293b 50%, #0f172a 100%);
}

.merlin-theme-modern {
  background: linear-gradient(135deg, #1e1b2e 0%, #312e81 50%, #4c1d95 100%);
}
</style>