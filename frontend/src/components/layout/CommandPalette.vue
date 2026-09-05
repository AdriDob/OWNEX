<script setup lang="ts">
/**
 * Command Palette — Per OWNEX_DESIGN_SYSTEM.md §5.2
 * Navegación principal: Ctrl+K
 * Scopes: > Acciones, / Navegación, @ Agentes, # Tags, $ Dinero
 */

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'

interface CommandItem {
  id: string
  title: string
  description?: string
  category: 'actions' | 'opportunities' | 'targets' | 'reports' | 'agents' | 'navigation' | 'settings'
  icon?: string
  shortcut?: string
  action: () => void | Promise<void>
  keywords?: string[]
  scope?: 'action' | 'nav' | 'agent' | 'tag' | 'money'
  metadata?: Record<string, any>
}

interface Props {
  modelValue: boolean
  items?: CommandItem[]
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  items: () => [],
  placeholder: 'Buscar acciones, oportunidades, targets, reportes...',
})

const emit = defineEmits<{ 'update:modelValue': [value: boolean]; close: []; execute: [item: CommandItem] }>()

const searchQuery = ref('')
const selectedIndex = ref(0)
const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const panelRef = ref<HTMLDivElement>()
const inputRef = ref<HTMLInputElement>()

// Helper to calculate global index
function getGlobalIndex(category: string, index: number): number {
  return index // Simplified for now
}

const scopes = {
  '>': 'actions',
  '/': 'navigation',
  '@': 'agents',
  '#': 'tags',
  $: 'money',
} as const

const scopeLabels = {
  actions: 'ACCIONES',
  opportunities: 'OPORTUNIDADES',
  targets: 'TARGETS',
  reports: 'REPORTES',
  agents: 'AGENTES',
  navigation: 'NAVEGACIÓN',
  settings: 'CONFIGURACIÓN',
} as const

const scopeIcons = {
  actions: '⚡',
  opportunities: '🔥',
  targets: '🎯',
  reports: '📄',
  agents: '🤖',
  navigation: '🧭',
  settings: '⚙️',
} as const

const filteredItems = computed(() => {
  if (!searchQuery.value.trim()) {
    return props.items
  }

  const query = searchQuery.value.toLowerCase()
  const firstChar = query[0]

  // Check for scope prefix
  let scopeFilter: keyof typeof scopes | null = null
  let searchTerms = query

  if (firstChar in scopes) {
    scopeFilter = firstChar as keyof typeof scopes
    searchTerms = query.slice(1).trim()
  }

  return props.items
    .filter((item) => {
      // Scope filter
      if (scopeFilter && item.category !== scopes[scopeFilter]) return false

      // Text search
      const searchable = [
        item.title,
        item.description || '',
        ...(item.keywords || []),
        scopeLabels[item.category].toLowerCase(),
      ]
        .join(' ')
        .toLowerCase()

      return searchable.includes(searchTerms)
    })
    .sort((a, b) => {
      // Prioritize exact matches
      const aTitle = a.title.toLowerCase()
      const bTitle = b.title.toLowerCase()
      const aExact = aTitle.startsWith(searchTerms) ? 0 : 1
      const bExact = bTitle.startsWith(searchTerms) ? 0 : 1
      if (aExact !== bExact) return aExact - bExact

      // Then by category order
      const catOrder = { actions: 0, opportunities: 1, targets: 2, reports: 3, agents: 4, navigation: 5, settings: 6 }
      return catOrder[a.category] - catOrder[b.category]
    })
})

const groupedItems = computed(() => {
  const groups: Record<string, CommandItem[]> = {}
  for (const item of filteredItems.value) {
    if (!groups[item.category]) groups[item.category] = []
    groups[item.category].push(item)
  }
  return groups
})

const categoryOrder = ['actions', 'opportunities', 'targets', 'reports', 'agents', 'navigation', 'settings']

