<script setup lang="ts">
import { ref, watch } from 'vue'

interface Tab {
  id: string
  label: string
  icon?: any
  badge?: number | string
  disabled?: boolean
}

const props = defineProps<{
  tabs: Tab[]
  modelValue?: string
  size?: 'sm' | 'md'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const activeTab = ref(props.modelValue || props.tabs[0]?.id || '')

watch(() => props.modelValue, (val) => {
  if (val) activeTab.value = val
})

function selectTab(id: string) {
  activeTab.value = id
  emit('update:modelValue', id)
}
</script>

<template>
  <div class="w-full">
    <!-- Tab bar -->
    <div class="flex gap-1 border-b border-border/40">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :disabled="tab.disabled"
        class="relative flex items-center gap-1.5 px-3 py-2 text-xs font-mono transition-colors"
        :class="[
          activeTab === tab.id
            ? 'text-foreground font-medium'
            : 'text-muted-foreground hover:text-foreground',
          tab.disabled && 'opacity-40 cursor-not-allowed',
        ]"
        @click="selectTab(tab.id)"
      >
        <component :is="tab.icon" v-if="tab.icon" class="h-3.5 w-3.5" />
        <span>{{ tab.label }}</span>
        <span
          v-if="tab.badge !== undefined"
          class="ml-1 rounded-full bg-primary/15 px-1.5 py-0.5 font-mono text-[9px] font-bold tabular-nums text-primary"
        >
          {{ tab.badge }}
        </span>
        <!-- Active indicator -->
        <span
          v-if="activeTab === tab.id"
          class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
        />
      </button>
    </div>

    <!-- Tab content -->
    <div class="pt-4">
      <slot :name="activeTab" />
    </div>
  </div>
</template>
