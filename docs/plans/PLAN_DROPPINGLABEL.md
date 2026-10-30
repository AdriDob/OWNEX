# Plan 0-100: Droppinglabel (OWnex Multi-Dev Tool)

## Visión General
**Droppinglabel** = Marca paraguas para múltiples líneas de producto bajo una sola marca, operando como **multi-development tool for public software tasks** + e-commerce sin stock.

### Modelo
- **Canal principal**: Instagram + WhatsApp Business + Facebook Page/Shop
- **Modelo**: Comisión / Dropshipping / Margen propio (sin stock propio)
- **Categorías**: Perfumes/Decants (principal), Ropa deportiva/urbana, Accesorios/Relojes
- **Automatización**: OWNEX gestiona proveedores, pedidos, márgenes, sync Meli

---

## Fase 0: Fundación (Semana 1)

### Semana 1: Fundación de Marca
| Día | Acción | Entregable |
|-----|--------|------------|
| Día 1 | Naming + Logo + Paleta + Tipografía | Brand kit completo (logo SVG/PNG, paleta, tipografía, assets IG) |
| Día 2 | Instagram Business + WhatsApp Business + FB Page | Cuentas creadas, vinculadas, verificadas |
| Día 3 | Landing page simple (Carrd/Notion/Carrd.co) | Landing con bio, linktree, catálogo preview |
| Día 4 | WhatsApp Business API / Meta Business Suite | Cuenta verificada, plantillas mensajes, catálogo |
| Día 5 | Facebook Page + Shop / Instagram Shopping | Tienda conectada, catálogo sincronizado |
| Día 6 | Google Sheets / Notion / Airtable (CRM + Proveedores + Pedidos) | CRM operativo |
| Día 7 | Revisión + Ajustes + Backup | Checkpoint Semana 1 ✅ |

### Assets Base (Crear en Figma/Canva - Gratis)
- [ ] Logo (SVG, PNG 512, 256, 128, 64, favicon)
- [ ] Logo variants: Horizontal, Vertical, Icono, Avatar, Favicon
- [ ] Paleta: Primario, Secundario, Acento, Neutros, Estados
- [ ] Tipografía: Display, Body, Mono (Google Fonts - gratis)
- [ ] Highlight Covers IG (6-8) - 1080x1920
- [ ] Reels Covers Template (consistente)
- [ ] Story Templates (3-5): Nuevo, Encuesta, Countdown, Q&A, Behind scenes
- [ ] Post Templates: Hero, Carousel, Quote, Producto
- [ ] Story Templates: Nuevo, Encuesta, Countdown, Q&A, Behind scenes
- [ ] Packaging/Sticker/Tag designs (para packaging físico futuro)

---

## Fase 1: Proveedores & Productos (Semanas 2-4)

### Semana 2: Investigación Proveedores (Catálogo 15-20 proveedores)

| Categoría | Proveedores Objetivo | Acción |
|-----------|---------------------|--------|
| Perfumes/Decants | 3-5 | Contactar Fábrica de Aromas, Aromas de Lujo, Once Mayorista, proveedores nicho |
| Ropa Deportiva | 3-5 | SAMPLES, CMMNTY, mayoristas deportivos |
| Ropa Urbana/Streetwear | 3-5 | Mayoristas streetwear, CMMNTY, Flex Sport |
| Accesorios/Relojes | 2-3 | Mayoristas accesorios, relojes, gorras |

**Plantilla contacto WhatsApp** (ver `docs/WHATSAPP_OUTREACH_SCRIPT.md`)

**Checklist por proveedor:**
- [ ] Comisión/Margen por escrito
- [ ] Dropshipping confirmado (envío directo, neutro, tracking)
- [ ] Stock real verificable (API/Sheets/WhatsApp)
- [ ] Fotos/Videos/Descripciones/Talles proporcionados
- [ ] Devoluciones/Cambios claros (quién paga, plazos)
- [ ] Fotos/Videos/Descripciones/Talles proporcionados
- [ ] Confiabilidad: 🟢/🟡/🔴

**Herramienta**: Google Sheets `docs/PROVEEDORES_TRACKING_TEMPLATE.csv` + `docs/PROVEEDORES_RESEARCH_TEMPLATE.md`

### Semana 3: Validación y Primer Catálogo (10-20 productos)

| Paso | Acción | Herramienta |
|------|--------|-------------|
| 1 | Filtrar proveedores 🟢 Viables (mín 3) | Sheet tracking |
| 2 | Negociar comisión/margen + logística | WhatsApp + Email |
| 3 | Solicitar catálogo + fotos + talles + precios | Drive/Sheets |
| 4 | Subir a OWNEX: `POST /suppliers` + `sync-catalog` | API OWNEX |
| 10 | Productos en DRAFT → revisar → precio → ACTIVE | OWNEX UI |
| 15 | Primeras 10-15 publicaciones IG | Meta Business Suite |

**Meta Semana 3**: 10-15 productos vivos en IG + Meli (DRAFT→ACTIVE)

