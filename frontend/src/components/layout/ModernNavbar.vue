<template>
  <nav class="modern-navbar">
    <div class="navbar-left">
      <div class="navbar-brand">
        <div class="brand-mark">
          <div class="o-ring o-ring-mini" />
          <div class="o-dot o-dot-mini" />
        </div>
        <span class="brand-text">OWNEX Alpha</span>
      </div>
    </div>

    <div class="navbar-center">
      <div class="search-bar">
        <div class="search-icon">🔍</div>
        <input
          v-model="searchQuery"
          @keyup.enter="handleSearch"
          type="text"
          placeholder="Buscar targets, hallazgos, reportes..."
          class="search-input"
        />
      </div>
    </div>

    <div class="navbar-right">
      <div class="navbar-actions">
        <button @click="navigateTo('/merlin')" class="nav-btn nav-merlin" title="Hablar con MERLIN">
          <div class="merlin-mini-avatar">
            <div class="avatar-border"></div>
            <div class="avatar-emoji">🧙</div>
          </div>
          <span class="nav-label">MERLIN</span>
        </button>

        <button @click="navigateTo('/targets/discovery')" class="nav-btn" title="Discovery">
          <div class="nav-icon">🎯</div>
          <span class="nav-label">Discovery</span>
        </button>

        <button @click="navigateTo('/intelligence/findings')" class="nav-btn" title="Hallazgos">
          <div class="nav-icon">🔍</div>
          <span class="nav-label">Hallazgos</span>
        </button>

        <button @click="navigateTo('/reports/queue')" class="nav-btn" title="Reportes">
          <div class="nav-icon">📊</div>
          <span class="nav-label">Reportes</span>
        </button>

        <button @click="navigateTo('/capital')" class="nav-btn" title="Capital">
          <div class="nav-icon">💰</div>
          <span class="nav-label">Capital</span>
        </button>

        <button @click="toggleSettings" class="nav-btn nav-settings" title="Configuración">
          <div class="nav-icon">⚙️</div>
        </button>
      </div>
    </div>

    <!-- ═══ MERLIN QUICK CHAT ═══ -->
    <div v-if="showMerlinChat" class="merlin-quick-chat">
      <div class="merlin-chat-header">
        <div class="merlin-chat-title">
          <div class="merlin-avatar-small">
            <div class="avatar-border-small"></div>
            <div class="avatar-emoji-small">🧙</div>
          </div>
          <span>MERLIN Quick Chat</span>
        </div>
        <button @click="closeMerlinChat" class="chat-close">✕</button>
      </div>
      <div class="merlin-chat-messages">
        <div class="chat-message chat-merlin">
          <div class="message-content">
            {{ merlinQuickGreeting }}
          </div>
        </div>
      </div>
      <div class="merlin-chat-input">
        <input
          v-model="quickChatInput"
          @keyup.enter="sendQuickMessage"
          type="text"
          placeholder="Escribe un mensaje rápido..."
          class="quick-input"
        />
        <button @click="sendQuickMessage" class="quick-send">📤</button>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchQuery = ref('')
const showMerlinChat = ref(false)
const quickChatInput = ref('')
const merlinQuickGreeting = ref('¡Hola! Soy MERLIN. ¿En qué puedo ayudarte rápidamente?')

function navigateTo(path: string) {
  router.push(path)
}

function handleSearch() {
  if (searchQuery.value.trim()) {
    // Implement search logic
  }
}

function toggleSettings() {
  router.push('/operations/settings')
}

function closeMerlinChat() {
  showMerlinChat.value = false
}

function sendQuickMessage() {
  if (quickChatInput.value.trim()) {
    // Send quick message to MERLIN
    quickChatInput.value = ''
  }
}
</script>

