
<template>
  <OwnexCard class="financial-reality-card">
    <CardHeader>
      <CardTitle class="text-white font-mono uppercase tracking-tighter">
        Financial Reality
      </CardTitle>
      <CardDescription class="text-zinc-500 text-xs">
        Verifiable Capital & Pipeline
      </CardDescription>
    </CardHeader>

    <CardContent class="space-y-6">
      <!-- Balance Grid -->
      <div class="grid grid-cols-2 gap-4">
        <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
          <div class="text-zinc-500 text-[10px] uppercase font-bold mb-1">Real Balance</div>
          <div class="text-2xl font-mono text-white leading-none">
            ${{ balance.real_balance.toLocaleString() }}
          </div>
        </div>
        <div class="p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg">
          <div class="text-zinc-500 text-[10px] uppercase font-bold mb-1">Pipeline</div>
          <div class="text-2xl font-mono text-cyan-400 leading-none">
            ${{ balance.pending_pipeline.toLocaleString() }}
          </div>
        </div>
      </div>

      <!-- Pipeline List -->
      <div class="space-y-2">
        <div class="text-zinc-500 text-[10px] uppercase font-bold px-1">Pending Payments</div>
        <div v-if="pipeline.length === 0" class="text-zinc-600 text-xs py-4 text-center italic">
          Pipeline empty. No pending inflows.
        </div>
        <div v-else class="max-h-40 overflow-y-auto space-y-2 pr-2">
          <div v-for="item in pipeline" :key="item.id" 
               class="flex items-center justify-between p-2 bg-zinc-900 border border-zinc-800 rounded text-xs group transition-colors hover:border-cyan-900">
            <div class="flex flex-col">
              <span class="text-zinc-300 font-mono">{{ item.source_id }}</span>
              <span class="text-zinc-600 text-[10px]">{{ formatDate(item.created_at) }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-white font-mono">${{ item.amount }}</span>
              <OwnexButton 
                size="sm" 
                variant="ghost" 
                class="opacity-0 group-hover:opacity-100 transition-opacity"
                @click="confirmPayment(item.id)"
              >
                Confirm
              </OwnexButton>
            </div>
          </div>
        </div>
      </div>
    </CardContent>

    <CardFooter>
      <div class="w-full flex justify-between items-center">
        <div class="text-zinc-500 text-[10px] font-mono">
          Total Expected: <span class="text-zinc-300">${{ balance.total_expected.toLocaleString() }}</span>
        </div>
        <div class="h-1 w-1 bg-cyan-500 rounded-full animate-pulse"></div>
      </div>
    </CardFooter>
  </OwnexCard>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { OwnexCard, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, OwnexButton } from '@/components/ui'
import { api } from '@/lib/api' // Assuming api client exists
import { useToast } from '@/composables/useToast'

const toast = useToast()
const balance = ref({ real_balance: 0, pending_pipeline: 0, total_expected: 0 })
const pipeline = ref([])

async function fetchFinancials() {
  try {
    const balRes = await api.get('/api/financial-truth/balance')
    const pipeRes = await api.get('/api/financial-truth/pipeline')
    balance.value = balRes.data
    pipeline.value = pipeRes.data
  } catch (e) {
    console.error('Financial Reality fetch failed', e)
  }
}

async function confirmPayment(id: string) {
  try {
    await api.post(`/api/financial-truth/payment/${id}/confirm`)
    toast.success('Payment verified and added to Real Balance')
    await fetchFinancials()
  } catch (e) {
    toast.error('Failed to confirm payment')
  }
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString()
}

let interval: any
onMounted(() => {
  fetchFinancials()
  interval = setInterval(fetchFinancials, 30000)
})
onUnmounted(() => clearInterval(interval))
</script>

<style scoped>
.financial-reality-card {
  background: black;
  border: 1px solid #27272a;
}
</style>
