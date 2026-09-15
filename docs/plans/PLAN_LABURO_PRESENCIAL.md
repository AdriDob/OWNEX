# Plan 0-100: Laburo Presencial Zona Sur / CABA

## Visión General
**Red de seguridad, NO renta base.** Trabajo presencial zona sur/CABA cuando los canales digitales no cubren el mes. Workspace `backup_income` (LAST_RESORT, nunca auto-rankeado como upside).

**Modelo**: CV/perfil → postulación → entrevista → empleo/ changa → sueldo.
**Regla**: se reporta aparte, jamás se mezcla con EV/h de bounties (distorsiona P(CASH)).

---

## 0. Requisitos ($0)
| Qué | Herramienta gratis |
|---|---|
| CV | Google Docs + PDF, plantilla ATS simple |
| Portfolio | GitHub Pages (el mismo de Adriel Webs) |
| Búsqueda | Zonajobs / Bumeran / Computrabajo (adapters read-only ya en OWNEX) + LinkedIn |
| Tracking | OWNEX `backup_income` workspace + Project OS |

## 1. Fases 0-100
### FASE 0 — Descubrimiento
- Zonas: definir barrios + radio + traslado (tiempo/costo).
- Salario neto/hora mínimo (con traslado incluido) — **nunca postular por debajo**.
- Rubros: soporte IT, desarrollo junior, QA manual, data entry (según perfil).

### FASE 1 — Preparación
- [ ] CV ATS 1 página (skills reales del Profile Kit, sin inventar).
- [ ] Perfil Zonajobs/Bumeran/Computrabajo completos.
- [ ] LinkedIn alineado (titular + experiencia real).
- [ ] Carta presentación plantilla 3 líneas.

### FASE 2 — Búsqueda (diaria, 30 min, solo si se activa)
- Revisar las 3 bolsas (OWNEX adapters read-only agregan).
- Filtrar: zona + neto/hora + modalidad.
- Postular max 5/día con carta adaptada (no spam).

### FASE 3 — Entrevistas
- Preparar: 5 preguntas típicas + demo portfolio.
- Registrar cada entrevista: empresa, puesto, salario ofrecido, estado.
- **Human Gate total**: aceptar oferta = decisión humana, OWNEX solo compara vs neto/hora mínimo.

### FASE 4 — Operación
- Si se acepta: registrar ingreso como `backup_income` (separado).
- No pausar canales digitales salvo que el horario lo exija.

### FASE 5+ — Optimización/Mantenimiento
- Revisar mensualmente si sigue siendo necesario.
- Objetivo: que los canales digitales lo vuelvan innecesario.

## 2. Métricas
`postulaciones · respuestas · entrevistas · ofertas · salario_neto_hora · tiempo_traslado`

## 3. Reglas no negociables
1. **LAST_RESORT**: nunca compite con bounties en el ranking.
2. **Neto/hora con traslado**: oferta bajo el mínimo = reject automático.
3. **Se activa explícitamente** (`allow_last_resort=True`), jamás por defecto.

## 4. Superficie OWNEX
- Workspace `backup_income` + `cores/workspaces/policies.py` (LAST_RESORT)
- Adapters read-only Zonajobs/Bumeran/Computrabajo (sin auto-apply)
- Project OS: registrar como proyecto si se activa
