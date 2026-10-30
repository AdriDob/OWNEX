<script setup lang="ts">
import { onMounted, ref, watch, computed, nextTick } from 'vue'
import { FolderOpen, Search, ZoomIn, ZoomOut, RotateCw, Trash2, Plus, Settings, Download, Upload, Minimize2, Maximize2 } from '@lucide/vue'
import { fetchKnowledgeGraphStats, fetchKnowledgeGraphSubgraph, searchKnowledgeGraphNodes, fetchKnowledgeGraphNodes, fetchKnowledgeGraphEdges, type KnowledgeGraphNode, type KnowledgeGraphEdge, type KnowledgeGraphSubgraph } from '@/services/ownexData'

const stats = ref<{ nodes: number; edges: number; node_types: Record<string, number>; relationships: Record<string, number> } | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const selectedNode = ref<KnowledgeGraphNode | null>(null)
const subgraph = ref<KnowledgeGraphSubgraph | null>(null)
const searchQuery = ref('')
const searchResults = ref<KnowledgeGraphNode[]>([])
const showSearch = ref(false)
const cy = ref<cytoscape.Core | null>(null)
const layout = ref<'cose' | 'cola' | 'dagre' | 'circle' | 'grid'>('cose')
const filterTypes = ref<string[]>([])
const filterRelationships = ref<string[]>([])
const showEdgeLabels = ref(false)
const nodeSizeMultiplier = ref(1)
const edgeWidthMultiplier = ref(1)

const availableNodeTypes = computed(() => {
  if (!stats.value) return []
  return Object.keys(stats.value.node_types).sort()
})

const availableRelationships = computed(() => {
  if (!stats.value) return []
  return Object.keys(stats.value.relationships).sort()
})

const filteredNodes = computed(() => {
  if (!subgraph.value) return []
  if (filterTypes.value.length === 0 && filterRelationships.value.length === 0) {
    return subgraph.value.nodes
  }
  return subgraph.value.nodes.filter(n =>
    (filterTypes.value.length === 0 || filterTypes.value.includes(n.type)) &&
    (filterRelationships.value.length === 0 || true)
  )
})

async function loadStats() {
  try {
    const data = await fetchKnowledgeGraphStats()
    stats.value = data
  } catch (e) {
    console.error('Failed to load stats:', e)
  }
}

async function loadSubgraph(nodeId?: string) {
  if (!nodeId) return
  loading.value = true
  error.value = null
  try {
    const data = await fetchKnowledgeGraphSubgraph(nodeId, 2, 100)
    subgraph.value = data
    selectedNode.value = data.nodes.find(n => n.id === nodeId) || null
    renderGraph()
  } catch (e: any) {
    error.value = e.message || 'Failed to load subgraph'
    console.error('Failed to load subgraph:', e)
  } finally {
    loading.value = false
  }
}

async function handleSearch() {
  if (!searchQuery.value.trim()) return
  loading.value = true
  try {
    const data = await searchKnowledgeGraphNodes(searchQuery.value)
    searchResults.value = data
    showSearch.value = true
  } catch (e: any) {
    error.value = e.message || 'Search failed'
  } finally {
    loading.value = false
  }
}

async function selectNode(node: KnowledgeGraphNode) {
  selectedNode.value = node
  showSearch.value = false
  searchQuery.value = ''
  searchResults.value = []
  await loadSubgraph(node.id)
}

async function loadInitialNode() {
  if (!stats.value) await loadStats()
  if (!stats.value) return

  // Try to find a "program" or "opportunity" node as starting point
  const nodes = await fetchKnowledgeGraphNodes({ type: 'program', limit: 1 })
  if (nodes.length > 0) {
    await loadSubgraph(nodes[0].id)
  } else {
    // Fallback: load any node
    const allNodes = await fetchKnowledgeGraphNodes({ limit: 1 })
    if (allNodes.length > 0) {
      await loadSubgraph(allNodes[0].id)
    }
  }
}

function renderGraph() {
  if (!subgraph.value || !cy.value) return

  const elements = [
    ...subgraph.value.nodes.map(n => ({
      data: {
        id: n.id,
        label: n.name,
        type: n.type,
        ...n.properties,
      },
      classes: `node-type-${n.type}`,
    })),
    ...subgraph.value.edges.map(e => ({
      data: {
        id: `${e.source}->${e.target}`,
        source: e.source,
        target: e.target,
        label: e.relationship,
        relationship: e.relationship,
        strength: e.strength,
      },
    })),
  ]

  cy.value.elements().remove()
  cy.value.add(elements)
  cy.value.layout({ name: layout.value, animate: true }).run()
}

