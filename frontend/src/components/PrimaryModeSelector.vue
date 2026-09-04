<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

interface ModeInfo {
  name: string
  description: string
  icon: string
  color: string
  features: string[]
}

const modes: Record<string, ModeInfo> = {
  lite: {
    name: 'LITE',
    description: 'Earn More — Minimalista, next best action, maximizar EV/hora',
    icon: '⚡',
    color: '#10b981',
    features: [
      'Next Best Action destacado',
      'Oportunidades rankeadas por EV',
      'Dashboard simplificado',
      'Foco en ingresos rápidos',
    ],
  },
  full: {
    name: 'FULL',
    description: 'Operate Everything — Completo, toda la complejidad visible',
    icon: '🚀',
    color: '#3b82f6',
    features: [
      'Todas las secciones visibles',
      'Pipelines y automatización',
      'Analytics avanzados',
      'Control total del sistema',
    ],
  },
  capital: {
    name: 'CAPITAL',
    description: 'Keep & Compound — Patrimonio, asignación, proyección $1M',
    icon: '💰',
    color: '#f59e0b',
    features: [
      'Patrimonial Ladder',
      'Asignación de capital',
      'Proyecciones a largo plazo',
      'Tracking de inversiones',
    ],
  },
}

const currentMode = ref<string>('lite')
const loading = ref(false)

const currentModeInfo = computed(() => modes[currentMode.value] || modes.lite)

async function fetchMode() {
  try {
    const res = await fetch('/api/settings/runtime/mode/primary')
    const data = await res.json()
    currentMode.value = data.mode || 'lite'
  } catch (e) {
    console.error('Failed to fetch mode:', e)
  }
}

async function setMode(mode: string) {
  if (mode === currentMode.value || loading.value) return

  loading.value = true
  try {
    const res = await fetch('/api/settings/runtime/mode/primary', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    })
    const data = await res.json()
    if (data.status === 'ok' || data.status === 'success') {
      currentMode.value = mode
      // Emit event for other components
      window.dispatchEvent(
        new CustomEvent('ownex:mode-change', { detail: { mode } })
      )
    }
  } catch (e) {
    console.error('Failed to set mode:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMode()
})
</script>

<template>
  <div class="primary-mode-selector">
    <div class="selector-header">
      <span class="selector-label">Modo Operativo</span>
    </div>

    <div class="mode-tabs">
      <button
        v-for="(info, key) in modes"
        :key="key"
        :class="['mode-tab', { active: currentMode === key }]"
        :style="{
          '--mode-color': info.color,
          '--mode-color-alpha': info.color + '20',
        }"
        @click="setMode(key)"
        :disabled="loading"
      >
        <span class="mode-icon">{{ info.icon }}</span>
        <span class="mode-name">{{ info.name }}</span>
      </button>
    </div>

    <div class="mode-tooltip" v-if="currentModeInfo">
      <div class="tooltip-content">
        <div class="tooltip-header">
          <span class="tooltip-icon" :style="{ color: currentModeInfo.color }">
            {{ currentModeInfo.icon }}
          </span>
          <span class="tooltip-name">{{ currentModeInfo.name }}</span>
        </div>
        <p class="tooltip-desc">{{ currentModeInfo.description }}</p>
        <ul class="tooltip-features">
          <li v-for="feature in currentModeInfo.features" :key="feature">
            {{ feature }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.primary-mode-selector {
  position: relative;
}

.selector-header {
  margin-bottom: 8px;
}

.selector-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #8b8d98;
}

.mode-tabs {
  display: flex;
  gap: 4px;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 4px;
}

.mode-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #8b8d98;
  font-size: 12px;
  font-weight: 500;
}

.mode-tab:hover:not(.active):not(:disabled) {
  background: rgba(255, 255, 255, 0.04);
  color: #d1d5db;
}

.mode-tab.active {
  background: var(--mode-color-alpha);
  color: var(--mode-color);
  box-shadow: 0 0 12px var(--mode-color-alpha);
}

.mode-tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-icon {
  font-size: 14px;
}

.mode-name {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  letter-spacing: 0.05em;
}

/* Tooltip on hover */
.primary-mode-selector:hover .mode-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.mode-tooltip {
  position: absolute;
  left: 100%;
  top: 0;
  margin-left: 12px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transition: all 0.2s ease;
  z-index: 1000;
  pointer-events: none;
}

.tooltip-content {
  background: #1a1d24;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  min-width: 240px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tooltip-icon {
  font-size: 20px;
}

.tooltip-name {
  font-size: 14px;
  font-weight: 700;
  color: #f5f5f4;
  font-family: 'JetBrains Mono', monospace;
}

.tooltip-desc {
  font-size: 12px;
  color: #8b8d98;
  margin: 0 0 12px;
  line-height: 1.5;
}

.tooltip-features {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tooltip-features li {
  font-size: 11px;
  color: #d1d5db;
  padding: 4px 0;
  padding-left: 16px;
  position: relative;
}

.tooltip-features li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: #8b8d98;
  font-size: 10px;
}
</style>
