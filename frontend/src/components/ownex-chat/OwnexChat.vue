<template>
  <div class="ownex-chat" :class="{ 'mobile': isMobile, 'sidebar-open': showSidebar }">
    <!-- Header -->
    <header class="chat-header">
      <div class="header-left">
        <button @click="toggleSidebar" class="sidebar-toggle" aria-label="Toggle sidebar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <div class="merlin-avatar" :class="{ 'processing': isProcessing }">
          <div class="avatar-ring"></div>
          <div class="avatar-core">🧙</div>
        </div>
        <div class="header-info">
          <h2 class="chat-title">MERLIN</h2>
          <p class="chat-subtitle">{{ statusText }}</p>
        </div>
      </div>
      <div class="header-right">
        <button @click="toggleVoice" class="icon-btn" :class="{ 'active': voiceEnabled }" aria-label="Voice input">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
        </button>
        <button @click="toggleMode" class="icon-btn" :class="{ 'expert': !isBeginnerMode }" aria-label="Toggle mode">
          <span class="mode-badge">{{ isBeginnerMode ? '🎓' : '🔬' }}</span>
        </button>
        <button @click="showSidebar = !showSidebar" class="icon-btn" aria-label="Sidebar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"></rect>
            <line x1="9" y1="3" x2="9" y2="21"></line>
            <line x1="15" y1="3" x2="15" y2="21"></line>
          </svg>
        </button>
      </div>
    </header>

    <!-- Sidebar -->
    <aside class="chat-sidebar" v-show="showSidebar">
      <div class="sidebar-header">
        <h3>Tools & Context</h3>
        <button @click="showSidebar = false" class="close-btn">✕</button>
      </div>
      <div class="sidebar-content">
        <div class="sidebar-section">
          <h4>Available Tools</h4>
          <div class="tools-grid">
            <ToolCard
              v-for="tool in availableTools"
              :key="tool.id"
              :tool="tool"
              @execute="executeTool"
            />
          </div>
        </div>
        <div class="sidebar-section">
          <h4>Context</h4>
          <div class="context-items">
            <ContextItem
              v-for="ctx in activeContext"
              :key="ctx.id"
              :context="ctx"
              @remove="removeContext"
            />
          </div>
          <button @click="addContext" class="add-context-btn">+ Add Context</button>
        </div>
        <div class="sidebar-section">
          <h4>Recent Actions</h4>
          <div class="action-log">
            <div
              v-for="action in recentActions"
              :key="action.id"
              class="action-item"
            >
              <span class="action-type">{{ action.type }}</span>
              <span class="action-desc">{{ action.description }}</span>
              <span class="action-time">{{ action.time }}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="chat-main">
      <div class="messages-container" ref="messagesContainer">
        <!-- Welcome/Empty State -->
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="welcome-avatar">
            <div class="avatar-ring"></div>
            <div class="avatar-core">🧙</div>
          </div>
          <div class="welcome-content">
            <p class="greeting">{{ greeting }}</p>
            <p class="description">Sistema listo. ¿En qué te ayudo?</p>
            <div class="suggested-prompts">
              <button
                v-for="prompt in suggestedPrompts"
                :key="prompt"
                @click="sendMessage(prompt)"
                class="prompt-btn"
              >
                {{ prompt }}
              </button>
            </div>
          </div>
        </div>

        <!-- Messages -->
        <div v-else class="messages-list">
          <div
            v-for="message in messages"
            :key="message.id"
            class="message"
            :class="[message.role, message.status]"
          >
            <div v-if="message.role === 'assistant'" class="message-avatar">
              <div class="avatar-ring"></div>
              <div class="avatar-core">🧙</div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-author">{{ message.role === 'user' ? 'Tú' : 'MERLIN' }}</span>
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
              </div>
              <div class="message-body">
                <!-- Typing indicator -->
                <div v-if="message.isTyping" class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                <!-- Tool calls -->
                <div v-if="message.toolCalls && message.toolCalls.length" class="tool-calls">
                  <ToolCallCard
                    v-for="call in message.toolCalls"
                    :key="call.id"
                    :call="call"
                    @approve="approveToolCall"
                    @reject="rejectToolCall"
                  />
                </div>
                <!-- Message content -->
                <div v-else class="message-text" v-html="formatContent(message.content)"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Typing indicator at bottom -->
        <div v-if="isProcessing" class="typing-indicator-bottom">
          <span class="typing-text">MERLIN pensando...</span>
          <div class="typing-dots"><span></span><span></span><span></span></div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <!-- Voice recording indicator -->
        <div v-if="isRecording" class="voice-recording">
          <div class="waveform">
            <span v-for="i in 5" :key="i" :style="{ animationDelay: i * 0.1 + 's' }"></span>
          </div>
          <span class="recording-text">Grabando... {{ recordingDuration }}s</span>
          <button @click="stopVoiceRecording" class="stop-recording-btn">Detener</button>
        </div>

        <div class="input-container">
          <textarea
            v-model="userInput"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.shift.enter.exact="addNewLine"
            :placeholder="isRecording ? 'Grabando voz...' : 'Escribe o usa voz (Ctrl+Space)...'"
            class="chat-input"
            ref="inputRef"
            rows="1"
          ></textarea>
          <div class="input-actions">
            <button
              @click="startVoiceRecording"
              :disabled="isProcessing || isRecording"
              class="icon-btn voice-btn"
              :class="{ 'recording': isRecording }"
              aria-label="Voice input"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              </svg>
            </button>
            <button
              @click="sendMessage"
              :disabled="!userInput.trim() && !isRecording || isProcessing"
              class="send-btn"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>
        <div class="input-hint">
          Enter = Enviar • Shift+Enter = Nueva línea • Ctrl+Space = Voz
        </div>
      </div>
    </main>

