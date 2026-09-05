<script setup lang="ts">
/**
 * OWNEX Sidebar — Collapsible navigation with work cycles
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed, ref } from 'vue'
import OwnexBadge from '../ui/OwnexBadge.vue'

interface Props {
  modelValue?: boolean
  activeCycle?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  activeCycle: 'security',
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'cycle-select': [cycle: string]
}>()

const isCollapsed = ref(props.modelValue)

const cycles = [
  { id: 'security', label: 'Security', icon: 'shield', color: 'var(--color-cycle-security)', jobs: 9 },
  { id: 'forge', label: 'Forge', icon: 'hammer', color: 'var(--color-cycle-forge)', jobs: 9 },
  { id: 'pulse', label: 'Pulse', icon: 'zap', color: 'var(--color-cycle-pulse)', jobs: 10 },
  { id: 'vault', label: 'Vault', icon: 'vault', color: 'var(--color-cycle-vault)', jobs: 2 },
  { id: 'atlas', label: 'Atlas', icon: 'globe', color: 'var(--color-cycle-atlas)', jobs: 2 },
  { id: 'odyssey', label: 'Odyssey', icon: 'rocket', color: 'var(--color-cycle-odyssey)', jobs: 1 },
]

const navItems = [
  { id: 'dashboard', label: 'Mission Control', icon: 'layout-dashboard' },
  { id: 'opportunities', label: 'Oportunidades', icon: 'search' },
  { id: 'findings', label: 'Hallazgos', icon: 'flag' },
  { id: 'reports', label: 'Reportes', icon: 'file-text' },
  { id: 'learning', label: 'Aprendizaje', icon: 'brain' },
  { id: 'settings', label: 'Configuración', icon: 'settings' },
]

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
  emit('update:modelValue', isCollapsed.value)
}

const selectCycle = (cycleId: string) => {
  emit('cycle-select', cycleId)
}
</script>

<template>
  <aside
    :class="['ownex-sidebar', { 'ownex-sidebar--collapsed': isCollapsed }]"
    :style="{ width: isCollapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)' }"
    role="navigation"
    aria-label="Navegación principal"
  >
    <!-- Logo / Brand -->
    <div class="ownex-sidebar__brand">
      <svg class="ownex-sidebar__logo" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <circle cx="16" cy="16" r="14" stroke="var(--ownex-accent)" stroke-width="1.5" opacity="0.3"/>
        <path d="M16 4l0 5M16 23l0 5M4 16l5 0M23 16l5 0M6.3 6.3l3.5 3.5M20.2 20.2l3.5 3.5M6.3 23.7l3.5-3.5M20.2 9.8l3.5-3.5" stroke="var(--ownex-accent)" stroke-width="1.5"/>
      </svg>
      <span v-if="!isCollapsed" class="ownex-sidebar__title">OWNEX</span>
    </div>

    <!-- Work Cycles -->
    <nav class="ownex-sidebar__section" aria-label="Ciclos de trabajo">
      <div v-if="!isCollapsed" class="ownex-sidebar__section-title">CICLOS</div>
      <ul class="ownex-sidebar__cycle-list" role="list">
        <li
          v-for="cycle in cycles"
          :key="cycle.id"
          class="ownex-sidebar__cycle-item"
        >
          <button
            :class="['ownex-sidebar__cycle-btn', { 'ownex-sidebar__cycle-btn--active': props.activeCycle === cycle.id }]"
            @click="selectCycle(cycle.id)"
            :aria-current="props.activeCycle === cycle.id ? 'page' : undefined"
            :title="isCollapsed ? cycle.label : undefined"
          >
            <span class="ownex-sidebar__cycle-icon" :style="{ color: cycle.color }" aria-hidden="true">
              <component :is="`icon-${cycle.icon}`" class="ownex-sidebar__icon-svg" />
            </span>
            <span v-if="!isCollapsed" class="ownex-sidebar__cycle-label">{{ cycle.label }}</span>
            <OwnexBadge
              v-if="!isCollapsed"
              variant="cycle"
              :cycle="cycle.id as any"
              size="sm"
              class="ownex-sidebar__cycle-count"
            >
              {{ cycle.jobs }}
            </OwnexBadge>
          </button>
        </li>
      </ul>
    </nav>

    <!-- Main Navigation -->
    <nav class="ownex-sidebar__section" aria-label="Navegación principal">
      <div v-if="!isCollapsed" class="ownex-sidebar__section-title">NAVEGACIÓN</div>
      <ul class="ownex-sidebar__nav-list" role="list">
        <li v-for="item in navItems" :key="item.id">
          <button
            class="ownex-sidebar__nav-btn"
            :title="isCollapsed ? item.label : undefined"
            @click="$emit('navigate', item.id)"
          >
            <span class="ownex-sidebar__nav-icon" aria-hidden="true">
              <component :is="`icon-${item.icon}`" class="ownex-sidebar__icon-svg" />
            </span>
            <span v-if="!isCollapsed" class="ownex-sidebar__nav-label">{{ item.label }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <!-- Collapse toggle -->
    <button
      class="ownex-sidebar__toggle"
      @click="toggleCollapse"
      :aria-expanded="!isCollapsed"
      :aria-label="isCollapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'"
      title="isCollapsed ? 'Expandir' : 'Colapsar'"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path v-if="isCollapsed" d="M9 18l6-6-6-6" />
        <path v-else d="M15 18l-6-6 6-6" />
      </svg>
    </button>
  </aside>
</template>

<style scoped>
.ownex-sidebar {
  position: fixed;
  top: var(--status-bar-height);
  left: 0;
  bottom: 0;
  z-index: var(--z-sidebar);
  background: var(--mica-bg);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base) cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
  font-family: var(--font-body);
}

.ownex-sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 64px;
}

.ownex-sidebar__logo {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.ownex-sidebar__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
}

.ownex-sidebar__section {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) var(--space-2);
}

.ownex-sidebar__section-title {
  display: none;
}
.ownex-sidebar:not(.ownex-sidebar--collapsed) .ownex-sidebar__section-title {
  display: block;
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ownex-text-disabled);
  padding: 0 var(--space-2) var(--space-2);
  margin-bottom: var(--space-2);
}

/* Cycles */
.ownex-sidebar__cycle-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.ownex-sidebar__cycle-btn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--ownex-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
}

