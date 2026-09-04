<script setup lang="ts">
import { ArcElement, Chart as ChartJS, Legend, Tooltip } from 'chart.js'
import { computed } from 'vue'
import { Doughnut } from 'vue-chartjs'

ChartJS.register(ArcElement, Tooltip, Legend)

interface Props {
  labels: string[]
  data: number[]
  colors?: string[]
  title?: string
  height?: number
  cutout?: string
  showLegend?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: 250,
  cutout: '60%',
  showLegend: true,
})

const isDark = computed(() => document.documentElement.classList.contains('dark'))

const defaultColors = computed(() => [
  'var(--ownex-accent)',
  'var(--ownex-text-primary)',
  'var(--ownex-green)',
  'var(--ownex-gold)',
  'var(--ownex-accent)',
  'var(--ownex-text-secondary)',
  '#14b8a6',
  'var(--ownex-yellow)',
  'var(--ownex-text-secondary)',
  'var(--ownex-text-secondary)',
  '#84cc16',
  'var(--ownex-text-secondary)',
  'var(--ownex-accent)',
  '#d946ef',
  '#0ea5e9',
])

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      data: props.data,
      backgroundColor: props.colors || defaultColors.value.slice(0, props.data.length),
      borderColor: isDark.value ? '#11131f' : 'var(--ownex-text-primary)',
      borderWidth: 2,
      hoverOffset: 8,
    },
  ],
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: props.cutout,
  plugins: {
    legend: {
      display: props.showLegend,
      position: 'bottom' as const,
      labels: {
        color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)',
        font: { size: 10 },
        padding: 12,
        usePointStyle: true,
        pointStyle: 'circle' as const,
      },
    },
    title: props.title
      ? {
          display: true,
          text: props.title,
          color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-bg-base)',
          font: { size: 12 },
          padding: { bottom: 12 },
        }
      : undefined,
    tooltip: {
      backgroundColor: isDark.value ? 'var(--ownex-bg-elevated)' : 'var(--ownex-text-primary)',
      titleColor: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-bg-base)',
      bodyColor: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)',
      borderColor: isDark.value ? 'var(--ownex-border)' : 'var(--ownex-text-secondary)',
      borderWidth: 1,
      cornerRadius: 8,
      callbacks: {
        label: (ctx: any) => {
          const total = ctx.dataset.data.reduce((a: number, b: number) => a + b, 0)
          const pct = ((ctx.parsed / total) * 100).toFixed(1)
          return `${ctx.label}: ${ctx.parsed} (${pct}%)`
        },
      },
    },
  },
  animation: { animateRotate: true, duration: 1000 },
}))

const emit = defineEmits<{ click: [{ index: number; label: string; value: number }] }>()

function handleClick(e: any) {
  const points = e.chart.getElementsAtEventForMode(e.native, 'index', { intersect: true }, false)
  if (points.length > 0) {
    const idx = points[0].index
    emit('click', { index: idx, label: props.labels[idx], value: props.data[idx] })
  }
}
</script>

<template>
  <div :style="{ height: `${height}px` }" class="w-full flex justify-center">
    <div class="max-w-xs w-full">
      <Doughnut :data="chartData" :options="chartOptions" @click="handleClick" />
    </div>
  </div>
</template>
