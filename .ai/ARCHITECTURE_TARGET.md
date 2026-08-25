# OWNEX — Arquitectura OBJETIVO (post-1.0-alpha)

> Solo entra aquí lo aprobado explícitamente por el owner. Nada se implementa
> hasta que Alpha 1.0 pase la validación Windows real y el código se congile.

## Fase inmediata (tras clean-install PASS)

1. **Autonomía progresiva del pipeline de ingresos**: OWNEX pasa de "dice qué
   hacer" (NEXT BEST ACTION) a "prepara todo lo preparable" — paquetes de
   entrega, drafts de evaluaciones, tracking post-aplicación — siempre con
   aprobación humana en acciones que violen ToS o envíen datos.
2. **Feedback loop de ingresos reales**: cada outcome (aceptado/pagado/rechazado)
   alimenta acceptance probability por plataforma/categoría (hoy UNKNOWN etiquetado).
3. **Code-signing** del instalador para eliminar SmartScreen.

## Explícitamente FUERA (rechazado o diferido)

- Microservicios, Kubernetes, multiusuario, cloud obligatorio
- Nuevos Work Cycles sin Revenue Rule positiva medible
- Refactor estético del twin core//cores (riesgo > beneficio)

## Criterio de entrada a cualquier cambio post-congelamiento

- Parche: v1.0.1-alpha (bug/security)
- Feature: v1.1.0-alpha (Revenue Rule + owner approval + tests)