### Semana 4: Lanzamiento Suave (Soft Launch)
- Publicar 3-5 posts + 3 Reels + 10 Stories
- Activar WhatsApp Business + catálogo sincronizado
- Primeras ventas → validar flujo completo (pedido → proveedor → envío → cliente)
- Documentar learnings, ajustar procesos

---

## Fase 2: Escalamiento (Meses 2-3)

### Mes 2: Optimización y Escalado
| Semana | Foco | KPI Target |
|--------|------|------------|
| 5-6 | Optimizar posts/Reels que funcionaron | 10-15% engagement rate |
| 7-8 | Escalar productos ganadores (variantes, bundles) | 50+ productos activos |
| 9-10 | Ads Meta (Product Ads) en ganadores | ROAS > 3x |
| 11-12 | Automatizar: sync pedidos → proveedor → tracking → cliente | 90% automatizado |

### KPIs Semanales (Dashboard OWNEX / Google Sheets)
| Métrica | Target Mes 1 | Target Mes 3 |
|---------|--------------|--------------|
| Seguidores IG | 500 | 2,000 |
| Engagement Rate | >5% | >8% |
| Consultas WhatsApp/semana | 20 | 100 |
| Ventas/semana | 5 | 30 |
| Ticket promedio | $15.000 | $25.000 |
| Margen neto | >30% | >35% |

---

## Fase 3: Automatización OWNEX (Meses 3-6)

### Automatizaciones Objetivo
| Proceso | Automatización | Herramienta |
|---------|----------------|-------------|
| Sync proveedor → catálogo DRAFT | Diario 06:00 | OWNEX Scheduler |
| Pedido → Proveedor (email/WhatsApp/API) | Inmediato post-venta | OWNEX Execution Queue |
| Tracking → Cliente (WhatsApp/Email) | Automático al despacho | WhatsApp API / Email |
| Tracking → Tracking Meli/Andreani/OCA | Webhook / Polling | OWNEX + APIs |
| Facturación AFIP | Diario batch | AFIP SDK / PyAFIP |
| Contabilidad / IVA / Ganancias | Mensual | Contador + Planilla |
| Comisiones proveedores | Mensual (liquidación) | Planilla + Transferencia |

### Stack Técnico (Gratis / Open Source)
| Capa | Herramienta |
|------|-------------|
| Backend | FastAPI (Python) - Ya en OWNEX |
| Frontend | Vue 3 + Vite + Tailwind (ya en OWNEX) |
| DB | SQLite (dev) / PostgreSQL (prod) |
| Queue/Queue | Redis + Celery / Redis Streams |
| Scheduler | APScheduler (ya en OWNEX) |
| Monitoring | Prometheus + Grafana (self-hosted) |
| Logs | Loki + Promtail |
| Deploy | Docker + Docker Compose / Coolify (self-hosted) |
| CI/CD | GitHub Actions / GitLab CI |
| Monitoring | Uptime Kuma / Healthchecks.io |

---

## Checklist Técnico (Definición de Hecho)

### Backend (OWNEX)
- [ ] `SupplierCatalogAdapter` funcional (fetch catálogo proveedor → DRAFT)
- [ ] `sync_supplier_catalog()` idempotente, idempotente
- [ ] `POST /suppliers/{id}/sync-catalog` endpoint funcional
- [ ] `Supplier` model con `commission_rate`, `api_endpoint`, `api_credentials`
- [ ] `SupplierType` incluye categorías necesarias
- [ ] `MeliAdapter.publish_item` prepara payload (Human Gate)
- [ ] `MeliAdapter.list_orders_recent` sync 15min
- [ ] `OrderOrchestrator.next_action` devuelve acción correcta
- [ ] `SourcingEngine.score_supplier_offer` calcula margen real
- [ ] `OrderOrchestrator.next_action` devuelve acción correcta

### Frontend (OWNEX Dashboard)
- [ ] Página Proveedores (CRUD + Sync Catalog)
- [ ] Página Productos (DRAFT → ACTIVE, pricing, margins)
- [ ] Página Pedidos (Estado, Tracking, Acciones)
- [ ] Página Métricas (Revenue, Margen, Conversión, Top Products)
- [ ] Configuración Proveedores (CRUD, Sync, Credenciales Vault)
- [ ] Catálogo Meli (Sync, Health, Métricas)

### Instagram/WhatsApp/Facebook
- [ ] Perfil Business verificado
- [ ] Catálogo sincronizado (Commerce Manager)
- [ ] WhatsApp Business API / Cloud API configurado
- [ ] Plantillas mensajes aprobadas (HSM)
- [ ] Instagram Shopping habilitado
- [ ] Facebook Shop sincronizado
- [ ] Pixel/CAPI instalado (eventos: ViewContent, AddToCart, Purchase)

---

## Automatizaciones Gratuitas / Open Source (Prioridad)