function initCytoscape() {
  // Dynamic import to avoid SSR issues
  import('cytoscape').then(({ default: cytoscape }) => {
    import('cytoscape-cose-bilkent').then(() => {
      cytoscape.use(require('cytoscape-cose-bilkent'))
    }).catch(() => {})

    import('cytoscape-dagre').then(() => {
      cytoscape.use(require('cytoscape-dagre'))
    }).catch(() => {})

    cy.value = cytoscape({
      container: document.getElementById('cy'),
      elements: [],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'font-family': 'JetBrains Mono, monospace',
            'background-color': 'mapData(confidence, 0, 1, var(--ownex-accent)40, var(--ownex-accent))',
            'border-width': '1.5px',
            'border-color': 'var(--ownex-accent)',
            'color': 'var(--ownex-text-primary)',
            'text-outline-width': '2px',
            'text-outline-color': 'var(--ownex-bg-deep)',
            'width': 'mapData(confidence, 0, 1, 20, 50)',
            'height': 'mapData(confidence, 0, 1, 20, 50)',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(strength, 0, 1, 1, 4)',
            'line-color': 'var(--ownex-accent)80',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': 'var(--ownex-accent)80',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '8px',
            'color': 'var(--ownex-accent)',
            'text-outline-width': '1px',
            'text-outline-color': 'var(--ownex-bg-deep)',
            'font-family': 'JetBrains Mono, monospace',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': '3px',
            'border-color': 'var(--ownex-accent)',
            'background-color': 'var(--ownex-accent)40',
          },
        },
        {
          selector: '.node-type-program',
          style: { 'background-color': 'var(--ownex-accent)', 'border-color': 'var(--ownex-accent)' },
        },
        {
          selector: '.node-type-opportunity',
          style: { 'background-color': 'var(--ownex-green)', 'border-color': 'var(--ownex-green)' },
        },
        {
          selector: '.node-type-finding',
          style: { 'background-color': 'var(--ownex-accent)', 'border-color': 'var(--ownex-accent)' },
        },
        {
          selector: '.node-type-tag',
          style: { 'background-color': 'var(--ownex-yellow)', 'border-color': 'var(--ownex-yellow)' },
        },
        {
          selector: '.node-type-capability',
          style: { 'background-color': 'var(--ownex-danger)', 'border-color': 'var(--ownex-danger)' },
        },
        {
          selector: '.node-type-user',
          style: { 'background-color': 'var(--ownex-accent)', 'border-color': 'var(--ownex-accent)' },
        },
      ],
      layout: {
        name: layout.value,
        animate: true,
        animationDuration: 500,
        nodeDimensionsIncludeLabels: true,
      },
      minZoom: 0.1,
      maxZoom: 5,
      zoomingEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: true,
    })

    // Event handlers
    cy.value.on('tap', 'node', (evt: any) => {
      const nodeId = evt.target.id()
      if (nodeId) {
        const node = subgraph.value?.nodes.find(n => n.id === nodeId)
        if (node) selectNode(node)
      }
    })

    cy.value.on('tap', 'edge', (evt: any) => {
      // Edge click handler
    })

    cy.value.on('background', () => {
      // Deselect on background click
    })

    // Initial render
    if (subgraph.value) {
      renderGraph()
    }
  }).catch(() => {
    console.error('Failed to load cytoscape')
  })
}

onMounted(async () => {
  await loadStats()
  await loadInitialNode()
  await nextTick()
  initCytoscape()
})

watch(layout, (newLayout) => {
  if (cy.value && subgraph.value) {
    cy.value.layout({ name: newLayout, animate: true }).run()
  }
})

watch(subgraph, () => {
  if (cy.value) {
    renderGraph()
  }
})

function zoomIn() {
  cy.value?.zoom(cy.value.zoom() * 1.2)
}

function zoomOut() {
  cy.value?.zoom(cy.value.zoom() / 1.2)
}

function resetView() {
  if (cy.value) {
    cy.value.fit(null, 50)
  }
}

function centerOnSelected() {
  if (cy.value && selectedNode.value) {
    cy.value.center(cy.value.$id(selectedNode.value.id))
  }
}

