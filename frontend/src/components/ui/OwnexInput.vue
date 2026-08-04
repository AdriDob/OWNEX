<script setup lang="ts">
/**
 * OWNEX Input — Search/Input field with glass styling
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'

interface Props {
  modelValue?: string
  placeholder?: string
  type?: 'text' | 'search' | 'password' | 'email' | 'number'
  disabled?: boolean
  readonly?: boolean
  error?: boolean
  label?: string
  helperText?: string
  icon?: string
  clearable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '',
  type: 'text',
  disabled: false,
  readonly: false,
  error: false,
  clearable: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  focus: []
  blur: []
  keydown: [event: KeyboardEvent]
}>()

const isFocused = ref(false)

const classes = computed(() => [
  'ownex-input',
  { 'ownex-input--focused': isFocused },
  { 'ownex-input--error': props.error },
  { 'ownex-input--disabled': props.disabled },
  { 'ownex-input--has-icon': !!props.icon },
  { 'ownex-input--has-clear': props.clearable && props.modelValue },
])

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
}

const handleClear = () => {
  emit('update:modelValue', '')
}

const handleFocus = () => {
  isFocused.value = true
  emit('focus')
}

const handleBlur = () => {
  isFocused.value = false
  emit('blur')
}
</script>

<template>
  <div :class="classes">
    <label v-if="label" class="ownex-input__label">{{ label }}</label>
    <div class="ownex-input__wrapper">
      <slot name="icon" v-if="icon">
        <span class="ownex-input__icon" :data-icon="icon" aria-hidden="true">
          <component :is="icon" class="ownex-input__icon-svg" />
        </span>
      </slot>
      <input
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :class="{ 'ownex-input__field': true }"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="emit('keydown', $event)"
        class="focus-glow"
      />
      <button
        v-if="clearable && modelValue && !disabled && !readonly"
        type="button"
        class="ownex-input__clear"
        @click="handleClear"
        aria-label="Clear input"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="ownex-input__clear-icon">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
    <span v-if="error" class="ownex-input__error" role="alert">
      <slot name="error">{{ errorMessage }}</slot>
    </span>
    <span v-else-if="helperText && !error" class="ownex-input__helper">
      {{ helperText }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const errorMessage = computed(() => 'Valor inválido')
</script>

<style scoped>
.ownex-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
}

.ownex-input__label {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-muted);
}

.ownex-input__wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.ownex-input__field {
  width: 100%;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: var(--radius-md);
  color: var(--ownex-white);
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: 13px;
  transition: all var(--transition-fast);
}

.ownex-input__field::placeholder {
  color: var(--ownex-text-muted);
}

.ownex-input__field:focus {
  outline: none;
  border-color: var(--ownex-blue);
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.15);
}

.ownex-input__field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ownex-input__icon {
  position: absolute;
  left: var(--space-3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ownex-text-muted);
  pointer-events: none;
}

.ownex-input__icon-svg {
  width: 18px;
  height: 18px;
}

.ownex-input__field {
  padding-left: var(--space-10);
}

.ownex-input__clear {
  position: absolute;
  right: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--ownex-text-muted);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ownex-input__clear:hover {
  background: var(--ownex-bg-surface);
  color: var(--ownex-white);
}

.ownex-input__clear-icon {
  width: 16px;
  height: 16px;
}

.ownex-input--has-clear .ownex-input__field {
  padding-right: var(--space-10);
}

.ownex-input__error {
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--ownex-red);
}

.ownex-input__helper {
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--ownex-text-muted);
}

/* Focus states */
.ownex-input--focused .ownex-input__icon {
  color: var(--ownex-blue);
}
</style>