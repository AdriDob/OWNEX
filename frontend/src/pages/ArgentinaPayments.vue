<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { DollarSign, ArrowRight, Globe, CreditCard, TrendingUp, AlertCircle, CheckCircle } from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

const exchangeRate = ref(950) // ARS/USD
const cryptoRate = ref(980) // ARS/USDT
const paymentMethods = ref([
  {
    id: 'wise',
    name: 'Wise',
    icon: Globe,
    fee: 0.5,
    time: '1-2 días',
    recommended: true,
  },
  {
    id: 'paypal',
    name: 'PayPal',
    icon: CreditCard,
    fee: 2.5,
    time: 'Instantáneo',
    recommended: false,
  },
  {
    id: 'binance',
    name: 'Binance P2P',
    icon: TrendingUp,
    fee: 0.1,
    time: '10-30 min',
    recommended: true,
  },
])

const recentPayments = ref([
  { id: 1, platform: 'Algora', amount: 500, method: 'Wise', date: '2024-01-15', received: 475000 },
  { id: 2, platform: 'Outlier', amount: 50, method: 'Binance', date: '2024-01-14', received: 49000 },
])

function calculateARS(usd: number, method: string) {
  const methodData = paymentMethods.value.find(m => m.id === method)
  const fee = methodData?.fee || 0
  const afterFee = usd * (1 - fee / 100)
  return afterFee * exchangeRate.value
}

function copyPaymentInfo(text: string) {
  navigator.clipboard.writeText(text)
  toast({
    title: 'Copiado',
    description: 'Información de pago copiada al portapapeles',
  })
}
</script>

<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold text-white mb-2">Cobros Internacionales</h1>
      <p class="text-gray-400">Gestión de pagos desde Argentina a nivel global</p>
    </div>

    <!-- Exchange Rates -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-400">USD → ARS</p>
              <p class="text-2xl font-bold text-white">${{ exchangeRate }}</p>
            </div>
            <DollarSign class="w-8 h-8 text-[#0070d1]" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-400">USDT → ARS</p>
              <p class="text-2xl font-bold text-white">${{ cryptoRate }}</p>
            </div>
            <TrendingUp class="w-8 h-8 text-[#00ff88]" />
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Payment Methods -->
    <Card class="mb-8">
      <CardHeader>
        <CardTitle class="text-white">Métodos de Pago Recomendados</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            v-for="method in paymentMethods"
            :key="method.id"
            class="bg-[#0d1117] border-2 rounded-xl p-4"
            :class="method.recommended ? 'border-[#00ff88]' : 'border-[#0070d1]/30'"
          >
            <div class="flex items-center justify-between mb-4">
              <component :is="method.icon" class="w-8 h-8" :class="method.recommended ? 'text-[#00ff88]' : 'text-[#0070d1]'" />
              <div v-if="method.recommended" class="flex items-center gap-1 text-[#00ff88] text-sm">
                <CheckCircle class="w-4 h-4" />
                Recomendado
              </div>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">{{ method.name }}</h3>
            <div class="space-y-1 text-sm text-gray-400">
              <p>Fee: {{ method.fee }}%</p>
              <p>Tiempo: {{ method.time }}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Calculator -->
    <Card class="mb-8">
      <CardHeader>
        <CardTitle class="text-white">Calculadora de Pagos</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">Monto en USD</label>
            <input
              type="number"
              class="w-full bg-[#0a0a0f] border border-[#0070d1]/30 rounded-lg px-4 py-3 text-white"
              placeholder="100"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-2">Método</label>
            <select class="w-full bg-[#0a0a0f] border border-[#0070d1]/30 rounded-lg px-4 py-3 text-white">
              <option v-for="method in paymentMethods" :key="method.id" :value="method.id">
                {{ method.name }}
              </option>
            </select>
          </div>
        </div>
        <div class="bg-[#0d1117] rounded-lg p-4">
          <p class="text-sm text-gray-400 mb-2">Recibirás en ARS:</p>
          <p class="text-3xl font-bold text-[#00ff88]">$475,000</p>
          <p class="text-sm text-gray-400">USD 500 → ARS (Wise)</p>
        </div>
      </CardContent>
    </Card>

    <!-- Recent Payments -->
    <Card>
      <CardHeader>
        <CardTitle class="text-white">Pagos Recientes</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <div
            v-for="payment in recentPayments"
            :key="payment.id"
            class="bg-[#0d1117] border border-[#0070d1]/30 rounded-lg p-4 flex items-center justify-between"
          >
            <div>
              <p class="font-bold text-white">{{ payment.platform }}</p>
              <p class="text-sm text-gray-400">{{ payment.date }}</p>
            </div>
            <div class="text-right">
              <p class="font-bold text-white">${{ payment.amount }} USD</p>
              <p class="text-sm text-[#00ff88]">${{ payment.received.toLocaleString() }} ARS</p>
            </div>
            <div class="text-right">
              <p class="text-sm text-gray-400">{{ payment.method }}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
