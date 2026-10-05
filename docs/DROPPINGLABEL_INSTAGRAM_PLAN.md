# DROPPINGLABEL INSTAGRAM $0 — plan operativo

> Sin stock, sin pauta, sin web. Embudo: **Instagram → WhatsApp → proveedor → cliente**.
> Regla no negociable: **primero venta, después dinero, después escala.**
> Métrica: **NET CASH / HUMAN HOUR** (vender 2×$30k de margen > 10×$5k si lo segundo te come la vida).

## Catálogo (4 líneas, orden de ataque)

| # | Línea | Héroe | Por qué primero |
|---|-------|-------|-----------------|
| 1 | 🕌 Perfumes árabes | Decant 5/10ml de originales + frasco sellado (Lattafa/Armaf/Afnan) | Mejor margen, sin talles, contenido que se vende solo |
| 2 | ⌚ Relojes/accesorios | Smart + acero (ticket alto, sin talles) | Complemento de ticket, logística ligera |
| 3 | ⚽ Fútbol importada | Retro **por encargo** (Flex Sport: 12 días hábiles) | Demanda real; vender como made-to-order, jamás 24-48h |
| 4 | 👕 Urbana | Oversize/remeras | Frecuencia de compra, suma volumen |

Precios orientativos (ejemplos matemáticos, NO cotizaciones): perfume $90-130k (costo $50-70k) ·
camiseta $60-90k (costo $30-50k) · smartwatch $35-60k (costo $10-25k).
Precio real siempre por `/sourcing/net-real` (VIABLE ≥25%).
Bandas en `/sourcing/suggest-price` → `bands`: MÍNIMO (piso 25%) /
COMPETITIVO (95% del rival, UNKNOWN sin rivales) / OBJETIVO (35%) / PREMIUM (50%).
Score 0-10 en `POST /products/{id}/score` (margen 25% + demanda 20% + competencia
15% + rotación 15% + scorecard + ticket, gates $0 duros, UNKNOWN honesto):
PRIORITY ≥7 / CANDIDATE ≥5 / DISCARD.

## Honestidad (cuenta viva > venta rápida)

- Réplica = réplica (AAA/sublimada, descrita tal cual). Nada de "original" falso.
- Decants solo de originales con lote verificable.
- Fotos del proveedor **con permiso**; testimonios solo reales.
- Regla de sistema: `authenticity` en `official|licensed|replica|unknown` —
  `unknown` **bloquea** `POST /products/{id}/optimize` (422) hasta definirlo.
  Verificado en Ecommerce.vue (badge por producto).

## Proveedores (sembrados en OWNEX, todos `verified=False` → gate FUTURE)

| Proveedor | Qué es | Estado real |
|---|---|---|
| Flex Sport Arg | Retro por encargo, CABA | Pedir unitario + despacho a nombre tercero + comisión |
| La Camiseteria | Retro réplicas premium ($70-74k) | Negociar unitario; vender como réplica |
| Mundo Tribuna | Retro/ascenso ($40-42k, 3x2) | Negociar unitario + despacho directo |
| Kingz Camisetas (Córdoba) | Retro + equipos a pedido (~$47k) | Preguntar unitario + tiempos |
| Sublime Sport (Bs.As.) | FÁBRICA sublimado fútbol/básquet/vóley | Vía para línea propia + básquet |
| La Bocha / Mundial Retro / Retro BA | Retro clubes/selección ($54-68k) | Negociar unitario + despacho |
| EFP / Kingz / Sublime | Fútbol personalizado e importado | Proponer reventa: la tienda despacha, vos marketineás |
| Bodacious / VONO / Caos / Beyond / Urbanwear / Mau / Callejero / Drip | Urbana/streetwear (fábricas y tiendas) | Fábricas: revendedor directo; tiendas: propuesta Droppinglabel |
| Canevic (Funes, verificado: canevic.com.ar, margen 40%+, kit $320k) / Fragancias de Oriente / Nilo / SyC / MAX ON | Mayoristas perfumes (leads owner) | Contactar por WA, pedir lista + unitario + despacho directo |
| El Zar (185 árabes + decants, programa mayorista) / Benito (decants 24h) / Ambrosia (305 árabes) / Fragandecants (45.5K IG) / Parfumerie (Lattafa $87-127k) | Perfumerías AR verificadas 200 | Proponer reventa: El Zar primero (ya busca mayoristas) |
| Dropi / Dropsheable / Unidrop / Dropdeal / Caufy / Ventaz | Plataformas | Dropdeal y Caufy full con abono → FUTURE |

Gate automático en `/suppliers` y `/suppliers/ranked` (`zero_capital`):
**🟢 ACTIVE** (verificado, sin capital/abono/mínimo, despacha el proveedor) ·
**🟡 FUTURE** (falta verificar o exige abono/mínimo) · **🔴 REJECTED** (exige capital o despachamos nosotros).
Filtro **"Solo $0 puro"** en Ecommerce.vue = `simple:true` (nada que pagar salvo % por venta;
hoy: Dropsheable, Ventaz, Dropi). Confirmar términos por WA → botón **$0 ✓**
(`POST /suppliers/{id}/verify`) → ACTIVE.

## Fases

1. **3 proveedores buenos** (1 fútbol + 1 perfumes + 1 urbano/accesorios): 5 por nicho contactados por WA con el mensaje IG de OWNEX → 2-3 verificados → `sync-catalog` → DRAFT.
2. **10-20 productos** (margen, ticket, despacho, devoluciones) → precio VIABLE → ACTIVE.
3. **Primera venta** → 4. **3 ventas** → 5. **10 ventas**.
6. OWNEX identifica qué convierte (`portfolio_funnel`, `money_per_human_hour`) y se mata el resto (0 ventas ≥60d → MATAR).

## Contenido $0 (1 post/día + 2-3 historias)

- Perfumes: abrir frasco, top 3 aromas, decant vs sellado.
- Fútbol: look completo, guía de talles (clave en por-encargo), 4×3.
- Relojes: close-up, unboxing, combinado con outfit.
- Captions/hashtags: `POST /products/{id}/cross-list` + `/content-plan` (default instagram).
- 2 perfiles: uno perfumes, uno ropa+relojes. Cierre siempre a WhatsApp Business.
- Kit en OWNEX (`/operations/ecommerce` → tarjeta Kit diseño): brief de formatos,
  flyers con `POST /design/flyer` (foto + precio + CTA, Pillow local),
  pack de 7 días y **cola de publicación** (`/design/queue` + botón Publicado ✓).
  Lindos: Canva gratis · Video: CapCut gratis · Programar todo: Meta Business Suite.

## WhatsApp Business en automático (gratis, nativo)

Configurar una vez en la app (Herramientas →):

- **Mensaje de bienvenida**: "Hola! Gracias por escribir a Droppinglabel 🛍️ Decime qué te gustó (perfume, camiseta o reloj) y te paso precio + stock + envío 👇"
- **Mensaje de ausencia** (fuera de horario): "Te leemos mañana a primera hora! Dejanos tu consulta + tu CP para calcular el envío 📦"
- **Respuestas rápidas**: `/precio` (lista de precios), `/envio` ("Despachamos a todo el país 24-72h, tracking incluido"), `/talle` (tabla de talles), `/pago` ("Aceptamos transferencia y MercadoPago. Se reserva con el pago").
- **Etiquetas**: nuevo / pagado / despachado / entregado (así medís el funnel sin planilla).