const handleKeydown = (event: KeyboardEvent) => {
  const items = filteredItems.value
  if (!items.length) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, items.length - 1)
      break
    case 'ArrowUp':
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      break
    case 'Enter':
      event.preventDefault()
      if (items[selectedIndex.value]) {
        executeItem(items[selectedIndex.value])
      }
      break
    case 'Escape':
      close()
      break
    case 'Tab':
      event.preventDefault()
      selectedIndex.value = (selectedIndex.value + 1) % items.length
      break
  }
}

const executeItem = async (item: CommandItem) => {
  await item.action()
  emit('execute', item)
  close()
}

const close = () => {
  isOpen.value = false
  searchQuery.value = ''
  selectedIndex.value = 0
  emit('close')
}

const handleClickOutside = (event: MouseEvent) => {
  if (panelRef.value && !panelRef.value.contains(event.target as Node)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleGlobalKeydown)
  nextTick(() => inputRef.value?.focus())
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleGlobalKeydown)
})

const handleGlobalKeydown = (event: KeyboardEvent) => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
    event.preventDefault()
    isOpen.value = !isOpen.value
    if (!isOpen.value) {
      searchQuery.value = ''
      selectedIndex.value = 0
    }
    nextTick(() => inputRef.value?.focus())
  }
}

watch(isOpen, (open) => {
  if (open) {
    document.body.style.overflow = 'hidden'
    searchQuery.value = ''
    selectedIndex.value = 0
    nextTick(() => inputRef.value?.focus())
  } else {
    document.body.style.overflow = ''
  }
})
</script>

<template>
  <Transition name="ownex-command-palette">
    <div v-if="isOpen" class="ownex-command-palette-overlay" @click.self="close" aria-hidden="true">
      <div ref="panelRef" class="ownex-command-palette" role="dialog" aria-modal="true" aria-label="Paleta de comandos">
        <!-- Input -->
        <div class="ownex-command-palette__input-wrapper">
          <svg class="ownex-command-palette__search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref="inputRef"
            type="text"
            class="ownex-command-palette__input"
            :placeholder="placeholder"
            v-model="searchQuery"
            @keydown="handleKeydown"
            autocomplete="off"
            spellcheck="false"
            aria-label="Buscar comandos"
            aria-autocomplete="list"
            aria-controls="command-palette-list"
          />
          <kbd class="ownex-command-palette__shortcut" aria-hidden="true">
            <span>⌘</span>K
          </kbd>
        </div>

        <!-- Results -->
        <div class="ownex-command-palette__results" id="command-palette-list" role="listbox" aria-label="Resultados">
          <div v-if="filteredItems.length === 0" class="ownex-command-palette__empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
              <path d="M14 11a3 3 0 1 1-6 0 3 3 0 0 1 6 0z" />
            </svg>
            <p>No se encontraron resultados</p>
            <span v-if="searchQuery">Intenta con otro término</span>
          </div>

          <div v-else class="ownex-command-palette__list">
            <div
              v-for="category in categoryOrder"
              :key="category"
              v-if="groupedItems[category] && groupedItems[category].length"
              class="ownex-command-palette__category"
            >
              <div class="ownex-command-palette__category-header">
                <span class="ownex-command-palette__category-icon" aria-hidden="true">
                  {{ scopeIcons[category as keyof typeof scopeIcons] }}
                </span>
                <span class="ownex-command-palette__category-label">
                  {{ scopeLabels[category as keyof typeof scopeLabels] }}
                </span>
                <span class="ownex-command-palette__category-count">
                  {{ groupedItems[category].length }}
                </span>
              </div>

              <div class="ownex-command-palette__items" role="group" :aria-label="scopeLabels[category as keyof typeof scopeLabels]">
                <div
                  v-for="(item, index) in groupedItems[category]"
                  :key="item.id"
                  class="ownex-command-palette__item"
                  :class="{ 'ownex-command-palette__item--selected': getGlobalIndex(category, index) === selectedIndex }"
                  role="option"
                  :aria-selected="getGlobalIndex(category, index) === selectedIndex"
                  @click="executeItem(item)"
                  @mousemove="selectedIndex = getGlobalIndex(category, index)"
                >
                  <span v-if="item.icon" class="ownex-command-palette__item-icon" aria-hidden="true">
                    {{ item.icon }}
                  </span>
                  <div class="ownex-command-palette__item-content">
                    <span class="ownex-command-palette__item-title">{{ item.title }}</span>
                    <span v-if="item.description" class="ownex-command-palette__item-description">{{ item.description }}</span>
                  </div>
                  <span v-if="item.shortcut" class="ownex-command-palette__item-shortcut">{{ item.shortcut }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Hints -->
        <div class="ownex-command-palette__hints">
          <kbd>↑↓</kbd> Navegar
          <kbd>Enter</kbd> Ejecutar
          <kbd>Esc</kbd> Cerrar
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.ownex-command-palette-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: var(--z-command-palette);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12vh;
  animation: ownex-fade-in var(--transition-fast) var(--spring-smooth);
}