function downloadGraph() {
  if (!subgraph.value) return
  const data = {
    nodes: subgraph.value.nodes,
    edges: subgraph.value.edges,
    exported_at: new Date().toISOString(),
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `knowledge-graph-${new Date().toISOString().split('T')[0]}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  showSearch.value = false
}

function clearFilters() {
  filterTypes.value = []
  filterRelationships.value = []
}

function toggleEdgeLabels() {
  if (!cy.value) return
  const style = cy.value.style()
  const edgeStyle = style.selector('edge').style('label')
  edgeStyle.value = showEdgeLabels.value ? 'data(label)' : ''
  cy.value.style(style).update()
}

function exportPNG() {
  if (!cy.value) return
  const png = cy.value.png({ full: true, scale: 2 })
  const a = document.createElement('a')
  a.href = png
  a.download = `knowledge-graph-${new Date().toISOString().split('T')[0]}.png`
  a.click()
}
</script>

<template>
  <div class="kg-explorer h-full flex flex-col">
    <!-- Header -->
    <div class="kg-header flex items-center justify-between p-4 border-b border-[var(--ownex-stroke)] bg-[var(--ownex-surface)]">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold text-[var(--ownex-text)]">Knowledge Graph</h2>
        <span class="text-xs px-2 py-0.5 bg-[var(--ownex-stroke)] text-[var(--ownex-text-muted)] rounded">
          {{ stats?.nodes }} nodes · {{ stats?.edges }} edges
        </span>
      </div>

      <div class="flex items-center gap-2">
        <div class="relative">
          <Search class="absolute left-2 top-1/2 -translate-y-1/2 text-[var(--ownex-text-muted)]" size={16} />
          <input
            v-model="searchQuery"
            @keydown.enter="handleSearch"
            placeholder="Search nodes..."
            class="w-64 pl-8 pr-4 py-1.5 text-sm bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] rounded-lg focus:outline-none focus:border-[var(--ownex-primary)]"
          />
          <button
            v-if="searchQuery"
            @click="clearSearch"
            class="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--ownex-text-muted)] hover:text-[var(--ownex-text)]"
          >
            <Trash2 size={14} />
          </button>
        </div>

        <select
          v-model="layout"
          class="px-3 py-1.5 text-sm bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] rounded-lg focus:outline-none focus:border-[var(--ownex-primary)]"
        >
          <option value="cose">COSE (force-directed)</option>
          <option value="dagre">Dagre (hierarchical)</option>
          <option value="circle">Circle</option>
          <option value="grid">Grid</option>
        </select>

        <button @click="zoomIn" class="p-2 rounded-lg bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] hover:bg-[var(--ownex-stroke)]">
          <ZoomIn size={16} />
        </button>
        <button @click="zoomOut" class="p-2 rounded-lg bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] hover:bg-[var(--ownex-stroke)]">
          <ZoomOut size={16} />
        </button>
        <button @click="resetView" class="p-2 rounded-lg bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] hover:bg-[var(--ownex-stroke)]" title="Fit to view">
          <Maximize2 size={16} />
        </button>
        <button @click="centerOnSelected" class="p-2 rounded-lg bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] hover:bg-[var(--ownex-stroke)]" title="Center on selected">
          <Minimize2 size={16} />
        </button>
        <button @click="downloadGraph" class="p-2 rounded-lg bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] hover:bg-[var(--ownex-stroke)]" title="Export JSON">
          <Download size={16} />
        </button>
        <button @click="exportPNG" class="p-2 rounded-lg bg-[var(--ownex-bg)] border border-[var(--ownex-stroke)] text-[var(--ownex-text)] hover:bg-[var(--ownex-stroke)]" title="Export PNG">
          <FolderOpen size={16} />
        </button>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="p-3 bg-red-500/20 border border-red-500/30 text-red-300 text-sm flex items-center justify-between">
      <span>{{ error }}</span>
      <button @click="error = null" class="text-red-300 hover:text-red-100">✕</button>
    </div>

    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar: Filters & Node Info -->
      <aside class="w-72 flex-shrink-0 border-r border-[var(--ownex-stroke)] bg-[var(--ownex-surface)] flex flex-col">
        <!-- Filters -->
        <div class="p-4 border-b border-[var(--ownex-stroke)]">
          <h3 class="text-xs font-semibold text-[var(--ownex-text-muted)] uppercase tracking-wider mb-3">Filters</h3>

          <div class="space-y-3">
            <div>
              <label class="text-xs text-[var(--ownex-text-muted)] mb-1 block">Node Types</label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="type in availableNodeTypes"
                  :key="type"
                  @click="filterTypes.includes(type) ? filterTypes.splice(filterTypes.indexOf(type), 1) : filterTypes.push(type)"
                  :class="[
                    'px-2 py-1 text-xs rounded border transition-colors',
                    filterTypes.includes(type)
                      ? 'bg-[var(--ownex-primary)] text-[var(--ownex-bg)] border-[var(--ownex-primary)]'
                      : 'bg-[var(--ownex-bg)] text-[var(--ownex-text-muted)] border-[var(--ownex-stroke)] hover:border-[var(--ownex-primary)]'
                  ]"
                >
                  {{ type }} ({{ stats?.node_types[type] || 0 }})
                </button>
              </div>
            </div>

            <div>
              <label class="text-xs text-[var(--ownex-text-muted)] mb-1 block">Relationships</label>
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="rel in availableRelationships"
                  :key="rel"
                  @click="filterRelationships.includes(rel) ? filterRelationships.splice(filterRelationships.indexOf(rel), 1) : filterRelationships.push(rel)"
                  :class="[
                    'px-2 py-1 text-xs rounded border transition-colors',
                    filterRelationships.includes(rel)
                      ? 'bg-[var(--ownex-primary)] text-[var(--ownex-bg)] border-[var(--ownex-primary)]'
                      : 'bg-[var(--ownex-bg)] text-[var(--ownex-text-muted)] border-[var(--ownex-stroke)] hover:border-[var(--ownex-primary)]'
                  ]"
                >
                  {{ rel }} ({{ stats?.relationships[rel] || 0 }})
                </button>
              </div>
            </div>

            <button
              @click="clearFilters"
              :disabled="!filterTypes.length && !filterRelationships.length"
              class="w-full mt-3 px-3 py-1.5 text-xs text-[var(--ownex-text-muted)] bg-transparent border border-[var(--ownex-stroke)] rounded hover:border-[var(--ownex-primary)] hover:text-[var(--ownex-text)] transition-colors disabled:opacity-50"
            >
              Clear Filters
            </button>
          </div>
        </div>

        <!-- Search Results -->
        <div v-if="showSearch && searchResults.length" class="p-4 border-b border-[var(--ownex-stroke)]">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-xs font-semibold text-[var(--ownex-text-muted)] uppercase tracking-wider">Search Results ({{ searchResults.length }})</h3>
            <button @click="clearSearch" class="text-xs text-[var(--ownex-text-muted)] hover:text-[var(--ownex-text)]">Clear</button>
          </div>
          <div class="space-y-1 max-h-48 overflow-y-auto">
            <button
              v-for="node in searchResults"
              :key="node.id"
              @click="selectNode(node)"
              class="w-full text-left p-2 rounded border border-[var(--ownex-stroke)] bg-[var(--ownex-bg)] hover:bg-[var(--ownex-stroke)] transition-colors text-left"
            >
              <div class="flex items-center gap-2">
                <span class="text-xs px-1.5 py-0.5 bg-[var(--ownex-stroke)] text-[var(--ownex-text-muted)] rounded">{{ node.type }}</span>
                <span class="text-sm text-[var(--ownex-text)] truncate">{{ node.name }}</span>
              </div>
            </button>
          </div>
        </div>

        <!-- Selected Node Details -->
        <div v-if="selectedNode" class="p-4 border-b border-[var(--ownex-stroke)] flex-1 overflow-y-auto">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-xs font-semibold text-[var(--ownex-text-muted)] uppercase tracking-wider">Selected Node</h3>
            <button @click="selectedNode = null" class="text-xs text-[var(--ownex-text-muted)] hover:text-[var(--ownex-text)]">Close</button>
          </div>

          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-0.5 bg-[var(--ownex-primary)] text-[var(--ownex-bg)] rounded">{{ selectedNode.type }}</span>
              <span class="text-sm font-medium text-[var(--ownex-text)] truncate">{{ selectedNode.name }}</span>
            </div>

            <div class="text-xs text-[var(--ownex-text-muted)]">
              ID: {{ selectedNode.id }}
            </div>

            <div v-if="Object.keys(selectedNode.properties).length" class="space-y-1">
              <h4 class="text-xs text-[var(--ownex-text-muted)] uppercase tracking-wider">Properties</h4>
              <div v-for="(value, key) in selectedNode.properties" :key="key" class="text-xs text-[var(--ownex-text)]">
                <span class="font-medium">{{ key }}:</span> {{ value }}
              </div>
            </div>

            <div class="pt-2 border-t border-[var(--ownex-stroke)]">
              <button
                @click="loadSubgraph(selectedNode.id)"
                class="w-full px-3 py-2 text-xs font-medium text-[var(--ownex-bg)] bg-[var(--ownex-primary)] rounded hover:bg-[var(--ownex-primary]/90] transition-colors"
              >
                <RotateCw class="inline w-3 h-3 mr-1" /> Explore Neighborhood
              </button>
            </div>
          </div>
        </div>

        <!-- Stats Summary -->
        <div v-if="!selectedNode && stats" class="p-4 border-t border-[var(--ownex-stroke)]">
          <h3 class="text-xs font-semibold text-[var(--ownex-text-muted)] uppercase tracking-wider mb-3">Graph Stats</h3>
          <div class="space-y-2 text-xs">
            <div class="flex justify-between">
              <span class="text-[var(--ownex-text-muted)]">Nodes</span>
              <span class="text-[var(--ownex-text)] font-medium">{{ stats.nodes }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--ownex-text-muted)]">Edges</span>
              <span class="text-[var(--ownex-text)] font-medium">{{ stats.edges }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--ownex-text-muted)]">Node Types</span>
              <span class="text-[var(--ownex-text)] font-medium">{{ Object.keys(stats.node_types).length }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-[var(--ownex-text-muted)]">Relationships</span>
              <span class="text-[var(--ownex-text)] font-medium">{{ Object.keys(stats.relationships).length }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Graph Canvas -->
      <main class="flex-1 relative overflow-hidden bg-[var(--ownex-bg)]">
        <div
          id="cy"
          class="absolute inset-0"
          :style="{ opacity: loading ? 0.5 : 1 }"
        ></div>

        <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-[var(--ownex-bg)]/80 z-10">
          <div class="flex flex-col items-center gap-3 text-[var(--ownex-text-muted)]">
            <div class="w-8 h-8 border-2 border-[var(--ownex-primary)] border-t-transparent rounded-full animate-spin"></div>
            <span>Loading graph...</span>
          </div>
        </div>

        <div v-if="error && !subgraph" class="absolute inset-0 flex items-center justify-center bg-[var(--ownex-bg)]/90 z-10">
          <div class="text-center p-6">
            <div class="text-red-400 mb-2">⚠️</div>
            <p class="text-[var(--ownex-text-muted)]">{{ error }}</p>
            <button
              @click="loadInitialNode"
              class="mt-4 px-4 py-2 text-sm bg-[var(--ownex-primary)] text-[var(--ownex-bg)] rounded hover:bg-[var(--ownex-primary)/90]"
            >
              Try Again
            </button>
          </div>
        </div>

        <!-- Legend -->
        <div class="absolute bottom-4 left-4 z-10 bg-[var(--ownex-surface)] border border-[var(--ownex-stroke)] rounded-lg p-3 text-xs">
          <div class="flex items-center gap-1 mb-1"><span class="w-3 h-3 rounded-full bg-[var(--ownex-accent)]"></span> Program</div>
          <div class="flex items-center gap-1 mb-1"><span class="w-3 h-3 rounded-full bg-[var(--ownex-green)]"></span> Opportunity</div>
          <div class="flex items-center gap-1 mb-1"><span class="w-3 h-3 rounded-full bg-[var(--ownex-accent)]"></span> Finding</div>
          <div class="flex items-center gap-1 mb-1"><span class="w-3 h-3 rounded-full bg-[var(--ownex-yellow)]"></span> Tag</div>
          <div class="flex items-center gap-1 mb-1"><span class="w-3 h-3 rounded-full bg-[var(--ownex-danger)]"></span> Capability</div>
          <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-full bg-[var(--ownex-accent)]"></span> User</div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.kg-explorer {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

#cy {
  width: 100%;
  height: 100%;
}

.kg-header {
  flex-shrink: 0;
}

#cy {
  touch-action: none;
}

/* Cytoscape custom scrollbar */
.cytoscape-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.cytoscape-scrollbar::-webkit-scrollbar-track {
  background: var(--ownex-bg);
}
.cytoscape-scrollbar::-webkit-scrollbar-thumb {
  background: var(--ownex-stroke);
  border-radius: 3px;
}
.cytoscape-scrollbar::-webkit-scrollbar-thumb:hover {
  background: var(--ownex-primary);
}

/* Search results animation */
button:hover {
  transition: all 0.15s ease;
}

/* Filter button active state */
button:focus-visible {
  outline: 2px solid var(--ownex-primary);
  outline-offset: 1px;
}
</style>