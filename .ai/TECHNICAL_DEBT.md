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
- **Status**: Fixed
- **File**: frontend/src/types/index.ts, frontend/src/lib/api.ts, frontend/src/pages/EnhancedPersonalizationWizard.vue
- **Action**: Definir interfaces específicas para cada respuesta de API (30+ interfaces creadas)
- **Details**: TypeScript type definitions creadas en frontend/src/types/index.ts con todas las interfaces necesarias

### 5. Wildcard Imports con `import *`
- **Status**: Fixed
- **File**: cores/setup/steps/__init__.py
- **Action**: Importar explícitamente símbolos necesarios
- **Details**: Reemplazados 7 wildcard imports con imports explícitos

### 6. Type Checking Deshabilitado para Módulos Críticos
- **Status**: Fixed (gradual)
- **File**: pyproject.toml
- **Modules**: cores.obsidian, cores.wear_os, cores.productivity, cores.onboarding, cores.setup.steps.enhanced_personalization
- **Action**: Habilitar type checking gradualmente (check_untyped_defs, disallow_any_unimported para nuevos módulos)

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
- **Status**: Partially Fixed
- **Files**: cores/obsidian/integration.py (type hints agregados)
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

|| Severidad | Cantidad | Status |
||-----------|----------|--------|
|| Critical | 2 | 1 documented, 1 false positive |
|| High | 4 | 3 fixed, 1 pending |
|| Medium | 5 | 1 fixed, 4 pending |
|| Low | 5 | 0 fixed, 5 pending |
|| **Total** | **16** | **4 fixed, 1 documented, 1 false positive** |

## Prioridades de Arreglo

1. ✅ GCS Backup bug (CRITICAL) - Fixed
2. ✅ Abstract methods with pass (CRITICAL) - False positive, not an issue
3. ✅ TODOs in dashboard.py (HIGH) - Fixed
4. ✅ console.log in frontend (MEDIUM) - Fixed
5. ✅ Replace `any` types in frontend (HIGH) - Fixed
6. ✅ Remove wildcard imports (HIGH) - Fixed
7. ✅ Enable type checking gradually (HIGH) - Fixed (for new modules)
8. Remove excessive type ignore comments (MEDIUM) - Next
9. Exception handling without logging (MEDIUM)
10. Methods with empty implementations (MEDIUM)
11. Missing type hints (MEDIUM) - Partially Fixed
