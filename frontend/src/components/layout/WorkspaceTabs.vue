<script setup lang="ts">
/**
 * OWNEX Workspace Tabs — Tabbed workspace area
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed, ref } from 'vue'

interface Tab {
  id: string
  label: string
  icon?: string
  closable?: boolean
  badge?: string | number
  badgeVariant?: 'default' | 'success' | 'warning' | 'error' | 'gold'
}

interface Props {
  modelValue?: string
  tabs?: Tab[]
  addable?: boolean
  maxTabs?: number
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  tabs: () => [],
  addable: false,
  maxTabs: 10,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'tab-close': [id: string]
  'tab-add': []
}>()

const newTabCounter = ref(1)

const activeTab = computed(() => props.tabs.find(t => t.id === props.modelValue))

const handleTabClick = (tab: Tab) => {
  emit('update:modelValue', tab.id)
}

const handleClose = (event: MouseEvent, tab: Tab) => {
  event.stopPropagation()
  if (tab.closable) {
    emit('tab-close', tab.id)
  }
}

const handleAdd = () => {
  emit('tab-add')
}
</script>

<template>
  <div class="ownex-workspace-tabs" role="tablist" aria-label="Espacios de trabajo">
    <div class="ownex-workspace-tabs__scroll" ref="scrollRef">
      <div class="ownex-workspace-tabs__list">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="['ownex-workspace-tabs__tab', { 'ownex-workspace-tabs__tab--active': modelValue === tab.id }]"
          :role="'tab'"
          :aria-selected="modelValue === tab.id"
          :aria-controls="`panel-${tab.id}`"
          :id="`tab-${tab.id}`"
          @click="handleTabClick(tab)"
        >
          <span v-if="tab.icon" class="ownex-workspace-tabs__tab-icon" aria-hidden="true">
            <component :is="`icon-${tab.icon}`" class="ownex-workspace-tabs__icon-svg" />
          </span>
          <span class="ownex-workspace-tabs__tab-label">{{ tab.label }}</span>
          <span
            v-if="tab.badge !== undefined"
            class="ownex-workspace-tabs__tab-badge"
            :class="`ownex-workspace-tabs__tab-badge--${tab.badgeVariant || 'default'}`"
          >
            {{ tab.badge }}
          </span>
          <button
            v-if="tab.closable"
            type="button"
            class="ownex-workspace-tabs__tab-close"
            @click="($event) => handleClose($event, tab)"
            :aria-label="`Cerrar ${tab.label}`"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </button>

        <!-- Add tab button -->
        <button
          v-if="addable && tabs.length < maxTabs"
          type="button"
          class="ownex-workspace-tabs__add-tab"
          @click="handleAdd"
          aria-label="Nueva pestaña"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Scroll indicators -->
    <button
      v-if="canScrollLeft"
      class="ownex-workspace-tabs__scroll-btn ownex-workspace-tabs__scroll-btn--left"
      @click="scrollLeft"
      aria-label="Desplazar izquierda"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M15 18l-6-6 6-6" />
      </svg>
    </button>
    <button
      v-if="canScrollRight"
      class="ownex-workspace-tabs__scroll-btn ownex-workspace-tabs__scroll-btn--right"
      @click="scrollRight"
      aria-label="Desplazar derecha"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 18l6-6-6-6" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUpdated } from 'vue'

const scrollRef = ref<HTMLDivElement>()

const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollButtons = () => {
  if (!scrollRef.value) return
  const { scrollLeft, scrollWidth, clientWidth } = scrollRef.value
  canScrollLeft.value = scrollLeft > 4
  canScrollRight.value = scrollLeft + clientWidth < scrollWidth - 4
}

onMounted(() => {
  updateScrollButtons()
  window.addEventListener('resize', updateScrollButtons)
})

onUpdated(() => {
  nextTick(updateScrollButtons)
})

const scrollLeft = () => {
  if (scrollRef.value) {
    scrollRef.value.scrollBy({ left: -200, behavior: 'smooth' })
  }
}

const scrollRight = () => {
  if (scrollRef.value) {
    scrollRef.value.scrollBy({ left: 200, behavior: 'smooth' })
  }
}
</script>

<style scoped>
.ownex-workspace-tabs {
  position: relative;
  height: 44px;
  background: rgba(8, 8, 8, 0.9);
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  display: flex;
  align-items: center;
  font-family: var(--font-body);
}

.ownex-workspace-tabs__scroll {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ownex-workspace-tabs__scroll::-webkit-scrollbar {
  display: none;
}

.ownex-workspace-tabs__list {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 var(--space-3);
  height: 100%;
  min-width: max-content;
}

.ownex-workspace-tabs__tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  height: 32px;
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--ownex-text-secondary);
  font-size: 12px;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ownex-workspace-tabs__tab:hover {
  background: var(--ownex-bg-surface);
  color: var(--ownex-white);
}

.ownex-workspace-tabs__tab--active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(59, 130, 246, 0.06));
  color: var(--ownex-blue);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.ownex-workspace-tabs__tab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: inherit;
  opacity: 0.8;
}

.ownex-workspace-tabs__icon-svg {
  width: 14px;
  height: 14px;
}

.ownex-workspace-tabs__tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 5px;
  font-size: 9px;
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-full);
  background: rgba(148, 163, 184, 0.15);
  color: var(--ownex-text-muted);
}

.ownex-workspace-tabs__tab-badge--success {
  background: rgba(16, 185, 129, 0.15);
  color: var(--ownex-green);
}

.ownex-workspace-tabs__tab-badge--warning {
  background: rgba(251, 191, 36, 0.15);
  color: var(--ownex-yellow);
}

.ownex-workspace-tabs__tab-badge--error {
  background: rgba(239, 68, 68, 0.15);
  color: var(--ownex-red);
}

.ownex-workspace-tabs__tab-badge--gold {
  background: rgba(245, 158, 11, 0.15);
  color: var(--ownex-gold);
}

.ownex-workspace-tabs__tab-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: 2px;
  border: none;
  background: transparent;
  color: inherit;
  opacity: 0.5;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ownex-workspace-tabs__tab-close:hover {
  opacity: 1;
  background: rgba(239, 68, 68, 0.15);
  color: var(--ownex-red);
}

/* Add tab */
.ownex-workspace-tabs__add-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px dashed rgba(59, 130, 246, 0.3);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--ownex-blue);
  opacity: 0.6;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ownex-workspace-tabs__add-tab:hover {
  opacity: 1;
  background: rgba(59, 130, 246, 0.08);
  border-style: solid;
}

