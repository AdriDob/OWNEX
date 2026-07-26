# ORION Product Principles — Principios de Producto

> Este archivo no es técnico. Define la filosofía de diseño que toda feature, módulo o
> integración debe respetar para que ORION evolucione como un ecosistema coherente,
> no como una colección de módulos.

---

## 1. Sistema único, no colección

ORION no debe sentirse como 20 proyectos separados pegados con cinta. Cada módulo debe compartir lenguaje, diseño, navegación, componentes y filosofía. Si algo no puede integrarse limpiamente, no debe incorporarse.

## 2. Información duplicada cero

Todo dato tiene una sola fuente de verdad. No repetir configuraciones, estados, eventos, contratos, registros o modelos en dos lugares.

## 3. Siempre explicar por qué

ORION nunca debe limitarse a ejecutar. Siempre debe explicar por qué recomienda algo, qué alternativas consideró, qué riesgos identificó y qué pasaría si se toma otro camino.

## 4. Todo módulo controlable desde el dashboard

No existe funcionalidad que solo pueda usarse desde terminal. Si un módulo hace algo útil, debe tener al menos un botón o vista en el frontend.

## 5. Toda automatización debe poder pausarse

El usuario siempre debe poder detener cualquier proceso automatizado sin forzar kills ni perder estado.

## 6. Todo proceso importante genera eventos

Si algo ocurre en el sistema (una ejecución, un error, una decisión, un cambio de estado), debe publicarse como evento en EventBus. No hay procesos silenciosos.

## 7. Todo dato importante queda persistido

Si un dato puede ser útil después de un reinicio, debe estar en SQLite o disco. Nada crítico vive solo en RAM.

## 8. Ninguna integración es una caja negra

Cada integración externa debe exponer al menos: estado de conexión, última sincronización, errores detectados, y logs de actividad. El usuario debe entender qué está pasando puertas adentro.

## 9. La IA propone, el usuario decide (cuando hay riesgo)

Las decisiones de bajo riesgo pueden automatizarse completamente. Las decisiones de alto riesgo (o sin retorno) requieren confirmación humana explícita. ORION debe saber diferenciar.

## 10. Claridad ante todo

El diseño prioriza claridad antes que espectacularidad. Más espacio en blanco > más elementos. Una métrica clara > tres gráficos confusos. Una acción visible > cinco menús anidados.

## 11. Consistencia de nombres

Un mismo concepto tiene un mismo nombre en todo el sistema: en APIs, eventos, contratos, modelos, DTOs, UI, documentación. No hay "User" aquí y "Usuario" allá.

## 12. Cada semana más útil, no más grande

El progreso no se mide en líneas de código ni módulos nuevos. Se mide en: ¿ORION es más rápido, más preciso, más autónomo, más fácil de usar que la semana pasada?

## 13. Sin regresiones

Nunca introducir un cambio que rompa funcionalidad existente. Ruff + tests + tipado + compatibilidad. Siempre. Sin excepción.

## 14. Lo simple es estable, lo estable es rápido, lo rápido es elegante

En ese orden. Nunca al revés. Una solución simple que funciona siempre va a superar a una solución elegante que falla.
