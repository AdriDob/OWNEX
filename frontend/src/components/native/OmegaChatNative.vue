<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'

interface ChatMessage {
  id: string
  type: 'user' | 'assistant' | 'system' | 'confirmation' | 'result' | 'error'
  content: string
  timestamp: Date
  commandId?: string
  reasoning?: string
  alternatives?: string[]
  pending?: boolean
}

interface Session {
  session_id: string
  device_id: string
  user_id: string
  created_at: string
}

const messages = ref<ChatMessage[]>([])
const input = ref('')
const session = ref<Session | null>(null)
const connecting = ref(false)
const connected = ref(false)
const sending = ref(false)
const pendingConfirmation = ref<ChatMessage | null>(null)
const sidebarOpen = ref(true)

const invoke = (window as any).__TAURI__.core.invoke

onMounted(async () => {
  await initSession()
  await checkBackendHealth()
})

async function initSession() {
  connecting.value = true
  try {
    const result = await invoke('remote_create_session', {
      request: {
        device_id: 'omega-desktop-' + Date.now().toString(36),
        user_id: 'adriel'
      }
    })
    session.value = result
    connected.value = true
    addMessage({
      type: 'system',
      content: `🔗 Conectado a OWNEX Alpha. Sesión: ${result.session_id}`,
      timestamp: new Date()
    })
  } catch (e) {
    addMessage({
      type: 'error',
      content: `❌ Error conectando: ${e}`,
      timestamp: new Date()
    })
  } finally {
    connecting.value = false
  }
}

async function checkBackendHealth() {
  try {
    const health = await invoke('remote_health')
    addMessage({
      type: 'system',
      content: `✅ Backend: ${health.status || 'OK'} (v${health.version || '7.0.0'})`,
      timestamp: new Date()
    })
  } catch {
    addMessage({
      type: 'error',
      content: '⚠️ Backend no responde. Iniciando...',
      timestamp: new Date()
    })
    try {
      await invoke('start_backend', { app_handle: null })
    } catch {}
  }
}

function addMessage(msg: Omit<ChatMessage, 'id'>) {
  messages.value.push({
    ...msg,
    id: Date.now().toString(36) + Math.random().toString(36).slice(2)
  })
  scrollToBottom()
}

function scrollToBottom() {
  nextTick(() => {
    const container = document.querySelector('.chat-messages')
    if (container) container.scrollTop = container.scrollHeight
  })
}

async function sendMessage() {
  if (!input.value.trim() || !session.value || sending.value) return
  
  const userMessage = input.value.trim()
  input.value = ''
  sending.value = true
  
  addMessage({
    type: 'user',
    content: userMessage,
    timestamp: new Date()
  })
  
  try {
    const result = await invoke('remote_chat', {
      request: {
        session_id: session.value.session_id,
        message: userMessage,
        auto_approve: false
      }
    })
    
    handleChatResult(result)
  } catch (e) {
    addMessage({
      type: 'error',
      content: `❌ Error: ${e}`,
      timestamp: new Date()
    })
  } finally {
    sending.value = false
  }
}

function handleChatResult(result: any) {
  if (result.type === 'confirmation_required') {
    const confirmMsg: ChatMessage = {
      type: 'confirmation',
      content: result.message,
      timestamp: new Date(),
      commandId: result.command_id,
      reasoning: result.reasoning,
      alternatives: result.alternatives,
      pending: true
    }
    addMessage(confirmMsg)
    pendingConfirmation.value = confirmMsg
  } else if (result.type === 'result') {
    if (result.success) {
      addMessage({
        type: 'result',
        content: result.output || result.message,
        timestamp: new Date()
      })
    } else {
      addMessage({
        type: 'error',
        content: result.message,
        timestamp: new Date()
      })
    }
    pendingConfirmation.value = null
  } else if (result.type === 'error') {
    addMessage({
      type: 'error',
      content: result.message,
      timestamp: new Date()
    })
  }
}

async function handleApproval(approve: boolean) {
  if (!pendingConfirmation.value || !session.value) return
  
  const cmdId = pendingConfirmation.value.commandId
  if (!cmdId) return
  
  if (approve) {
    addMessage({
      type: 'user',
      content: '✅ Confirmado — ejecutando...',
      timestamp: new Date()
    })
    
    try {
      const result = await invoke('remote_approve', {
        request: { session_id: session.value!.session_id, command_id: cmdId }
      })
      handleChatResult(result)
    } catch (e) {
      addMessage({ type: 'error', content: `❌ ${e}`, timestamp: new Date() })
    }
  } else {
    addMessage({
      type: 'system',
      content: '❌ Cancelado por el usuario',
      timestamp: new Date()
    })
    pendingConfirmation.value = null
  }
}

function clearChat() {
  messages.value = []
  addMessage({
    type: 'system',
    content: '🧹 Chat limpiado',
    timestamp: new Date()
  })
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

const formattedTime = (date: Date) => 
  date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })

