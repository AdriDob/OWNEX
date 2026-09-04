<script setup lang="ts">
/**
 * EmptyState — contextual empty state with icon, message, and optional action.
 * NEVER shows just "No data" — always provides context and next step.
 */

import { Inbox } from '@lucide/vue'
import type { Component } from 'vue'
import OwnexButton from './OwnexButton.vue'

interface Props {
  icon?: Component
  title: string
  description?: string
  actionLabel?: string
  actionRoute?: string
}

const props = withDefaults(defineProps<Props>(), {
  icon: Inbox,
  description: '',
  actionLabel: '',
  actionRoute: '',
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 px-6 text-center">
    <!-- Icon -->
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-muted/20 mb-4">
      <component :is="icon" class="h-6 w-6 text-muted-foreground" />
    </div>

    <!-- Title -->
    <h3 class="text-sm font-semibold text-foreground mb-1">{{ title }}</h3>

    <!-- Description -->
    <p v-if="description" class="text-xs text-muted-foreground max-w-xs mb-4">
      {{ description }}
    </p>

    <!-- Action -->
    <OwnexButton
      v-if="actionLabel"
      variant="outline"
      size="sm"
      @click="actionRoute ? $router.push(actionRoute) : emit('action')"
    >
      {{ actionLabel }}
    </OwnexButton>
  </div>
</template>
