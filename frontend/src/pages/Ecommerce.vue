<script setup lang="ts">
/**
 * Ecommerce — Droppinglabel + MercadoLibre + IG/WA en una vista.
 * Backend: /api/ecommerce/* (status, products, orders, metrics, sourcing/score).
 * Sin stock propio: proveedor → cliente. Sin credenciales, los adapters
 * reportan no-configurado y la página lo muestra en vez de inventar.
 */
import { onMounted, ref } from 'vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import {
  fetchEcommerceMetrics,
  fetchEcommerceOrders,
  fetchEcommerceProducts,
  fetchEcommerceStatus,
  fetchEcommerceSuppliers,
  fetchSupplierOutreach,
  markSupplierContacted,
  setSupplierOutreachStatus,
  scoreSourcingOffer,
  type EcommerceMetrics,
  type EcommerceOrder,
  type EcommerceProduct,
  type EcommerceStatus,
  type EcommerceSupplier,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref('')
const status = ref<EcommerceStatus | null>(null)
const products = ref<EcommerceProduct[]>([])
const orders = ref<EcommerceOrder[]>([])
const metrics = ref<EcommerceMetrics | null>(null)
const suppliers = ref<EcommerceSupplier[]>([])
const supplierSearch = ref('')
const supplierFilter = ref<'all' | 'pending' | 'contacted' | 'verified'>('all')
const outreachBusy = ref<string | null>(null)
const outreachMsg = ref<Record<string, { body: string; wa_url: string }>>({})

const costInput = ref('20')
const priceInput = ref('60')
const scoreResult = ref<{ verdict: string; margin_pct: number; margin_usd: number; note: string } | null>(null)
const scoreBusy = ref(false)

const usd = (n: number | null | undefined): string => (n != null ? `$${Number(n).toLocaleString('es-AR')}` : '—')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [s, p, o, m, sup] = await Promise.all([
      fetchEcommerceStatus(),
      fetchEcommerceProducts().catch(() => ({ total: 0, products: [] })),
      fetchEcommerceOrders().catch(() => ({ total: 0, orders: [] })),
      fetchEcommerceMetrics(30).catch(() => null),
      fetchEcommerceSuppliers().catch(() => ({ total: 0, suppliers: [] })),
    ])
    status.value = s
    products.value = p.products ?? []
    orders.value = o.orders ?? []
    metrics.value = m
    suppliers.value = sup.suppliers ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error cargando E-commerce'
  } finally {
    loading.value = false
  }
}

async function openContact(s: EcommerceSupplier): Promise<void> {
  outreachBusy.value = s.id
  try {
    const data = await fetchSupplierOutreach(s.id)
    outreachMsg.value[s.id] = { body: data.message.body, wa_url: data.message.wa_url }
    await markSupplierContacted(s.id)
    window.open(data.message.wa_url, '_blank')
    // refresh suppliers to show contacted
    const sup = await fetchEcommerceSuppliers().catch(() => ({ total: 0, suppliers: [] as EcommerceSupplier[] }))
    suppliers.value = sup.suppliers ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'No se pudo abrir WhatsApp'
  } finally {
    outreachBusy.value = null
  }
}

async function copyMsg(s: EcommerceSupplier): Promise<void> {
  try {
    const data = await fetchSupplierOutreach(s.id)
    await navigator.clipboard.writeText(data.message.body)
  } catch {}
}

async function markVerified(s: EcommerceSupplier): Promise<void> {
  try {
    await setSupplierOutreachStatus(s.id, 'verified', 'Validado por usuario')
    const sup = await fetchEcommerceSuppliers().catch(() => ({ total: 0, suppliers: [] as EcommerceSupplier[] }))
    suppliers.value = sup.suppliers ?? []
  } catch {}
}

const filteredSuppliers = () => {
  let list = suppliers.value
  if (supplierFilter.value !== 'all') list = list.filter(x => x.outreach.status === supplierFilter.value)
  if (supplierSearch.value.trim()) {
    const q = supplierSearch.value.toLowerCase()
    list = list.filter(x => x.name.toLowerCase().includes(q) || x.id.toLowerCase().includes(q))
  }
  return list.slice(0, 50)
}