.ownex-command-palette {
  width: 100%;
  max-width: 720px;
  margin: 0 var(--space-4);
  background: var(--ownex-bg-elevated);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-3), var(--shadow-glow);
  overflow: hidden;
  animation: ownex-scale-in-spring var(--transition-slower) var(--spring-bounce);
}

@keyframes ownex-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Input */
.ownex-command-palette__input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--ownex-bg-surface);
}

.ownex-command-palette__search-icon {
  position: absolute;
  left: var(--space-4);
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  pointer-events: none;
}

.ownex-command-palette__input {
  width: 100%;
  padding: var(--space-3) var(--space-4) var(--space-3) 48px;
  background: var(--ownex-bg-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.ownex-command-palette__input:focus {
  border-color: var(--ownex-blue);
  box-shadow: var(--focus-ring);
}

.ownex-command-palette__input::placeholder {
  color: var(--text-muted);
}

.ownex-command-palette__shortcut {
  margin-left: var(--space-3);
  padding: var(--space-1) var(--space-2);
  background: var(--ownex-bg-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.ownex-command-palette__shortcut span:first-child {
  padding-right: var(--space-1);
  border-right: 1px solid var(--border-subtle);
  margin-right: var(--space-1);
}

/* Results */
.ownex-command-palette__results {
  max-height: 60vh;
  overflow-y: auto;
  padding: var(--space-3);
}

.ownex-command-palette__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  text-align: center;
  color: var(--text-muted);
  gap: var(--space-2);
}

.ownex-command-palette__empty svg {
  width: 48px;
  height: 48px;
  opacity: 0.3;
}

/* Categories */
.ownex-command-palette__category {
  margin-bottom: var(--space-3);
}

.ownex-command-palette__category-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-command-palette__category-icon {
  font-size: var(--text-sm);
}

.ownex-command-palette__category-count {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--ownex-bg-base);
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
}

/* Items */
.ownex-command-palette__items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ownex-command-palette__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-instant);
}

.ownex-command-palette__item:hover,
.ownex-command-palette__item--selected {
  background: rgba(255, 255, 255, 0.1);
}

.ownex-command-palette__item-icon {
  font-size: 1.25rem;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
}

.ownex-command-palette__item-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ownex-command-palette__item-title {
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ownex-command-palette__item-description {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ownex-command-palette__item-shortcut {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--ownex-bg-base);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

/* Hints */
.ownex-command-palette__hints {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
  background: var(--ownex-bg-surface);
}

.ownex-command-palette__hints kbd {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-2);
  background: var(--ownex-bg-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-command-palette-overlay,
  .ownex-command-palette {
    animation: none;
  }
}

/* Mobile */
@media (max-width: 640px) {
  .ownex-command-palette-overlay {
    padding-top: 0;
    align-items: stretch;
  }

  .ownex-command-palette {
    margin: 0;
    border-radius: 0;
    height: 100vh;
    max-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .ownex-command-palette__results {
    flex: 1;
  }

  .ownex-command-palette__hints {
    position: sticky;
    bottom: 0;
  }
}
</style>