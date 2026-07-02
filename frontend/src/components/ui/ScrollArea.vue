<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <div :class="cn('overflow-y-auto custom-scroll', props.class)">
    <slot />
  </div>
</template>
