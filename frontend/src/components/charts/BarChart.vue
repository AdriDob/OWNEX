<script setup lang="ts">
import { BarElement, CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale, Title, Tooltip } from 'chart.js'
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, Filler)

interface DataSet {
  label: string
  data: number[]
  backgroundColor?: string | string[]
  borderColor?: string | string[]
  borderWidth?: number
  borderRadius?: number
}

interface Props {
  labels: string[]
  datasets: DataSet[]
  title?: string
  height?: number
  horizontal?: boolean
  stacked?: boolean
  yLabel?: string
  xLabel?: string
  showLegend?: boolean
  indexAxis?: 'x' | 'y'
}

const props = withDefaults(defineProps<Props>(), {
  height: 250,
  horizontal: false,
  stacked: false,
  showLegend: true,
  indexAxis: 'x',
})

const isDark = computed(() => document.documentElement.classList.contains('dark'))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map((ds) => ({
    ...ds,
    backgroundColor:
      ds.backgroundColor ||
      (isDark.value
        ? [
            'rgba(156, 163, 175,0.7)',
            'rgba(255,255,255,0.7)',
            'rgba(22,163,74,0.7)',
            'rgba(217, 119, 6,0.7)',
            'rgba(0,213,255,0.7)',
          ]
        : [
            'rgba(156, 163, 175,0.6)',
            'rgba(255,255,255,0.6)',
            'rgba(22,163,74,0.6)',
            'rgba(217, 119, 6,0.6)',
            'rgba(0,213,255,0.6)',
          ]),
    borderColor: ds.borderColor || 'transparent',
    borderWidth: ds.borderWidth || 0,
    borderRadius: ds.borderRadius ?? 4,
  })),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: props.horizontal ? ('y' as const) : props.indexAxis,
  plugins: {
    legend: { display: props.showLegend, labels: { color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)', font: { size: 10 } } },
    title: props.title
      ? { display: true, text: props.title, color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-bg-base)', font: { size: 12 } }
      : undefined,
    tooltip: {
      backgroundColor: isDark.value ? 'var(--ownex-bg-elevated)' : 'var(--ownex-text-primary)',
      titleColor: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-bg-base)',
      bodyColor: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)',
      borderColor: isDark.value ? 'var(--ownex-border)' : 'var(--ownex-text-secondary)',
      borderWidth: 1,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      grid: { color: isDark.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)' },
      ticks: { color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)', font: { size: 10 } },
      stacked: props.stacked,
      title: props.xLabel
        ? { display: true, text: props.xLabel, color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)' }
        : undefined,
    },
    y: {
      grid: { color: isDark.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)' },
      ticks: { color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)', font: { size: 10 } },
      stacked: props.stacked,
      beginAtZero: true,
      title: props.yLabel
        ? { display: true, text: props.yLabel, color: isDark.value ? 'var(--ownex-text-secondary)' : 'var(--ownex-text-muted)' }
        : undefined,
    },
  },
  animation: { duration: 800, easing: 'easeOutQuart' as const },
  interaction: { intersect: false, mode: 'index' as const },
}))

function handleClick(e: any) {
  const points = e.chart.getElementsAtEventForMode(e.native, 'index', { intersect: true }, false)
  if (points.length > 0) {
    const idx = points[0].index
    emit('click', { index: idx, label: props.labels[idx] })
  }
}

const emit = defineEmits<{ click: [{ index: number; label: string }] }>()
</script>

<template>
  <div :style="{ height: `${height}px` }" class="w-full">
    <Bar :data="chartData" :options="chartOptions" @click="handleClick" />
  </div>
</template>
