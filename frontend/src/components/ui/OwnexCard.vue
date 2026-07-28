<script setup lang="ts">
/**
 * OWNEX Card — Glassmorphism base card component
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'

interface Props {
  variant?: 'base' | 'elevated' | 'highlight' | 'cycle'
  cycle?: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  hoverable?: boolean
  padded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'base',
  hoverable: true,
  padded: true,
})

const classes = computed(() => [
  'ownex-card',
  `ownex-card--${props.variant}`,
  { 'ownex-card--hoverable': props.hoverable },
  { 'ownex-card--padded': props.padded },
  { [`ownex-card--cycle-${props.cycle}`]: props.variant === 'cycle' && props.cycle },
])

const cycleStyle = computed(() => {
  if (props.variant !== 'cycle' || !props.cycle) return {}
  const colors: Record<string, string> = {
    security: 'var(--color-cycle-security)',
    forge: 'var(--color-cycle-forge)',
    pulse: 'var(--color-cycle-pulse)',
    vault: 'var(--color-cycle-vault)',
    atlas: 'var(--color-cycle-atlas)',
    odyssey: 'var(--color-cycle-odyssey)',
  }
  return { '--cycle-color': colors[props.cycle] }
})
</script>

<template>
  <div
    :class="classes"
    :style="cycleStyle"
    role="region"
  >
    <slot />
  </div>
</template>

<style scoped>
.ownex-card {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.85), rgba(5, 5, 5, 0.65));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.ownex-card--padded {
  padding: var(--space-4);
}

.ownex-card--hoverable:hover {
  border-color: var(--color-border-light);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
}

/* Variants */
.ownex-card--elevated {
  background: var(--ownex-bg-surface);
  box-shadow: var(--shadow-md);
}

.ownex-card--highlight {
  border-left: 2px solid var(--ownex-blue);
}

.ownex-card--cycle {
  border-color: rgba(var(--cycle-color-rgb), 0.2);
}
.ownex-card--cycle:hover {
  border-color: rgba(var(--cycle-color-rgb), 0.4);
  box-shadow: 0 2px 20px rgba(var(--cycle-color-rgb), 0.08);
}

/* Cycle color RGB values for rgba() */
.ownex-card--cycle-security { --cycle-color-rgb: 59, 130, 246; }
.ownex-card--cycle-forge    { --cycle-color-rgb: 168, 85, 247; }
.ownex-card--cycle-pulse    { --cycle-color-rgb: 16, 185, 129; }
.ownex-card--cycle-vault    { --cycle-color-rgb: 245, 158, 11; }
.ownex-card--cycle-atlas    { --cycle-color-rgb: 226, 232, 240; }
.ownex-card--cycle-odyssey  { --cycle-color-rgb: 249, 115, 22; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-card {
    transition: none;
  }
}
</style>