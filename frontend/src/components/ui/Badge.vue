<script setup lang="ts">
import { cn } from '@/lib/utils'
import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

const badgeVariants = cva(
  'inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary/15 text-primary',
        destructive: 'border-transparent bg-destructive/15 text-destructive',
        warning: 'border-transparent bg-warning/15 text-warning',
        success: 'border-transparent bg-success/15 text-success',
        info: 'border-transparent bg-accent/15 text-accent',
        outline: 'text-foreground border-border',
        gold: 'border-transparent bg-gold/15 text-gold',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

type BadgeVariants = VariantProps<typeof badgeVariants>

interface Props {
  variant?: BadgeVariants['variant']
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <span :class="cn(badgeVariants({ variant }), props.class)">
    <slot />
  </span>
</template>