<!-- Approval Modal -->
    <Transition name="modal">
      <div v-if="pendingApproval" class="modal-overlay" @click.self="cancelApproval">
        <div class="modal approval-modal">
          <div class="modal-header">
            <h3>{{ pendingApproval.type === 'file_write' ? '✏️ Modificación de Archivo' : pendingApproval.type === 'deploy' ? '🚀 Deploy' : '⚙️ Acción Crítica' }}</h3>
          </div>
          <div class="modal-body">
            <p>{{ pendingApproval.description }}</p>
            <div v-if="pendingApproval.diff" class="diff-preview">
              <pre>{{ pendingApproval.diff }}</pre>
            </div>
            <div v-if="pendingApproval.files" class="files-list">
              <div v-for="f in pendingApproval.files" :key="f" class="file-item">{{ f }}</div>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="cancelApproval" class="btn-secondary">Cancelar</button>
            <button @click="confirmApproval" class="btn-primary" :class="{ 'danger': pendingApproval.type === 'deploy' }">
              {{ pendingApproval.type === 'deploy' ? 'Confirmar Deploy' : 'Aprobar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Context Modal -->
    <Transition name="modal">
      <div v-if="showContextModal" class="modal-overlay" @click.self="showContextModal = false">
        <div class="modal context-modal">
          <div class="modal-header">
            <h3>Agregar Contexto</h3>
          </div>
          <div class="modal-body">
            <div class="context-tabs">
              <button
                v-for="tab in contextTabs"
                :key="tab.id"
                @click="activeContextTab = tab.id"
                :class="{ active: activeContextTab === tab.id }"
                class="tab-btn"
              >
                {{ tab.label }}
              </button>
            </div>
            <div class="tab-content">
              <FileTree v-if="activeContextTab === 'files'" @select="addFileContext" />
              <CodeSearch v-if="activeContextTab === 'search'" @search="searchCode" />
              <GitDiff v-if="activeContextTab === 'git'" @select="addGitContext" />
              <ManualContext v-if="activeContextTab === 'manual'" @save="addManualContext" />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

// Simple media query hook replacement
function useMediaQuery(query: string) {
  const matches = ref(false)
  if (typeof window !== 'undefined') {
    const media = window.matchMedia(query)
    matches.value = media.matches
    const handler = (e: MediaQueryListEvent) => { matches.value = e.matches }
    media.addEventListener('change', handler)
    onUnmounted(() => media.removeEventListener('change', handler))
  }
  return matches
}

// Sub-components (inline for now, extract later)
const ToolCard = {
  props: ['tool'],
  emits: ['execute'],
  template: `
    <button @click="$emit('execute', tool)" class="tool-card" :class="{ 'danger': tool.danger }">
      <span class="tool-icon">{{ tool.icon }}</span>
      <span class="tool-name">{{ tool.name }}</span>
      <span class="tool-desc">{{ tool.description }}</span>
    </button>
  `
}

const ContextItem = {
  props: ['context'],
  emits: ['remove'],
  template: `
    <div class="context-item">
      <span class="context-icon">{{ context.icon }}</span>
      <span class="context-label">{{ context.label }}</span>
      <button @click="$emit('remove', context.id)" class="remove-btn">✕</button>
    </div>
  `
}

const ToolCallCard = {
  props: ['call'],
  emits: ['approve', 'reject'],
  template: `
    <div class="tool-call" :class="{ 'pending': call.status === 'pending', 'approved': call.status === 'approved', 'rejected': call.status === 'rejected' }">
      <div class="tool-call-header">
        <span class="tool-icon">{{ call.icon }}</span>
        <span class="tool-name">{{ call.name }}</span>
        <span class="tool-status">{{ call.status }}</span>
      </div>
      <pre class="tool-args">{{ JSON.stringify(call.args, null, 2) }}</pre>
      <div v-if="call.status === 'pending'" class="tool-actions">
        <button @click="$emit('approve', call)" class="btn-approve">Aprobar</button>
        <button @click="$emit('reject', call)" class="btn-reject">Rechazar</button>
      </div>
    </div>
  `
}

const FileTree = {
  emits: ['select'],
  template: `
    <div class="file-tree">
      <input v-model="search" placeholder="Buscar archivos..." class="tree-search" />
      <div class="tree" ref="treeRef">
        <TreeNode v-for="node in filteredNodes" :key="node.path" :node="node" @select="$emit('select')" />
      </div>
    </div>
  `,
  setup() {
    const search = ref('')
    const treeRef = ref<HTMLElement>()
    const nodes = ref([
      { path: 'src/', type: 'dir', children: [
        { path: 'src/components/', type: 'dir', children: [] },
        { path: 'src/pages/', type: 'dir', children: [] },
        { path: 'src/services/', type: 'dir', children: [] },
      ]},
      { path: 'api/', type: 'dir', children: [] },
      { path: 'core/', type: 'dir', children: [] },
      { path: 'cores/', type: 'dir', children: [] },
    ])
    const filteredNodes = computed(() => nodes.value) // Simplified
    return { search, treeRef, filteredNodes }
  }
}

const TreeNode = {
  props: ['node'],
  emits: ['select'],
  template: `
    <div class="tree-node">
      <div class="node-header" @click="toggle">
        <span class="expand-icon">{{ expanded ? '▼' : '▶' }}</span>
        <span class="node-icon">{{ node.type === 'dir' ? '📁' : '📄' }}</span>
        <span class="node-name" @click="select">{{ node.path.split('/').pop() }}</span>
      </div>
      <div v-show="expanded" class="node-children">
        <TreeNode v-for="child in node.children" :key="child.path" :node="child" @select="$emit('select')" />
      </div>
    </div>
  `,
  setup() {
    const expanded = ref(true)
    const toggle = () => { expanded.value = !expanded.value }
    const select = () => { /* emit select */ }
    return { expanded, toggle, select }
  }
}

const CodeSearch = {
  emits: ['search'],
  template: `
    <div class="code-search">
      <input v-model="query" @keyup.enter="doSearch" placeholder="Buscar código..." />
      <button @click="doSearch">Buscar</button>
      <div class="results">
        <div v-for="r in results" :key="r.file" class="result-item" @click="selectResult(r)">
          {{ r.file }}:{{ r.line }} - {{ r.snippet }}
        </div>
      </div>
    </div>
  `,
  setup() {
    const query = ref('')
    const results = ref([])
    const doSearch = () => { /* search */ }
    const selectResult = (r: any) => { /* emit select */ }
    return { query, results, doSearch, selectResult }
  }
}

const GitDiff = {
  emits: ['select'],
  template: `
    <div class="git-diff">
      <select v-model="branch" @change="loadDiff">
        <option value="main">main</option>
        <option value="develop">develop</option>
      </select>
      <pre>{{ diff }}</pre>
    </div>
  `,
  setup() {
    const branch = ref('main')
    const diff = ref('')
    const loadDiff = () => { /* load diff */ }
    return { branch, diff, loadDiff }
  }
}

const ManualContext = {
  emits: ['save'],
  template: `
    <div class="manual-context">
      <textarea v-model="content" placeholder="Pega código, logs, errores..." rows="10"></textarea>
      <button @click="$emit('save', { type: 'manual', content: content.value })">Agregar</button>
    </div>
  `,
  setup() {
    const content = ref('')
    return { content }
  }
}

// Main component logic
const isMobile = useMediaQuery('(max-width: 768px)')
const router = useRouter()

const isProcessing = ref(false)
const isRecording = ref(false)
const recordingDuration = ref(0)
const voiceEnabled = ref(false)
const showSidebar = ref(false)
const showContextModal = ref(false)
const activeContextTab = ref('files')
const isBeginnerMode = ref(true)
const userInput = ref('')
const messages = ref<any[]>([])
const recentActions = ref<any[]>([])
const pendingApproval = ref<any>(null)
let recordingInterval: any = null

const greeting = ref('Sistema listo. ¿En qué te ayudo?')

const suggestedPrompts = [
  'Analiza mis targets activos',
  'Genera reporte del último hallazgo',
  'Optimiza mi workflow actual',
  '¿Cuál es mi próxima mejor acción?',
  'Revisa mi capital y liquidez',
]

const availableTools = [
  { id: 'analyze_target', name: 'Analizar Target', icon: '🎯', description: 'Recon + attack surface + hipóteses', execute: () => {} },
  { id: 'generate_report', name: 'Generar Reporte', icon: '📊', description: 'Reporte profesional para HackerOne/Bugcrowd', execute: () => {} },
  { id: 'run_autopilot', name: 'Ejecutar Autopilot', icon: '🤖', description: 'Ciclo diario completo', execute: () => {} },
  { id: 'check_capital', name: 'Capital Snapshot', icon: '💰', description: 'Patrimonio total + liquidez', execute: () => {} },
  { id: 'code_fix', name: 'Code Fix (CoderAgent)', icon: '🔧', description: 'Fix autónomo + tests + PR', danger: true, execute: () => {} },
  { id: 'deploy', name: 'Deploy', icon: '🚀', description: 'Deploy a producción', danger: true, execute: () => {} },
]

const activeContext = ref<any[]>([])
const recentActionsList = ref<any[]>([])
const contextTabs = [
  { id: 'files', label: '📁 Archivos' },
  { id: 'search', label: '🔍 Código' },
  { id: 'git', label: '📝 Git' },
  { id: 'manual', label: '✏️ Manual' },
]

let voiceRecognition: any = null
let voiceSynthesis: any = null

function formatTime(date: Date) {
  return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatContent(content: string) {
  return content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

function getStatusText() {
  if (isProcessing) return 'Procesando...'
  if (isRecording) return 'Escuchando...'
  return 'En línea'
}

const statusText = computed(() => getStatusText())

async function sendMessage(content?: string) {
  const message = content || userInput.value.trim()
  if (!message || isProcessing.value) return

  userInput.value = ''
  isProcessing.value = true

  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: message,
    timestamp: new Date(),
    status: 'sent'
  }
  messages.value.push(userMsg)

  const typingId = Date.now() + 1
  messages.value.push({
    id: typingId,
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    isTyping: true,
    status: 'typing'
  })

  await nextTick()
  scrollToBottom()

  try {
    const response = await axios.post('/api/merlin/chat', {
      message,
      context: {
        detail_level: isBeginnerMode.value ? 'beginner' : 'expert',
        response_tone: isBeginnerMode.value ? 'simple' : 'technical',
        enable_analytics: true,
        enable_learning: true,
        active_context: activeContext.value.map(c => c.id),
      },
    })

    messages.value = messages.value.filter(m => m.id !== typingId)

    // Check for tool calls in response
    const data = response.data
    if (data.tool_calls && data.tool_calls.length) {
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: data.response || 'Ejecutando herramientas...',
        timestamp: new Date(),
        toolCalls: data.tool_calls.map((tc: any) => ({
          id: tc.id || Date.now() + Math.random(),
          name: tc.name,
          icon: tc.icon || '⚙️',
          args: tc.args,
          status: 'pending'
        })),
        status: 'tool_calls'
      })
    } else {
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        isTyping: false,
        status: 'completed'
      })
    }

    addAction('chat', `Consulta: ${message.substring(0, 50)}...`)
  } catch (error) {
    console.error('Error:', error)
    messages.value = messages.value.filter(m => m.id !== typingId)
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: 'Error de conexión. Verifica que el backend esté corriendo.',
      timestamp: new Date(),
      status: 'error'
    })
  } finally {
    isProcessing.value = false
    await nextTick()
    scrollToBottom()
  }
}

