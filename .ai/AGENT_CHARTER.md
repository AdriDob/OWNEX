# Agent Charter — Constitución del Sistema CATEYE

Este documento es la constitución del proyecto. Todos los agentes (OpenCode, Cline, Copilot, futuros) DEBEN leerlo antes de cualquier acción.

## 0. IDENTIDAD DEL SISTEMA

CATEYE no es una aplicación.
CATEYE es un sistema de inteligencia operativa privada para análisis, detección, validación y priorización de oportunidades en bug bounty y seguridad digital.

Su objetivo no es "asistir".
Su objetivo es **producir resultados accionables reales con el mínimo de intervención humana posible.**

El usuario no es operador manual del sistema.
El usuario es **supervisor de decisiones críticas.**

## 1. PRINCIPIO FUNDAMENTAL

El sistema siempre prioriza en este orden:

1. **Seguridad del sistema**
2. **Integridad de datos**
3. **Continuidad operacional**
4. **Resultados reales (findings, validaciones, reportes)**
5. **Optimización / performance**
6. **UX / estética**
7. **Expansión de features**

Ninguna feature puede romper este orden.

## 2. REGLA DE ORO

**Antes de implementar cualquier cambio, debes demostrar con evidencia que esa funcionalidad no existe ya implementada correctamente.**

Si ya existe y está correctamente implementada:
- NO escribir código nuevo
- NO refactorizar
- NO reemplazar
- Actualizar el registro de verificación en COMPLETED_FEATURES.json
- Pasar automáticamente al siguiente objetivo de mayor impacto

## 3. CICLO OBLIGATORIO (VERIFICATION LOOP)

Antes de cualquier acción, el agente DEBE ejecutar este ciclo:

### 3.1 Observar Estado Actual
- Leer `.ai/CURRENT_STATE.md`
- Leer `.ai/COMPLETED_FEATURES.json`
- Escanear código relevante del sistema
- Detectar si la feature ya existe o está parcialmente implementada

### 3.2 Clasificación Obligatoria
Toda tarea debe clasificarse en UNA de estas categorías:
- **NO EXISTE** → implementar desde cero
- **PARCIAL** → extender lo existente sin reemplazar lógica estable
- **COMPLETA** → NO tocar código. Solo verificar y registrar.
- **OBSOLETA** → marcar para eliminación o refactor seguro

### 3.3 Check de Duplicación
Antes de escribir código:
- Buscar implementación existente
- Comparar funcionalidad
- Verificar si ya resuelve el problema

❌ SI EXISTE → NO REIMPLEMENTAR

### 3.4 Decisión de Ejecución
Solo se puede actuar si:
- la feature NO existe
- o está incompleta
- o hay bug verificado

Si está completa → pasar a siguiente tarea automáticamente.

### 3.5 Ejecución Controlada
Durante implementación:
- cambios mínimos necesarios
- no refactorizar sistemas estables
- no reescribir módulos completos sin razón
- mantener compatibilidad total

### 3.6 Verificación Post-Ejecución
Checklist obligatorio:
- [ ] corre en runtime
- [ ] no rompe otros módulos
- [ ] produce output observable
- [ ] pasa flujo end-to-end si aplica
- [ ] persiste si es necesario
- [ ] no introduce duplicación

### 3.7 Restart Test (Crítico)
Si el cambio afecta estado o lógica central:
- reiniciar sistema
- validar comportamiento
- validar persistencia
- comparar con estado previo

❌ FAIL si cambia comportamiento tras restart

### 3.8 Registro Obligatorio
Actualizar uno o más:
- `.ai/CURRENT_STATE.md`
- `.ai/COMPLETED_FEATURES.json`
- `.ai/TASK_QUEUE.md`

Debe incluir: qué se hizo, por qué, evidencia de funcionamiento, impacto en sistema.

### 3.9 Anti-Repetición
Está PROHIBIDO:
- reimplementar features existentes
- mejorar algo sin diagnóstico de fallo
- tocar módulos estables sin motivo
- repetir tareas ya marcadas como DONE

### 3.10 Optimización Inteligente
Si una tarea ya está completa:
→ el agente debe automáticamente:
1. confirmar estabilidad
2. registrar verificación
3. avanzar a siguiente tarea de mayor impacto

## 4. DEFINICIÓN DE "DONE" (DO-DO-OR-DIE)

"Si no puede verificarse, no existe."

### 4.1 Criterio de Funcionalidad Real
Una feature está DONE solo si:
- Se ejecuta sin errores en runtime real
- Produce output observable (UI / API / logs)
- No depende de mocks, stubs o simulaciones
- Está conectada a otros módulos del sistema

❌ FAIL si: código existe pero no se ejecuta, solo pasa tests aislados, está parcialmente conectado

### 4.2 Criterio de Persistencia
Toda feature crítica debe:
- Sobrevivir restart del backend
- Mantener estado consistente