.ownex-sidebar__cycle-btn:hover {
  background: var(--ownex-bg-surface);
  color: var(--ownex-white);
}

.ownex-sidebar__cycle-btn--active {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
  color: var(--ownex-blue);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.ownex-sidebar__cycle-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.ownex-sidebar__icon-svg {
  width: 18px;
  height: 18px;
}

.ownex-sidebar__cycle-label {
  font-size: 13px;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
}

.ownex-sidebar__cycle-count {
  margin-left: auto;
}

/* Main Nav */
.ownex-sidebar__nav-list {
  list-style: none;
  margin: var(--space-4) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.ownex-sidebar__nav-btn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--ownex-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-align: left;
}

.ownex-sidebar__nav-btn:hover {
  background: var(--ownex-bg-surface);
  color: var(--ownex-white);
}

.ownex-sidebar__nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  color: var(--ownex-text-muted);
}

.ownex-sidebar__nav-btn:hover .ownex-sidebar__nav-icon {
  color: var(--ownex-blue);
}

.ownex-sidebar__nav-label {
  font-size: 13px;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
}

/* Toggle */
.ownex-sidebar__toggle {
  position: absolute;
  bottom: var(--space-4);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border);
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  color: var(--ownex-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ownex-sidebar__toggle:hover {
  background: var(--ownex-bg-surface);
  border-color: var(--color-border-light);
  color: var(--ownex-white);
}

/* Collapsed state */
.ownex-sidebar--collapsed .ownex-sidebar__section-title,
.ownex-sidebar--collapsed .ownex-sidebar__cycle-label,
.ownex-sidebar--collapsed .ownex-sidebar__cycle-count,
.ownex-sidebar--collapsed .ownex-sidebar__nav-label,
.ownex-sidebar--collapsed .ownex-sidebar__title {
  display: none;
}

.ownex-sidebar--collapsed .ownex-sidebar__cycle-btn,
.ownex-sidebar--collapsed .ownex-sidebar__nav-btn {
  justify-content: center;
  padding: var(--space-2);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-sidebar {
    transition: none;
  }
  .ownex-sidebar__cycle-btn,
  .ownex-sidebar__nav-btn {
    transition: none;
  }
}
</style>