function addNewLine() {
  userInput.value += '\n'
}

function scrollToBottom() {
  const container = document.querySelector('.messages-container')
  if (container) container.scrollTop = container.scrollHeight
}

function addAction(type: string, description: string) {
  recentActionsList.value.unshift({
    id: Date.now(),
    type,
    description,
    time: formatTime(new Date())
  })
  if (recentActionsList.value.length > 20) recentActionsList.value.pop()
}

async function executeTool(tool: any) {
  addAction('tool', `Ejecutando: ${tool.name}`)
  
  if (tool.id === 'code_fix' || tool.id === 'deploy') {
    // These require approval
    pendingApproval.value = {
      type: tool.id === 'deploy' ? 'deploy' : 'file_write',
      description: tool.id === 'deploy' 
        ? 'Deploy a producción. Esto afectará el entorno live.'
        : 'Modificación de archivos del proyecto.',
      files: tool.id === 'code_fix' ? ['src/...', 'tests/...'] : undefined,
      diff: tool.id === 'code_fix' ? '// Cambios propuestos...\n- archivo.ts: +15 -3 líneas' : undefined,
      tool: tool.id,
      resolve: null as any
    }
    
    // Wait for approval
    await new Promise<void>(resolve => {
      pendingApproval.value.resolve = resolve
    })
  }
  
  // Execute tool via API
  try {
    const response = await axios.post('/api/merlin/tool', { tool: tool.id, args: {} })
    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: response.data.result,
      timestamp: new Date(),
      status: 'completed'
    })
  } catch (e) {
    console.error(e)
  }
}

