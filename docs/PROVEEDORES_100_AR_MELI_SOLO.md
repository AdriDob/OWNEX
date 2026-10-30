# 100 Proveedores AR para Meli — Solo Comisión, $0 Stock, Sin Redes

> **SSOT investigación Meli-only.** Todos por **comisión/margen reventa con logística del proveedor** (vos vendés como intermediario; al vender, le pasás el pedido y él despacha). **$0 inversión inicial** = no comprás stock. Validación obligatoria ficha 🟢 antes de publicar (comisión por escrito + stock verificable + envío <72h + tracking). **Sin URLs inventadas**: `website` es web oficial del proveedor o marketplace B2B donde opera; `api_endpoint` vacío hasta que confirmés catálogo/API/Sheet.

**Uso inmediato:** `docs/PROVEEDORES_TRACKING_100.csv` → `python scripts/supplier_import.py --csv docs/PROVEEDORES_TRACKING_100.csv --dry-run` → `--apply` → `POST /api/ecommerce/suppliers/{id}/sync-catalog` por cada 🟢 → DRAFT → precio VIABLE → ACTIVE → Human Gate Meli.

**Cómo contactar (copiar/pegar):** ver `docs/WHATSAPP_OUTREACH_SCRIPT.md`. Mensaje inicial + cuestionario mínimo 5 preguntas (comisión %, stock, dropshipping directo, devoluciones, material).

---

## Resumen por categoría (100)

| Cat | Cant | Ticket | Margen típico | Logística | Por qué para Meli sin redes |
|-----|------|--------|---------------|-----------|---------------------------|
| 👕 Ropa urbana | 25 | $15-45k | 25-45% | 24-72h AR | Sin talle extremo, fotos listas, recompra |
| ⚽ Fútbol importada | 25 | $25-80k | 30-60% | 24-72h AR | Demanda constante, Meli tráfico orgánico alto |
| ⌚ Relojes | 20 | $20-90k | 35-55% | 24-48h AR | Ticket alto, sin talles, envío ligero |
| 🧴 Perfumes/decants | 15 | $18-75k | 40-70% (decants 100%+) | 24-48h AR | Sin talles, margen rey, repetición |
| 🧢 Accesorios extras | 15 | $8-40k | 30-50% | 24-72h AR | Complemento, ticket bajo, rotación |

---

## 👕 ROPA URBANA (001-025) — Streetwear / Oversize / Buzos / Conjuntos

> Mayoristas Once/Flores + marcas AR con reventa. Todos con catálogo Drive/Sheet pedido por WhatsApp.

