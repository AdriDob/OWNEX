<script setup lang="ts">
import { cn } from '@/lib/utils'
import { computed } from 'vue'

interface Props {
  variant?: 'primary' | 'secondary' | 'ghost' | 'gold' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
})

const variantStyles: Record<string, string> = {
  primary: 'bg-[rgb(0,112,209)]/10 text-[rgb(0,112,209)] border border-[rgb(0,112,209)]/20 hover:bg-[rgb(0,112,209)]/20 hover:border-[rgb(0,112,209)]/40 focus-glow',
  secondary: 'bg-[rgb(15,17,23)] text-[rgb(240,240,240)] border border-[rgb(26,26,46)] hover:bg-[rgb(16,16,24)] hover:border-[rgb(37,37,64)] focus-glow',
  ghost: 'text-[rgb(139,139,149)] hover:text-[rgb(240,240,240)] hover:bg-[rgb(15,17,23)]/40',
  gold: 'bg-[rgb(245,158,11)]/10 text-[rgb(245,158,11)] border border-[rgb(245,158,11)]/20 hover:bg-[rgb(245,158,11)]/20 hover:border-[rgb(245,158,11)]/40 focus-glow',
  outline: 'bg-transparent text-[rgb(240,240,240)] border border-[rgb(26,26,46)] hover:border-[rgb(0,112,209)]/30 hover:text-[rgb(0,112,209)]',
}

const sizeStyles: Record<string, string> = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-2.5 text-base',
}
</script>

<template>
  <button
    :class="cn(
      'btn-press inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200',
      variantStyles[variant],
      sizeStyles[size],
      (loading || disabled) && 'opacity-50 cursor-not-allowed',
    )"
    :disabled="loading || disabled"
  >
    <span v-if="loading" class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
    <slot />
  </button>
</template>