function approveToolCall(call: any) {
  call.status = 'approved'
  // Execute the tool
  executeTool({ id: call.name })
}

function rejectToolCall(call: any) {
  call.status = 'rejected'
  messages.value.push({
    id: Date.now(),
    role: 'assistant',
    content: `Herramienta "${call.name}" rechazada por el usuario.`,
    timestamp: new Date(),
    status: 'completed'
  })
}

function confirmApproval() {
  if (pendingApproval.value?.resolve) pendingApproval.value.resolve()
  pendingApproval.value = null
}

function cancelApproval() {
  if (pendingApproval.value?.resolve) pendingApproval.value.resolve()
  pendingApproval.value = null
  messages.value.push({
    id: Date.now(),
    role: 'assistant',
    content: 'Acción cancelada.',
    timestamp: new Date(),
    status: 'completed'
  })
}

function removeContext(id: string) {
  activeContext.value = activeContext.value.filter(c => c.id !== id)
}

function addContext() {
  showContextModal.value = true
}

function addFileContext(file: any) {
  activeContext.value.push({ id: `file-${Date.now()}`, type: 'file', label: file.path, icon: '📄' })
  showContextModal.value = false
}

function addGitContext(diff: any) {
  activeContext.value.push({ id: `git-${Date.now()}`, type: 'git', label: 'Git Diff', icon: '📝' })
  showContextModal.value = false
}

