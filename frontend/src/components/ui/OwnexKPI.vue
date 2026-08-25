<script setup lang="ts">
/**
 * OWNEX KPI — Key Performance Indicator display
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2 - Mission Control KPI cards
 */

import { computed, onMounted, ref } from 'vue'

interface Props {
  label: string
  value: string | number
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'gold' | 'cycle'
  cycle?: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: string
}

const props = withDefaults(defineProps<Props>(), {
  trend: 'neutral',
  variant: 'default',
  size: 'md',
  loading: false,
})

const classes = computed(() => [
  'ownex-kpi',
  `ownex-kpi--${props.size}`,
  { 'ownex-kpi--loading': props.loading },
])

const accentColor = computed(() => {
  if (props.variant === 'cycle' && props.cycle) {
    const colors: Record<string, string> = {
      security: 'var(--ownex-cycle-security)',
      forge: 'var(--ownex-cycle-forge)',
      pulse: 'var(--ownex-cycle-pulse)',
      vault: 'var(--ownex-cycle-vault)',
      atlas: 'var(--ownex-cycle-atlas)',
      odyssey: 'var(--ownex-cycle-odyssey)',
    }
    return colors[props.cycle]
  }
  const variants: Record<string, string> = {
    primary: 'var(--ownex-blue)',
    success: 'var(--ownex-green)',
    warning: 'var(--ownex-yellow)',
    gold: 'var(--ownex-gold)',
    default: 'var(--ownex-text-muted)',
  }
  return variants[props.variant]
})

const isLarge = computed(() => props.size === 'lg')
const isSmall = computed(() => props.size === 'sm')

// Animate number on mount
const displayValue = ref(props.loading ? '—' : String(props.value))

onMounted(() => {
  if (!props.loading && typeof props.value === 'number') {
    animateNumber(0, props.value, 800)
  }
})

const animateNumber = (from: number, to: number, duration: number) => {
  const start = performance.now()
  const animate = (now: number) => {
    const progress = Math.min((now - start) / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
    displayValue.value = Math.round(from + (to - from) * eased).toLocaleString()
    if (progress < 1) requestAnimationFrame(animate)
  }
  requestAnimationFrame(animate)
}
</script>

<template>
  <div :class="classes" :style="{ '--kpi-accent': accentColor }" role="region" :aria-label="label">
    <div class="ownex-kpi__header">
      <span v-if="icon" class="ownex-kpi__icon" :data-icon="icon" aria-hidden="true">
        <component :is="icon" class="ownex-kpi__icon-svg" />
      </span>
      <span class="ownex-kpi__label">{{ label }}</span>
    </div>

    <div class="ownex-kpi__value-wrapper">
      <span class="ownex-kpi__value animate-count" v-if="!loading">{{ displayValue }}</span>
      <span v-else class="ownex-kpi__value ownex-kpi__value--skeleton">
        <span class="skeleton-pulse" style="width: 80px; height: 32px; display: inline-block; border-radius: 4px;" />
      </span>
      <span v-if="trend !== 'neutral' && !loading" class="ownex-kpi__trend" :class="`ownex-kpi__trend--${trend}`">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
          <path v-if="trend === 'up'" d="M18 15l-6-6-6 6" />
          <path v-else-if="trend === 'down'" d="M6 9l6 6 6-6" />
        </svg>
        <span v-if="trendValue">{{ trendValue }}</span>
      </span>
    </div>

    <div v-if="$slots.detail" class="ownex-kpi__detail">
      <slot name="detail" />
    </div>
  </div>
</template>

<style scoped>
.ownex-kpi {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.85), rgba(5, 5, 5, 0.65));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
  position: relative;
  overflow: hidden;
}

.ownex-kpi:hover {
  border-color: var(--color-border-light);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
}

/* Accent top border */
.ownex-kpi::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--kpi-accent);
  opacity: 0.6;
}

/* Sizes */
.ownex-kpi--sm {
  padding: var(--space-3);
  min-width: 140px;
}

.ownex-kpi--md {
  padding: var(--space-4);
  min-width: 180px;
}

.ownex-kpi--lg {
  padding: var(--space-5);
  min-width: 240px;
}

/* Header */
.ownex-kpi__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.ownex-kpi__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: var(--kpi-accent);
  opacity: 0.8;
}

.ownex-kpi__icon-svg {
  width: 18px;
  height: 18px;
}

.ownex-kpi__label {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ownex-text-muted);
}

.ownex-kpi--sm .ownex-kpi__label { font-size: 10px; }
.ownex-kpi--lg .ownex-kpi__label { font-size: 12px; }

/* Value */
.ownex-kpi__value-wrapper {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.ownex-kpi__value {
  font-family: var(--font-display);
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  line-height: 1.1;
  tabular-nums: true;
}

.ownex-kpi--sm .ownex-kpi__value { font-size: 20px; }
.ownex-kpi--md .ownex-kpi__value { font-size: 28px; }
.ownex-kpi--lg .ownex-kpi__value { font-size: 36px; }

.ownex-kpi__value--skeleton {
  display: inline-block;
}

/* Trend */
.ownex-kpi__trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
}

.ownex-kpi--sm .ownex-kpi__trend { font-size: 10px; }
.ownex-kpi--lg .ownex-kpi__trend { font-size: 13px; }

.ownex-kpi__trend--up { color: var(--ownex-green); }
.ownex-kpi__trend--down { color: var(--ownex-danger); }
.ownex-kpi__trend--neutral { color: var(--ownex-text-muted); }

/* Detail slot */
.ownex-kpi__detail {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

/* Loading state */
.ownex-kpi--loading {
  pointer-events: none;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-kpi__value.animate-count {
    animation: none;
  }
}
</style>