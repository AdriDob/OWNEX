<script setup lang="ts">
import { ref } from 'vue'
import { cn } from '@/lib/utils'
import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium font-mono transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 relative overflow-hidden btn-press tracking-wide uppercase',
  {
    variants: {
      variant: {
        default: 'bg-[rgb(0,112,209)] text-[rgb(239,246,255)] hover:bg-[rgb(0,112,209)]/90 shadow-sm shadow-[rgb(0,112,209)]/10',
        destructive: 'bg-[rgb(239,68,68)] text-white hover:bg-[rgb(239,68,68)]/90 shadow-sm shadow-[rgb(239,68,68)]/10',
        outline: 'border border-[rgb(26,26,46)] bg-transparent hover:bg-[rgb(15,17,23)] hover:text-[rgb(240,240,240)]',
        secondary: 'bg-[rgb(15,17,23)] text-[rgb(240,240,240)] hover:bg-[rgb(16,16,24)]',
        ghost: 'hover:bg-[rgb(15,17,23)] text-[rgb(100,116,139)] hover:text-[rgb(240,240,240)]',
        link: 'text-[rgb(0,112,209)] underline-offset-4 hover:underline',
        phosphor: 'bg-transparent border border-[rgb(0,112,209)]/30 text-[rgb(0,112,209)] hover:bg-[rgb(0,112,209)]/10 hover:border-[rgb(0,112,209)]/60 shadow-sm shadow-[rgb(0,112,209)]/5 phosphor',
        tactical: 'bg-transparent border-2 border-[rgb(37,37,64)] text-[rgb(240,240,240)] hover:border-[rgb(0,112,209)]/40 hover:text-[rgb(0,112,209)] tactical-border',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 rounded-md px-8',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

type ButtonVariants = VariantProps<typeof buttonVariants>

interface Props {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  disabled?: boolean
  loading?: boolean
  asChild?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  asChild: false,
})
const ripples = ref<{ id: number; x: number; y: number }[]>([])
let rippleId = 0

function onClick(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const id = ++rippleId
  ripples.value.push({ id, x, y })
  setTimeout(() => {
    ripples.value = ripples.value.filter(r => r.id !== id)
  }, 500)
}
</script>

<template>
  <button
    v-if="!asChild"
    :class="cn(buttonVariants({ variant, size }), props.class)"
    :disabled="disabled || loading"
    @click="onClick"
  >
    <span v-if="loading" class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
    <slot />
    <span
      v-for="r in ripples" :key="r.id"
      class="pointer-events-none absolute rounded-full bg-white/20 animate-ripple"
      :style="{ left: r.x + 'px', top: r.y + 'px', width: '8px', height: '8px', marginLeft: '-4px', marginTop: '-4px' }"
    />
  </button>
  <slot v-else />
</template>

<style scoped>
@keyframes rippleEffect {
  from { transform: scale(0); opacity: 0.6; }
  to { transform: scale(12); opacity: 0; }
}
:deep(.animate-ripple) {
  animation: rippleEffect 0.5s ease-out forwards;
}
</style>