<style scoped>
/* ═══ MODERN NAVBAR ═══ */
.modern-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-left {
  display: flex;
  align-items: center;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.navbar-brand:hover {
  transform: scale(1.02);
}

.brand-mark {
  position: relative;
  width: 32px;
  height: 32px;
}

.o-ring-mini {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  animation: pulse-ring-mini 3s ease-in-out infinite;
}

@keyframes pulse-ring-mini {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.05); }
}

.o-dot-mini {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ownex-accent);
  animation: pulse-dot-mini 2s ease-in-out infinite;
}

@keyframes pulse-dot-mini {
  0%, 100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 0.7; transform: translate(-50%, -50%) scale(1.2); }
}

.brand-text {
  font-size: 1.125rem;
  font-weight: 700;
  color: white;
  letter-spacing: 0.05em;
}

.navbar-center {
  flex: 1;
  max-width: 500px;
  margin: 0 2rem;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9999px;
  transition: all 0.2s;
}

.search-bar:focus-within {
  border-color: rgba(255, 255, 255, 0.3);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
}

.search-icon {
  font-size: 1rem;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: white;
  font-size: 0.875rem;
  outline: none;
}

.search-input::placeholder {
  color: var(--ownex-text-muted);
}

.navbar-right {
  display: flex;
  align-items: center;
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  color: var(--ownex-text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-btn:hover {
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.nav-merlin {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(99, 102, 241, 0.1);
}

.nav-merlin:hover {
  border-color: rgba(99, 102, 241, 0.5);
  background: rgba(99, 102, 241, 0.2);
}

.merlin-mini-avatar {
  position: relative;
  width: 24px;
  height: 24px;
}

.avatar-border {
  position: absolute;
  inset: 0;
  border: 1px solid var(--ownex-text-muted);
  border-radius: 50%;
  animation: retro-border-mini 3s linear infinite;
}

@keyframes retro-border-mini {
  0% { border-color: var(--ownex-text-muted); }
  25% { border-color: var(--ownex-accent); }
  50% { border-color: var(--ownex-text-muted); }
  75% { border-color: var(--ownex-accent); }
  100% { border-color: var(--ownex-text-muted); }
}

.avatar-emoji {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--ownex-text-secondary) 0%, var(--ownex-accent) 100%);
  border-radius: 50%;
  font-size: 0.75rem;
  z-index: 1;
}

.nav-icon {
  font-size: 1rem;
}

.nav-label {
  font-size: 0.875rem;
  font-weight: 600;
}

.nav-settings {
  padding: 0.5rem;
}

/* ═══ MERLIN QUICK CHAT ═══ */
.merlin-quick-chat {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 0.5rem;
  width: 350px;
  background: rgba(30, 41, 59, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  animation: slide-down 0.3s ease;
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.merlin-chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.merlin-chat-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
}

.merlin-avatar-small {
  position: relative;
  width: 24px;
  height: 24px;
}

.avatar-border-small {
  position: absolute;
  inset: 0;
  border: 1px solid var(--ownex-text-muted);
  border-radius: 50%;
  animation: retro-border-mini 3s linear infinite;
}

.avatar-emoji-small {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--ownex-text-secondary) 0%, var(--ownex-accent) 100%);
  border-radius: 50%;
  font-size: 0.625rem;
  z-index: 1;
}

.chat-close {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--ownex-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.chat-close:hover {
  color: white;
}

.merlin-chat-messages {
  padding: 1rem;
  max-height: 200px;
  overflow-y: auto;
}

.chat-message {
  margin-bottom: 0.75rem;
}

.chat-merlin .message-content {
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 0.5rem;
  padding: 0.75rem;
  color: var(--ownex-text-secondary);
  font-size: 0.875rem;
}

.merlin-chat-input {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.quick-input {
  flex: 1;
  padding: 0.5rem;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.25rem;
  color: white;
  font-size: 0.875rem;
  outline: none;
}

.quick-input:focus {
  border-color: rgba(255, 255, 255, 0.3);
}

.quick-send {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-send:hover {
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.3);
}
</style>