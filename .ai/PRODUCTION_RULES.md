# Production Rules — Reglas de Producción

## Principio Fundamental

Este proyecto debe converger continuamente hacia un producto terminado. Cada cambio debe acercarlo a producción, no alejarlo.

## Reglas

### 1. No refactorizar por estética
Solo refactorizar cuando exista un beneficio técnico demostrable:
- Mejora de rendimiento medible
- Reducción de complejidad ciclomática
- Eliminación de deuda técnica documentada
- Corrección de bug

### 2. No reemplazar arquitectura estable
Si un módulo está en producción y funcionando:
- NO reescribirlo desde cero
- NO cambiar su interfaz pública sin periodo de migración
- NO cambiar el patrón arquitectónico subyacente

### 3. Solo extender
Cuando una funcionalidad existe pero necesita ampliarse:
- Añadir código nuevo, no modificar el existente
- Preservar compatibilidad hacia atrás
- Usar inyección de dependencias para cambios de comportamiento

### 4. Preservar integraciones
Antes de modificar un módulo, verificar:
- Qué otros módulos lo importan
- Qué tests lo cubren
- Qué endpoints lo exponen
- Qué datos persiste

### 5. Validar antes de mergear
Todo cambio debe pasar:
- Ruff lint
- pytest suite
- Verificación manual del flujo modificado

### 6. Documentar cambios
Toda modificación relevante debe actualizar:
- SESSION_CHECKPOINT.md
- CURRENT_STATE.md (si aplica)
- COMPLETED_FEATURES.json (si es una funcionalidad completa)
- DECISIONS.md (si es una decisión arquitectónica)

### 7. Una responsabilidad por módulo
Si un módulo hace más de una cosa, evaluar si debe dividirse antes de extenderlo.

### 8. Sin secretos en código
- No hardcodear API keys, tokens, o contraseñas
- No commitear archivos de configuración con secretos
- Usar variables de entorno o IdentityVault

### 9. Cero regresiones
Nunca introducir un cambio que rompa funcionalidad existente. Si es inevitable, documentar el breaking change y proveer migración.

### 10. Priorizar seguridad
En caso de conflicto entre una mejora de seguridad y cualquier otra cosa, la seguridad gana siempre.
