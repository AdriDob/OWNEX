<script setup lang="ts">
import { computed, ref } from 'vue'
import { useGuidedMode } from '@/composables/useGuidedMode'

const { currentMode, setMode, modeDescriptions } = useGuidedMode()

const modes = [
  { value: 'guided', label: 'Guiado', icon: '🧭', color: 'from-blue-500 to-cyan-500' },
  { value: 'assisted', label: 'Asistido', icon: '🤝', color: 'from-green-500 to-emerald-500' },
  { value: 'autonomous', label: 'Autónomo', icon: '🤖', color: 'from-purple-500 to-violet-500' },
  { value: 'expert', label: 'Experto', icon: '🔧', color: 'from-orange-500 to-red-500' },
] as const
</script>

<template>
  <div class="mode-selector">
    <div class="mode-selector__header">
      <h3 class="mode-selector__title">Modo de Operación</h3>
      <p class="mode-selector__subtitle">
        {{ modeDescriptions[currentMode.value]?.subtitle || '' }}
      </p>
    </div>

    <div class="mode-selector__grid" role="radiogroup" aria-label="Seleccionar modo de operación">
      <button
        v-for="mode in modes"
        :key="mode.value"
        :class="[
          'mode-selector__card',
          currentMode.value === mode.value ? 'mode-selector__card--active' : '',
        ]"
        @click="setMode(mode.value)"
        :aria-pressed="currentMode.value === mode.value"
        :style="{
          '--mode-color': mode.color,
        }"
      >
        <div class="mode-selector__icon" :style="{ background: `linear-gradient(135deg, ${mode.color})` }">
          {{ mode.icon }}
        </div>
        <div class="mode-selector__content">
          <h4 class="mode-selector__name">{{ mode.label }}</h4>
          <p class="mode-selector__desc">{{ modeDescriptions[mode.value]?.desc || '' }}</p>
        </div>
        <div
          v-if="currentMode.value === mode.value"
          class="mode-selector__check"
          aria-hidden="true"
        >
          ✓
        </div>
      </button>
    </div>

    <div class="mode-selector__details" v-if="modeDescriptions[currentMode.value]">
      <h4 class="mode-selector__detail-title">{{ modeDescriptions[currentMode.value].title }}</h4>
      <ul class="mode-selector__features">
        <li v-for="feature in modeDescriptions[currentMode.value].features" :key="feature">
          {{ feature }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.mode-selector {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
}

.mode-selector__header {
  margin-bottom: 20px;
}

.mode-selector__title {
  font-size: 1rem;
  font-weight: 600;
  color: #f0f0f0;
  margin: 0 0 4px;
}

.mode-selector__subtitle {
  font-size: 0.875rem;
  color: #888;
  margin: 0;
}

.mode-selector__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.mode-selector__card {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-height: 140px;
}

.mode-selector__card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.05);
  transform: translateY(-2px);
}

.mode-selector__card--active {
  border-color: var(--mode-color);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, color-mix(in srgb, var(--mode-color) 10%, transparent) 100%);
  box-shadow: 0 0 0 1px var(--mode-color), 0 4px 20px color-mix(in srgb, var(--mode-color) 20%, transparent);
}

.mode-selector__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 12px;
  color: white;
  box-shadow: 0 4px 16px color-mix(in srgb, var(--mode-color) 40%, transparent);
}

.mode-selector__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.mode-selector__name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #f0f0f0;
  margin: 0 0 4px;
}

.mode-selector__desc {
  font-size: 0.75rem;
  color: #888;
  margin: 0;
  line-height: 1.4;
}

.mode-selector__check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--mode-color);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--mode-color) 40%, transparent);
}

.mode-selector__details {
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.mode-selector__detail-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--mode-color);
  margin: 0 0 12px;
}

.mode-selector__features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.mode-selector__features li {
  font-size: 0.75rem;
  color: #aaa;
  padding-left: 16px;
  position: relative;
}

.mode-selector__features li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: var(--mode-color);
  font-size: 0.625rem;
}

@media (max-width: 768px) {
  .mode-selector__grid {
    grid-template-columns: repeat(2, 1fr);
  }

   .mode-selector__features {
    grid-template-columns: 1fr;
  }
}
</style>