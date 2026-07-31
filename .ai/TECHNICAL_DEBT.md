# Technical Debt - OWNEX OMEGA

Documentación de deuda técnica y areas de mejora identificadas.

## CRITICAL Issues

### 1. Import Inconsistency: core/ vs cores/
- **Status**: Documented, deferred
- **Description**: El código base tiene inconsistencia fundamental entre imports `from core.` y `from cores.`
- **Impact**: Potenciales ImportError en producción si la estructura cambia
- **Files afectados**: api/main.py (37 imports from core/), cores/setup/steps/__init__.py
- **Decision**: Ambos directorios existen y funcionan actualmente. La migración completa requiere análisis profundo.
- **Planned action**: Estandarizar a `cores/` en un refactor separado (prioridad baja-media)
- **Note**: Este es un legacy issue que necesita más investigación antes de cambiar

### 2. Abstract Methods con `pass` - False Positive
- **Status**: Not an issue
- **Description**: Las clases abstractas (STTProvider, TTSProvider, etc.) tienen métodos con `@abstractmethod` y `pass`
- **Analysis**: Esto es el comportamiento normal de ABC en Python. Las clases hijas (LocalSTTProvider, LocalTTSProvider) implementan estos métodos correctamente.
- **Decision**: No requiere acción. Los métodos abstractos están correctamente definidos y las implementaciones concretas funcionan.

## HIGH Priority Issues

### 3. TODOs sin Implementar en Código de Producción
- **Status**: Pending
- **File**: api/routers/dashboard.py
- **Lines**: 180, 187
- **Endpoints**: /keys, /sessions
- **Action**: Implementar funcionalidad o remover endpoints

### 3. Excesivo Uso de `any` en TypeScript Frontend
- **Status**: Pending
- **File**: frontend/src/lib/api.ts
- **Count**: 20+ usos de `any`
- **Action**: Definir interfaces específicas para cada respuesta de API

### 4. Wildcard Imports con `import *`
- **Status**: Pending
- **Files**: cores/setup/steps/__init__.py, core/evolution/__init__.py, etc.
- **Action**: Importar explícitamente símbolos necesarios o usar __all__ explícito

### 5. Type Checking Deshabilitado para Módulos Críticos
- **Status**: Pending
- **File**: pyproject.toml
- **Modules**: cores.agents.financial, cores.agents.memory, cores.agents.coordinator, etc.
- **Action**: Habilitar type checking gradualmente

## MEDIUM Priority Issues

### 6. Excesivos Type Ignore Comments
- **Status**: Pending
- **Count**: 56+ ocurrencias de `# type: ignore`
- **Action**: Revisar y corregir problemas de tipado subyacentes

### 7. console.log en Código Frontend de Producción
- **Status**: Pending
- **Files**: ModernNavbar.vue, SteamBigPictureSplash.vue, VoiceCommandPanel.vue
- **Action**: Remover o usar sistema de logging condicional

### 8. Exception Handling Genérico sin Logging
- **Status**: Pending
- **File**: cores/opportunity/auto_scanner.py
- **Action**: Loggear excepciones con contexto

### 9. Métodos de Agentes con Implementaciones Vacías
- **Status**: Pending
- **Files**: 
  - cores/agents/specialists/orchestrator.py
  - cores/agents/specialists/commander.py
  - cores/agents/specialists/planner.py
- **Action**: Implementar lógica de coordinación o documentar

### 10. Faltan Type Hints en Funciones Públicas
- **Status**: Pending
- **Files**: Múltiples archivos Python
- **Action**: Agregar type hints según PEP 484

## LOW Priority Issues

### 11. Naming Inconsistency - Logger Names
- **Status**: Pending
- **Description**: "ownex.", "cateye.", "catseye."
- **Action**: Estandarizar a "ownex."

### 12. Hardcoded Strings
- **Status**: Pending
- **Files**: Varios archivos
- **Action**: Mover a constantes o configuración

### 13. Duplicate Code en Cloud Backup Providers
- **Status**: Pending
- **File**: cores/cloud_backup/cloud_backup.py
- **Action**: Extraer lógica común a clase base

### 14. Imports No Usados
- **Status**: Pending
- **Files**: Múltiples archivos __init__.py
- **Action**: Revisar necessity o remover

### 15. Parámetro `skipAuth` No Usado
- **Status**: Pending
- **File**: frontend/src/lib/api.ts
- **Action**: Implementar uso o remover parámetro

## Resumen

| Severidad | Cantidad | Status |
|-----------|----------|--------|
| Critical | 2 | 1 fixed, 1 documented (1 false positive removed) |
| High | 4 | 0 fixed |
| Medium | 5 | 0 fixed |
| Low | 5 | 0 fixed |
| **Total** | **16** | **1 fixed, 1 documented** |

## Prioridades de Arreglo

1. ✅ GCS Backup bug (CRITICAL) - Fixed
2. ✅ Abstract methods with pass (CRITICAL) - False positive, not an issue
3. TODOs in dashboard.py (HIGH) - Next
4. Replace `any` types in frontend (HIGH)
5. Remove wildcard imports (HIGH)
6. Enable type checking gradually (HIGH)