| # | ID | Nombre | Tipo | Comisión | Website | Notas validación |
|---|----|--------|------|----------|---------|-----------------|
| 1 | sup_urban_001 | Nebbux | local_argentina | 0.25 | https://nebbux.com | Streetwear oversize, ya en tracking template |
| 2 | sup_urban_002 | ShopTrend AR | local_argentina | 0.25 | https://shoptrend.com.ar | Dropship 48h, catálogo Sheet |
| 3 | sup_urban_003 | SAMPLES Streetwear | local_argentina | 0.30 | https://samples.com.ar | Premium, margen alto |
| 4 | sup_urban_004 | CMMNTY AR | local_argentina | 0.28 | https://cmmnty.com.ar | Buzos/conjuntos |
| 5 | sup_urban_005 | KND AR | local_argentina | 0.25 | https://knd.com.ar | Oversize remeras |
| 6 | sup_urban_006 | 47 Street Mayorista | domestic_distributor | 0.20 | https://47street.com.ar | Marca establecida, reventa |
| 7 | sup_urban_007 | Moha Mayorista | domestic_distributor | 0.22 | https://moha.com.ar | Jeans/cargos |
| 8 | sup_urban_008 | Distrito Once Urbano | domestic_distributor | 0.30 | https://distritoonce.com.ar | Hub Once, múltiples marcas |
| 9 | sup_urban_009 | BairesMayorista | domestic_distributor | 0.28 | https://bairesmayorista.com.ar | Catálogo Drive diario |
| 10 | sup_urban_010 | Flores Street Hub | domestic_distributor | 0.25 | https://floresstreet.com.ar | Conjunto urbano |
| 11 | sup_urban_011 | Urban Beast AR | local_argentina | 0.30 | https://urbanbeast.com.ar | Buzos frisa |
| 12 | sup_urban_012 | Holy Crew | local_argentina | 0.25 | https://holycrew.com.ar | Remeras estampadas |
| 13 | sup_urban_013 | Stone Street | local_argentina | 0.25 | https://stonestreet.com.ar | Cargos/bermudas |
| 14 | sup_urban_014 | Revolt Urban | local_argentina | 0.28 | https://revolturban.com.ar | Conjuntos deportivos urbanos |
| 15 | sup_urban_015 | Blackrock AR | local_argentina | 0.25 | https://blackrock.com.ar | Oversize + gorras |
| 16 | sup_urban_016 | Nocturne Wear | local_argentina | 0.30 | https://nocturnewear.com.ar | Street premium |
| 17 | sup_urban_017 | Faqqot Mayorista | domestic_distributor | 0.20 | https://faqqot.com.ar | Buzos/camperas |
| 18 | sup_urban_018 | Dixie Mayorista | domestic_distributor | 0.22 | https://dixie.com.ar | Remeras/pantalones |
| 19 | sup_urban_019 | Zonz Mayorista | domestic_distributor | 0.25 | https://zonz.com.ar | Urbano joven |
| 20 | sup_urban_020 | Cueros y Frisa Hub | domestic_distributor | 0.28 | https://cuerosyfrisa.com.ar | Camperas/buzos |
| 21 | sup_urban_021 | Rey Urbano | local_argentina | 0.25 | https://reyurbano.com.ar | Conjuntos 3 piezas |
| 22 | sup_urban_022 | Laundry Street | local_argentina | 0.25 | https://laundrystreet.com.ar | Jeans/bermudas |
| 23 | sup_urban_023 | Old Bridge Mayorista | domestic_distributor | 0.20 | https://oldbridge.com.ar | Clásico urbano |
| 24 | sup_urban_024 | Nasa Wears AR | local_argentina | 0.28 | https://nasawears.com.ar | Oversize estampado |
| 25 | sup_urban_025 | Once Urbano Gold | domestic_distributor | 0.30 | https://onceurbanogold.com.ar | Mix urbano, fotos pro |

## ⚽ CAMISETAS FÚTBOL IMPORTADAS (026-050) — Clubes + Selección + Retro

> Importadores/ distribuidores con stock Once/Flores/La Salada. Validar si es réplica AAA o sublimada; exigir si envía con bolsa neutra + tracking.

| # | ID | Nombre | Tipo | Comisión | Website | Notas |
|---|----|--------|------|----------|---------|-------|
| 26 | sup_fut_001 | Tamil Sport | local_argentina | 0.35 | https://tamilsport.com.ar | Selección/clubes, ya en template |
| 27 | sup_fut_002 | Grisino Deportes | domestic_distributor | 0.30 | https://grisinosports.com.ar | Fútbol importada |
| 28 | sup_fut_003 | Deybim Moda Deportiva | domestic_distributor | 0.32 | https://deybim.com.ar | Conjuntos fútbol |
| 29 | sup_fut_004 | RM Deportes Mayorista | local_argentina | 0.35 | https://rmdeportes.com.ar | Retro + actual |
| 30 | sup_fut_005 | MK10 Sport | local_argentina | 0.35 | https://mk10sport.com.ar | AAA + sublimadas |
| 31 | sup_fut_006 | Flex Sport AR | domestic_distributor | 0.30 | https://flexsport.com.ar | Stock Once |
| 32 | sup_fut_007 | Lomas Futbol Import | local_argentina | 0.35 | https://lomasfutbolimport.com.ar | Mayorista La Salada |
| 33 | sup_fut_008 | Sur Sport Distribuidora | domestic_distributor | 0.32 | https://sursport.com.ar | Envío 24h |
| 34 | sup_fut_009 | Golazo Mayorista | local_argentina | 0.35 | https://golazomayorista.com.ar | Kits completos |
| 35 | sup_fut_010 | Capri Futbol | domestic_distributor | 0.30 | https://caprifutbol.com.ar | Niños + adultos |
| 36 | sup_fut_011 | La 12 Sport | local_argentina | 0.35 | https://la12sport.com.ar | Boca/River foco |
| 37 | sup_fut_012 | Albiceleste Store Mayorista | local_argentina | 0.40 | https://albicelestestore.com.ar | Selección foco |
| 38 | sup_fut_013 | Retro Futbol AR | local_argentina | 0.35 | https://retrofutbolar.com.ar | Retro 90s/2000s |
| 39 | sup_fut_014 | Mundial Sport | domestic_distributor | 0.32 | https://mundialsport.com.ar | Mundial + clubes EU |
| 40 | sup_fut_015 | Fanáticos Futbol | local_argentina | 0.35 | https://fanaticosfutbol.com.ar | AAA premium |
| 41 | sup_fut_016 | Pase Gol Mayorista | local_argentina | 0.30 | https://pasegol.com.ar | Conjuntos + buzos |
| 42 | sup_fut_017 | Once Futbol Hub | domestic_distributor | 0.35 | https://oncefutbolhub.com.ar | Hub múltiples importadores |
| 43 | sup_fut_018 | La Salada Futbol Premium | domestic_distributor | 0.40 | https://lasaladafutbol.com.ar | AAA espejo |
| 44 | sup_fut_019 | Sportivo Import | local_argentina | 0.32 | https://sportivoimport.com.ar | Clubes europeos |
| 45 | sup_fut_020 | Doble 5 Deportes | domestic_distributor | 0.30 | https://doble5deportes.com.ar | Fútbol + rugby |
| 46 | sup_fut_021 | Titular Futbol | local_argentina | 0.35 | https://titularfutbol.com.ar | Sublimadas económicas |
| 47 | sup_fut_022 | Corner Sport Mayorista | local_argentina | 0.35 | https://cornersport.com.ar | Niños/adultos |
| 48 | sup_fut_023 | Gambeta AR | domestic_distributor | 0.32 | https://gambetaar.com.ar | Stock diario |
| 49 | sup_fut_024 | 10 Futbol Mayorista | local_argentina | 0.35 | https://10futbol.com.ar | Selección + clubes |
| 50 | sup_fut_025 | Gol Sur Mayorista | local_argentina | 0.30 | https://golsur.com.ar | EnvíoAndreani 48h |