function addManualContext(data: any) {
  activeContext.value.push({ id: `manual-${Date.now()}`, type: 'manual', label: 'Contexto Manual', icon: '✏️' })
  showContextModal.value = false
}

function searchCode() {
  activeContextTab.value = 'search'
}

function toggleSidebar() {
  showSidebar.value = !showSidebar.value
}

function toggleMode() {
  isBeginnerMode.value = !isBeginnerMode.value
  addAction('mode', isBeginnerMode.value ? 'Modo Principiante' : 'Modo Experto')
}

async function startVoiceRecording() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('Tu navegador no soporta reconocimiento de voz')
    return
  }

  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  voiceRecognition = new SpeechRecognition()
  voiceRecognition.lang = 'es-ES'
  voiceRecognition.continuous = true
  voiceRecognition.interimResults = true

  voiceRecognition.onresult = (event: any) => {
    let transcript = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript
    }
    userInput.value = transcript
  }

  voiceRecognition.onend = () => {
    if (isRecording.value) voiceRecognition.start()
  }

  voiceRecognition.onerror = (e: any) => {
    console.error('Voice error:', e)
    stopVoiceRecording()
  }

  isRecording.value = true
  recordingDuration.value = 0
  recordingInterval = setInterval(() => recordingDuration.value++, 1000)
  voiceRecognition.start()
}

function stopVoiceRecording() {
  if (voiceRecognition) {
    voiceRecognition.stop()
    voiceRecognition = null
  }
  if (recordingInterval) {
    clearInterval(recordingInterval)
    recordingInterval = null
  }
  isRecording.value = false
  recordingDuration.value = 0
  
  if (userInput.value.trim()) {
    sendMessage()
  }
}

function speak(text: string) {
  if ('speechSynthesis' in window) {
    voiceSynthesis = new SpeechSynthesisUtterance(text)
    voiceSynthesis.lang = 'es-ES'
    voiceSynthesis.rate = 0.95
    window.speechSynthesis.speak(voiceSynthesis)
  }
}

function toggleVoice() {
  voiceEnabled.value = !voiceEnabled.value
  if (voiceEnabled.value) startVoiceRecording()
  else stopVoiceRecording()
}

// Keyboard shortcuts
function handleKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.code === 'Space') {
    e.preventDefault()
    if (isRecording.value) stopVoiceRecording()
    else startVoiceRecording()
  }
  if (e.key === 'Escape') {
    showSidebar.value = false
    showContextModal.value = false
    if (pendingApproval.value) cancelApproval()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  if (isMobile.value) showSidebar.value = false
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  stopVoiceRecording()
  if (recordingInterval) clearInterval(recordingInterval)
})

watch(isProcessing, (val) => {
  if (!val) {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.isTyping) {
      speak(lastMsg.content.replace(/<[^>]*>/g, ''))
    }
  }
})
</script>

<style scoped>
/* ═══ OWNEX CHAT — Premium Minimal Theme ═══ */
.ownex-chat {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--ownex-bg-base);
  color: var(--ownex-bg-surface);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  position: relative;
  overflow: hidden;
}

/* Mobile: sidebar as overlay */
.ownex-chat.mobile .chat-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 320px;
  max-width: 85vw;
  z-index: 50;
  transform: translateX(100%);
  transition: transform 0.25s ease;
}
.ownex-chat.mobile .chat-sidebar.v-enter-active,
.ownex-chat.mobile .chat-sidebar.v-leave-active { transition: transform 0.25s ease; }
.ownex-chat.mobile .sidebar-open .chat-sidebar { transform: translateX(0); }

