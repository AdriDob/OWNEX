<script setup lang="ts">
import IconBase from './IconBase.vue'
</script>

<template>
  <IconBase v-bind="$attrs">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 6v6l4 2" />
  </IconBase>
</template>