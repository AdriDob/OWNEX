<script setup lang="ts">
import { cn } from '@/lib/utils'
import { ChevronDown } from '@lucide/vue'

interface SelectOption {
  value: string | number
  label: string
}

interface Props {
  options: SelectOption[]
  modelValue?: string | number | null
  placeholder?: string
  class?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

function onChange(e: Event) {
  const target = e.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <div class="relative">
    <select
      :value="modelValue"
      @change="onChange"
      :class="cn(
        'flex h-9 w-full appearance-none rounded-lg border border-[rgb(37,37,64)] bg-[rgb(15,17,23)]/50 px-3 py-1 pr-8 text-sm text-[rgb(240,240,240)] shadow-sm transition-colors',
        'focus:border-[rgb(0,112,209)]/30 focus:outline-none focus:ring-1 focus:ring-[rgb(0,112,209)]/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        !modelValue && 'text-[rgb(100,116,139)]/50',
        props.class,
      )"
    >
      <option v-if="placeholder" value="" disabled selected>{{ placeholder }}</option>
      <option
        v-for="opt in options"
        :key="opt.value"
        :value="opt.value"
        :selected="opt.value === modelValue"
      >{{ opt.label }}</option>
    </select>
    <ChevronDown class="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
  </div>
</template>