/* Scroll buttons */
.ownex-workspace-tabs__scroll-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  color: var(--ownex-text-secondary);
  box-shadow: var(--shadow-md);
  cursor: pointer;
  z-index: 10;
  transition: all var(--transition-fast);
}

.ownex-workspace-tabs__scroll-btn:hover {
  background: var(--ownex-bg-surface);
  color: var(--ownex-white);
}

.ownex-workspace-tabs__scroll-btn--left {
  left: var(--space-2);
}

.ownex-workspace-tabs__scroll-btn--right {
  right: var(--space-2);
}

/* Scroll gradient masks */
.ownex-workspace-tabs__scroll::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 40px;
  height: 100%;
  background: linear-gradient(90deg, rgba(8,8,8,0.9), transparent);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.ownex-workspace-tabs__scroll::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 40px;
  height: 100%;
  background: linear-gradient(270deg, rgba(8,8,8,0.9), transparent);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.ownex-workspace-tabs__scroll:has(.ownex-workspace-tabs__scroll-btn--left:not([style*="display: none"]))::before {
  opacity: 1;
}

.ownex-workspace-tabs__scroll:has(.ownex-workspace-tabs__scroll-btn--right:not([style*="display: none"]))::after {
  opacity: 1;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-workspace-tabs__tab,
  .ownex-workspace-tabs__tab-close,
  .ownex-workspace-tabs__add-tab,
  .ownex-workspace-tabs__scroll-btn {
    transition: none;
  }
  .ownex-workspace-tabs__scroll {
    scroll-behavior: auto !important;
  }
}
</style>