async function doScore(): Promise<void> {
  const cost = Number(costInput.value)
  const price = Number(priceInput.value)
  if (!Number.isFinite(cost) || !Number.isFinite(price) || price <= 0) return
  scoreBusy.value = true
  try {
    scoreResult.value = await scoreSourcingOffer({ cost_usd: cost, sale_price_usd: price })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'No se pudo calcular'
  } finally {
    scoreBusy.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="E-commerce">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">E-commerce</h1>
        <p class="text-sm opacity-70">Droppinglabel + MercadoLibre + IG/WA. Sin stock: proveedor → cliente.</p>
      </div>
      <div class="ml-auto">
        <OwnexButton variant="secondary" size="sm" @click="load">Actualizar</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Cargando e-commerce..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <OwnexCard v-if="status" class="mb-4" variant="highlight">
        <div class="flex flex-wrap items-center gap-4 text-sm">
          <div><span class="opacity-60">Productos:</span> <strong>{{ status.products }}</strong></div>
          <div><span class="opacity-60">Activos:</span> <strong>{{ status.active_products }}</strong></div>
          <div><span class="opacity-60">Órdenes:</span> <strong>{{ status.orders }}</strong></div>
          <div><span class="opacity-60">Pendientes:</span> <strong>{{ status.pending_orders }}</strong></div>
          <div><span class="opacity-60">Proveedores:</span> <strong>{{ status.suppliers }}</strong> · <span class="opacity-60">Outreach:</span> <strong>{{ suppliers.filter(s=>s.outreach.status==='contacted').length }} contactados / {{ suppliers.filter(s=>s.outreach.status==='verified').length }} verificados</strong></div>
        </div>
        <div class="mt-2 flex flex-wrap gap-1">
          <OwnexBadge
            v-for="(info, key) in status.adapters"
            :key="key"
            size="xs"
            :variant="info.available ? 'success' : 'default'"
          >
            {{ key }}: {{ info.available ? 'conectado' : 'sin configurar' }}
          </OwnexBadge>
        </div>
      </OwnexCard>

      <!-- 100 Proveedores — outreach 1-click WhatsApp -->
      <OwnexCard class="mb-4">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-base font-semibold">Proveedores (100) — Meli solo, comisión, $0 stock, sin redes</h2>
          <OwnexBadge size="xs" variant="success">{{ suppliers.length }} cargados</OwnexBadge>
          <div class="ml-auto flex flex-wrap items-center gap-2">
            <input v-model="supplierSearch" placeholder="Buscar: Nebbux, perfumes, fútbol..." class="rounded border border-border bg-background px-2 py-1 text-sm w-56" />
            <select v-model="supplierFilter" class="rounded border border-border bg-background px-2 py-1 text-sm">
              <option value="all">Todos</option>
              <option value="pending">Pendientes</option>
              <option value="contacted">Contactados</option>
              <option value="verified">Verificados 🟢</option>
            </select>
          </div>
        </div>
        <p class="mt-1 text-xs opacity-60">1 click = mensaje personalizado por categoría + WhatsApp pre-llenado + tracking automático. Sin razonar: el sistema propone, vos solo enviás. Validá 5 por tanda → sync-catalog → DRAFT → precio VIABLE → Meli.</p>
        <div v-if="suppliers.length===0" class="mt-3 text-sm opacity-60">Sin proveedores. Importá: <code>python scripts/supplier_import.py --csv docs/PROVEEDORES_TRACKING_100.csv --apply</code></div>
        <div v-else class="mt-3 overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border opacity-50">
                <th class="pb-1 text-left">Proveedor</th>
                <th class="pb-1 text-left">Tipo</th>
                <th class="pb-1 text-left">Comisión</th>
                <th class="pb-1 text-left">Estado</th>
                <th class="pb-1 text-left">Acción</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in filteredSuppliers()" :key="s.id" class="border-b border-border/40">
                <td class="py-2"><div class="font-medium">{{ s.name }}</div><div class="font-mono text-xs opacity-60">{{ s.id }} · <a :href="s.website" target="_blank" class="underline">{{ s.website.replace('https://','') }}</a></div></td>
                <td class="py-2 font-mono text-xs">{{ s.type }}</td>
                <td class="py-2 font-mono">{{ s.commission_rate!=null ? (s.commission_rate*100).toFixed(0)+'%' : '—' }}</td>
                <td class="py-2"><OwnexBadge size="xs" :variant="s.outreach.status==='verified' ? 'success' : s.outreach.status==='contacted' ? 'warning' : 'default'">{{ s.outreach.status }}</OwnexBadge></td>
                <td class="py-2">
                  <div class="flex flex-wrap gap-1">
                    <OwnexButton size="xs" variant="primary" :loading="outreachBusy===s.id" @click="openContact(s)">WhatsApp →</OwnexButton>
                    <OwnexButton size="xs" variant="secondary" @click="copyMsg(s)">Copiar</OwnexButton>
                    <OwnexButton v-if="s.outreach.status==='contacted'" size="xs" variant="secondary" @click="markVerified(s)">✓ Verificado</OwnexButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="mt-2 text-xs opacity-60">Mostrando 50 de {{ suppliers.length }}. Usá el buscador para filtrar por categoría (urban, fut, watch, perf, acc).</div>
        </div>
      </OwnexCard>

      <OwnexCard v-if="metrics" class="mb-4">
        <div class="text-xs uppercase opacity-60">Últimos {{ metrics.period_days }} días</div>
        <div class="flex flex-wrap items-center gap-4 text-sm">
          <div><span class="opacity-60">Revenue:</span> <strong>{{ usd(metrics.total_revenue_usd) }}</strong></div>
          <div><span class="opacity-60">Margen:</span> <strong>{{ usd(metrics.total_margin_usd) }}</strong></div>
          <div><span class="opacity-60">Margen %:</span> <strong>{{ metrics.avg_margin_pct.toFixed(1) }}%</strong></div>
          <div><span class="opacity-60">Ticket:</span> <strong>{{ usd(metrics.avg_order_value_usd) }}</strong></div>
        </div>
      </OwnexCard>

      <div class="mb-4 grid gap-4 md:grid-cols-2">
        <OwnexCard>
          <h2 class="mb-2 text-base font-semibold">Calculadora de sourcing</h2>
          <p class="mb-3 text-sm opacity-70">Margen tras fees Meli (~13%) + envío. VIABLE exige ≥25%.</p>
          <div class="flex flex-wrap items-end gap-2">
            <label class="flex flex-col gap-1 text-sm">
              Costo (USD)
              <input v-model="costInput" type="number" min="0" step="0.01" class="rounded border border-border bg-background px-2 py-1" />
            </label>
            <label class="flex flex-col gap-1 text-sm">
              Venta (USD)
              <input v-model="priceInput" type="number" min="0" step="0.01" class="rounded border border-border bg-background px-2 py-1" />
            </label>
            <OwnexButton variant="primary" size="sm" :loading="scoreBusy" @click="doScore">Calcular</OwnexButton>
          </div>
          <div v-if="scoreResult" class="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <OwnexBadge :variant="scoreResult.verdict === 'VIABLE' ? 'success' : scoreResult.verdict === 'THIN' ? 'warning' : 'error'">
              {{ scoreResult.verdict }}
            </OwnexBadge>
            <span class="font-mono">{{ scoreResult.margin_pct }}% · {{ usd(scoreResult.margin_usd) }}</span>
          </div>
        </OwnexCard>

        <OwnexCard>
          <h2 class="mb-2 text-base font-semibold">Órdenes recientes</h2>
          <EmptyState v-if="orders.length === 0" title="Sin órdenes" description="El sync Meli corre cada 15m cuando hay credenciales." />
          <ul v-else class="flex flex-col gap-2">
            <li v-for="o in orders.slice(0, 8)" :key="o.id" class="flex flex-wrap items-center gap-2 rounded border border-border/60 px-3 py-2 text-sm">
              <OwnexBadge size="xs" variant="default">{{ o.marketplace }}</OwnexBadge>
              <strong>{{ o.id }}</strong>
              <span class="ml-auto font-mono">{{ usd(o.total_usd) }}</span>
              <div class="w-full text-xs opacity-60">{{ o.next_action }}</div>
            </li>
          </ul>
        </OwnexCard>
      </div>

      <OwnexCard>
        <h2 class="mb-3 text-base font-semibold">Catálogo</h2>
        <EmptyState v-if="products.length === 0" title="Sin productos" description="Alta por POST /api/ecommerce/products o importá tu catálogo." />
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border opacity-50">
                <th class="pb-1 text-left">SKU</th>
                <th class="pb-1 text-left">Producto</th>
                <th class="pb-1 text-left">Costo</th>
                <th class="pb-1 text-left">Venta</th>
                <th class="pb-1 text-left">Margen</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in products" :key="p.id" class="border-b border-border/40">
                <td class="py-2 font-mono text-xs">{{ p.sku }}</td>
                <td class="py-2"><div class="font-medium">{{ p.name }}</div><div class="text-xs opacity-60">{{ p.category }}</div></td>
                <td class="py-2 font-mono">{{ usd(p.cost_usd) }}</td>
                <td class="py-2 font-mono">{{ usd(p.sale_price_usd) }}</td>
                <td class="py-2 font-mono">{{ p.margin_pct.toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </OwnexCard>
    </template>
  </div>
</template>