| Necesidad | Herramienta | Gratis? |
|-----------|-------------|---------|
| Programación posts | Meta Business Suite / Buffer Free / Postiz (self-hosted) | ✅ |
| Edición Reels | CapCut Desktop / DaVinci Resolve / Shotcut | ✅ |
| Diseño gráfico | Figma / Photopea / Krita / Inkscape | ✅ |
| Imágenes stock | Unsplash / Pexels / Pixabay | ✅ |
| Quitar fondo | Remove.bg (50 gratis/mes) / Photopea | ✅ |
| Upscale | Upscayl (Open Source) | ✅ |
| Compresión video | HandBrake | ✅ |
| Programación posts | Meta Business Suite / Postiz (self-hosted) | ✅ |
| Analytics | Meta Business Suite / Social Blade | ✅ |
| CRM | Google Sheets / Notion / Airtable (gratis) | ✅ |
| Facturación AFIP | PyAFIP / FacturAr (oficial) | ✅ |
| Contabilidad | GnuCash / Ledger / Contador | ✅ |
| Deploy | Docker + Coolify / Portainer | ✅ |
| CI/CD | GitHub Actions | ✅ |
| Monitoreo | Uptime Kuma / Healthchecks.io | ✅ |

---

## Próximos Pasos Inmediatos (Esta Semana)

| Acción | Responsable | Deadline |
|--------|-------------|----------|
| Definir nombre final + registrar dominio | Vos | Hoy |
| Crear brand kit completo (Figma) | Vos | Día 1-2 |
| Crear cuentas IG / FB / WA Business | Vos | Día 1 |
| Contactar 5 proveedores fútbol (template listo) | Vos | Día 1-2 |
| Crear hoja tracking proveedores (Google Sheets) | Vos | Día 1 |
| Enviar mensajes iniciales a 5 proveedores fútbol | Vos | Día 1-2 |
| Completar fichas proveedores (template) | Vos | Día 2-3 |
| Clasificar 🟢/🟡/🔴 + cargar viables en OWNEX | Vos | Día 3-4 |
| Sync catálogo → DRAFT → revisar → precio → ACTIVE | Vos | Día 4-5 |
| Publicar primeros 5 posts + 3 Reels | Vos | Día 6-7 |
| Activar WA Business + Catálogo sincronizado | Vos | Día 7 |
| Primeras ventas → validar flujo completo | Vos | Semana 2 |

---

## Recursos y Links Útiles

### Proveedores Iniciales (Investigar/Contactar)
| Categoría | Proveedores Potenciales |
|-----------|------------------------|
| Perfumes/Decants | Fábrica de Aromas, Aromas de Lujo, Once Mayorista, Aromas de Lujo |
| Ropa Deportiva | SAMPLES, CMMNTY, RM Mayoristas, MK10, Flex Sport |
| Streetwear | SAMPLES, CMMNTY, Workana, Freelancer, Fiverr |
| Accesorios/Relojes | Once Mayorista, Coverr, Pexels, Unidrop, Dropsheable |

### Herramientas Gratis Clave
| Categoría | Herramienta | Link |
|-----------|-------------|------|
| Diseño UI | Figma (Free) | figma.com |
| Edición Reels | CapCut Desktop / DaVinci Resolve | capcut.com / davinci resolve |
| Diseño gráfico | Photopea / Figma / Krita | photopea.com / figma.com |
| Imágenes stock | Unsplash / Pexels / Pixabay | unsplash.com / pexels.com |
| Quitar fondo | remove.bg (50 gratis/mes) / Photopea | remove.bg |
| Upscale | Upscayl (Open Source) | upscayl.org |
| Compresión video | HandBrake | handbrake.fr |
| Programación posts | Meta Business Suite / Postiz (self-hosted) | business.facebook.com / postiz.com |
| Analytics | Meta Business Suite / Social Blade | business.facebook.com |
| CRM | Google Sheets / Notion / Airtable (gratis) | sheets.google.com |
| Facturación | PyAFIP / FacturAr | github.com/pyafip |
| Deploy | Docker + Coolify | coolify.io |
| CI/CD | GitHub Actions | github.com/features/actions |

---

## Próximos Pasos (Tu Acción Inmediata)

1. **Hoy**: Definir nombre + registrar dominio + crear brand kit (Figma)
2. **Hoy-Mañana**: Crear cuentas IG/FB/WA Business + vincular
3. **Mañana**: Contactar 5 proveedores fútbol (template listo)
4. **Próximos 3 días**: Completar fichas proveedores, clasificar 🟢/🟡/🔴
5. **Próximos 3-5 días**: Cargar viables en OWNEX → Sync → DRAFT → Precio → ACTIVE
6. **Semana 1**: Publicar 5 posts + 3 Reels + 10 Stories
7. **Semana 1-2**: Activar WA Business + Catálogo sincronizado
8. **Semana 2**: Primeras ventas → validar flujo completo

---

> **Nota**: Este plan es vivo. Se actualiza conforme avances. La clave: **validar proveedores ANTES de publicar**. El sistema OWNEX ya está listo para recibir proveedores y sincronizar catálogos. Tu foco ahora: **conseguir proveedores reales, validados, con comisión/logística claras**.