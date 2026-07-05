<script setup lang="ts">
import { ref } from 'vue'
import { Copy, Check } from '@lucide/vue'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<{
  text: string
  label?: string
  icon?: boolean
  variant?: 'icon' | 'button' | 'chip'
}>(), {
  label: 'Copy',
  icon: true,
  variant: 'icon',
})

const copied = ref(false)

async function copy() {
  try {
    await navigator.clipboard.writeText(props.text)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = props.text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  }
}
</script>

<template>
  <button
    class="inline-flex items-center gap-1 transition-colors"
    :class="[
      variant === 'icon' && 'p-1 rounded text-muted hover:text-foreground hover:bg-surface-hover',
      variant === 'button' && 'px-2 py-1 rounded-md text-xs font-medium text-muted hover:text-foreground hover:bg-surface-hover border border-border/40',
      variant === 'chip' && 'px-2 py-0.5 rounded-full text-[10px] font-mono text-muted hover:text-foreground bg-surface/60 border border-border/30',
    ]"
    :aria-label="label"
    @click="copy"
  >
    <component :is="copied ? Check : Copy" class="w-3.5 h-3.5" :class="{ 'text-success': copied }" />
    <span v-if="!icon">{{ copied ? 'Copied!' : label }}</span>
  </button>
</template>
