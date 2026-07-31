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
- **Status**: Fixed
- **File**: api/routers/dashboard.py
- **Lines**: 180, 187
- **Endpoints**: /keys, /sessions
- **Action**: Endpoints deshabilitados con error 501 (Not Implemented)

### 4. Excesivo Uso de `any` en TypeScript Frontend
- **Status**: Pending
- **File**: frontend/src/lib/api.ts
- **Count**: 20+ usos de `any`
- **Action**: Definir interfaces específicas para cada respuesta de API

### 5. Wildcard Imports con `import *`
- **Status**: Pending
- **Files**: cores/setup/steps/__init__.py, core/evolution/__init__.py, etc.
- **Action**: Importar explícitamente símbolos necesarios o usar __all__ explícito

### 6. Type Checking Deshabilitado para Módulos Críticos
- **Status**: Pending
- **File**: pyproject.toml
- **Modules**: cores.agents.financial, cores.agents.memory, cores.agents.coordinator, etc.
- **Action**: Habilitar type checking gradualmente

## MEDIUM Priority Issues

### 7. Excesivos Type Ignore Comments
- **Status**: Pending
- **Count**: 56+ ocurrencias de `# type: ignore`
- **Action**: Revisar y corregir problemas de tipado subyacentes

### 8. console.log en Código Frontend de Producción
- **Status**: Fixed
- **Files**: 
  - ModernNavbar.vue (comentado)
  - SteamBigPictureSplash.vue (comentado)
  - VoiceCommandPanel.vue (comentado)
- **Action**: Removidos o comentados console.logs de producción

### 9. Exception Handling Genérico sin Logging
- **Status**: Pending
- **File**: cores/opportunity/auto_scanner.py
- **Action**: Loggear excepciones con contexto

### 10. Métodos de Agentes con Implementaciones Vacías
- **Status**: Pending
- **Files**: 
  - cores/agents/specialists/orchestrator.py
  - cores/agents/specialists/commander.py
  - cores/agents/specialists/planner.py
- **Action**: Implementar lógica de coordinación o documentar

### 11. Faltan Type Hints en Funciones Públicas
- **Status**: Pending
- **Files**: Múltiples archivos Python
- **Action**: Agregar type hints según PEP 484

## LOW Priority Issues

### 12. Naming Inconsistency - Logger Names
- **Status**: Pending
- **Description**: "ownex.", "cateye.", "catseye."
- **Action**: Estandarizar a "ownex."

### 13. Hardcoded Strings
- **Status**: Pending
- **Files**: Varios archivos
- **Action**: Mover a constantes o configuración

### 14. Duplicate Code en Cloud Backup Providers
- **Status**: Pending
- **File**: cores/cloud_backup/cloud_backup.py
- **Action**: Extraer lógica común a clase base

### 15. Imports No Usados
- **Status**: Pending
- **Files**: Múltiples archivos __init__.py
- **Action**: Revisar necessity o remover

### 16. Parámetro `skipAuth` No Usado
- **Status**: Pending
- **File**: frontend/src/lib/api.ts
- **Action**: Implementar uso o remover parámetro

## Resumen

| Severidad | Cantidad | Status |
|-----------|----------|--------|
| Critical | 2 | 1 documented, 1 false positive |
| High | 4 | 1 fixed, 3 pending |
| Medium | 5 | 1 fixed, 4 pending |
| Low | 5 | 0 fixed, 5 pending |
| **Total** | **16** | **2 fixed, 1 documented, 1 false positive** |

## Prioridades de Arreglo

1. ✅ GCS Backup bug (CRITICAL) - Fixed
2. ✅ Abstract methods with pass (CRITICAL) - False positive, not an issue
3. ✅ TODOs in dashboard.py (HIGH) - Fixed
4. ✅ console.log in frontend (MEDIUM) - Fixed
5. Replace `any` types in frontend (HIGH) - Next
6. Remove wildcard imports (HIGH)
7. Enable type checking gradually (HIGH)
8. Exception handling without logging (MEDIUM)
9. Methods with empty implementations (MEDIUM)
10. Missing type hints (MEDIUM)
