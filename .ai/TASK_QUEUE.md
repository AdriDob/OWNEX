# Task Queue — Tareas Pendientes

> Cada tarea DEBE tener evidencia de que no existe ya implementada antes de comenzar.
> Cuando una tarea se completa, se ELIMINA de esta cola.

## Prioridad Alta

### 1. Verificar cobertura de tests para cambios recientes
- **Prioridad**: Alta
- **Impacto**: Garantizar que no hay regresiones
- **Dependencias**: Ninguna
- **Estado**: COMPLETED (359 tests pasan, verificado en sesión jul 2026)

### 2. Completar COMPLETED_FEATURES.json con evidencia
- **Prioridad**: Alta
- **Impacto**: Trazabilidad del proyecto
- **Dependencias**: Tener acceso al código de cada módulo
- **Estado**: COMPLETED (archivo creado con 8 features, verificado en sesión jul 2026)

### 3. Revisar y consolidar documentación dispersa
- **Prioridad**: Alta
- **Impacto**: Fuente de verdad única
- **Dependencias**: .ai/ creado y funcional
- **Estado**: COMPLETED (opencode.json estabilizado, .save eliminado, AGENT_CHARTER.md actualizado con DO-DO-OR-DIE + Verification Loop)

## Prioridad Media

### 4. Unificar 3 sistemas de salud superpuestos
- **Prioridad**: Media
- **Impacto**: Eliminar estado contradictorio
- **Dependencias**: Ninguna
- **Estado**: Pendiente
- **Responsable**: Próximo agente
- **Criterio de finalización**: SystemHealthEngine + HealthMonitor + Watchdog → UnifiedHealthMonitor

### 5. Agregar persistencia a health snapshots
- **Prioridad**: Media
- **Impacto**: Historial de salud sobrevive reinicios
- **Dependencias**: RecoveryStore ya tiene tabla health_snapshots
- **Estado**: Pendiente
- **Responsable**: Próximo agente
- **Criterio de finalización**: Health snapshots persisten en SQLite

### 6. Conectar DuplicateDetector con DedupTracker
- **Prioridad**: Media
- **Impacto**: Consistencia en detección de duplicados
- **Dependencias**: cores/dedup.py existe
- **Estado**: Pendiente
- **Responsable**: Próximo agente
- **Criterio de finalización**: DuplicateDetector usa fingerprints de DedupTracker

## Prioridad Baja

### 7. Mover API keys del frontend al backend
- **Prioridad**: Baja
- **Impacto**: Seguridad de credenciales
- **Dependencias**: IdentityVault funcional
- **Estado**: Pendiente
- **Responsable**: Próximo agente
- **Criterio de finalización**: API keys almacenadas en IdentityVault, no en sessionStorage

### 8. Auditoría de dependencias no utilizadas
- **Prioridad**: Baja
- **Impacto**: Mantenibilidad
- **Dependencias**: Ninguna
- **Estado**: Pendiente
- **Responsable**: Próximo agente
- **Criterio de finalización**: Lista de dependencias no utilizadas identificadas y evaluadas para eliminación