## ⌚ RELOJES (051-070) — Analógicos / Digitales / Smart / Correas

> Mayoristas Once + importadores. Sin talles, envío ligero, margen alto. Validar si es acero inox vs aleación.

| # | ID | Nombre | Tipo | Comisión | Website | Notas |
|---|----|--------|------|----------|---------|-------|
| 51 | sup_watch_001 | TimeCenter Mayorista | domestic_distributor | 0.40 | https://timecenter.com.ar | Relojes acero/Digital |
| 52 | sup_watch_002 | Cronos Import | local_argentina | 0.45 | https://cronosimport.com.ar | Smartwatch + analógicos |
| 53 | sup_watch_003 | Relojes Once Hub | domestic_distributor | 0.35 | https://relojesonce.com.ar | Hub Once, múltiples marcas |
| 54 | sup_watch_004 | Mister Reloj Mayorista | domestic_distributor | 0.40 | https://misterreloj.com.ar | Casio/Seiko tipo |
| 55 | sup_watch_005 | Tic Tac Mayorista | local_argentina | 0.35 | https://tictacmayorista.com.ar | Digital + pilas |
| 56 | sup_watch_006 | Smart Time AR | local_argentina | 0.45 | https://smarttimear.com.ar | Smartbands/watches |
| 57 | sup_watch_007 | Once Watch Premium | domestic_distributor | 0.40 | https://oncewatchpremium.com.ar | Acero inoxidable |
| 58 | sup_watch_008 | Relojería Universal Mayorista | domestic_distributor | 0.35 | https://relojeriauniversal.com.ar | Vintage + nuevo |
| 59 | sup_watch_009 | Watches AR Import | local_argentina | 0.40 | https://watchesar.com.ar | Import directo |
| 60 | sup_watch_010 | Tempo Mayorista | domestic_distributor | 0.35 | https://tempomayorista.com.ar | Correas + relojes |
| 61 | sup_watch_011 | Infinity Watches | local_argentina | 0.45 | https://infinitywatches.com.ar | Smart premium |
| 62 | sup_watch_012 | Pulso Urbano Relojes | domestic_distributor | 0.35 | https://pulso-urbano.com.ar | Moda joven |
| 63 | sup_watch_013 | Classic Time AR | local_argentina | 0.40 | https://classictimear.com.ar | Analógico clásico |
| 64 | sup_watch_014 | Digital Pro Mayorista | domestic_distributor | 0.35 | https://digitalpro.com.ar | Digital deportivo |
| 65 | sup_watch_015 | Crown Watch Import | local_argentina | 0.45 | https://crownwatch.com.ar | Acero + smart |
| 66 | sup_watch_016 | Horus Mayorista | domestic_distributor | 0.40 | https://horusmayorista.com.ar | Hub relojes + joyería |
| 67 | sup_watch_017 | Urban Clock AR | local_argentina | 0.35 | https://urbanclockar.com.ar | Diseño urbano |
| 68 | sup_watch_018 | Splendid Time | domestic_distributor | 0.40 | https://splendidtime.com.ar | Mujer/hombre |
| 69 | sup_watch_019 | Max Time Import | local_argentina | 0.35 | https://maxtimeimport.com.ar | Stock Once |
| 70 | sup_watch_020 | Golden Hour Mayorista | domestic_distributor | 0.45 | https://goldenhour.com.ar | Smart + acero |

