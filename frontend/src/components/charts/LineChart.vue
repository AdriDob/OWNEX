<script setup lang="ts">
import { Line } from 'vue-chartjs'
import {
  CategoryScale, Chart as ChartJS, Filler, Legend, LinearScale,
  LineElement, PointElement, Title, Tooltip,
} from 'chart.js'
import { computed } from 'vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface DataSet {
  label: string
  data: number[]
  borderColor?: string
  backgroundColor?: string
  fill?: boolean
  tension?: number
  pointRadius?: number
}

interface Props {
  labels: string[]
  datasets: DataSet[]
  title?: string
  height?: number
  yLabel?: string
  xLabel?: string
  area?: boolean
  showLegend?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: 250,
  area: false,
  showLegend: true,
})

const isDark = computed(() => document.documentElement.classList.contains('dark'))

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.datasets.map((ds, i) => {
    const colors = ['#7c3aed', '#3b82f6', '#22c55e', '#eab308', '#ef4444']
    const borderColor = ds.borderColor || colors[i % colors.length]
    return {
      ...ds,
      borderColor,
      backgroundColor: ds.backgroundColor || (props.area
        ? (isDark.value ? `${borderColor}30` : `${borderColor}20`)
        : 'transparent'),
      fill: ds.fill ?? props.area,
      tension: ds.tension ?? 0.3,
      pointRadius: ds.pointRadius ?? (props.area ? 0 : 3),
      pointHoverRadius: 5,
    }
  }),
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: props.showLegend, labels: { color: isDark.value ? '#c4c7d0' : '#374151', font: { size: 10 } } },
    title: props.title ? { display: true, text: props.title, color: isDark.value ? '#e2e4e9' : '#111827', font: { size: 12 } } : undefined,
    tooltip: {
      backgroundColor: isDark.value ? '#1e2230' : '#fff',
      titleColor: isDark.value ? '#e2e4e9' : '#111827',
      bodyColor: isDark.value ? '#c4c7d0' : '#374151',
      borderColor: isDark.value ? '#2a2e3d' : '#e5e7eb',
      borderWidth: 1,
      cornerRadius: 8,
      mode: 'index' as const,
      intersect: false,
    },
  },
  scales: {
    x: {
      grid: { color: isDark.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)' },
      ticks: { color: isDark.value ? '#7c8299' : '#6b7280', font: { size: 10 } },
      title: props.xLabel ? { display: true, text: props.xLabel, color: isDark.value ? '#7c8299' : '#6b7280' } : undefined,
    },
    y: {
      grid: { color: isDark.value ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)' },
      ticks: { color: isDark.value ? '#7c8299' : '#6b7280', font: { size: 10 } },
      beginAtZero: true,
      title: props.yLabel ? { display: true, text: props.yLabel, color: isDark.value ? '#7c8299' : '#6b7280' } : undefined,
    },
  },
  animation: { duration: 1000, easing: 'easeOutQuart' as const },
  interaction: { intersect: false, mode: 'index' as const },
}))

const emit = defineEmits<{ click: [{ index: number; label: string }] }>()

function handleClick(e: any) {
  const points = e.chart.getElementsAtEventForMode(e.native, 'index', { intersect: true }, false)
  if (points.length > 0) {
    const idx = points[0].index
    emit('click', { index: idx, label: props.labels[idx] })
  }
}
</script>

<template>
  <div :style="{ height: `${height}px` }" class="w-full">
    <Line :data="chartData" :options="chartOptions" @click="handleClick" />
  </div>
</template>
