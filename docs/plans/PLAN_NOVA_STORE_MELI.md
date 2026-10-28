# Plan 0-100: Nova Store - Mercado Libre + Print on Demand

## Visión General
**Nova Store** = Cuenta profesional Mercado Libre enfocada en **dropshipping + Print on Demand**, administrada progresivamente por OWNEX.

**Modelo**: Proveedor → Dropsheable → Mercado Libre → Cliente
**Canal único**: Mercado Libre (sin tienda propia, sin IG inicialmente)
**Automatización**: OWNEX gestiona proveedores, pedidos, márgenes, sync Meli, Ads

---

## 1. Modelo Económico

### Ganancia Real por Venta
```
Precio de venta
− comisión Mercado Libre (categoría + tipo publicación)
− costos de cuotas (si corresponden)
− costo de envío/logística (según peso/dimensiones)
− Costo Dropsheable / Proveedor
− Impuestos / percepciones (IIBB, IVA, percepciones)
− Descuentos / promociones
− Devoluciones / mermas esperadas
= GANANCIA NETA
```

**Regla de oro**: Nunca uses "costo × 1.5". Cada producto se calcula con **Simulador Oficial Mercado Libre**.

### Filtro de Productos (Score 0-100)
| Factor | Puntos |
|--------|--------|
| Ganancia neta | 25 |
| Demanda | 20 |
| Competencia | 15 |
| Stock proveedor | 10 |
| Logística (peso/tamaño) | 10 |
| Calidad contenido | 10 |
| Diferenciación | 10 |
| **TOTAL** | **100** |

**Decisión**:
- 85-100 → PRIORIDAD (Publicar)
- 70-84 → CANDIDATO (Investigar)
- 50-69 → OBSERVAR
- <50 → DESCARTAR

---

## Productos Prioritarios (DropShipping Meli)

### 🥇 Prioridad 1: Accesorios Tecnológicos
- Soportes celular, hubs USB, cables, cargadores
- Soportes notebook/monitor, mouse, teclados, mousepads
- Iluminación USB, accesorios gaming, escritorio

### 🥈 Prioridad 2: Hogar/Organización
- Organizadores, cajas, cables, dispensers, cocina, baño

### 🥉 Prioridad 3: Mascotas
- Cepillos, quitapelos, juguetes, bebederos, comederos

### ❌ EVITAR (Inicio)
- Celulares, notebooks, TVs, frágiles, pesados, talles, garantías complejas, alta devolución

---

## Stack Técnico

| Área | Herramienta |
|------|-------------|
| Canal | Mercado Libre (único) |
| Proveedores | Dropsheable + Proveedores directos |
| Cobros | Mercado Pago |
| Logística | Mercado Envíos / Proveedor compatible |
| Fiscal | ARCA (ex AFIP) |
| Datos | Google Sheets → OWNEX |
| Automatización | OWNEX (scheduler, queue, executors) |
| Publicidad | Mercado Ads (solo sobre ganadores) |
| Marca | **Nova Store** |
| Videos | NO requeridos — estrategia 100% orgánica sin videos (ver abajo) |

---

## Estrategia 100% orgánica y gratis, sin videos (decisión owner 2026-09-15)

> Sin videos, sin pauta inicial, $0. El tráfico es orgánico de Mercado Libre
> (búsqueda + catálogo) + Instagram @estampalo.ig solo POD promocional.

1. **SEO de listing**: título con keywords exactas de búsqueda Meli + ficha completa (atributos, medidas, compatibilidad) + 6-10 fotos proveedor optimizadas (Squoosh).
2. **Precio psicológico + envío**: full vs flex según margen; precio bajo XX.999 en test inicial.
3. **Preguntas <1h**: responder todo en <1h los primeros 30 días (determina reputación/termómetro).
4. **1 producto TEST** (no 30): validar demanda real antes de escalar catálogo.
5. **Mercado Ads SOLO sobre ganadores** con ventas probadas; jamás para descubrir demanda.
6. **POD vía @estampalo.ig**: diseños → DM/WhatsApp → pedido → proveedor imprime/envía; Meli solo para productos con stock proveedor confirmado.
7. **Métricas semanales**: visitas, conversión, preguntas, reputación; cortar <1% conversión tras 200 visitas.

---

## Plan de Acción: 0 a 100

### DÍA 0: Infraestructura
```
NOVA_STORE/
├── 01_ADMIN
├── 02_PROVEEDORES
├── 03_PRODUCTOS
├── 04_MERCADO_LIBRE
├── 05_FINANZAS
├── 06_CONTENIDO
└── 07_OWNEX
```
- Crear cuenta vendedor Meli (profesional)
- Configurar Mercado Pago + Mercado Envíos
- Conectar Dropsheable (revisar proveedores, condiciones, stock)
- Planilla maestra (Google Sheets): Productos, Costos, Márgenes, Stock

---

### DÍA 1: Setup + 30 Candidatos
- Crear cuenta vendedor Meli profesional
- Configurar Dropsheable (revisar proveedores, categorías, condiciones)
- Seleccionar **30 productos candidatos** (filtro score ≥70)

### DÍA 2: Filtrado 30 → 15
Criterios: margen ≥20%, stock estable, logística simple, demanda comprobada

### DÍA 3: Filtrado 15 → 5-10
Calcular cada uno con **Simulador Oficial Mercado Libre**
- Precio mínimo = Costo + ML + Logística + Impuestos + Margen objetivo (≥20%)
- Verificar en simulador oficial