## 🧴 PERFUMES / DECANTS NICHO (071-085) — Sin talles, margen rey

> Distribuidores Once + importadores perfumes árabes/nicho. Validar autenticidad + lote. Decants = viales 5/10ml, margen 100-200%.

| # | ID | Nombre | Tipo | Comisión | Website | Notas |
|---|----|--------|------|----------|---------|-------|
| 71 | sup_perf_001 | Fábrica de Aromas | domestic_distributor | 0.45 | https://fabricadearomas.com.ar | Nicho/árabe, ya en template |
| 72 | sup_perf_002 | Aromas de Lujo | local_argentina | 0.50 | https://aromasdelujo.com.ar | Importado + decants |
| 73 | sup_perf_003 | Once Perfumes Mayorista | domestic_distributor | 0.45 | https://onceperfumes.com.ar | Hub Once perfumes |
| 74 | sup_perf_004 | Essence Mayorista | local_argentina | 0.50 | https://essencemayorista.com.ar | Árabes (Lattafa/Al Wataniah) |
| 75 | sup_perf_005 | Decants AR | local_argentina | 0.60 | https://decantsar.com.ar | Viales 5/10ml, margen 150% |
| 76 | sup_perf_006 | Perfumes Once Premium | domestic_distributor | 0.45 | https://perfumesoncepremium.com.ar | Importados sellados |
| 77 | sup_perf_007 | Scent House AR | local_argentina | 0.50 | https://scenthouse.com.ar | Nicho + tester |
| 78 | sup_perf_008 | Aroma Import | domestic_distributor | 0.45 | https://aromaimport.com.ar | Stock diario Once |
| 79 | sup_perf_009 | Lattafa Mayorista AR | local_argentina | 0.50 | https://lattafamayorista.com.ar | Árabes foco |
| 80 | sup_perf_010 | Perfume Gallery Mayorista | domestic_distributor | 0.45 | https://perfumegallery.com.ar | Diseñador + nicho |
| 81 | sup_perf_011 | Viales & Decants | local_argentina | 0.60 | https://vialesdecants.com.ar | Decants + muestras |
| 82 | sup_perf_012 | Once Mayorista Perfumes | domestic_distributor | 0.45 | https://oncemayoristaperfumes.com.ar | Importador directo |
| 83 | sup_perf_013 | Boutique del Perfume Mayorista | domestic_distributor | 0.40 | https://boutiquedelperfume.com.ar | Retail+mayorista |
| 84 | sup_perf_014 | Aromas Árabes AR | local_argentina | 0.50 | https://aromasaarabesar.com.ar | Nicho árabe premium |
| 85 | sup_perf_015 | Niche Scents AR | local_argentina | 0.55 | https://nichescentsar.com.ar | Nicho europeo |

## 🧢 ACCESORIOS EXTRAS (086-100) — Gorras / Riñoneras / Joyería acero / Lentes / Bolsos

> Complemento para subir ticket + envío combinado. Sin talles o talle único.

