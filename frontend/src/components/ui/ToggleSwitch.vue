<template>
  <button
    @click="toggle"
    :class="['toggle-switch', { active: modelValue, disabled: disabled }]"
    :aria-pressed="modelValue"
    :disabled="disabled"
    type="button"
  >
    <span class="toggle-thumb" />
  </button>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function toggle() {
  if (!disabled) {
    emit('update:modelValue', !modelValue)
  }
}
</script>

<style scoped>
.toggle-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  background: var(--ownex-bg-elevated);
  border-color: rgba(255, 255, 255, 0.15);
  flex-shrink: 0;
}

.toggle-switch:not(.disabled):hover {
  background: #262a33;
  border-color: rgba(0, 213, 255, 0.3);
}

.toggle-switch:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 213, 255, 0.4);
}

.toggle-switch.active {
  background: var(--ownex-accent);
  border-color: var(--ownex-accent);
}

.toggle-switch.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.toggle-thumb {
  display: block;
  border-radius: 50%;
  background: var(--ownex-text-secondary);
  transition: transform 0.15s ease, background 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.toggle-switch.active .toggle-thumb {
  transform: translateX(100%);
  background: var(--ownex-bg-base);
}

.toggle-switch.sm {
  width: 36px;
  height: 20px;
}

.toggle-switch.sm .toggle-thumb {
  width: 16px;
  height: 16px;
  margin: 2px;
}

.toggle-switch.sm.active .toggle-thumb {
  transform: translateX(16px);
}

.toggle-switch.md {
  width: 44px;
  height: 24px;
}

.toggle-switch.md .toggle-thumb {
  width: 20px;
  height: 20px;
  margin: 2px;
}

.toggle-switch.md.active .toggle-thumb {
  transform: translateX(20px);
}

.toggle-switch.lg {
  width: 52px;
  height: 28px;
}

.toggle-switch.lg .toggle-thumb {
  width: 24px;
  height: 24px;
  margin: 2px;
}

.toggle-switch.lg.active .toggle-thumb {
  transform: translateX(24px);
}
</style>