### DÍA 4: Reducir 15 → 5-10
Calcular cada uno en simulador oficial Meli

### DÍA 5: Publicar **1 producto** (TEST)
Primero comprobamos: venta → Dropsheable → proveedor → despacho → tracking → cliente

### DÍA 6
Si todo funciona: publicar 4-9 más

### DÍA 7
Analizar: visitas, preguntas, favoritos, ventas, precio, margen, problemas

---

### MES 1: Objetivo
- **10-30 publicaciones buenas**
- Encontrar **1-3 productos "ganadores"** (ventas constantes + margen)
- Métricas: visitas, preguntas, favoritos, ventas, precio, margen, problemas

### MES 2: Concentración
| Estado | Acción |
|--------|--------|
| 🟥 Malos | Eliminar |
| 🟨 Prometedores | Optimizar (título, fotos, precio, descripción) |
| 🟢 Ganadores | Duplicar esfuerzo (variantes, bundles) |
| 🔥 Estrellas | Ads + variantes + bundles + productos complementarios |

### MES 3: Escala
- Aumentar publicaciones alrededor de categorías ganadoras
- Negociar mejores costos/proveedores
- Aumentar Ads en productos rentables
- Crear bundles, subir ticket, optimizar títulos/fotos/conversión
- Automatizar seguimiento (OWNEX)

---

## Automatización OWNEX (Fase 2)

### Flujo Automatizado Objetivo
```
Mercado Libre (venta)
      ↓
   OWNEX (webhook / polling)
      ↓
   Dropsheable / Proveedor (auto PO)
      ↓
   Proveedor despacha
      ↓
   Tracking → Meli + Cliente (auto)
      ↓
   Entrega → PAID en ledger
      ↓
   OWNEX: reconcilia → aprende → optimiza
```

### Jobs OWNEX Requeridos (Scheduler)
| Job | Frecuencia | Handler |
|-----|------------|---------|
| `meli_order_sync` | */15 min | `cores.ecommerce.pipeline:run_ecommerce_order_sync` |
| `meli_listing_health` | 07:30 daily | `cores.ecommerce.pipeline:run_ecommerce_listing_health` |
| `supplier_catalog_sync` | 06:15 daily | `cores.ecommerce.engine:sync_supplier_catalog` |
| `market_evolution_daily` | 06:30 daily | `cores.cycles.tasks:run_daily_market_evolution` |
| `trading_risk_check` | */5 min | `cores.trading.copy_trading:run_trading_risk_check` |

---

## Stack Definitivo

| Área | Herramienta |
|------|-------------|
| Canal venta | **Mercado Libre** (único) |
| Proveedores | **Dropsheable** + Proveedores directos |
| Cobros | **Mercado Pago** |
| Logística | **Mercado Envíos** / Opción proveedor |
| Fiscal | **ARCA** |
| Datos | Google Sheets → OWNEX |
| Automatización | **OWNEX** (scheduler, queue, executors) |
| Publicidad | **Mercado Ads** (solo ganadores) |
| Marca | **Nova Store** |
| Inventario | Dropsheable / Proveedores |
| Atención | Mercado Libre (mensajería nativa) |
| Tienda propia | ❌ Inicialmente |
| Instagram venta | ❌ (fase 2+) |
| Stock propio | ❌ Inicialmente |

---

## Métricas de Éxito (KPIs)

| Métrica | Mes 1 | Mes 3 | Mes 6 | Mes 12 |
|---------|-------|-------|-------|--------|
| Publicaciones activas | 10-30 | 50-100 | 100-200 | 200+ |
| Ventas/mes | 10-50 | 100-300 | 500-1000 | 1000+ |
| Ganancia neta/mes | $50k-150k | $300k-500k | $1M-2M | $3M+ |
| Margen neto promedio | >20% | >22% | >25% | >25% |
| Tasa devolución | <10% | <8% | <5% | <5% |
| Tiempo despacho | <48h | <24h | <24h | <12h |

---

## Checklist Lanzamiento (Semana 1)

- [ ] Cuenta vendedor Meli profesional verificada
- [ ] Mercado Pago + Mercado Envíos configurados
- [ ] Dropsheable conectado (proveedores, stock, condiciones)
- [ ] 30 productos candidatos → 15 → 5-10 finales
- [ ] 5-10 productos publicados (simulador Meli verificado)
- [ ] 1 venta test completa: venta → Dropsheable → proveedor → despacho → tracking → cliente
- [ ] Planilla maestra Google Sheets (Productos, Costos, Márgenes, Stock, Proveedores)
- [ ] OWNEX conectado (API Meli, Dropsheable, scheduler jobs activos)

---

## Próximos Pasos Inmediatos (Esta Semana)

| Día | Acción |
|-----|--------|
| Hoy | Cuenta Meli Pro + Mercado Pago + Envíos + Dropsheable |
| Mañana | 30 candidatos → filtrar 15 → 10 |
| Mañana+1 | Calcular 10 en simulador Meli → 5-10 finales |
| Mañana+2 | Publicar 1 (TEST) → validar flujo completo |
| Mañana+2 | Si OK: publicar 4-9 más |
| Día 7 | Analizar: visitas, preguntas, favoritos, ventas, precio, margen |

---

> **Regla de Oro**: No publicar 100 productos. Publicar **10 bien calculados**, medir, escalar los ganadores. La máquina de margen se construye producto a producto, no por volumen.