❌ FAIL si: usa solo memoria RAM, pierde datos tras reinicio, requiere reconfiguración manual

### 4.3 Criterio End-to-End
INPUT → PROCESO → OUTPUT
Ejemplo: target creado → scan ejecutado → finding guardado → report generado → visible en UI
❌ FAIL si falta cualquier paso

### 4.4 Criterio de Visibilidad
Todo debe ser verificable por: UI (frontend) / API response / logs estructurados / base de datos
❌ FAIL si existe solo en backend sin exposición

### 4.5 Criterio de Verificación Post-Restart
Después de cada cambio importante: reiniciar, validar funcionamiento, validar datos persistentes
❌ FAIL si solo funciona en sesión actual

### 4.6 Criterio de Integración
Debe conectarse a al menos 1 sistema real (DB / API / UI / pipeline), ser usada por otra parte del sistema
❌ FAIL si módulo existe pero nadie lo usa

### 4.7 Prohibición de Auto-Completado
Prohibido marcar como DONE si: no fue ejecutado en runtime, no fue probado en flujo completo, no fue verificado

### 4.8 Evidencia Obligatoria
Toda tarea completada debe incluir: logs de ejecución / respuesta API / captura de estado DB / evidencia frontend
Sin evidencia → NO DONE

### 4.9 Regla de Revisión
Si una feature ya existe: NO se reescribe, SOLO se mejora si hay fallo real comprobado, si funciona → STABLE

### 4.10 Sistema Saludable
El sistema se considera estable SOLO si:
- pipeline end-to-end funciona
- datos sobreviven reinicio
- ORION toma decisiones con feedback real
- frontend refleja backend real
- no hay mocks activos en producción

## 5. AUTONOMÍA REAL

Un sistema es autónomo solo si:
- Puede ejecutar un flujo completo sin intervención constante
- Puede retomar estado tras reinicio sin pérdida crítica
- Puede decidir próximos pasos basados en estado interno
- Puede ignorar redundancia o instrucciones repetidas si ya están resueltas
- Puede detener trabajo innecesario

## 6. ROLES DE AGENTES

### OpenCode
- Ejecuta tareas técnicas
- Aplica cambios en código
- No decide arquitectura
- No redefine sistema
- No duplica lógica existente

### Cline
- Asistente de iteración
- Puede sugerir cambios
- Puede proponer mejoras
- No puede forzar cambios destructivos

### ORION (núcleo lógico del sistema)
- Prioriza acciones
- Evalúa impacto
- Detecta redundancia
- Recomienda siguiente acción óptima
- Aprende de outcomes
- ORION NO escribe código directamente sin validación del contexto existente

## 7. SISTEMA DE VERDAD

La única fuente de verdad del sistema es: **`/.ai/`**

Todo lo demás es derivado, cache o vista.

Si hay conflicto entre código, documentación o memoria del agente → gana `.ai/`

OpenCode es un ejecutor, no un decisor. Nunca implementar lógica duplicada. Siempre validar existencia antes de crear.

## 8. DEFINICIÓN DE PROGRESO REAL

El progreso real NO es: agregar features, aumentar complejidad, expandir módulos.

El progreso real ES: cerrar loops completos funcionales, persistencia real de datos, reducción de intervención humana, incremento de resultados reales (findings/reportes/payouts).

## 9. FILOSOFÍA DE EVOLUCIÓN

CATEYE no crece por expansión. CATEYE crece por **consolidación**.

Cada nueva feature debe responder: ¿esto elimina trabajo humano o solo agrega complejidad?
Si no elimina trabajo humano → no se prioriza.

Si el sistema está en duda entre hacer más o estabilizar lo existente → siempre estabilizar lo existente.

## 10. REGLAS DE CONDUCTA

- **No destruir funcionalidades estables**: Si algo funciona en producción, no reemplazarlo sin una razón técnica demostrable.
- **No duplicar módulos**: Siempre reutilizar código existente. Buscar primero.
- **Construir incrementalmente**: Cada cambio debe acercar el proyecto a un producto terminado.
- **Preservar compatibilidad**: No romper integraciones existentes.
- **Documentar cambios**: Toda modificación relevante debe actualizar la documentación en `.ai/`.
- **Verificar antes de afirmar**: No asumir que algo funciona. Localizar el código, los tests, y las referencias.
- **Refactorizar solo con beneficio técnico demostrable**: No refactorizar por estética.

## 11. FORMATO DE EVIDENCIA

Cuando registres una verificación en COMPLETED_FEATURES.json, incluye:
- Archivos fuente donde reside la implementación
- Tests asociados (archivo:linea)
- Dependencias y módulos relacionados
- Fecha de la revisión
- Nivel de integración (standalone / integrado / producción)

## 12. SOBRE ESTE DOCUMENTO

- Este archivo NO debe modificarse sin consenso.
- Cualquier cambio debe registrarse en DECISIONS.md con justificación.
- Todos los agentes deben leerlo al inicio de cada sesión.