const messageClass = (msg: ChatMessage) => [
  'chat-msg',
  `chat-msg--${msg.type}`,
  msg.pending ? 'chat-msg--pending' : ''
].join(' ')
</script>

<template>
  <div class="omega-chat-native">
    <aside v-show="sidebarOpen" class="chat-sidebar">
      <div class="sidebar-header">
        <h2>💬 OMEGA Chat</h2>
        <button class="icon-btn" @click="toggleSidebar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>
      
      <div class="session-info" v-if="session">
        <div class="session-badge">
          <span class="status-dot" :class="connected ? 'connected' : 'disconnected'"></span>
          <span>Conectado</span>
        </div>
        <div class="session-id">{{ session.session_id.slice(0, 12) }}...</div>
      </div>
      
      <div class="sidebar-actions">
        <button class="action-btn" @click="clearChat">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          Limpiar
        </button>
        <button class="action-btn" @click="initSession">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          Reconectar
        </button>
      </div>
    </aside>

    <main class="chat-main">
      <header class="chat-header">
        <div class="header-left">
          <h1>OWNEX Omega → Alpha</h1>
          <span class="connection-status" :class="connected ? 'online' : 'offline'">
            <span class="dot"></span>
            {{ connected ? 'Conectado a Alpha' : 'Desconectado' }}
          </span>
        </div>
        <div class="header-right">
          <button class="icon-btn" @click="toggleSidebar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
        </div>
      </header>

      <div class="chat-messages" ref="messagesContainer">
        <div v-for="msg in messages" :key="msg.id" :class="messageClass(msg)">
          <div class="msg-avatar">
            <span v-if="msg.type === 'user'">👤</span>
            <span v-else-if="msg.type === 'assistant' || msg.type === 'result'">🤖</span>
            <span v-else-if="msg.type === 'system'">📢</span>
            <span v-else-if="msg.type === 'error'">⚠️</span>
            <span v-else-if="msg.type === 'confirmation'">⚠️</span>
          </div>
          <div class="msg-content">
            <div class="msg-header">
              <span class="msg-type">{{ msg.type.toUpperCase() }}</span>
              <span class="msg-time">{{ formattedTime(msg.timestamp) }}</span>
            </div>
            <div class="msg-body" v-html="formatContent(msg.content)"></div>
            
            <div v-if="msg.type === 'confirmation'" class="confirmation-details">
              <div v-if="msg.reasoning" class="reasoning">
                <strong>Razonamiento:</strong> {{ msg.reasoning }}
              </div>
              <div v-if="msg.alternatives && msg.alternatives.length" class="alternatives">
                <strong>Alternativas:</strong>
                <ul>
                  <li v-for="alt in msg.alternatives" :key="alt">{{ alt }}</li>
                </ul>
              </div>
              <div class="confirmation-actions">
                <button class="btn btn-danger" @click="handleApproval(false)">Cancelar</button>
                <button class="btn btn-primary" @click="handleApproval(true)">Confirmar ✓</button>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="sending" class="typing-indicator">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
          <span>Procesando...</span>
        </div>
      </div>

      <footer class="chat-input-area">
        <div class="input-wrapper">
          <textarea
            v-model="input"
            @keydown.enter.exact="sendMessage"
            @keydown.shift.enter="addNewline"
            placeholder="Escribe libremente... (Enter para enviar, Shift+Enter para nueva línea)"
            :disabled="sending || !connected"
            rows="1"
            class="chat-input"
          ></textarea>
          <button
            class="send-btn"
            @click="sendMessage"
            :disabled="sending || !input.trim() || !connected"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div class="input-hints">
          <kbd>Enter</kbd> Enviar · <kbd>Shift+Enter</kbd> Nueva línea · Comando libre, la IA razona y ejecuta
        </div>
      </footer>
    </main>
  </div>
</template>

<script>
function addNewline() {
  this.input += '\n'
}

