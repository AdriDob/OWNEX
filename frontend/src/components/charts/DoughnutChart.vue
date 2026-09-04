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
  '#00d5ff',
  '#ffffff',
  '#16A34A',
  '#A16207',
  '#00d5ff',
  '#9CA3AF',
  '#14b8a6',
  '#D97706',
  '#9CA3AF',
  '#9CA3AF',
  '#84cc16',
  '#9CA3AF',
  '#a855f7',
  '#d946ef',
  '#0ea5e9',
])

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      data: props.data,
      backgroundColor: props.colors || defaultColors.value.slice(0, props.data.length),
      borderColor: isDark.value ? '#11131f' : '#fff',
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
        color: isDark.value ? '#c4c7d0' : '#374151',
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
          color: isDark.value ? '#e2e4e9' : '#111827',
          font: { size: 12 },
          padding: { bottom: 12 },
        }
      : undefined,
    tooltip: {
      backgroundColor: isDark.value ? '#1e2230' : '#fff',
      titleColor: isDark.value ? '#e2e4e9' : '#111827',
      bodyColor: isDark.value ? '#c4c7d0' : '#374151',
      borderColor: isDark.value ? '#2a2e3d' : '#e5e7eb',
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