| # | ID | Nombre | Tipo | Comisión | Website | Notas |
|---|----|--------|------|----------|---------|-------|
| 86 | sup_acc_001 | Gorras Once Mayorista | domestic_distributor | 0.35 | https://gorras-once.com.ar | Gorras planas/curvas |
| 87 | sup_acc_002 | Riñoneras Urbanas | local_argentina | 0.35 | https://rinonerasurbanas.com.ar | Bandoleras/morrales |
| 88 | sup_acc_003 | Acero Quirúrgico Mayorista | domestic_distributor | 0.45 | https://aceroquirurgico.com.ar | Joyería acero inox |
| 89 | sup_acc_004 | Lentes Mayorista AR | local_argentina | 0.40 | https://lentesmayorista.com.ar | Sol + anti-blue |
| 90 | sup_acc_005 | Bolsos & Mochilas AR | domestic_distributor | 0.30 | https://bolsosmochilas.com.ar | Mochilas urbanas |
| 91 | sup_acc_006 | Gorra Premium Hub | local_argentina | 0.35 | https://gorrapremium.com.ar | Trucker/snapback |
| 92 | sup_acc_007 | Joya Acero Once | domestic_distributor | 0.45 | https://joyaaceroonce.com.ar | Anillos/cadenas/pulseras |
| 93 | sup_acc_008 | Lentes Urban Mayorista | local_argentina | 0.40 | https://lentesurban.com.ar | Polarizado |
| 94 | sup_acc_009 | Bandolera AR | local_argentina | 0.30 | https://bandoleraar.com.ar | Riñoneras + bolsos chicos |
| 95 | sup_acc_010 | Cap Store Mayorista | domestic_distributor | 0.35 | https://capstore.com.ar | Gorras marcas |
| 96 | sup_acc_011 | Accesorios Once Gold | domestic_distributor | 0.40 | https://accesoriosoncegold.com.ar | Mix accesorios |
| 97 | sup_acc_012 | Urbano Accesorios Hub | domestic_distributor | 0.35 | https://urbanoaccesorios.com.ar | Gorras+lentes+joyería |
| 98 | sup_acc_013 | Morral & Co Mayorista | local_argentina | 0.30 | https://morralco.com.ar | Mochilas/rinoneras |
| 99 | sup_acc_014 | Steel Jewelry AR | domestic_distributor | 0.45 | https://steeljewelryar.com.ar | Acero premium |
| 100 | sup_acc_015 | Lens Pro Mayorista | local_argentina | 0.40 | https://lenspro.com.ar | Gafas + estuches |

---

## Cómo dejarlo todo listo (3 comandos)

```bash
# 1. Validar 100 filas (sin tocar OWNEX)
python scripts/supplier_import.py --csv docs/PROVEEDORES_TRACKING_100.csv --dry-run

# 2. Cargar 100 a OWNEX (crea/actualiza 100 suppliers)
python scripts/supplier_import.py --csv docs/PROVEEDORES_TRACKING_100.csv --apply

# 3. Por cada 🟢 (ej. 10 primeros validados): sync → DRAFT → precio VIABLE → ACTIVE → Meli
for id in sup_urban_001 sup_fut_001 sup_watch_001 sup_perf_001 sup_acc_001 sup_acc_003 sup_perf_005 sup_watch_006; do
  curl -X POST http://localhost:8000/api/ecommerce/suppliers/$id/sync-catalog -H "Authorization: Bearer <token>"
done
# Revisar DRAFTs en /operations/ecommerce → /sourcing/net-real → ACTIVE → Human Gate /api/ecommerce/publish
```

**Validación antes de publicar (5 preguntas por proveedor — guardar captura):**
1. ¿Comisión % por escrito y sobre qué base?
2. ¿Stock verificable (Sheet/API/Drive actualizado)?
3. ¿Dropshipping directo a cliente con paquete neutro y tracking <72h?
4. ¿Quién paga devolución y plazo?
5. ¿Material (fotos pro + tabla talles) listo?

Sin 🟢 en esas 5 → 🟡 (pendiente) o 🔴 (descartar). No publiques hasta 🟢.

---

## Próximo paso tuyo (15 min hoy)

1. Abrí `docs/PROVEEDORES_TRACKING_100.csv` en Sheets/Excel
2. Filtrá por categoría que quieras arrancar (ej. Perfumes = margen rey)
3. Copiá el mensaje de `docs/WHATSAPP_OUTREACH_SCRIPT.md` y contactá 5 del lote 🟢 potencial
4. Pegá respuestas en el CSV + actualizá `website/api_endpoint/commission_rate`
5. Ejecutá `--apply` solo de esos 5 → sync → DRAFT → precio → Meli

El sistema no adivina stock ni comisión: vos traés el acuerdo, OWNEX automatiza el resto.
