<script setup lang="ts">
import Skeleton from './Skeleton.vue'

interface Props {
  count?: number
  height?: string
}

withDefaults(defineProps<Props>(), {
  count: 4,
  height: 'h-24',
})
</script>

<template>
  <div :class="['space-y-4', $attrs.class as string]">
    <div :class="['grid grid-cols-2 gap-4 sm:grid-cols-4']">
      <Skeleton v-for="i in count" :key="i" :class="`${height} rounded-xl`" />
    </div>
    <Skeleton class="h-48 rounded-xl" />
  </div>
</template>