function formatContent(content: string) {
  return content
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.omega-chat-native {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
  background: var(--ownex-bg, #050505);
  color: var(--ownex-text, #f0f0f0);
  font-family: var(--font-sans, 'Inter', sans-serif);
}

.chat-sidebar {
  border-right: 1px solid var(--ownex-border, #2a2e37);
  background: var(--ownex-bg-elevated, #111318);
  display: flex;
  flex-direction: column;
  padding: var(--space-md, 16px);
  gap: var(--space-lg, 24px);
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.icon-btn {
  background: none;
  border: none;
  color: var(--ownex-text-dim, #8b8d98);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm, 6px);
}
.icon-btn:hover { color: var(--ownex-text); }

.session-info {
  padding: var(--space-md);
  background: var(--ownex-bg-card, #161920);
  border-radius: var(--radius-md, 10px);
  border: 1px solid var(--ownex-border, #2a2e37);
}

.session-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--ownex-text-dim);
}

.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--ownex-text-muted, #5a5d6a);
}
.status-dot.connected {
  background: var(--ownex-success, #00e39a);
  box-shadow: 0 0 8px var(--ownex-success-glow);
}

.session-id {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--ownex-text-muted);
  margin-top: 4px;
}

.sidebar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--ownex-bg-card);
  border: 1px solid var(--ownex-border);
  border-radius: var(--radius-md);
  color: var(--ownex-text);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.action-btn:hover {
  border-color: var(--ownex-accent);
  background: var(--ownex-accent-dim);
}

.chat-main {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--ownex-border);
  background: var(--ownex-bg-elevated);
}

.header-left h1 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--ownex-text-dim);
  margin-top: 2px;
}
.connection-status .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--ownex-text-muted);
}
.connection-status.online .dot {
  background: var(--ownex-success);
  box-shadow: 0 0 8px var(--ownex-success-glow);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.chat-msg {
  display: flex;
  gap: 12px;
  max-width: 85%;
  animation: slideUp var(--transition-normal);
}

.chat-msg--user { align-self: flex-end; flex-direction: row-reverse; }
.chat-msg--user .msg-content { text-align: right; }

.msg-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  background: var(--ownex-bg-card);
  border: 1px solid var(--ownex-border);
  flex-shrink: 0;
}

.msg-content { flex: 1; min-width: 0; }

.msg-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: var(--ownex-text-muted);
  margin-bottom: 4px;
}

.msg-type {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.chat-msg--user .msg-type { color: var(--ownex-accent); }
.chat-msg--result .msg-type { color: var(--ownex-success); }
.chat-msg--error .msg-type { color: var(--ownex-accent); }
.chat-msg--confirmation .msg-type { color: var(--ownex-warning); }

.msg-body {
  font-size: 0.9rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.msg-body code {
  background: var(--ownex-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.85em;
}

.confirmation-details {
  margin-top: 12px;
  padding: 12px;
  background: var(--ownex-warning-dim, rgba(251,191,36,0.1));
  border: 1px solid var(--ownex-warning-glow);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
}

.reasoning { margin-bottom: 8px; }
.alternatives { margin-bottom: 12px; }
.alternatives ul { margin: 4px 0 0 16px; }

.confirmation-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 12px;
}

.btn {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all var(--transition-fast);
}
.btn-primary {
  background: var(--ownex-accent); color: white;
}
.btn-primary:hover { background: #d01e23; box-shadow: var(--shadow-glow); }
.btn-danger {
  background: var(--ownex-bg-card); color: var(--ownex-text);
  border: 1px solid var(--ownex-border);
}
.btn-danger:hover { border-color: var(--ownex-accent); color: var(--ownex-accent); }

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  color: var(--ownex-text-dim);
  font-size: 0.85rem;
}
.typing-indicator .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ownex-accent);
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator .dot:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator .dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }

.chat-input-area {
  border-top: 1px solid var(--ownex-border);
  background: var(--ownex-bg-elevated);
  padding: var(--space-md) var(--space-lg);
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  min-height: 44px;
  max-height: 160px;
  padding: 10px 14px;
  background: var(--ownex-bg);
  color: var(--ownex-text);
  border: 1px solid var(--ownex-border);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.5;
  resize: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.chat-input:focus {
  outline: none;
  border-color: var(--ownex-accent);
  box-shadow: 0 0 0 3px var(--ownex-accent-dim);
}
.chat-input::placeholder { color: var(--ownex-text-muted); }
.chat-input:disabled { opacity: 0.6; }

.send-btn {
  width: 44px; height: 44px;
  border-radius: var(--radius-md);
  background: var(--ownex-accent);
  color: white;
  border: none;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast);
}
.send-btn:hover:not(:disabled) {
  background: #d01e23;
  box-shadow: var(--shadow-glow);
}
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.input-hints {
  margin-top: 8px;
  font-size: 0.7rem;
  color: var(--ownex-text-muted);
}
.input-hints kbd {
  background: var(--ownex-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  border: 1px solid var(--ownex-border);
}

@media (max-width: 1024px) {
  .omega-chat-native {
    grid-template-columns: 1fr;
  }
  .chat-sidebar {
    position: fixed;
    left: -300px; top: 0; bottom: 0;
    z-index: 100;
    width: 280px;
    transition: left var(--transition-normal);
  }
}

.chat-messages::-webkit-scrollbar { width: 6px; }
.chat-messages::-webkit-scrollbar-track { background: var(--ownex-bg); }
.chat-messages::-webkit-scrollbar-thumb { background: var(--ownex-border); border-radius: 3px; }
.chat-messages::-webkit-scrollbar-thumb:hover { background: var(--ownex-border-light); }
</style>
