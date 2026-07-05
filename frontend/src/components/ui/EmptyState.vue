<script setup lang="ts">
import { Package } from '@lucide/vue'
import type { Component } from 'vue'
import { useRouter } from 'vue-router'
import Button from './Button.vue'

const props = withDefaults(defineProps<{
  title: string
  description?: string
  actionLabel?: string
  actionRoute?: string
  icon?: Component
}>(), {
  icon: Package,
})

const router = useRouter()

function handleAction() {
  if (props.actionRoute) router.push(props.actionRoute)
}
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 px-4 text-center">
    <div class="w-16 h-16 rounded-full glass flex items-center justify-center mb-4">
      <component :is="icon" class="w-8 h-8 text-muted" />
    </div>
    <h3 class="text-lg font-semibold text-foreground mb-1">{{ title }}</h3>
    <p v-if="description" class="text-sm text-muted max-w-md mb-4 leading-relaxed">{{ description }}</p>
    <Button v-if="actionLabel" size="sm" @click="handleAction">{{ actionLabel }}</Button>
  </div>
</template>
