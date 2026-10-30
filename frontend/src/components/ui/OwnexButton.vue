<script setup lang="ts">
/**
 * OWNEX Button — Primary action component with variants
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'gold'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  fullWidth?: boolean
  type?: 'button' | 'submit' | 'reset'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  disabled: false,
  loading: false,
  fullWidth: false,
  type: 'button',
})

const classes = computed(() => [
  'ownex-btn',
  `ownex-btn--${props.variant}`,
  `ownex-btn--${props.size}`,
  { 'ownex-btn--full': props.fullWidth },
  { 'ownex-btn--loading': props.loading },
  { 'ownex-btn--disabled': props.disabled || props.loading },
])
</script>

<template>
  <button
    :class="classes"
    :type="type"
    :disabled="disabled || loading"
    class="btn-press motion-safe"
  >
    <span v-if="loading" class="ownex-btn__spinner" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke-opacity="1" stroke-linecap="round" />
      </svg>
    </span>
    <span :class="{ 'ownex-btn__content-hidden': loading }">
      <slot />
    </span>
  </button>
</template>

<style scoped>
.ownex-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-body);
  font-weight: var(--font-weight-medium);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

/* Sizes */
.ownex-btn--sm {
  padding: var(--space-1) var(--space-3);
  font-size: 12px;
  height: 32px;
}

.ownex-btn--md {
  padding: var(--space-2) var(--space-4);
  font-size: 13px;
  height: 40px;
}

.ownex-btn--lg {
  padding: var(--space-3) var(--space-6);
  font-size: 14px;
  height: 48px;
}

.ownex-btn--full {
  width: 100%;
}

/* Variants */
.ownex-btn--primary {
  background: var(--ownex-accent);
  color: var(--ownex-white);
}
.ownex-btn--primary:hover:not(:disabled) {
  filter: brightness(0.95);
  box-shadow: 0 4px 20px rgba(232, 33, 39, 0.18);
}

.ownex-btn--secondary {
  background: var(--glass-bg);
  border: var(--glass-border);
  color: var(--ownex-white);
  backdrop-filter: var(--glass-blur);
}
.ownex-btn--secondary:hover:not(:disabled) {
  background: var(--ownex-bg-surface);
  border-color: rgba(255, 255, 255, 0.25);
}

.ownex-btn--ghost {
  background: transparent;
  color: var(--ownex-text-secondary);
}
.ownex-btn--ghost:hover:not(:disabled) {
  color: var(--ownex-white);
  background: var(--ownex-bg-surface);
}

.ownex-btn--danger {
  background: var(--ownex-danger);
  color: var(--ownex-white);
}
.ownex-btn--danger:hover:not(:disabled) {
  background: var(--ownex-danger);
  box-shadow: 0 0 20px rgba(0, 213, 255, 0.2);
}

.ownex-btn--gold {
  background: linear-gradient(135deg, var(--ownex-gold), var(--ownex-yellow));
  color: var(--ownex-bg-deep);
  font-weight: var(--font-weight-bold);
}
.ownex-btn--gold:hover:not(:disabled) {
  box-shadow: var(--shadow-gold);
}

/* Disabled state */
.ownex-btn--disabled,
.ownex-btn--disabled:hover {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* Loading spinner */
.ownex-btn__spinner {
  position: absolute;
  width: 18px;
  height: 18px;
  animation: spin 0.8s linear infinite;
}

.ownex-btn__content-hidden {
  visibility: hidden;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Press animation */
.btn-press:active:not(:disabled) {
  transform: scale(0.97);
}

/* Focus visible */
.ownex-btn:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring), 0 0 0 4px rgba(232, 33, 39, 0.12);
}
</style>