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
  primary: 'bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 hover:border-primary/40 focus-glow',
  secondary: 'bg-surface text-foreground border border-border hover:bg-surface-hover hover:border-border-light focus-glow',
  ghost: 'text-muted-foreground hover:text-foreground hover:bg-surface/40',
  gold: 'bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 hover:border-primary/40 focus-glow',
  outline: 'bg-transparent text-foreground border border-border hover:border-primary/30 hover:text-primary',
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
