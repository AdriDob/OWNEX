<script setup lang="ts">
import { cn } from '@/lib/utils'
import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'

const badgeVariants = cva(
  'inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-mono font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 uppercase tracking-wider',
  {
    variants: {
      variant: {
        default: 'bg-surface text-muted-foreground border border-border/50',
        destructive: 'bg-destructive/15 text-destructive border border-destructive/20',
        warning: 'bg-warning/15 text-warning border border-warning/20',
        success: 'bg-success/15 text-success border border-success/20',
        info: 'bg-accent/15 text-accent border border-accent/20',
        outline: 'border border-border text-muted-foreground',
        gold: 'bg-gold/15 text-gold border border-gold/20',
        active: 'bg-success/15 text-success border border-success/20 phosphor',
        scanning: 'bg-accent/15 text-accent border border-accent/20 animate-pulse',
        critical: 'bg-destructive/20 text-destructive border border-destructive/30 animate-pulse',
        offline: 'bg-muted/10 text-muted border border-border/30',
      },
      size: {
        xs: 'text-[9px] px-1.5 py-0.5',
        sm: 'text-[10px] px-2 py-0.5',
        md: 'text-xs px-2.5 py-1',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'sm',
    },
  },
)

type BadgeVariants = VariantProps<typeof badgeVariants>

interface Props {
  variant?: BadgeVariants['variant']
  size?: BadgeVariants['size']
  class?: string
}
const props = defineProps<Props>()
</script>

<template>
  <span :class="cn(badgeVariants({ variant, size }), props.class)">
    <slot />
  </span>
</template>
