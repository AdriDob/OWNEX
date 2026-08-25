<script setup lang="ts">
import { computed } from 'vue'

/**
 * MoneyValue — canonical economic value rendering (design system F1b).
 *
 * Semantics per product rules: potential / expected / confirmed are
 * DIFFERENT kinds of money and must never be mixed or colored alike.
 * Uses .money utility (mono + tabular figures) so columns align.
 */
interface Props {
  /** Numeric amount, or a literal like '—' when unknown */
  value: number | string
  currency?: string
  /** Economic semantics — drives the label and color */
  kind?: 'potential' | 'expected' | 'hourly' | 'confirmed'
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  currency: 'USD',
  kind: 'potential',
  size: 'md',
})

const KIND_LABEL: Record<NonNullable<Props['kind']>, string> = {
  potential: 'Potencial',
  expected: 'Esperado',
  hourly: 'Por hora',
  confirmed: 'Confirmado',
}

const KIND_COLOR: Record<NonNullable<Props['kind']>, string> = {
  potential: 'var(--color-text)',
  expected: 'var(--color-info)',
  hourly: 'var(--color-text)',
  confirmed: 'var(--color-success)',
}

const SIZE_CLASS = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-2xl font-semibold tracking-tight',
} as const

const isHourly = computed(() => props.kind === 'hourly')

const formatted = computed(() => {
  if (typeof props.value === 'string') return props.value
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: props.currency,
    maximumFractionDigits: props.value >= 1000 ? 0 : 2,
  }).format(props.value)
})

const suffix = computed(() => (isHourly.value ? '/h' : ''))

const ariaLabel = computed(() =>
  `${KIND_LABEL[props.kind]}: ${formatted.value}${suffix.value} ${props.currency}`.trim(),
)
</script>

<template>
  <div class="money-value inline-flex flex-col gap-0.5" :role="'text'" :aria-label="ariaLabel">
    <span
      class="money inline-flex items-baseline"
      :class="SIZE_CLASS[size]"
      :style="{ color: KIND_COLOR[kind] }"
    >
      {{ formatted }}<span v-if="suffix" class="ml-0.5 text-xs opacity-70">{{ suffix }}</span>
    </span>
    <span class="text-[10px] uppercase tracking-widest" style="color: var(--color-text-muted)">
      {{ KIND_LABEL[kind] }}
    </span>
  </div>
</template>
