
<template>
  <OwnexCard class="investment-command-card">
    <CardHeader>
      <CardTitle class="text-white font-mono uppercase tracking-tighter">
        Investment Command
      </CardTitle>
      <CardDescription class="text-zinc-500 text-xs">
        Strategist Proposals & Capital Deployment
      </CardDescription>
    </CardHeader>

    <CardContent class="space-y-6">
      <!-- Real Asset Summary -->
      <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
        <div class="flex justify-between items-center mb-3">
          <div class="text-zinc-500 text-[10px] uppercase font-bold">Real-time Assets</div>
          <OwnexButton size="sm" variant="ghost" class="text-[10px]" @click="syncAssets">
            Sync Reality
          </OwnexButton>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div v-for="(amount, asset) in assets" :key="asset" class="flex justify-between text-xs font-mono p-1 border-b border-zinc-800">
            <span class="text-zinc-400">{{ asset }}</span>
            <span class="text-white">{{ amount }}</span>
          </div>
        </div>
      </div>

      <!-- Proposals List -->
      <div class="space-y-3">
        <div class="text-zinc-500 text-[10px] uppercase font-bold px-1">Recommended Strategies</div>
        <div v-if="proposals.length === 0" class="text-zinc-600 text-xs py-4 text-center italic">
          No active proposals. Strategist is analyzing market...
        </div>
        <div v-else class="space-y-3">
          <div v-for="proposal in proposals" :key="proposal.id" 
               class="p-3 bg-zinc-900 border border-zinc-800 rounded-lg group transition-all hover:border-cyan-900">
            <div class="flex justify-between items-start mb-2">
              <div class="text-sm font-mono text-white">{{ proposal.action }}</div>
              <div class="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded">
                {{ proposal.priority }}
              </div>
            </div>
            <div class="text-xs text-zinc-500 mb-4 leading-relaxed">
              {{ proposal.reasoning }}
            </div>
            <div class="flex items-center justify-between gap-4">
              <div class="text-xs font-mono text-zinc-300">
                Expected: <span class="text-white">${{ proposal.expected_yield }}</span>
              </div>
              <OwnexButton 
                size="sm" 
                variant="primary" 
                class="bg-white text-black hover:bg-zinc-200"
                @click="executeProposal(proposal.id)"
              >
                Execute
              </OwnexButton>
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </OwnexCard>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { OwnexCard, CardHeader, CardTitle, CardDescription, CardContent, OwnexButton } from '@/components/ui'
import { api } from '@/lib/api'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const assets = ref({})
const proposals = ref([])

async function syncAssets() {
  try {
    const res = await api.get('/api/financial-truth/sync-assets')
    assets.value = res.data.balances
    toast.success('Balances synchronized with exchanges')
  } catch (e) {
    toast.error('Sync failed')
  }
}

async function fetchProposals() {
  try {
    // We'll use the investment manager's proposal endpoint
    const res = await api.get('/api/investment/proposals')
    proposals.value = res.data
  } catch (e) {
    console.error('Failed to fetch proposals', e)
  }
}

async function executeProposal(id: string) {
  try {
    await api.post(`/api/investment/execute/${id}`, { confirmed: true })
    toast.success('Trade executed successfully')
    await fetchProposals()
    await syncAssets()
  } catch (e) {
    toast.error('Execution failed')
  }
}

onMounted(() => {
  syncAssets()
  fetchProposals()
})
</script>

<style scoped>
.investment-command-card {
  background: black;
  border: 1px solid #27272a;
}
</style>
