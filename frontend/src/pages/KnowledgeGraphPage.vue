<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  Share2, Search, AlertTriangle, RefreshCw, Network,
  Target, FileText, Activity, DollarSign, ExternalLink,
  Bug, Shield, Globe, Cpu,
} from '@lucide/vue'

interface KGNode {
  id: string; node_type: string; name: string; display_label: string
  properties: Record<string, any>; source: string; created_at: string
}

interface KGEdge {
  id: number; source_id: string; target_id: string; edge_type: string
  weight: number; properties: Record<string, any>
}

interface KGStats {
  total_nodes: number; total_edges: number
  nodes_by_type: Record<string, number>
  edges_by_type: Record<string, number>
}

interface NeighborEntry {
  node: KGNode; edge: { id: number; type: string; weight: number; direction: string }; depth: number
}

const router = useRouter()
const stats = ref<KGStats | null>(null)
const selectedType = ref<string>('')
const searchNode = ref('')
const nodes = ref<KGNode[]>([])
const loading = ref(true)
const error = ref('')

const nodeTypeColors: Record<string, string> = {
  target: 'text-success', program: 'text-success', asset: 'text-intigriti',
  domain: 'text-primary', endpoint: 'text-warning',
  finding: 'text-destructive', report: 'text-gold', reward: 'text-success',
  decision: 'text-accent', technology: 'text-intigriti',
}

const nodeTypeIcons: Record<string, any> = {
  target: Target, program: Target, asset: Shield,
  domain: Globe, endpoint: Activity,
  finding: Bug, report: FileText, reward: DollarSign,
  decision: Activity, technology: Cpu,
}

async function fetchAll() {
  loading.value = true; error.value = ''
  try {
    const [statsRes, nodesRes] = await Promise.allSettled([
      api.get<KGStats>('/core/knowledge/stats'),
      api.get<{ nodes: KGNode[]; count: number }>('/core/knowledge/nodes', { limit: 200 }),
    ])
    if (statsRes.status === 'fulfilled') stats.value = statsRes.value
    if (nodesRes.status === 'fulfilled') nodes.value = nodesRes.value.nodes || []
  } catch (e: any) {
    error.value = e?.message || 'Error loading knowledge graph'
  } finally { loading.value = false }
}

onMounted(fetchAll)

const topNodeTypes = computed(() => {
  if (!stats.value) return []
  return Object.entries(stats.value.nodes_by_type)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
})

const filteredNodes = computed(() => {
  let list = nodes.value
  if (selectedType.value) list = list.filter(n => n.node_type === selectedType.value)
  if (searchNode.value) {
    const q = searchNode.value.toLowerCase()
    list = list.filter(n => n.name.toLowerCase().includes(q) || n.display_label?.toLowerCase().includes(q))
  }
  return list.slice(0, 100)
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between animate-in">
      <div class="space-y-1">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Knowledge Graph</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Intelligence Graph</h1>
        <p class="text-sm text-muted-foreground">Connected entities — targets, findings, reports, and decisions</p>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" @click="fetchAll">Retry</Button>
      </div>
    </template>

    <template v-else>
      <!-- Stats grid -->
      <div v-if="stats" class="grid grid-cols-2 gap-4 sm:grid-cols-4 animate-in">
        <div class="rounded-xl card-base p-4 text-center">
          <p class="font-mono text-[10px] text-muted-foreground tracking-wider">Total Nodes</p>
          <p class="mt-1 text-2xl font-bold font-mono text-foreground">{{ stats.total_nodes }}</p>
        </div>
        <div class="rounded-xl card-base p-4 text-center">
          <p class="font-mono text-[10px] text-muted-foreground tracking-wider">Total Edges</p>
          <p class="mt-1 text-2xl font-bold font-mono text-foreground">{{ stats.total_edges }}</p>
        </div>
        <div class="rounded-xl card-base p-4 text-center">
          <p class="font-mono text-[10px] text-muted-foreground tracking-wider">Node Types</p>
          <p class="mt-1 text-2xl font-bold font-mono text-foreground">{{ Object.keys(stats.nodes_by_type).length }}</p>
        </div>
        <div class="rounded-xl card-base p-4 text-center">
          <p class="font-mono text-[10px] text-muted-foreground tracking-wider">Edge Types</p>
          <p class="mt-1 text-2xl font-bold font-mono text-foreground">{{ Object.keys(stats.edges_by_type).length }}</p>
        </div>
      </div>

      <!-- Node types breakdown -->
      <div v-if="topNodeTypes.length" class="grid grid-cols-2 gap-2 sm:grid-cols-4 animate-in">
        <div v-for="[type, count] in topNodeTypes" :key="type"
          class="flex items-center gap-3 rounded-xl border border-border/40 bg-surface/40 p-3 cursor-pointer transition-all hover:border-primary/30"
          :class="selectedType === type ? 'ring-1 ring-primary/40 border-primary/40' : ''"
          @click="selectedType = selectedType === type ? '' : type">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg" :class="'bg-' + nodeTypeColors[type]?.replace('text-', '') + '/10'">
            <component :is="nodeTypeIcons[type] || Network" class="h-4 w-4" :class="nodeTypeColors[type] || 'text-muted-foreground'" />
          </div>
          <div>
            <p class="text-xs font-semibold text-foreground capitalize">{{ type }}</p>
            <p class="font-mono text-[10px] text-muted-foreground">{{ count }} nodes</p>
          </div>
        </div>
      </div>

      <!-- Search + filter -->
      <div class="flex flex-wrap items-center gap-3 animate-in">
        <div class="relative flex-1 min-w-[200px] max-w-xs">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input v-model="searchNode" placeholder="Search nodes..."
            class="w-full rounded-lg border border-border/60 bg-surface/60 py-2 pl-9 pr-3 text-xs text-foreground" />
        </div>
        <Button variant="outline" size="sm" @click="fetchAll" class="gap-2">
          <RefreshCw class="h-3.5 w-3.5" /> Refresh
        </Button>
      </div>

      <!-- Node list -->
      <div v-if="filteredNodes.length" class="space-y-1.5 animate-in">
        <div v-for="node in filteredNodes" :key="node.id"
          class="flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all hover:bg-surface/30 cursor-pointer"
          @click="router.push(node.node_type === 'finding' ? `/findings/${node.properties?.finding_id || ''}` : node.node_type === 'report' ? `/reports/${node.properties?.report_id || ''}` : node.node_type === 'target' || node.node_type === 'program' ? `/programs/${node.properties?.target_id || node.properties?.program_id || ''}` : undefined)">
          <component :is="nodeTypeIcons[node.node_type] || Network" class="h-3.5 w-3.5 shrink-0" :class="nodeTypeColors[node.node_type] || 'text-muted-foreground'" />
          <span class="flex-1 text-xs text-foreground truncate">{{ node.display_label || node.name }}</span>
          <Badge variant="outline" class="text-[8px]">{{ node.node_type }}</Badge>
          <span class="font-mono text-[9px] text-muted-foreground">{{ new Date(node.created_at).toLocaleDateString() }}</span>
        </div>
      </div>
      <div v-else class="flex flex-col items-center py-10 text-center">
        <Network class="h-8 w-8 text-muted-foreground/50 mb-2" />
        <p class="text-xs text-muted-foreground">No nodes match your filter</p>
      </div>
    </template>
  </div>
</template>
