# Plan 0-100: YouTube MPT (solo YouTube)

## Visión General
**Canal YouTube 100% generado con MoneyPrinterTurbo (MPT) local, $0.** Guion (Ollama) → voz (Edge TTS gratis) → video (Pexels/Coverr gratis) → subtítulos → upload manual con aprobación.

**Modelo**: vistas → suscriptores → monetización YPP (largo plazo) + afiliados/descripciones (corto plazo).
**Canal**: por definir (NO usar @estampalo.ig — ese es solo POD promocional de Nova Store).
**Regla $0**: Ollama local + Edge TTS + Pexels/Coverr free. Sin ElevenLabs, sin stock pago.

---

## 0. Requisitos ($0)
| Qué | Herramienta gratis | Estado |
|---|---|---|
| Guion | Ollama local (qwen2.5:3b-instruct vía MPT) | `cores/content_factory/mpt_client.py` |
| Voz | Edge TTS `en-US-GuyNeural` / `es-AR-*` | MPT config |
| Video | Pexels API key gratis / Coverr | `pexels.com/api` |
| Edición | MPT pipeline + CapCut/DaVinci gratis | — |
| Upload | Manual con Human Gate (nunca auto-publicar) | — |

## 1. Fases 0-100
### FASE 0 — Descubrimiento
- Nicho: curiosidad/ciencia/tecnología (alineado a Content Factory existente).
- Formato: Shorts 9:16 ≤60s + largos 16:9 ocasionales del mismo guion.
- Competencia: 5 canales del nicho auditados (frecuencia, duración, CTA).

### FASE 1 — Preparación
- [ ] Pexels API key gratis en MPT config (`cores/content_factory/mpt_client.py`).
- [ ] Definir nombre canal + branding (logo Canva gratis).
- [ ] Crear cuenta YouTube + verificar (teléfono).
- [ ] Bank de 30 temas (`cores/content_factory/topic_bank.py`).

### FASE 2 — Construcción (por video, ~20 min c/u, 90% automático)
1. MPT genera guion (Ollama) → revisar 2 min.
2. MPT genera voz + video + subs → preview.
3. **Human Gate**: aprobar título/descripción/tags/thumbnail.
4. Exportar MP4.

### FASE 3 — Lanzamiento
- Subir manual 1 Short/día 14 días (consistencia > calidad inicial).
- Descripción con links afiliados (Amazon/Meli) + hashtags nicho.
- **Nunca auto-publicar**: upload siempre manual aprobado.

### FASE 4 — Operación (diaria, 30 min)
- Generar 1 video (MPT) → aprobar → subir → responder comentarios 10 min.
- Registrar en OWNEX: video_id, vistas 24h/7d, subs, CTR.

### FASE 5 — Optimización (semanal)
- Retención <30% → hook débil: reescribir primeros 3s.
- CTR <4% → thumbnail/título test A/B.
- Cortar formatos con 0 tracción tras 10 videos.

### FASE 6 — Crecimiento
- 1k subs + 10M Shorts views/90d → aplicar YPP.
- Serie numerada (parte 1/2/3) para binge.
- Reciclar winners a largos 16:9.

### FASE 7+ — Escala/Mantenimiento
- Batch semanal (7 videos domingo) → cola de publicación.
- Solo mantener ritmo + responder comunidad.

## 2. Métricas (por video)
`vistas_24h · vistas_7d · retención_% · CTR · subs_ganados · ingresos_afiliados`

## 3. Reglas no negociables
1. **Upload manual con aprobación.** MPT prepara, humano publica.
2. **$0 siempre.** Si algo pide tarjeta, buscar alternativa gratis primero.
3. **Canal separado de @estampalo.ig.** No mezclar POD con contenido.
4. **Evidencia**: todo video registrado en OWNEX antes de subir.

## 4. Superficie OWNEX
- `cores/content_factory/` (mpt_client, scheduler, service, topic_bank)
- `GET /api/content-factory/*` (status, jobs)
- Human Gate: `POST /api/copilot/approve` antes de publish
