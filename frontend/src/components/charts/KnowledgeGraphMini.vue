<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as d3 from 'd3'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

interface Props {
  class?: string
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  height: 200,
})

const svgRef = ref<SVGSVGElement | null>(null)
const data = ref<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] })
const loading = ref(true)

async function fetchGraphData() {
  loading.value = true
  try {
    const [nodesRes, edgesRes] = await Promise.allSettled([
      api.get<{ nodes: any[] }>('/knowledge-graph/nodes?limit=30'),
      api.get<{ edges: any[] }>('/knowledge-graph/edges?limit=40'),
    ])
    const nodes = (nodesRes.status === 'fulfilled' ? nodesRes.value.nodes : []).map((n: any, i: number) => ({
      id: n.id || `node-${i}`,
      label: n.name || n.type || n.id,
      type: n.type || 'unknown',
    }))
    const edges = (edgesRes.status === 'fulfilled' ? edgesRes.value.edges : []).map((e: any, i: number) => ({
      source: e.source_id || e.source,
      target: e.target_id || e.target,
      type: e.type || 'connected',
    }))
    data.value = { nodes, links: edges }
  } catch {
    // Sin fuente de grafo disponible: empty honesto, nunca datos de muestra.
    data.value = { nodes: [], links: [] }
  }
  loading.value = false
}


const colorMap: Record<string, string> = {
  target: '#a855f7',
  finding: '#f5a623',
  endpoint: '#38bdf8',
  program: '#00ff41',
  cve: '#ff1744',
  report: '#00d5ff',
  unknown: '#6b6b80',
}

watch([svgRef, data], () => {
  if (!svgRef.value || !data.value.nodes.length) return
  renderGraph()
}, { deep: false })

function renderGraph() {
  const el = svgRef.value!
  const width = el.clientWidth || 400
  const height = props.height

  d3.select(el).selectAll('*').remove()

  const svg = d3.select(el)
    .attr('width', width)
    .attr('height', height)

  svg.append('defs').append('filter')
    .attr('id', 'glow')
    .append('feGaussianBlur')
    .attr('stdDeviation', 2)
    .attr('result', 'coloredBlur')

  const simulation = d3.forceSimulation(data.value.nodes as any)
    .force('link', d3.forceLink(data.value.links as any).id((d: any) => d.id).distance(50))
    .force('charge', d3.forceManyBody().strength(-80))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide(15))

  const link = svg.append('g')
    .selectAll('line')
    .data(data.value.links)
    .join('line')
    .attr('stroke', 'rgba(156, 163, 175, 0.15)')
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', '2,2')

  const node = svg.append('g')
    .selectAll('circle')
    .data(data.value.nodes)
    .join('circle')
    .attr('r', 6)
    .attr('fill', (d: any) => colorMap[d.type] || colorMap.unknown)
    .attr('stroke', (d: any) => colorMap[d.type] || colorMap.unknown)
    .attr('stroke-width', 1.5)
    .attr('opacity', 0.8)
    .style('filter', (d: any) => d.type === 'target' ? 'url(#glow)' : 'none')
    .call(d3.drag<any, any>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
      }))

  const labels = svg.append('g')
    .selectAll('text')
    .data(data.value.nodes)
    .join('text')
    .text((d: any) => d.label.length > 10 ? d.label.slice(0, 10) + '…' : d.label)
    .attr('font-size', '7px')
    .attr('dx', 8)
    .attr('dy', 2)
    .attr('fill', 'rgba(255,255,255,0.4)')
    .attr('font-family', 'JetBrains Mono')

  simulation.on('tick', () => {
    link
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y)
    node
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y)
    labels
      .attr('x', (d: any) => d.x)
      .attr('y', (d: any) => d.y)
  })
}

onMounted(fetchGraphData)
</script>

<template>
  <div :class="cn('relative rounded-xl overflow-hidden', props.class)">
    <svg v-if="!loading && data.nodes.length" ref="svgRef" class="w-full" />
    <div v-else-if="loading" class="flex items-center justify-center" :style="{ height: height + 'px' }">
      <div class="flex gap-1">
        <span class="h-1.5 w-1.5 rounded-full bg-primary dot-pulse" />
        <span class="h-1.5 w-1.5 rounded-full bg-primary dot-pulse" />
        <span class="h-1.5 w-1.5 rounded-full bg-primary dot-pulse" />
      </div>
    </div>
    <div v-else class="flex items-center justify-center px-4 text-center" :style="{ height: height + 'px' }">
      <p class="font-mono text-[10px] leading-relaxed text-muted-foreground">
        Grafo de conocimiento no disponible aún — corre un pipeline para generarlo.
      </p>
    </div>
  </div>
</template>
