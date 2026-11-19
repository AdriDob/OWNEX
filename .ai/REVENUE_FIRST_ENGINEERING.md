# REVENUE-FIRST ENGINEERING — Directiva Suprema

> Estado: **ACTIVA** · Aprobada por el propietario · 2026-11-19
> Prioridad: superior a cualquier decisión de arquitectura, diseño o expansión funcional.

## 1. Objetivo principal

OWNEX es un sistema operativo personal para generar ingresos reales mediante plataformas externas, tareas remuneradas, desarrollo de software, automatización, recompensas, bounties y actividades económicas verificables.

**El éxito NO se mide por líneas de código, módulos, fuentes registradas, endpoints ni dashboards. Se mide por transformar oportunidades externas en trabajo completado, aceptado y efectivamente cobrado.**

Toda funcionalidad debe justificar cómo contribuye a: descubrir oportunidades reales, conseguir acceso, reducir tiempo hasta trabajo, mejorar probabilidad de aceptación, automatizar ejecución, aumentar tareas completadas, reducir rechazos, acelerar entregas, facilitar cobros/retiros, aumentar ingresos netos, o reducir costos/riesgos. Si no contribuye a eso ni es necesaria para seguridad/estabilidad/mantenimiento → baja prioridad.

## 2. Pipeline end-to-end obligatorio

```
OPORTUNIDAD REAL → PLATAFORMA COMPATIBLE → REGISTRO Y ACCESO → CUENTA CONECTADA
→ TAREA DISPONIBLE → ELEGIBILIDAD CONFIRMADA → TRABAJO PREPARADO
→ EJECUCIÓN ASISTIDA POR IA → TESTS Y VALIDACIÓN → ENTREGA
→ ACEPTACIÓN → RECOMPENSA APROBADA → PAGO → RETIRO → INGRESO NETO VERIFICADO
```

Cada etapa: estado independiente, evidencia, timestamp y motivo de bloqueo. Un recorrido NO está completo por tener solo una etapa implementada.

## 3. Priorización por rentabilidad y viabilidad

Evaluar cada oportunidad por: compatibilidad AR, accesibilidad de registro, posibilidad de conectar cuenta, disponibilidad de tareas, experiencia requerida, dificultad, evaluaciones/entrevistas, idioma, recompensa, tiempo estimado, probabilidad de aceptación, competencia, comisiones, método de cobro, plazo de pago, riesgo de rechazo, esfuerzo de integración.

Métricas: ingreso neto esperado por tarea y por hora, tiempo hasta primer pago, probabilidad de conseguir tarea, probabilidad de aceptación, costo de ejecución, rentabilidad estimada, nivel de confianza.

**Una tarea de USD 40 accesible y ejecutable puede ser mejor que USD 500 con requisitos desconocidos.** Nunca favorecer por recompensa anunciada elevada.

Implementación canónica: `score_opportunity()` / `rank_opportunities()` en `cores/opportunity/live_pipeline.py`.

## 4. Conectores que produzcan trabajo

Priorizar integraciones que entreguen tareas reales. Para cada plataforma documentar: registro, verificación, autenticación, acceso a tareas, info real, preparación, ejecución, entrega, seguimiento de aceptación, cobro, retiro desde Argentina. Integraciones completas antes que catálogo amplio. Fuentes sin API: navegador autorizado, MCP, email o webhooks — siempre respetando ToS.

## 5. Ejecución que ahorre trabajo real

Automatizar (con IA/agentes, dentro de lo permitido): búsqueda, investigación de requisitos, análisis de repos, preparación de entornos, código, tests, corrección de errores, reportes, preparación de entregas, seguimiento, registro de pagos. Medir tiempo ahorrado. **Prohibido**: automatizar acciones prohibidas por plataformas o suplantar verificaciones personales (CAPTCHA, identidad, MFA).

## 6. HIT0 — Primer ingreso como objetivo operativo

Circuito mínimo verificable: plataforma compatible → cuenta conectada → oportunidad vigente → tarea accesible → trabajo completado → entrega real → aceptación externa → pago confirmado → retiro verificable. **No esperar a completar las 1.000 fuentes.** Desarrollo por integraciones verticales completas.

## 7. Métricas de negocio

Dashboard prioriza: oportunidades vigentes/accesibles, tareas disponibles/listas, horas invertidas, completadas, entregadas, tasa de aceptación/rechazo, recompensas aprobadas, pagos pendientes/recibidos, dinero retirado, ingreso neto por hora, tiempo hasta primer pago, costos. **Estimaciones ≠ resultados reales. Ingresos verificados permanecen en USD 0 hasta evidencia externa.**

## 8. Priorización del roadmap

Ante cualquier decisión: ¿consigue trabajo real? ¿conecta cuenta real? ¿obtiene tareas actuales? ¿ejecuta tarea? ¿entrega resultado? ¿cobra? ¿reduce tiempo o mejora aceptación? ¿es necesaria para seguridad/estabilidad? → mayor impacto económico verificable sin comprometer seguridad/integridad.

## 9. Regla anti-simulación

Prohibido presentar como real: conexiones simuladas, cuentas ficticiamente conectadas, tareas inventadas, oportunidades vencidas, saldos ficticios, pagos estimados como recibidos, fetchers que no consultan servicios reales, entregas nunca enviadas, aceptaciones inferidas, rentabilidad de backtests como beneficio.

Toda pantalla debe identificar datos simulados, estimados, cacheados y verificados.

## 10. Criterio final de éxito

Demostrar progresivamente que OWNEX genera ingresos reales con menor intervención manual. Construir, probar, medir, cobrar, mejorar. **La prioridad absoluta es convertir OWNEX en herramienta que produzca resultados económicos verificables.**

### Hitos HIT0

| # | Hito | Resultado exigido |
|---|------|-------------------|
| 1 | Primera cuenta externa conectada | conexión verificada por probe real |
| 2 | Primera tarea real sincronizada | fetch con evidencia |
| 3 | Primera tarea ejecutada desde OWNEX | workspace + código + tests |
| 4 | Primera entrega enviada | submission con evidencia externa |
| 5 | Primera tarea aceptada | estado `accepted` con evidencia |
| 6 | Primer pago recibido | estado `paid` con evidencia de cobro |
| 7 | Primer retiro verificado | funds recibidos en cuenta del usuario |
| 8 | Repetición del ciclo | menor intervención humana por iteración |

### Estrategia

Primero un circuito de ingresos funcional con **3-5 plataformas realmente útiles**; después expandir. Inversiones/trading permanecen como módulos pero **no desplazan el motor de generación de ingresos**. Escalar con evidencia: USD 20 → 100 → 500, no prometer USD 10.000/mes.