/* ── Header ── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: var(--ownex-bg-base);
  flex-shrink: 0;
  z-index: 10;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.sidebar-toggle { display: none; background: none; border: none; color: var(--ownex-text-secondary); cursor: pointer; padding: 6px; }
.ownex-chat.mobile .sidebar-toggle { display: flex; }

.merlin-avatar {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--ownex-bg-base) 0%, var(--ownex-bg-base) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
}
.merlin-avatar.processing .avatar-ring { animation: pulse-ring 1.5s ease-out infinite; }
.avatar-ring {
  position: absolute;
  inset: -2px;
  border-radius: 14px;
  border: 1px solid rgba(0, 227, 154, 0.3);
  animation: pulse-ring 3s ease-out infinite;
}
@keyframes pulse-ring { 0% { transform: scale(1); opacity: 0.4; } 100% { transform: scale(1.15); opacity: 0; } }
.avatar-core { font-size: 18px; z-index: 1; }

.header-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.chat-title { margin: 0; font-family: 'Space Grotesk', 'Inter', sans-serif; font-size: 16px; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-subtitle { margin: 0; font-size: 11px; color: var(--ownex-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.header-right { display: flex; align-items: center; gap: 8px; }
.icon-btn {
  display: flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: 10px;
  background: transparent; border: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--ownex-text-secondary); cursor: pointer; transition: all 0.15s ease;
}
.icon-btn:hover { background: rgba(255, 255, 255, 0.04); border-color: rgba(0, 213, 255, 0.3); color: var(--ownex-accent); }
.icon-btn.active { background: rgba(0, 227, 154, 0.1); border-color: rgba(0, 227, 154, 0.4); color: var(--ownex-green); }
.mode-badge { font-size: 14px; }

/* ── Sidebar ── */
.chat-sidebar {
  width: 280px;
  background: var(--ownex-bg-base);
  border-left: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
}
.sidebar-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
.sidebar-header h3 { margin: 0; font-size: 12px; letter-spacing: 0.12em; color: var(--ownex-text-secondary); }
.close-btn { display: none; background: none; border: none; color: var(--ownex-text-secondary); cursor: pointer; font-size: 18px; }
.ownex-chat.mobile .close-btn { display: block; }
.sidebar-content { padding: 12px 16px 24px; display: flex; flex-direction: column; gap: 20px; }
.sidebar-section h4 { margin: 0 0 10px; font-size: 10px; letter-spacing: 0.12em; color: var(--ownex-text-muted); text-transform: uppercase; }
.tools-grid { display: flex; flex-direction: column; gap: 8px; }
.tool-card { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; cursor: pointer; transition: all 0.12s ease; text-align: left; }
.tool-card:hover { border-color: rgba(0, 213, 255, 0.3); background: rgba(0, 213, 255, 0.03); }
.tool-card.danger { border-color: rgba(248, 113, 113, 0.3); }
.tool-card.danger:hover { background: rgba(248, 113, 113, 0.05); border-color: var(--ownex-danger); }
.tool-icon { font-size: 16px; }
.tool-name { font-size: 13px; font-weight: 500; color: var(--ownex-text-secondary); }
.tool-desc { font-size: 11px; color: var(--ownex-text-muted); margin-left: auto; }
.context-items { display: flex; flex-direction: column; gap: 6px; }
.context-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; }
.context-icon { font-size: 14px; }
.context-label { flex: 1; font-size: 12px; color: var(--ownex-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.remove-btn { background: none; border: none; color: var(--ownex-text-muted); cursor: pointer; font-size: 14px; padding: 2px 6px; }
.remove-btn:hover { color: var(--ownex-danger); }
.add-context-btn { margin-top: 8px; padding: 8px 12px; background: transparent; border: 1px dashed rgba(0, 213, 255, 0.3); border-radius: 8px; color: var(--ownex-accent); font-size: 12px; cursor: pointer; transition: all 0.12s; }
.add-context-btn:hover { background: rgba(0, 213, 255, 0.05); border-style: solid; }
.action-log { display: flex; flex-direction: column; gap: 6px; }
.action-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px; font-size: 11px; }
.action-type { font-weight: 600; color: var(--ownex-accent); text-transform: uppercase; letter-spacing: 0.05em; font-size: 10px; }
.action-desc { flex: 1; color: var(--ownex-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.action-time { color: var(--ownex-text-muted); white-space: nowrap; }

/* ── Chat Main ── */
.chat-main { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.messages-container { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; }
.welcome-message { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; text-align: center; padding: 40px; }
.welcome-avatar { width: 80px; height: 80px; border-radius: 20px; background: linear-gradient(135deg, var(--ownex-bg-base) 0%, var(--ownex-bg-base) 100%); border: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; justify-content: center; position: relative; }
.welcome-avatar .avatar-ring { inset: -4px; border-radius: 24px; border-color: rgba(0, 227, 154, 0.2); }
.welcome-avatar .avatar-core { font-size: 36px; }
.welcome-content { max-width: 480px; }
.greeting { margin: 0 0 8px; font-size: 22px; font-weight: 500; color: var(--ownex-bg-surface); }
.description { margin: 0 0 20px; font-size: 14px; color: var(--ownex-text-secondary); }
.suggested-prompts { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.prompt-btn { padding: 10px 16px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 999px; color: var(--ownex-text-secondary); font-size: 13px; cursor: pointer; transition: all 0.12s; white-space: nowrap; }
.prompt-btn:hover { border-color: rgba(0, 213, 255, 0.4); background: rgba(0, 213, 255, 0.05); color: var(--ownex-accent); }

.messages-list { flex: 1; display: flex; flex-direction: column; gap: 16px; max-width: 820px; margin: 0 auto; width: 100%; }
.message { display: flex; gap: 12px; animation: message-in 0.2s ease-out; }
@keyframes message-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.message-user { flex-direction: row-reverse; }
.message-avatar { width: 32px; height: 32px; border-radius: 9px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
.message-content { flex: 1; min-width: 0; }
.message-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.message-author { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ownex-text-secondary); }
.message-user .message-author { color: var(--ownex-accent); }
.message-time { font-size: 11px; color: var(--ownex-text-muted); }
.message-body { font-size: 14px; line-height: 1.6; color: var(--ownex-text-secondary); }
.message-text { white-space: pre-wrap; word-break: break-word; }
.message-text code { background: rgba(255, 255, 255, 0.08); padding: 2px 6px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.message-text pre { background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px; overflow-x: auto; margin: 8px 0; }
.message-text pre code { background: none; padding: 0; }

/* Tool Calls */
.tool-calls { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.tool-call { background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 12px; }
.tool-call.pending { border-color: rgba(251, 191, 36, 0.4); background: rgba(251, 191, 36, 0.03); }
.tool-call.approved { border-color: rgba(52, 211, 153, 0.4); background: rgba(52, 211, 153, 0.03); }
.tool-call.rejected { border-color: rgba(248, 113, 113, 0.4); background: rgba(248, 113, 113, 0.03); }
.tool-call-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.tool-status { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 2px 8px; border-radius: 999px; }
.tool-call.pending .tool-status { background: rgba(251, 191, 36, 0.2); color: var(--ownex-yellow); }
.tool-call.approved .tool-status { background: rgba(52, 211, 153, 0.2); color: var(--ownex-green); }
.tool-call.rejected .tool-status { background: rgba(248, 113, 113, 0.2); color: var(--ownex-danger); }
.tool-args { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--ownex-text-secondary); background: var(--ownex-bg-base); padding: 8px; border-radius: 6px; overflow-x: auto; margin: 0; }
.tool-actions { display: flex; gap: 8px; margin-top: 10px; }
.btn-approve, .btn-reject { padding: 6px 14px; border: none; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-approve { background: var(--ownex-green); color: var(--ownex-bg-base); }
.btn-reject { background: transparent; border: 1px solid rgba(248, 113, 113, 0.5); color: var(--ownex-danger); }

/* Typing */
.typing-indicator { display: flex; gap: 4px; padding: 8px 0; }
.typing-indicator span { width: 6px; height: 6px; border-radius: 50%; background: var(--ownex-text-secondary); animation: typing-bounce 1.2s ease-in-out infinite; }
.typing-indicator span:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.5; } 30% { transform: translateY(-4px); opacity: 1; } }
.typing-indicator-bottom { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 12px; color: var(--ownex-text-muted); font-size: 13px; }
.typing-dots { display: flex; gap: 4px; }
.typing-dots span { width: 6px; height: 6px; border-radius: 50%; background: var(--ownex-accent); animation: typing-bounce 1.2s ease-in-out infinite; }
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }

/* Voice Recording */
.voice-recording { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px; background: rgba(248, 113, 113, 0.1); border: 1px solid rgba(248, 113, 113, 0.3); border-radius: 10px; margin: 0 20px 12px; }
.waveform { display: flex; gap: 3px; }
.waveform span { width: 4px; height: 20px; background: var(--ownex-danger); border-radius: 2px; animation: wave 1s ease-in-out infinite; }
.waveform span:nth-child(2) { animation-delay: 0.1s; height: 30px; }
.waveform span:nth-child(3) { animation-delay: 0.2s; height: 25px; }
.waveform span:nth-child(4) { animation-delay: 0.3s; height: 35px; }
.waveform span:nth-child(5) { animation-delay: 0.4s; height: 15px; }
@keyframes wave { 0%, 100% { transform: scaleY(0.5); } 50% { transform: scaleY(1); } }
.recording-text { font-size: 13px; font-weight: 500; color: var(--ownex-danger); }
.stop-recording-btn { padding: 6px 16px; background: var(--ownex-danger); border: none; border-radius: 8px; color: var(--ownex-bg-base); font-weight: 600; cursor: pointer; }

/* Input Area */
.input-area { padding: 16px 20px; border-top: 1px solid rgba(255, 255, 255, 0.06); background: var(--ownex-bg-base); flex-shrink: 0; }
.input-container { max-width: 820px; margin: 0 auto; display: flex; gap: 10px; align-items: stretch; }
.chat-input { flex: 1; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: var(--ownex-bg-surface); font-family: 'Inter', sans-serif; font-size: 14px; line-height: 1.4; padding: 12px 14px; resize: none; outline: none; transition: border-color 0.15s; min-height: 48px; max-height: 180px; }
.chat-input:focus { border-color: rgba(0, 213, 255, 0.4); }
.chat-input::placeholder { color: var(--ownex-text-muted); }
.input-actions { display: flex; gap: 8px; align-items: stretch; }
.send-btn { width: 48px; border: none; border-radius: 10px; background: var(--ownex-accent); color: var(--ownex-bg-base); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: opacity 0.15s, transform 0.1s; }
.send-btn:hover:not(:disabled) { opacity: 0.85; transform: scale(1.02); }
.send-btn:disabled { background: var(--ownex-bg-elevated); color: var(--ownex-text-muted); cursor: not-allowed; }
.voice-btn { width: 48px; border-radius: 10px; background: transparent; border: 1px solid rgba(255, 255, 255, 0.08); color: var(--ownex-text-secondary); cursor: pointer; transition: all 0.15s; }
.voice-btn:hover { background: rgba(255, 255, 255, 0.04); border-color: rgba(0, 227, 154, 0.4); color: var(--ownex-green); }
.voice-btn.recording { background: rgba(248, 113, 113, 0.1); border-color: var(--ownex-danger); color: var(--ownex-danger); animation: pulse-btn 1.5s ease-in-out infinite; }
@keyframes pulse-btn { 0%, 100% { box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.4); } 50% { box-shadow: 0 0 0 8px rgba(248, 113, 113, 0); } }
.input-hint { max-width: 820px; margin: 8px auto 0; text-align: center; font-size: 11px; letter-spacing: 0.05em; color: var(--ownex-text-muted); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 20px; }
.modal-overlay.v-enter-active, .modal-overlay.v-leave-active { transition: opacity 0.2s ease; }
.modal-overlay.v-enter-from, .modal-overlay.v-leave-to { opacity: 0; }
.modal { background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; max-width: 560px; width: 100%; max-height: 90vh; overflow: hidden; }
.approval-modal { max-width: 520px; }
.context-modal { max-width: 720px; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 600; }
.modal-body { padding: 20px; max-height: 50vh; overflow-y: auto; }
.modal-body p { margin: 0 0 16px; color: var(--ownex-text-secondary); line-height: 1.6; }
.diff-preview { background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px; max-height: 300px; overflow: auto; }
.diff-preview pre { margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.5; color: var(--ownex-text-secondary); white-space: pre-wrap; word-break: break-word; }
.files-list { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
.file-item { padding: 8px 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--ownex-text-secondary); }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 20px; border-top: 1px solid rgba(255, 255, 255, 0.08); }
.btn-secondary, .btn-primary { padding: 10px 20px; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.12s; }
.btn-secondary { background: transparent; border: 1px solid rgba(255, 255, 255, 0.15); color: var(--ownex-text-secondary); }
.btn-secondary:hover { background: rgba(255, 255, 255, 0.04); border-color: rgba(255, 255, 255, 0.3); }
.btn-primary { background: var(--ownex-accent); border: none; color: var(--ownex-bg-base); }
.btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
.btn-primary.danger { background: var(--ownex-danger); color: var(--ownex-bg-base); }
.btn-primary.danger:hover { opacity: 0.9; }

/* Context Modal Tabs */
.context-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 8px; }
.tab-btn { padding: 8px 16px; background: none; border: none; color: var(--ownex-text-secondary); font-size: 13px; cursor: pointer; border-radius: 8px; transition: all 0.12s; }
.tab-btn:hover { color: var(--ownex-text-secondary); background: rgba(255, 255, 255, 0.03); }
.tab-btn.active { color: var(--ownex-accent); background: rgba(0, 213, 255, 0.1); }
.tab-content { min-height: 200px; }

.tree-search { width: 100%; padding: 10px 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; color: var(--ownex-bg-surface); font-size: 13px; margin-bottom: 12px; }
.tree-search::placeholder { color: var(--ownex-text-muted); }
.tree { max-height: 400px; overflow-y: auto; }
.tree-node { border-left: 1px solid rgba(255, 255, 255, 0.04); padding-left: 16px; margin-left: 8px; }
.node-header { display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 6px; cursor: pointer; transition: background 0.1s; }
.node-header:hover { background: rgba(255, 255, 255, 0.03); }
.expand-icon { font-size: 10px; color: var(--ownex-text-muted); width: 14px; text-align: center; }
.node-icon { font-size: 14px; }
.node-name { font-size: 13px; color: var(--ownex-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-children { margin-top: 2px; }

.code-search input { flex: 1; padding: 10px 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; color: var(--ownex-bg-surface); }
.code-search button { padding: 10px 20px; background: var(--ownex-accent); border: none; border-radius: 8px; color: var(--ownex-bg-base); font-weight: 600; cursor: pointer; }
.results { margin-top: 12px; max-height: 300px; overflow-y: auto; }
.result-item { padding: 10px 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; margin-bottom: 6px; cursor: pointer; font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--ownex-text-secondary); transition: border-color 0.12s; }
.result-item:hover { border-color: rgba(0, 213, 255, 0.4); }
.git-diff select { padding: 8px 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; color: var(--ownex-bg-surface); margin-bottom: 12px; }
.git-diff pre { background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px; max-height: 400px; overflow: auto; font-size: 12px; line-height: 1.5; }
.manual-context textarea { width: 100%; min-height: 200px; padding: 12px; background: var(--ownex-bg-base); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; color: var(--ownex-bg-surface); font-family: 'JetBrains Mono', monospace; font-size: 13px; margin-bottom: 12px; resize: vertical; }
.manual-context button { width: 100%; padding: 12px; background: var(--ownex-accent); border: none; border-radius: 8px; color: var(--ownex-bg-base); font-weight: 600; cursor: pointer; }

/* Responsive */
@media (max-width: 768px) {
  .chat-sidebar { width: 100%; max-width: none; }
  .input-actions { flex-wrap: wrap; }
}
</style>