<script setup lang="ts">
/**
 * OWNEX Badge — Status indicator with variants
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'

interface Props {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'cycle' | 'gold' | 'platform'
  cycle?: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  platform?: 'hackerone' | 'bugcrowd' | 'intigriti' | 'synack' | 'yeswehack'
  size?: 'sm' | 'md'
  dot?: boolean
  removable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md',
  dot: false,
  removable: false,
})

const emit = defineEmits<{ remove: [] }>()

const classes = computed(() => [
  'ownex-badge',
  `ownex-badge--${props.size}`,
  `ownex-badge--${props.variant}`,
  { 'ownex-badge--dot': props.dot },
  { 'ownex-badge--removable': props.removable },
])

const cycleColors: Record<string, string> = {
  security: 'var(--color-cycle-security)',
  forge: 'var(--color-cycle-forge)',
  pulse: 'var(--color-cycle-pulse)',
  vault: 'var(--color-cycle-vault)',
  atlas: 'var(--color-cycle-atlas)',
  odyssey: 'var(--color-cycle-odyssey)',
}

const platformColors: Record<string, string> = {
  hackerone: 'var(--color-hackerone)',
  bugcrowd: 'var(--color-bugcrowd)',
  intigriti: 'var(--color-intigriti)',
  synack: 'var(--color-synack)',
  yeswehack: 'var(--color-yeswehack)',
}

const badgeStyle = computed(() => {
  if (props.variant === 'cycle' && props.cycle) {
    return { '--badge-color': cycleColors[props.cycle] }
  }
  if (props.variant === 'platform' && props.platform) {
    return { '--badge-color': platformColors[props.platform] }
  }
  return {}
})

const handleRemove = (event: MouseEvent) => {
  event.stopPropagation()
  emit('remove')
}
</script>

<template>
  <span
    :class="classes"
    :style="badgeStyle"
    role="status"
  >
    <span v-if="dot" class="ownex-badge__dot" :style="{ backgroundColor: 'var(--badge-color)' }" />
    <slot />
    <button
      v-if="removable"
      type="button"
      class="ownex-badge__remove"
      @click="handleRemove"
      aria-label="Remove"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </button>
  </span>
</template>

<style scoped>
.ownex-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-body);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-full);
  white-space: nowrap;
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.ownex-badge--sm {
  padding: 2px 8px;
  font-size: 10px;
  height: 20px;
}

.ownex-badge--md {
  padding: 3px 10px;
  font-size: 11px;
  height: 24px;
}

.ownex-badge--dot {
  padding-left: 6px;
}

.ownex-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Variants */
.ownex-badge--default {
  background: rgba(148, 163, 184, 0.1);
  border-color: rgba(148, 163, 184, 0.2);
  color: var(--ownex-text-secondary);
}

.ownex-badge--success {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.25);
  color: var(--ownex-green);
}

.ownex-badge--warning {
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.25);
  color: var(--ownex-yellow);
}

.ownex-badge--error {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.25);
  color: var(--ownex-red);
}

.ownex-badge--gold {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.25);
  color: var(--ownex-gold);
  font-weight: var(--font-weight-bold);
}

.ownex-badge--cycle {
  background: rgba(var(--badge-color-rgb), 0.12);
  border-color: rgba(var(--badge-color-rgb), 0.25);
  color: var(--badge-color);
}

.ownex-badge--platform {
  background: rgba(var(--badge-color-rgb), 0.12);
  border-color: rgba(var(--badge-color-rgb), 0.25);
  color: var(--badge-color);
}

/* RGB values for rgba() */
.ownex-badge--cycle-security { --badge-color-rgb: 59, 130, 246; --badge-color: var(--color-cycle-security); }
.ownex-badge--cycle-forge    { --badge-color-rgb: 168, 85, 247; --badge-color: var(--color-cycle-forge); }
.ownex-badge--cycle-pulse    { --badge-color-rgb: 16, 185, 129; --badge-color: var(--color-cycle-pulse); }
.ownex-badge--cycle-vault    { --badge-color-rgb: 245, 158, 11; --badge-color: var(--color-cycle-vault); }
.ownex-badge--cycle-atlas    { --badge-color-rgb: 226, 232, 240; --badge-color: var(--color-cycle-atlas); }
.ownex-badge--cycle-odyssey  { --badge-color-rgb: 249, 115, 22; --badge-color: var(--color-cycle-odyssey); }

.ownex-badge--platform-hackerone  { --badge-color-rgb: 0, 212, 106; --badge-color: var(--color-hackerone); }
.ownex-badge--platform-bugcrowd   { --badge-color-rgb: 245, 110, 47; --badge-color: var(--color-bugcrowd); }
.ownex-badge--platform-intigriti  { --badge-color-rgb: 105, 53, 211; --badge-color: var(--color-intigriti); }
.ownex-badge--platform-synack     { --badge-color-rgb: 30, 136, 229; --badge-color: var(--color-synack); }
.ownex-badge--platform-yeswehack  { --badge-color-rgb: 255, 107, 107; --badge-color: var(--color-yeswehack); }

/* Removable */
.ownex-badge--removable {
  padding-right: 6px;
}

.ownex-badge__remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: 2px;
  border: none;
  background: transparent;
  color: inherit;
  opacity: 0.6;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ownex-badge__remove:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}

.ownex-badge__remove svg {
  width: 10px;
  height: 10px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-badge {
    transition: none;
  }
}
</style>