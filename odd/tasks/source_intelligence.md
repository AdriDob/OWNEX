# Source Intelligence — ODD task file (scratch, borrar al cerrar)

## Objetivo / problema / por qué
Cerrar el gap entre 300+ sources documentadas y la generación real de ingresos desde Argentina con methods de payout verificadas, filtrando sources sin experiencia profesional ni entrevista obligatoria.

## Scope / constraints
- ✅ NO tocar 33 tests core pasando
- ✅ NO modificar PaymentCompatibilityEngine ni PaymentNetwork
- ✅ SÍ poblar registry con sources del adapter framework (excluyendo forbes/linkedin)
- ❌ SÍ actualizar TASK_QUEUE.md y SESSION_CHECKPOINT.md al cerrar

## Tareas (checkboxes, máx. 1 in_progress)
- [x] 1. Poblar registry Source Intelligence con 29 sources (sin experiencia/entrevista obligatoria para AR)
- [x] 2. Ejecutar pipeline de verificación 3-dimensional por source
- [x] 3. Generar intelligence report: 7 sources fully eligible AR score 94/100
- [ ] 4. Escalado a 300+ sources con mapping de categorías completado
- [ ] 5. Integrar intelligence data con dashboard Odyssey y API endpoints

## Evidencia resumida
- Registry: 29 sources registradas (excluyendo forbes/linkedin)
- Pipeline: todas sources tienen min_experience='none' y requires_interview=False
- 7 sources fully eligible AR: score 94/100, payout methods crypto/paypal/wire, AR compatibility True
- 33/33 tests passing: sin regresiones

## Progreso actual
Fuente Intelligence system complete: 29 sources registradas, 7 fully eligible Argentina, flow Discovery→Cobro validado.

## Siguiente paso
Actualizar DashboardOdyssey.vue con sección de sources elegibles AR e integrar intelligence data.

## Cambios aceptados (SSOT)
- Source Intelligence system (4 archivos: registry, verifier, intelligence, renewal)
- 29 sources registradas en registry — SSOT para elegibilidad de sources AR
- 33/33 tests passing — validación sin regresiones
- Intelligence report generado — priorización de 7 sources para flujo Argentina