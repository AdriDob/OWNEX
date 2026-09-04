<script setup lang="ts">
interface Props {
  label: string
  required: boolean
}

const props = defineProps<Props>()

const badgeColor = computed(() => (props.required ? 'from-cyan-500 to-blue-500' : 'from-green-500 to-emerald-500'))

const badgeLabel = computed(() => (props.required ? 'REQUERIDO' : 'NO requerido'))
</script>

<template>
  <div class="requirement-badge" :style="{ '--badge-color': badgeColor }">
    <span class="requirement-badge__label">{{ label }}</span>
    <span class="requirement-badge__status" :style="{ background: `linear-gradient(135deg, ${badgeColor})` }">
      {{ badgeLabel }}
    </span>
  </div>
</template>

<style scoped>
.requirement-badge {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 10px 14px;
  min-width: 140px;
  flex: 1;
}

.requirement-badge__label {
  font-size: 0.75rem;
  font-weight: 500;
  color: #ddd;
}

.requirement-badge__status {
  font-size: 0.625rem;
  font-weight: 600;
  color: white;
  padding: 3px 8px;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--badge-color) 40%, transparent);
}
</style>