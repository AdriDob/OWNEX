<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  placeholder?: string
  type?: 'text' | 'password' | 'email' | 'search' | 'number'
  modelValue?: string | number | null
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'update:modelValue': [value: string | number | null] }>()

function onInput(e: Event) {
  const target = e.target as HTMLInputElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <input
    :type="type || 'text'"
    :placeholder="placeholder"
    :value="modelValue"
    @input="onInput"
    :class="cn(
      'flex h-9 w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-1 text-sm text-foreground shadow-sm transition-colors',
      'placeholder:text-muted-foreground/50',
      'focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20',
      'disabled:cursor-not-allowed disabled:opacity-50',
      props.class,
    )"
  />
</template>
