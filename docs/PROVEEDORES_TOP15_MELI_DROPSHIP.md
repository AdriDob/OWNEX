# TOP 15 Proveedores Meli Dropshipping $0 — SIN redes ni videos

> **Estrategia guardada 2026-09-16.** MercadoLibre = tráfico orgánico propio (60M+ compradores/mes AR), sin redes sociales, sin videos: publicás al detalle con fotos pro del proveedor + SEO Meli (título ≤60 chars, keywords, categoría correcta). Filtro aplicado: **comisión ≥45% + envío 24-48h + sin talles** (perfumes/decants/relojes/acero = margen rey, logística ligera, sin devoluciones por talle).

Regla: todo se publica DRAFT-first (`sync-catalog`) → precio VIABLE ≥25% tras fees Meli ~13% (`/sourcing/net-real`) → ACTIVE → Human Gate publish. Validar cada proveedor con las 5 preguntas (comisión por escrito, stock verificable, dropship<72h paquete neutro, devoluciones, fotos) antes de escalar.

---

## Top 15 (por comisión ↑)

| # | ID | Proveedor | Tipo | Comisión | Envío | Por qué gana en Meli |
|---|----|-----------|------|----------|-------|----------------------|
| 1 | `sup_perf_005` | **Decants AR** | local_argentina | **60%** | 24h | Viales 5/10ml = margen 150%+, ticket #1 en perfume, sin talles |
| 2 | `sup_perf_011` | **Viales & Decants** | local_argentina | **60%** | 24h | Decants + muestras, recompra alta |
| 3 | `sup_perf_015` | **Niche Scents AR** | local_argentina | **55%** | 24h | Perfume nicho europeo, diferenciación total (0 competidores iguales) |
| 4 | `sup_perf_002` | **Aromas de Lujo** | local_argentina | 50% | 24h | Importados + decants, fotos pro |
| 5 | `sup_perf_004` | **Essence Mayorista** | local_argentina | 50% | 24h | Árabes (Lattafa/Al Wataniah) — demanda creciente |
| 6 | `sup_perf_007` | **Scent House AR** | local_argentina | 50% | 24h | Nicho + tester, ticket al detalle |
| 7 | `sup_perf_009` | **Lattafa Mayorista AR** | local_argentina | 50% | 24h | Marca árabe con búsqueda real en Meli |
| 8 | `sup_perf_014` | **Aromas Árabes AR** | local_argentina | 50% | 24h | Nicho árabe premium, sin competencia genérica |
| 9 | `sup_watch_002` | **Cronos Import** | local_argentina | 45% | 24h | Smart + analógicos, sin talles, envío ligero |
| 10 | `sup_watch_006` | **Smart Time AR** | local_argentina | 45% | 24h | Smartbands/watches — alto ticket, rotación |
| 11 | `sup_watch_011` | **Infinity Watches** | local_argentina | 45% | 24h | Smart premium, estático → SEO Meli |
| 12 | `sup_watch_020` | **Golden Hour Mayorista** | domestic_distributor | 45% | 24h | Smart + acero, magro al detalle |
| 13 | `sup_acc_003` | **Acero Quirúrgico Mayorista** | domestic_distributor | 45% | 24h | Joyería acero inox, sin talles, fotos brillantes = alto CTR |
| 14 | `sup_acc_007` | **Joya Acero Once** | domestic_distributor | 45% | 24h | Anillos/cadenas/pulseras — upsell cruzado |
| 15 | `sup_acc_014` | **Steel Jewelry AR** | domestic_distributor | 45% | 24h | Acero premium, marca propia con fotos |

---

## Productos sugeridos por nicho (SKUs para sync-catalog)

| Nicho | Producto tipo | Costo/venta estimado (ARS) | Margen neto aprox | Por qué SEO Meli |
|-------|---------------|-----------------------------|--------------------|------------------|
| **Perfume nicho** | Decant 5ml árabe (Lattafa/All Wataniah) | $8-14k / $25-45k | 100-200% | "decant lattafa" es keyword con demanda real; poco volumen ~1 publicación por vendedor |
| **Perfume importado** | Frasco 100ml sellado | $60-120k / $150-280k | 45-60% | Título con marca + "original" + "+ lote" sube conversión |
| **Reloj smart** | Smartwatch acero símil premium | $45-90k / $100-220k | 40-55% | "smartwatch acero + batería + notificaciones" atrae búsqueda; fotos 360° |
| **Reloj analógico** | Crono piel/acerom | $35-70k / $80-160k | 40-55% | "reloj cronógrafo hombre" volumen alto; sin talles |
| **Joyería acero** | Pulsera/ cadena/ anillo acero 316L | $8-20k / $25-55k | 45-60% | "acero quirúrgico no se oxida" = beneficio en tu título |
| **Fútbol + gorra** | Camiseta (sup_fut_001) + gorra combo | $30-60k / $60-110k | 30-45% | Trae tráfico del fútbol (estacional campeonato) y sube ticket |

Cada uno termina en `POST /api/ecommerce/products` (o `sync-catalog` del proveedor) → `/sourcing/net-real` fija precio VIABLE → ACTIVE → Human Gate `/publish`.

---

## Amazon desde Argentina: NO es free (déjalo fuera de $0)

- Cuenta de vendedor requiere **identidad fiscal + banco en país soportado** (AR no está en Seller Central). Necesitarías entidad US (LLC) = inversión + contabilidad.
- Tarifas: $39.99/mes (Professional) o $0.99/venta + listing fees; envío no incluido (FBA exige stock; FBM paga label).
- Dropshipping con proveedor que despacha directo: restringido — tenés que ser vendedor oficial, paquete sin marca del proveedor, devoluciones y atención propias.
- **Decisión**: Amazon queda documentado como "requiere capital + entidad — NO es $0", NO como opción free. Highway: Meli primero; Amazon solo si mañana comprás la estructura.

---

## Cómo arrancar (15 min)

```bash
# 1. Los 15 ya están en OWNEX (de los 100 cargados)
.venv/bin/python -c "from cores.ecommerce.engine import EcommerceEngine; e=EcommerceEngine(); print([s.name for s in e.list_suppliers(active_only=True) if s.commission_rate and float(s.commission_rate)>=0.45][:15])"

# 2. Validar cada uno (5 preguntas) y marcar 🟢
# 3. sync-catalog del proveedor → revisar DRAFTs → /sourcing/net-real → precio VIABLE → ACTIVE → Human Gate Meli
```